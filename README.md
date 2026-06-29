# airtelmoney-ug

Python client for the **Airtel Money Uganda Open APIs** — Collections, Disbursements,
KYC and Account — with built-in request **signing** (`x-signature` / `x-key`) and
**PIN encryption**, automatic OAuth2 token management and friendly error-code lookups.

## Features

- OAuth2 client-credentials token handling with caching/auto-refresh.
- Automatic message signing for write APIs (AES-256-CBC payload + RSA-encrypted key/IV).
- Automatic RSA PIN encryption for disbursements.
- Encryption-key fetching and caching.
- Typed exceptions and a complete map of documented `response_code` values.
- Fully covered by offline unit tests.

## Installation

```bash
pip install airtelmoney-ug
```

For local development:

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from airtelmoney import AirtelMoney

client = AirtelMoney(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    environment="staging",   # or "production"
)

# Or load credentials from a JSON file (airtel_client_id / airtel_client_secret):
client = AirtelMoney.from_credentials_file("airtel_credentials.json")

# Or load from environment variables / a .env file (recommended):
client = AirtelMoney.from_env()
```

> Default base URLs are `https://openapiuat.airtel.ug` (staging) and
> `https://openapi.airtel.ug` (production). Pass `base_url=...` to override,
> e.g. for the pan-African endpoints `https://openapi.airtel.africa`.

### Configuration via `.env`

Install the optional dependency and copy `.env.example` to `.env`:

```bash
pip install "airtelmoney-py[env]"
cp .env.example .env
```

| Variable | Description | Default |
| --- | --- | --- |
| `AIRTEL_CLIENT_ID` | Application client id (required) | — |
| `AIRTEL_CLIENT_SECRET` | Application client secret (required) | — |
| `AIRTEL_ENVIRONMENT` | `staging` or `production` | `staging` |
| `AIRTEL_BASE_URL` | Explicit base URL (overrides environment) | — |
| `AIRTEL_COUNTRY` | `X-Country` header | `UG` |
| `AIRTEL_CURRENCY` | `X-Currency` header | `UGX` |

```python
from airtelmoney import AirtelMoney

client = AirtelMoney.from_env()  # reads .env if python-dotenv is installed
```

## Usage

### Collections

```python
# USSD push payment (payload signed automatically using the consumer RSA key)
res = client.collection.payment(
    reference="Order #123",
    msisdn="752604392",
    amount=1000,
)
txn_id = res["data"]["transaction"]["id"]

# Transaction enquiry
client.collection.enquiry(txn_id)

# Refund a successful transaction
client.collection.refund("CI210104.1105.C00018")
```

### Disbursements

```python
# PIN is RSA-encrypted with the consumer public key automatically
res = client.disbursement.payment(
    msisdn="752604392",
    amount=500,
    reference="payout-1",
    pin="1234",
)
client.disbursement.enquiry(res["data"]["transaction"]["id"])

# Already have an encrypted PIN? Pass it directly:
client.disbursement.payment(
    msisdn="752604392", amount=500, reference="p-2",
    encrypted_pin="KYJExln8rZwb14G1K5UE5YF/lD7KheNUM171MUEG3/f/QD8nmNKRsa44",
)
```

### KYC and Account

```python
client.kyc.user_enquiry("256752604392")
client.account.balance()
```

### Callbacks

Airtel posts transaction updates to your configured callback URL. For authenticated
callbacks you can verify the signature:

```python
# payload is the decoded JSON body Airtel POSTed to your callback URL
valid = client.collection.verify_callback_hash(payload, secret="YOUR_CLIENT_SECRET")
```

## Manual signing / encryption

The signing primitives are exposed if you need them directly:

```python
from airtelmoney import sign_payload, encrypt_pin

public_key = client.get_encryption_key()  # base64 DER RSA public key

signed = sign_payload(public_key, {"reference": "1234", "transaction": {"id": "x"}})
# signed.payload      -> exact JSON body you MUST send
# signed.x_signature  -> x-signature header
# signed.x_key        -> x-key header

enc_pin = encrypt_pin(public_key, "1234")
```

### How signing works

1. Generate a random 256-bit AES key and 128-bit IV.
2. Base64-encode the key and IV.
3. Fetch the consumer RSA public key (`client.get_encryption_key()`).
4. Encrypt the JSON payload with `AES/CBC/PKCS5Padding` → `x-signature` header.
5. Concatenate `key:iv` (both base64) and RSA-encrypt with the public key → `x-key` header.

The server decrypts `key:iv` with its private RSA key, re-encrypts the received payload
and compares it against `x-signature`. A mismatch yields a `Forbidden`
(`DP00800001026` / `DP00900001016`).

## Error handling

```python
from airtelmoney import AirtelAPIError, describe, is_success

try:
    res = client.account.balance()
except AirtelAPIError as exc:
    print(exc.status_code, exc.response_code, exc.message)

# Interpret any documented response code
info = describe("DP00800001007")   # ResponseCode(code=..., reason='Not enough balance', ...)
is_success("DP00800001001")        # True
```

## Response codes

All documented codes are available via `airtelmoney.RESPONSE_CODES` and `describe()`,
covering encryption, collection (`DP008...`), disbursement (`DP009...`), user
enquiry (`DP022...`) and balance (`DP021...`).

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
