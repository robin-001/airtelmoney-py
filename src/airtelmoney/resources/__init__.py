"""API resource groups for the Airtel Money client."""

from .account import AccountAPI
from .collection import CollectionAPI
from .disbursement import DisbursementAPI
from .kyc import KYCAPI

__all__ = ["AccountAPI", "CollectionAPI", "DisbursementAPI", "KYCAPI"]
