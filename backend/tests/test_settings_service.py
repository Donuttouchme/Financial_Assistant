import pytest

from app.services import settings_service


def test_get_creates_default_row(db_session):
    s = settings_service.get_settings(db_session)
    assert s.id == 1
    assert s.base_currency == "CHF"


def test_get_is_idempotent(db_session):
    s1 = settings_service.get_settings(db_session)
    s2 = settings_service.get_settings(db_session)
    assert s1.id == s2.id == 1


def test_set_base_currency_valid(db_session):
    settings_service.set_base_currency(db_session, "HUF")
    s = settings_service.get_settings(db_session)
    assert s.base_currency == "HUF"


def test_set_base_currency_rejects_unknown(db_session):
    with pytest.raises(ValueError, match="unknown currency"):
        settings_service.set_base_currency(db_session, "XYZ")
