## airtelmoney-py v1.0.5

### Changes
- **Default base URLs are now the Uganda hosts**: `https://openapiuat.airtel.ug` (staging) and `https://openapi.airtel.ug` (production). Override with `base_url=...` for the pan-African endpoints.
- **Encryption key parsing supports both response shapes** — the documented `.africa` `data.key` form and the `.ug` host's top-level `key`/`key_id`/`valid_upto`.
- **More informative error** when the encryption-keys endpoint returns no key (includes the API status message / response body).
- Bearer-token handling: validated before every request and auto re-authenticated + retried once on `401`.
- Synced `__version__` with the package version.

### Install
```bash
pip install --upgrade airtelmoney-py
```

**Full changelog:** https://github.com/robin-001/airtelmoney-py/compare/v1.0.1...v1.0.5
