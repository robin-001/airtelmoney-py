"""Tests for the AirtelMoney HTTP client using mocked responses."""

import base64
import time

import pytest
import responses
from Crypto.PublicKey import RSA

from airtelmoney import AirtelAPIError, AirtelMoney, STAGING_URL
from airtelmoney.errors import describe, is_success

TOKEN_URL = STAGING_URL + "/auth/oauth2/token"


def _public_key_b64():
    key = RSA.generate(2048)
    return base64.b64encode(key.publickey().export_key(format="DER")).decode()


@pytest.fixture
def client():
    return AirtelMoney(client_id="id", client_secret="secret", environment="staging")


def _mock_token():
    responses.add(
        responses.POST,
        STAGING_URL + "/auth/oauth2/token",
        json={"token_type": "bearer", "access_token": "tok123", "expires_in": 180},
        status=200,
    )


@responses.activate
def test_get_access_token_cached(client):
    _mock_token()
    assert client.get_access_token() == "tok123"
    # Second call should not hit the network again (cached).
    assert client.get_access_token() == "tok123"
    assert len(responses.calls) == 1


@responses.activate
def test_balance_enquiry(client):
    _mock_token()
    responses.add(
        responses.GET,
        STAGING_URL + "/standard/v1/users/balance",
        json={
            "data": {"balance": "37,600.00", "currency": "UGX", "account_status": "Active"},
            "status": {"code": "200", "response_code": "DP02100000001", "success": True},
        },
        status=200,
    )
    body = client.account.balance()
    assert body["data"]["balance"] == "37,600.00"
    assert is_success(body["status"]["response_code"])


@responses.activate
def test_disbursement_encrypts_pin(client):
    _mock_token()
    responses.add(
        responses.GET,
        STAGING_URL + "/v1/rsa/encryption-keys",
        json={"data": {"key_id": 1, "key": _public_key_b64()}, "status": {"success": True}},
        status=200,
    )
    responses.add(
        responses.POST,
        STAGING_URL + "/standard/v2/disbursements/",
        json={"data": {"transaction": {"id": "x", "status": "TS"}},
              "status": {"response_code": "DP00900001001", "success": True}},
        status=200,
    )
    body = client.disbursement.payment(
        msisdn="752604392", amount=1000, reference="ref-1", pin="1234",
        transaction_id="abc",
    )
    assert body["data"]["transaction"]["status"] == "TS"
    # The PIN must have been encrypted (not sent as plain "1234").
    disburse_call = responses.calls[-1]
    assert '"1234"' not in disburse_call.request.body.decode()


@responses.activate
def test_collection_payment_signs(client):
    _mock_token()
    responses.add(
        responses.GET,
        STAGING_URL + "/v1/rsa/encryption-keys",
        json={"data": {"key": _public_key_b64()}, "status": {"success": True}},
        status=200,
    )
    responses.add(
        responses.POST,
        STAGING_URL + "/merchant/v2/payments/",
        json={"data": {"transaction": {"id": "abc", "status": "SUCCESS"}},
              "status": {"response_code": "DP00800001001", "success": True}},
        status=200,
    )
    client.collection.payment(reference="r", msisdn="752604392", amount=1000,
                              transaction_id="abc")
    pay_call = responses.calls[-1]
    assert "x-signature" in pay_call.request.headers
    assert "x-key" in pay_call.request.headers


@responses.activate
def test_http_error_raises(client):
    _mock_token()
    responses.add(
        responses.GET,
        STAGING_URL + "/standard/v1/payments/12345",
        json={"error_description": "The access token is invalid or has expired",
              "error": "invalid_token"},
        status=401,
    )
    with pytest.raises(AirtelAPIError) as exc:
        client.collection.enquiry("12345")
    assert exc.value.status_code == 401


def test_describe_known_code():
    info = describe("DP00800001026")
    assert info is not None
    assert info.reason == "Forbidden"


def test_from_env(monkeypatch):
    monkeypatch.setenv("AIRTEL_CLIENT_ID", "env-id")
    monkeypatch.setenv("AIRTEL_CLIENT_SECRET", "env-secret")
    monkeypatch.setenv("AIRTEL_ENVIRONMENT", "production")
    monkeypatch.setenv("AIRTEL_CURRENCY", "UGX")
    monkeypatch.setenv("AIRTEL_COUNTRY", "UG")

    c = AirtelMoney.from_env()
    assert c.client_id == "env-id"
    assert c.client_secret == "env-secret"
    assert c.base_url == "https://openapiuat.airtel.ug"
    assert c.currency == "UGX"


def test_from_env_missing_raises(monkeypatch):
    monkeypatch.delenv("AIRTEL_CLIENT_ID", raising=False)
    monkeypatch.delenv("AIRTEL_CLIENT_SECRET", raising=False)
    with pytest.raises(Exception):
        AirtelMoney.from_env()


@responses.activate
def test_token_refreshes_after_expiry(client):
    responses.add(responses.POST, TOKEN_URL,
                  json={"access_token": "t1", "expires_in": 180}, status=200)
    responses.add(responses.POST, TOKEN_URL,
                  json={"access_token": "t2", "expires_in": 180}, status=200)

    assert client.get_access_token() == "t1"
    # Simulate the 180s token having expired.
    client._token_expiry = time.time() - 1
    assert client.get_access_token() == "t2"
    assert len(responses.calls) == 2


@responses.activate
def test_401_triggers_reauth_and_retry(client):
    # Two tokens: the stale one, then the refreshed one after the 401.
    responses.add(responses.POST, TOKEN_URL,
                  json={"access_token": "stale", "expires_in": 180}, status=200)
    responses.add(responses.POST, TOKEN_URL,
                  json={"access_token": "fresh", "expires_in": 180}, status=200)

    balance_url = STAGING_URL + "/standard/v1/users/balance"
    # First call: token rejected. Second call (after refresh): success.
    responses.add(responses.GET, balance_url,
                  json={"error": "invalid_token"}, status=401)
    responses.add(responses.GET, balance_url,
                  json={"data": {"balance": "100.00"},
                        "status": {"response_code": "DP02100000001", "success": True}},
                  status=200)

    body = client.account.balance()
    assert body["data"]["balance"] == "100.00"

    # The bearer token must have been refreshed and the failed request retried.
    token_calls = [c for c in responses.calls if c.request.url == TOKEN_URL]
    assert len(token_calls) == 2
    last_balance = [c for c in responses.calls if c.request.url == balance_url][-1]
    assert last_balance.request.headers["Authorization"] == "Bearer fresh"


@responses.activate
def test_401_retried_only_once(client):
    responses.add(responses.POST, TOKEN_URL,
                  json={"access_token": "t1", "expires_in": 180}, status=200)
    responses.add(responses.POST, TOKEN_URL,
                  json={"access_token": "t2", "expires_in": 180}, status=200)
    responses.add(responses.GET, STAGING_URL + "/standard/v1/users/balance",
                  json={"error": "invalid_token"}, status=401)

    with pytest.raises(AirtelAPIError) as exc:
        client.account.balance()
    assert exc.value.status_code == 401
