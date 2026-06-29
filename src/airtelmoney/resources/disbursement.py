"""Disbursement APIs: send money to a payee, transaction enquiry."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from ..encryption import encrypt_pin
from .base import BaseAPI

_DISBURSE_PATH = "/standard/v2/disbursements/"
_ENQUIRY_PATH = "/standard/v1/disbursements/{transaction_id}"


class DisbursementAPI(BaseAPI):
    """Send money from your wallet to subscribers (Disbursements)."""

    def payment(
        self,
        *,
        msisdn: str,
        amount: Union[int, float, str],
        reference: str,
        pin: Optional[Union[str, int]] = None,
        encrypted_pin: Optional[str] = None,
        transaction_id: Optional[str] = None,
        public_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Disburse money to a payee.

        Provide either ``pin`` (plain PIN; it will be RSA-encrypted with the
        consumer public key) or a pre-computed ``encrypted_pin``.

        Args:
            msisdn: Payee phone number.
            amount: Amount to disburse.
            reference: Your reference for the transaction.
            pin: Plain disbursement PIN (encrypted automatically).
            encrypted_pin: Already RSA-encrypted, base64 PIN.
            transaction_id: Unique transaction id. Generated if omitted.
            public_key: RSA public key for PIN encryption. Fetched if omitted.
        """
        if not encrypted_pin:
            if pin is None:
                raise ValueError("Provide either pin or encrypted_pin.")
            key = public_key or self._client.get_encryption_key()
            encrypted_pin = encrypt_pin(key, pin)

        txn_id = transaction_id or self._new_transaction_id()
        payload = {
            "payee": {"msisdn": str(msisdn)},
            "reference": reference,
            "pin": encrypted_pin,
            "transaction": {"amount": amount, "id": txn_id},
        }
        return self._client.request(
            "POST",
            _DISBURSE_PATH,
            json_body=payload,
            include_country_currency=True,
            auth=True,
        )

    def enquiry(self, transaction_id: str) -> Dict[str, Any]:
        """Get the status of a disbursement by your transaction id."""
        return self._client.request(
            "GET",
            _ENQUIRY_PATH.format(transaction_id=transaction_id),
            include_country_currency=True,
            auth=True,
        )

    transaction_enquiry = enquiry
