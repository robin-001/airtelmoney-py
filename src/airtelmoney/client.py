"""Core HTTP client for the Airtel Money Uganda Open APIs."""

from __future__ import annotations

import logging
import json
import os
import time
from typing import Any, Dict, Mapping, Optional

import requests

from .exceptions import (
    AirtelAPIError,
    AirtelAuthError,
    AirtelConfigError,
)

#: Default Airtel Open API base URLs.
STAGING_URL = "https://openapiuat.airtel.africa"
PRODUCTION_URL = "https://openapi.airtel.africa"

_TOKEN_PATH = "/auth/oauth2/token"
_ENCRYPTION_KEY_PATH = "/v1/rsa/encryption-keys"

# Refresh the bearer token this many seconds before it actually expires.
_TOKEN_EXPIRY_SKEW = 15


class AirtelMoney:
    """Client for the Airtel Money Uganda Open APIs.

    Example:
        >>> from airtelmoney import AirtelMoney
        >>> client = AirtelMoney(
        ...     client_id="...",
        ...     client_secret="...",
        ...     environment="staging",
        ... )
        >>> client.collection.payment(reference="Order #1", msisdn="752604392", amount=1000)

    Args:
        client_id: Airtel application client id.
        client_secret: Airtel application client secret.
        environment: ``"staging"`` (default) or ``"production"``. Ignored if
            ``base_url`` is provided.
        base_url: Explicit base URL, overriding ``environment``.
        country: Default ``X-Country`` header value (default ``"UG"``).
        currency: Default ``X-Currency`` header value (default ``"UGX"``).
        timeout: Per-request timeout in seconds.
        session: Optional pre-configured :class:`requests.Session`.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        environment: str = "staging",
        base_url: Optional[str] = None,
        country: str = "UG",
        currency: str = "UGX",
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.logger = logging.getLogger('http')
        if not client_id or not client_secret:
            raise AirtelConfigError("client_id and client_secret are required.")

        if base_url is None:
            env = (environment or "").lower()
            if env in ("staging", "uat", "sandbox", "test"):
                base_url = STAGING_URL
            elif env in ("production", "prod", "live"):
                base_url = PRODUCTION_URL
            else:
                raise AirtelConfigError(
                    f"Unknown environment {environment!r}; use 'staging' or 'production', "
                    "or pass base_url explicitly."
                )

        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self.country = country
        self.currency = currency
        self.timeout = timeout
        self.session = session or requests.Session()

        self._token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._encryption_key: Optional[str] = None
        self._encryption_key_expiry: Optional[str] = None

        # Lazily imported to avoid circular imports.
        from .resources import (
            AccountAPI,
            CollectionAPI,
            DisbursementAPI,
            KYCAPI,
        )

        self.collection = CollectionAPI(self)
        self.disbursement = DisbursementAPI(self)
        self.kyc = KYCAPI(self)
        self.account = AccountAPI(self)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_credentials_file(
        cls, path: str, *, environment: str = "staging", **kwargs: Any
    ) -> "AirtelMoney":
        """Build a client from a JSON credentials file.

        The file should contain ``airtel_client_id`` and ``airtel_client_secret``
        (and optionally ``staging_url`` / ``prod_url``).
        """
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        client_id = data.get("airtel_client_id") or data.get("client_id")
        client_secret = data.get("airtel_client_secret") or data.get("client_secret")
        if not client_id or not client_secret:
            raise AirtelConfigError(
                "Credentials file must contain airtel_client_id and airtel_client_secret."
            )

        base_url = kwargs.pop("base_url", None)
        if base_url is None:
            env = (environment or "").lower()
            if env in ("production", "prod", "live"):
                base_url = data.get("prod_url")
            else:
                base_url = data.get("staging_url")

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment,
            base_url=base_url,
            **kwargs,
        )

    @classmethod
    def from_env(
        cls, *, dotenv_path: Optional[str] = None, **kwargs: Any
    ) -> "AirtelMoney":
        """Build a client from environment variables (and an optional .env file).

        Reads the following variables:

        - ``AIRTEL_CLIENT_ID`` (required)
        - ``AIRTEL_CLIENT_SECRET`` (required)
        - ``AIRTEL_ENVIRONMENT`` (``staging`` | ``production``, default ``staging``)
        - ``AIRTEL_BASE_URL`` (optional, overrides environment)
        - ``AIRTEL_COUNTRY`` (default ``UG``)
        - ``AIRTEL_CURRENCY`` (default ``UGX``)

        If ``python-dotenv`` is installed, a ``.env`` file is loaded first.
        Any keyword arguments override the values read from the environment.
        """
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=dotenv_path)
        except ImportError:
            if dotenv_path is not None:
                raise AirtelConfigError(
                    "dotenv_path was given but python-dotenv is not installed. "
                    "Install it with `pip install airtelmoney-py[env]`."
                )

        client_id = kwargs.pop("client_id", None) or os.getenv("AIRTEL_CLIENT_ID")
        client_secret = kwargs.pop("client_secret", None) or os.getenv(
            "AIRTEL_CLIENT_SECRET"
        )
        if not client_id or not client_secret:
            raise AirtelConfigError(
                "AIRTEL_CLIENT_ID and AIRTEL_CLIENT_SECRET must be set in the "
                "environment or a .env file."
            )

        environment = kwargs.pop("environment", None) or os.getenv(
            "AIRTEL_ENVIRONMENT", "staging"
        )
        base_url = kwargs.pop("base_url", None) or os.getenv("AIRTEL_BASE_URL")
        country = kwargs.pop("country", None) or os.getenv("AIRTEL_COUNTRY", "UG")
        currency = kwargs.pop("currency", None) or os.getenv("AIRTEL_CURRENCY", "UGX")

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment,
            base_url=base_url,
            country=country,
            currency=currency,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def get_access_token(self, *, force_refresh: bool = False) -> str:
        """Return a valid bearer token, fetching/refreshing as needed."""
        if (
            not force_refresh
            and self._token is not None
            and time.time() < self._token_expiry
        ):
            return self._token

        url = self.base_url + _TOKEN_PATH
        try:
            resp = self.session.post(
                url,
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
                headers={"Content-Type": "application/json", "Accept": "*/*"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AirtelAuthError(f"Token request failed: {exc}") from exc

        try:
            body = resp.json()
        except ValueError:
            body = {}

        if resp.status_code != 200 or "access_token" not in body:
            raise AirtelAuthError(
                body.get("error_description")
                or body.get("error")
                or f"Failed to obtain access token (HTTP {resp.status_code})."
            )

        self._token = body["access_token"]
        expires_in = int(body.get("expires_in", 180))
        self._token_expiry = time.time() + max(expires_in - _TOKEN_EXPIRY_SKEW, 0)
        return self._token

    # ------------------------------------------------------------------
    # Encryption key
    # ------------------------------------------------------------------
    def get_encryption_key(self, *, force_refresh: bool = False) -> str:
        """Fetch (and cache) the RSA public key for this consumer.

        Returns the base64 DER public key string used for signing and PIN
        encryption.
        """
        if not force_refresh and self._encryption_key is not None:
            return self._encryption_key

        body = self.request(
            "GET",
            _ENCRYPTION_KEY_PATH,
            include_country_currency=True,
            auth=True,
        )
        data = body.get("data") or {}
        key = data.get("key")
        if not key:
            status = body.get("status") or {}
            detail = status.get("message") or body.get("error_description")
            raise AirtelAPIError(
                "Encryption key not present in response"
                + (f": {detail}" if detail else f". Full response: {body}"),
                response_code=status.get("response_code"),
                payload=body,
            )
        self._encryption_key = key
        self._encryption_key_expiry = data.get("valid_upto")
        return key

    # ------------------------------------------------------------------
    # Low-level request
    # ------------------------------------------------------------------
    def _build_headers(
        self,
        *,
        auth: bool,
        include_country_currency: bool,
        extra: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if include_country_currency:
            headers["X-Country"] = self.country
            headers["X-Currency"] = self.currency
        if auth:
            headers["Authorization"] = f"Bearer {self.get_access_token()}"
        if extra:
            headers.update(extra)
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        raw_body: Optional[str] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        auth: bool = True,
        include_country_currency: bool = False,
    ) -> Dict[str, Any]:
        """Send a request and return the decoded JSON body.

        Raises:
            AirtelAPIError: on HTTP >= 400 or an explicit error body.
        """
        url = self.base_url + path

        kwargs: Dict[str, Any] = {"timeout": self.timeout, "params": params}
        body_content_type = raw_body is not None or json_body is not None
        if raw_body is not None:
            kwargs["data"] = raw_body.encode("utf-8")
        elif json_body is not None:
            kwargs["json"] = json_body

        # The bearer token is validated (and refreshed when expired) before every
        # request via get_access_token(). If the server still rejects it with a
        # 401 (e.g. the token was revoked before its expiry), force a refresh and
        # retry the request once.
        attempted_refresh = False
        while True:
            request_headers = self._build_headers(
                auth=auth,
                include_country_currency=include_country_currency,
                extra=headers,
            )
            if body_content_type:
                request_headers.setdefault("Content-Type", "application/json")

            try:
                resp = self.session.request(
                    method, url, headers=request_headers, **kwargs
                )
                self.logger.debug(f"Request to {path} returned status {resp.status_code}")
                self.logger.debug(f"Request headers: {request_headers}")
                self.logger.debug(f"Request body: {kwargs.get('data') or kwargs.get('json')}")
                self.logger.debug(f"Response body: {resp.text}")
            except requests.RequestException as exc:
                raise AirtelAPIError(f"Request to {path} failed: {exc}") from exc

            if resp.status_code == 401 and auth and not attempted_refresh:
                attempted_refresh = True
                self.get_access_token(force_refresh=True)
                continue

            try:
                body = resp.json()
            except ValueError:
                body = {"raw": resp.text}

            self._raise_for_response(resp.status_code, body)
            return body

    @staticmethod
    def _raise_for_response(status_code: int, body: Any) -> None:
        status = body.get("status") if isinstance(body, dict) else None
        response_code = status.get("response_code") if isinstance(status, dict) else None

        if status_code >= 400:
            message = ""
            if isinstance(body, dict):
                message = (
                    body.get("error_description")
                    or body.get("error")
                    or body.get("status_message")
                    or (status or {}).get("message")
                    or ""
                )
            raise AirtelAPIError(
                message or "Airtel Money API request failed.",
                status_code=status_code,
                response_code=response_code,
                payload=body,
            )
