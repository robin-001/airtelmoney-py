"""Shared base for API resource groups."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..client import AirtelMoney


class BaseAPI:
    """Base class holding a reference to the parent client."""

    def __init__(self, client: "AirtelMoney") -> None:
        self._client = client

    @staticmethod
    def _new_transaction_id() -> str:
        """Generate a unique transaction id (UUID4 hex-with-dashes)."""
        return str(uuid.uuid4())
