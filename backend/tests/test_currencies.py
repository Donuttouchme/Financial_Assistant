from app.services.currencies import SUPPORTED_CURRENCIES, MOST_USED


def test_supported_currencies_contain_expected_subset():
    expected = {"EUR", "HUF", "USD", "CHF", "GBP", "JPY"}
    assert expected.issubset(SUPPORTED_CURRENCIES)


def test_supported_currencies_size():
    # frankfurter.app currently lists 31 currencies
    assert len(SUPPORTED_CURRENCIES) == 31


def test_most_used_is_subset_of_supported():
    assert set(MOST_USED).issubset(SUPPORTED_CURRENCIES)


def test_most_used_order():
    assert MOST_USED == ("EUR", "HUF", "USD", "CHF", "GBP")
