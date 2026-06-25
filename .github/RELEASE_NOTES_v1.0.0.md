## airtelmoney-py v1.0.0

First release of **airtelmoney-py**, a Python client for the Airtel Money Uganda Open APIs with built-in request signing and PIN encryption.

### Features
- **Collections**: USSD-push payment (auto-signed `x-signature` / `x-key`), transaction enquiry, refund, and callback hash verification.
- **Disbursements**: send money with automatic RSA PIN encryption, plus transaction enquiry.
- **KYC**: user enquiry by MSISDN.
- **Account**: balance enquiry.
- **Auth**: OAuth2 client-credentials with token caching and auto-refresh.
- **Encryption**: AES-256-CBC payload signing + RSA-encrypted key/IV, encryption-key fetching and caching.
- **Config**: build a client from explicit args, a credentials JSON file, or environment variables / `.env` (`AirtelMoney.from_env()`).
- Typed exceptions and a complete map of documented `response_code` values.
- Fully covered by offline unit tests.

### Install
```bash
pip install airtelmoney-py
```

### Quick start
```python
from airtelmoney import AirtelMoney

client = AirtelMoney.from_env()  # or AirtelMoney(client_id=..., client_secret=...)
res = client.collection.payment(reference="Order #1", msisdn="752604392", amount=1000)
```

See the [README](https://github.com/robin-001/airtelmoney-py#readme) for full usage.
