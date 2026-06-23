"""Collection (merchant) APIs: USSD push payment, enquiry, refund, callbacks."""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any, Dict, Optional, Union

from ..encryption import sign_payload
from .base import BaseAPI

_PAYMENT_PATH = "/merchant/v2/payments/"
_ENQUIRY_PATH = "/standard/v1/payments/{transaction_id}"
_REFUND_PATH = "/standard/v1/payments/refund"


class CollectionAPI(BaseAPI):
    """Accept money from customers (Collections)."""

    def payment(
        self,
        *,
        reference: str,
        msisdn: str,
        amount: Union[int, float, str],
        transaction_id: Optional[str] = None,
        country: Optional[str] = None,
        currency: Optional[str] = None,
        sign: bool = True,
        public_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request a USSD-push payment from a subscriber.

        The subscriber is prompted on their handset to authorise the payment.

        Args:
            reference: Free-text reference shown for the transaction.
            msisdn: Subscriber phone number (without country code prefix).
            amount: Transaction amount.
            transaction_id: Unique transaction id. Generated if omitted.
            country / currency: Override the client defaults.
            sign: When ``True`` (default) the payload is signed and the
                ``x-signature`` / ``x-key`` headers are attached.
            public_key: RSA public key to sign with. Fetched automatically if
                omitted.

        Returns:
            The decoded API response. ``data.transaction.id`` echoes the id you
            supplied; keep it for the enquiry call.
        """
        country = country or self._client.country
        currency = currency or self._client.currency
        txn_id = transaction_id or self._new_transaction_id()

        payload = {
            "reference": reference,
            "subscriber": {
                "country": country,
                "currency": currency,
                "msisdn": str(msisdn),
            },
            "transaction": {
                "amount": amount,
                "country": country,
                "currency": currency,
                "id": txn_id,
            },
        }

        headers: Dict[str, str] = {}
        raw_body: Optional[str] = None
        if sign:
            key = public_key or self._client.get_encryption_key()
            signed = sign_payload(key, payload)
            headers.update(signed.headers)
            raw_body = signed.payload

        if raw_body is not None:
            return self._client.request(
                "POST",
                _PAYMENT_PATH,
                raw_body=raw_body,
                headers=headers,
                include_country_currency=True,
                auth=True,
            )
        return self._client.request(
            "POST",
            _PAYMENT_PATH,
            json_body=payload,
            include_country_currency=True,
            auth=True,
        )

    def enquiry(self, transaction_id: str) -> Dict[str, Any]:
        """Get the status of a collection transaction by your transaction id."""
        return self._client.request(
            "GET",
            _ENQUIRY_PATH.format(transaction_id=transaction_id),
            auth=True,
        )

    # Convenience alias matching the collection naming.
    transaction_enquiry = enquiry

    def refund(self, airtel_money_id: str) -> Dict[str, Any]:
        """Make a full refund for a previously successful transaction.

        Args:
            airtel_money_id: The ``airtel_money_id`` returned for the original
                transaction.
        """
        return self._client.request(
            "POST",
            _REFUND_PATH,
            json_body={"transaction": {"airtel_money_id": airtel_money_id}},
            include_country_currency=True,
            auth=True,
        )

    # ------------------------------------------------------------------
    # Callback verification helpers
    # ------------------------------------------------------------------
    @staticmethod
    def verify_callback_hash(payload: Dict[str, Any], secret: str) -> bool:
        """Verify the ``hash`` of an authenticated callback payload.

        Airtel signs authenticated callbacks with an HMAC-SHA256 of the
        transaction object (compact JSON) using your client secret, base64
        encoded. This compares the supplied ``hash`` against a freshly computed
        one in constant time.

        Args:
            payload: The full decoded callback body (must contain ``transaction``
                and ``hash``).
            secret: Your application client secret.
        """
        import json

        received = payload.get("hash")
        if not received:
            return False
        transaction = payload.get("transaction", {})
        message = json.dumps(transaction, separators=(",", ":")).encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
        expected = base64.b64encode(digest).decode("ascii")
        return hmac.compare_digest(expected, received)
