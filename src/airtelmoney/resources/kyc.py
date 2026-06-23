"""KYC APIs: user enquiry."""

from __future__ import annotations

from typing import Any, Dict

from .base import BaseAPI

_USER_PATH = "/standard/v1/users/{msisdn}"


class KYCAPI(BaseAPI):
    """Know-Your-Subscriber endpoints."""

    def user_enquiry(self, msisdn: str) -> Dict[str, Any]:
        """Look up registration details for a subscriber by MSISDN.

        Args:
            msisdn: Subscriber phone number including country code, e.g.
                ``"25675123456"``.
        """
        return self._client.request(
            "GET",
            _USER_PATH.format(msisdn=msisdn),
            include_country_currency=True,
            auth=True,
        )
