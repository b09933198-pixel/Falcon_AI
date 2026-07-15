from src.analysis.risk.account import Account


def test_account():

    account = Account(

        balance=10000,

        equity=10100,

        free_margin=9800,

        leverage=20,

    )

    assert account.balance == 10000

    assert account.currency == "USD"

    assert account.leverage == 20