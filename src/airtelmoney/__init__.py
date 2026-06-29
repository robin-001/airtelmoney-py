"""airtelmoney-ug: Python client for the Airtel Money Uganda Open APIs.

Quick start::

    from airtelmoney import AirtelMoney

    client = AirtelMoney(
        client_id="...",
        client_secret="...",
        environment="staging",  # or "production"
    )

    # Collections: request a USSD-push payment
    res = client.collection.payment(
        reference="Order #123",
        msisdn="752604392",
        amount=1000,
    )

    # Disbursements: send money (PIN is RSA-encrypted automatically)
    client.disbursement.payment(
        msisdn="752604392", amount=500, reference="payout-1", pin="1234",
    )

    # KYC + Account
    client.kyc.user_enquiry("256752604392")
    client.account.balance()
"""

from .client import PRODUCTION_URL, STAGING_URL, AirtelMoney
from .encryption import SignedRequest, encrypt_pin, rsa_encrypt, sign_payload
from .errors import (
    RESPONSE_CODES,
    ResponseCode,
    describe,
    is_pending,
    is_success,
)
from .exceptions import (
    AirtelAPIError,
    AirtelAuthError,
    AirtelConfigError,
    AirtelEncryptionError,
    AirtelMoneyError,
)

__version__ = "1.0.5"

__all__ = [
    "AirtelMoney",
    "STAGING_URL",
    "PRODUCTION_URL",
    "sign_payload",
    "rsa_encrypt",
    "encrypt_pin",
    "SignedRequest",
    "RESPONSE_CODES",
    "ResponseCode",
    "describe",
    "is_success",
    "is_pending",
    "AirtelMoneyError",
    "AirtelConfigError",
    "AirtelAuthError",
    "AirtelEncryptionError",
    "AirtelAPIError",
    "__version__",
]
