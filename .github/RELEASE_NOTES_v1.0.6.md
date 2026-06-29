## airtelmoney-py v1.0.6

### Changes
- **Disbursement payload updated** to match the Airtel Money Uganda B2C contract:
  - `payee` now includes `currency` (from the client's configured currency).
  - `transaction` now includes `"type": "B2C"`.

### Install
```bash
pip install --upgrade airtelmoney-py
```

**Full changelog:** https://github.com/robin-001/airtelmoney-py/compare/v1.0.5...v1.0.6
