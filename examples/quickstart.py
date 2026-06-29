"""Example usage for the airtelmoney-ug package (staging)."""

from airtelmoney import AirtelMoney, describe

    # client = AirtelMoney(
    #     client_id="YOUR_CLIENT_ID",
    #     client_secret="YOUR_CLIENT_SECRET",
    #     environment="staging",
    # )
# Or load from the credentials JSON file:
client = AirtelMoney.from_credentials_file("airtel_credentials.json")


def main() -> None:
    # Collections: USSD push payment (payload signed automatically)
    pay = client.collection.payment(
        reference="Order #123", msisdn="750396876", amount=1000
    )
    txn_id = pay["data"]["transaction"]["id"]
    print("collection.payment:", pay)

    # Collections: transaction enquiry + refund
    print("collection.enquiry:", client.collection.enquiry(txn_id))
    # print("refund:", client.collection.refund("CI210104.1105.C00018"))

    # Disbursements: PIN is RSA-encrypted automatically
    dis = client.disbursement.payment(
        msisdn="750396876", amount=500, reference="payout-1", pin="1234"
    )
    print("disbursement.payment:", dis)
    print("disbursement.enquiry:", client.disbursement.enquiry(
        dis["data"]["transaction"]["id"]))

    # KYC + Account
    print("kyc.user_enquiry:", client.kyc.user_enquiry("750396876"))
    print("account.balance:", client.account.balance())

    # Interpret a response code
    info = describe("DP00800001026")
    print("code DP00800001026 ->", info.reason, "-", info.description)


if __name__ == "__main__":
    main()
