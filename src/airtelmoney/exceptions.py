"""Exceptions raised by the Airtel Money client."""

from __future__ import annotations

from typing import Any, Optional

from .errors import ResponseCode, describe


class AirtelMoneyError(Exception):
    """Base class for all errors raised by this library."""


class AirtelConfigError(AirtelMoneyError):
    """Raised when the client is misconfigured (missing credentials, etc.)."""


class AirtelAuthError(AirtelMoneyError):
    """Raised when authentication / token retrieval fails."""


class AirtelEncryptionError(AirtelMoneyError):
    """Raised when signing or PIN/key encryption fails."""


class AirtelAPIError(AirtelMoneyError):
    """Raised when the API returns an error response.

    Attributes:
        status_code: HTTP status code of the response (if any).
        response_code: Airtel ``response_code`` from the body (if any).
        message: Human readable message from the API.
        payload: The full decoded response body.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_code: Optional[str] = None,
        payload: Any = None,
    ) -> None:
        self.status_code = status_code
        self.response_code = response_code
        self.message = message
        self.payload = payload
        super().__init__(self._build_message())

    @property
    def response_code_info(self) -> Optional[ResponseCode]:
        """The documented :class:`~airtelmoney.errors.ResponseCode`, if known."""
        return describe(self.response_code)

    def _build_message(self) -> str:
        parts = []
        if self.status_code is not None:
            parts.append(f"HTTP {self.status_code}")
        if self.response_code:
            parts.append(self.response_code)
            info = describe(self.response_code)
            if info:
                parts.append(f"({info.reason})")
        parts.append(self.message or "Airtel Money API error")
        return " - ".join(str(p) for p in parts)
