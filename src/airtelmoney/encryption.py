"""Request signing and RSA encryption helpers for Airtel Money.

Airtel uses a "message signing" scheme for write APIs:

1. Generate a random 256-bit AES key and a 128-bit IV.
2. Base64 encode the key and IV.
3. Fetch the consumer's RSA public key from the encryption-keys API.
4. Encrypt the JSON payload with ``AES/CBC/PKCS5Padding`` using the key/IV.
   The base64 result is sent as the ``x-signature`` header.
5. Concatenate ``key:iv`` (both base64) separated by a colon.
6. RSA-encrypt ``key:iv`` with the public key. The base64 result is sent as
   the ``x-key`` header.

The same RSA public key is used to encrypt the disbursement ``pin``.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Mapping, Tuple, Union

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad

from .exceptions import AirtelEncryptionError

AES_KEY_BYTES = 32  # 256-bit key
AES_IV_BYTES = 16  # 128-bit IV


def _load_public_key(public_key: str) -> RSA.RsaKey:
    """Load an RSA public key supplied as base64 DER or PEM text."""
    try:
        key_text = public_key.strip()
        if "-----BEGIN" in key_text:
            return RSA.import_key(key_text)
        # The API returns a bare base64 DER (X.509 SubjectPublicKeyInfo) string.
        der = base64.b64decode(key_text)
        return RSA.import_key(der)
    except Exception as exc:  # noqa: BLE001 - re-raise as library error
        raise AirtelEncryptionError(f"Invalid RSA public key: {exc}") from exc


def rsa_encrypt(public_key: str, plaintext: Union[str, bytes]) -> str:
    """RSA-encrypt ``plaintext`` with PKCS#1 v1.5 and return base64 text."""
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    key = _load_public_key(public_key)
    cipher = PKCS1_v1_5.new(key)
    try:
        encrypted = cipher.encrypt(plaintext)
    except Exception as exc:  # noqa: BLE001
        raise AirtelEncryptionError(f"RSA encryption failed: {exc}") from exc
    return base64.b64encode(encrypted).decode("ascii")


def encrypt_pin(public_key: str, pin: Union[str, int]) -> str:
    """Encrypt a disbursement PIN with the RSA public key.

    Returns the base64 ciphertext to place in the ``pin`` body field.
    """
    return rsa_encrypt(public_key, str(pin))


@dataclass
class SignedRequest:
    """Result of signing a payload.

    Attributes:
        payload: The exact JSON string that must be sent as the request body.
        x_signature: Value for the ``x-signature`` header.
        x_key: Value for the ``x-key`` header.
        aes_key: Base64 AES key (useful for debugging/tests).
        aes_iv: Base64 AES IV (useful for debugging/tests).
    """

    payload: str
    x_signature: str
    x_key: str
    aes_key: str
    aes_iv: str

    @property
    def headers(self) -> dict:
        """The signing headers to merge into the request."""
        return {"x-signature": self.x_signature, "x-key": self.x_key}


def _aes_encrypt(payload: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(payload, AES.block_size))


def sign_payload(
    public_key: str,
    payload: Union[str, bytes, Mapping[str, Any]],
    *,
    aes_key: Union[bytes, None] = None,
    aes_iv: Union[bytes, None] = None,
) -> SignedRequest:
    """Sign ``payload`` and produce the ``x-signature`` / ``x-key`` headers.

    Args:
        public_key: The RSA public key (base64 DER or PEM) for the consumer.
        payload: A mapping (serialised to compact JSON), or a pre-serialised
            JSON ``str``/``bytes``. When a mapping is given, the exact JSON
            string used for signing is returned on :attr:`SignedRequest.payload`
            and **must** be the body actually sent, otherwise the signature
            will not match server-side.
        aes_key: Optional 32-byte AES key (random if omitted). For tests.
        aes_iv: Optional 16-byte IV (random if omitted). For tests.
    """
    if isinstance(payload, Mapping):
        payload_str = json.dumps(payload, separators=(",", ":"))
    elif isinstance(payload, bytes):
        payload_str = payload.decode("utf-8")
    else:
        payload_str = payload

    key = aes_key if aes_key is not None else get_random_bytes(AES_KEY_BYTES)
    iv = aes_iv if aes_iv is not None else get_random_bytes(AES_IV_BYTES)
    if len(key) != AES_KEY_BYTES:
        raise AirtelEncryptionError("AES key must be 32 bytes (256 bits).")
    if len(iv) != AES_IV_BYTES:
        raise AirtelEncryptionError("AES IV must be 16 bytes (128 bits).")

    encrypted = _aes_encrypt(payload_str.encode("utf-8"), key, iv)
    x_signature = base64.b64encode(encrypted).decode("ascii")

    key_b64 = base64.b64encode(key).decode("ascii")
    iv_b64 = base64.b64encode(iv).decode("ascii")
    x_key = rsa_encrypt(public_key, f"{key_b64}:{iv_b64}")

    return SignedRequest(
        payload=payload_str,
        x_signature=x_signature,
        x_key=x_key,
        aes_key=key_b64,
        aes_iv=iv_b64,
    )
