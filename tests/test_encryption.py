"""Tests for the encryption / signing helpers.

These run fully offline by generating a throwaway RSA key pair and verifying
the AES signature + RSA-encrypted key:iv can be decrypted/round-tripped.
"""

import base64
import json

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad

from airtelmoney.encryption import encrypt_pin, sign_payload


def _make_keypair():
    key = RSA.generate(2048)
    private_pem = key.export_key()
    public_der_b64 = base64.b64encode(key.publickey().export_key(format="DER")).decode()
    return private_pem, public_der_b64


def test_sign_payload_roundtrip():
    private_pem, public_b64 = _make_keypair()
    payload = {
        "reference": "1234",
        "subscriber": {"country": "UG", "currency": "UGX", "msisdn": "752604392"},
        "transaction": {"amount": "100", "country": "UG", "currency": "UGX", "id": "test_id"},
    }

    signed = sign_payload(public_b64, payload)

    # x-signature must be the AES encryption of the exact payload string.
    expected_payload = json.dumps(payload, separators=(",", ":"))
    assert signed.payload == expected_payload

    # Decrypt x-key with the private key to recover key:iv.
    priv = RSA.import_key(private_pem)
    decryptor = PKCS1_v1_5.new(priv)
    recovered = decryptor.decrypt(base64.b64decode(signed.x_key), b"sentinel")
    assert recovered != b"sentinel"
    key_b64, iv_b64 = recovered.decode().split(":")
    assert key_b64 == signed.aes_key
    assert iv_b64 == signed.aes_iv

    # Use the recovered key/iv to decrypt x-signature and match the payload.
    cipher = AES.new(base64.b64decode(key_b64), AES.MODE_CBC, base64.b64decode(iv_b64))
    plaintext = unpad(cipher.decrypt(base64.b64decode(signed.x_signature)), AES.block_size)
    assert plaintext.decode() == expected_payload


def test_known_vector_decrypts_to_expected_payload():
    # Validate the AES implementation against Airtel's documented example by
    # decrypting the documented x-signature with the documented key/IV.
    key = base64.b64decode("PSw37xtnShLl7zgWn4dLSnf1J5GRhRsOD4OfvJOuLIM=")
    iv = base64.b64decode("gGIhDvCBnSBhBgYiXCyMnw==")
    documented_signature = (
        "bDOsVGZzbK0P5jO/M5QVMH/qxSmRJLEvIPZCdW6H81xvsZNI6jZej54oBQlHZ38yy63QNeyy"
        "YcfEkGJ8f3f15wHWs86V9BCIpHSesS3SrhozE/gGA1fLydeSS26mw0jhyt9XIpabk1RjDH59"
        "SfsrkHKU38I5mRlthG/t2qXJck0FhNR64bgOExm9CsuxUlfpsSoW1g81g1u5a4yMFIHhp77f"
        "+h3EXNHzcEsdSWhqTho="
    )
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(
        cipher.decrypt(base64.b64decode(documented_signature)), AES.block_size
    ).decode()
    data = json.loads(plaintext)
    assert data["reference"] == "1234"
    assert data["subscriber"]["msisdn"] == "752604392"
    assert data["transaction"]["id"].strip() == "test_id"

    # And re-signing that exact recovered string reproduces the documented value
    # byte-for-byte, proving compatibility with Airtel's AES/CBC/PKCS5 scheme.
    _, public_b64 = _make_keypair()
    signed = sign_payload(public_b64, plaintext, aes_key=key, aes_iv=iv)
    assert signed.x_signature == documented_signature


def test_encrypt_pin_roundtrip():
    private_pem, public_b64 = _make_keypair()
    enc = encrypt_pin(public_b64, "1234")
    priv = RSA.import_key(private_pem)
    decryptor = PKCS1_v1_5.new(priv)
    recovered = decryptor.decrypt(base64.b64decode(enc), b"sentinel")
    assert recovered.decode() == "1234"
