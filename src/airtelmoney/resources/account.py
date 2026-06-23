"""Account APIs: balance enquiry."""

from __future__ import annotations

from typing import Any, Dict

from .base import BaseAPI

_BALANCE_PATH = "/standard/v1/users/balance"


class AccountAPI(BaseAPI):
    """Wallet/account endpoints."""

    def balance(self) -> Dict[str, Any]:
        """Fetch the available balance of your Airtel Money account."""
        return self._client.request(
            "GET",
            _BALANCE_PATH,
            include_country_currency=True,
            auth=True,
        )

    # Alias matching the documented endpoint name.
    balance_enquiry = balance
