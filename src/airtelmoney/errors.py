"""Airtel Money Uganda API response codes.

This maps the documented ``response_code`` values returned by the Airtel
Money Open APIs to a short reason and a longer description. Use
:func:`describe` to look up a code.
"""

from __future__ import annotations

from typing import Dict, NamedTuple, Optional


class ResponseCode(NamedTuple):
    code: str
    reason: str
    description: str


#: Mapping of Airtel Money ``response_code`` -> :class:`ResponseCode`.
RESPONSE_CODES: Dict[str, ResponseCode] = {
    rc.code: rc
    for rc in [
        # Encryption
        ResponseCode("DP02010001000", "Error while fetching encryption key",
                     "Could not fetch encryption key."),
        ResponseCode("DP02010001001", "Successfully fetched encryption key.",
                     "Encryption key has been fetched successfully."),
        # Collection (DP008...)
        ResponseCode("DP00800001000", "Ambiguous",
                     "The transaction is still processing and is in ambiguous state. "
                     "Please do the transaction enquiry to fetch the transaction status."),
        ResponseCode("DP00800001001", "Success", "Transaction is successful."),
        ResponseCode("DP00800001002", "Incorrect Pin", "Incorrect pin has been entered."),
        ResponseCode("DP00800001003", "Exceeds withdrawal amount limit(s)",
                     "The User has exceeded their wallet allowed transaction limit."),
        ResponseCode("DP00800001004", "Invalid Amount",
                     "The amount User is trying to transfer is less than the minimum amount allowed."),
        ResponseCode("DP00800001005", "Transaction ID is invalid", "User didn't enter the pin."),
        ResponseCode("DP00800001006", "In process",
                     "Transaction in pending state. Please check after sometime."),
        ResponseCode("DP00800001007", "Not enough balance",
                     "User wallet does not have enough money to cover the payable amount."),
        ResponseCode("DP00800001008", "Refused", "The transaction was refused."),
        ResponseCode("DP00800001009", "Do not honor",
                     "This is a generic refusal that has several possible causes."),
        ResponseCode("DP00800001010", "Transaction not permitted to Payee",
                     "Payee is already initiated for churn or barred or not registered on "
                     "Airtel Money platform."),
        ResponseCode("DP00800001024", "Transaction Timed Out", "The transaction was timed out."),
        ResponseCode("DP00800001025", "Transaction Not Found", "The transaction was not found."),
        ResponseCode("DP00800001026", "Forbidden", "X-signature and payload did not match."),
        ResponseCode("DP00800001029", "Transaction Expired", "Transaction has been expired."),
        # User enquiry (DP022...)
        ResponseCode("DP02200000000", "Failed", "User enquiry is failed."),
        ResponseCode("DP02200000001", "Success", "User enquiry is successful."),
        # Balance enquiry (DP021...)
        ResponseCode("DP02100000000", "Failed", "Balance enquiry is failed."),
        ResponseCode("DP02100000001", "Success", "Balance enquiry is successful."),
        ResponseCode("DP02100000002", "User Not Found", "Invalid MSISDN provided as input."),
        # Disbursement (DP009...)
        ResponseCode("DP00900001000", "Ambiguous",
                     "The transaction is still processing and is in ambiguous state. "
                     "Please do the transaction enquiry to fetch the transaction status."),
        ResponseCode("DP00900001001", "Success", "Transaction is successful."),
        ResponseCode("DP00900001003", "Maximum transaction limit reached",
                     "Maximum transaction limit reached for the day."),
        ResponseCode("DP00900001004", "Invalid Amount",
                     "Amount entered is out of range with respect to defined limits."),
        ResponseCode("DP00900001005", "Failed", "Transaction failed."),
        ResponseCode("DP00900001006", "Processing", "Transaction is in process."),
        ResponseCode("DP00900001007", "Insufficient Funds",
                     "Not enough funds in account to complete the transaction."),
        ResponseCode("DP00900001009", "Invalid Initiatee",
                     "Initiatee of the transaction is invalid."),
        ResponseCode("DP00900001010", "User not allowed", "Payer is not an allowed user."),
        ResponseCode("DP00900001011", "Transaction not allowed",
                     "Transaction with similar information already exists in this system."),
        ResponseCode("DP00900001012", "Invalid mobile number",
                     "Mobile number entered is incorrect."),
        ResponseCode("DP00900001013", "Refused", "The transaction was refused."),
        ResponseCode("DP00900001014", "Transaction Timed Out",
                     "The transaction may be processed or failed due to time out. "
                     "To know the exact status please do the transaction enquiry."),
        ResponseCode("DP00900001015", "Transaction Not Found", "The transaction was not found."),
        ResponseCode("DP00900001016", "Forbidden", "X-signature and payload did not match."),
        ResponseCode("DP00900001017", "Duplicate transaction Id",
                     "Duplicate Transaction Id. To know the status of the actual transaction, "
                     "please do transaction enquiry."),
    ]
}

#: Response codes that indicate a successful outcome.
SUCCESS_CODES = {
    "DP02010001001",
    "DP00800001001",
    "DP02200000001",
    "DP02100000001",
    "DP00900001001",
}

#: Response codes that indicate the transaction is still pending / in progress.
PENDING_CODES = {
    "DP00800001000",
    "DP00800001006",
    "DP00900001000",
    "DP00900001006",
}


def describe(code: Optional[str]) -> Optional[ResponseCode]:
    """Return the :class:`ResponseCode` for ``code`` or ``None`` if unknown."""
    if code is None:
        return None
    return RESPONSE_CODES.get(code)


def is_success(code: Optional[str]) -> bool:
    """Return ``True`` if ``code`` is a documented success code."""
    return code in SUCCESS_CODES


def is_pending(code: Optional[str]) -> bool:
    """Return ``True`` if ``code`` indicates a pending/ambiguous transaction."""
    return code in PENDING_CODES
