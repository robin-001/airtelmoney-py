## airtelmoney-py v1.0.1

Patch release improving bearer-token handling.

### Improvements
- **Token validity is checked before every request.** The cached bearer token (valid for 180s) is reused only while valid, minus a small safety skew, and re-fetched automatically when expired.
- **Automatic re-authentication on HTTP 401.** If Airtel rejects a request with `401` despite a seemingly valid cached token (e.g. revoked early), the client forces a token refresh and retries the request once. A second consecutive `401` is raised as `AirtelAPIError`.
- Fixed `__version__` to match the released package version.

### Install
```bash
pip install --upgrade airtelmoney-py
```

**Full changelog:** https://github.com/robin-001/airtelmoney-py/compare/v1.0.0...v1.0.1
