import pytest

from app.services import category_service


def test_create_category_persists_with_user_id(db_session):
    cat = category_service.create_category(db_session, user_id=1, name="Groceries")
    assert cat.id is not None
    assert cat.name == "Groceries"
    assert cat.user_id == 1


def test_list_categories_returns_only_users_own(db_session):
    category_service.create_category(db_session, user_id=1, name="Groceries")
    category_service.create_category(db_session, user_id=1, name="Rent")
    category_service.create_category(db_session, user_id=2, name="Other user's cat")

    names = [c.name for c in category_service.list_categories(db_session, user_id=1)]
    assert sorted(names) == ["Groceries", "Rent"]


def test_create_category_rejects_duplicate_name_for_same_user(db_session):
    category_service.create_category(db_session, user_id=1, name="Groceries")
    with pytest.raises(ValueError, match="already exists"):
        category_service.create_category(db_session, user_id=1, name="Groceries")


def test_delete_category_removes_it(db_session):
    cat = category_service.create_category(db_session, user_id=1, name="Misc")
    category_service.delete_category(db_session, user_id=1, category_id=cat.id)
    assert category_service.list_categories(db_session, user_id=1) == []


def test_delete_unknown_category_raises_lookup_error(db_session):
    with pytest.raises(LookupError):
        category_service.delete_category(db_session, user_id=1, category_id=999)


def test_create_category_defaults_kind_to_expense(db_session):
    cat = category_service.create_category(db_session, user_id=1, name="Groceries")
    assert cat.kind == "expense"


def test_create_category_accepts_income_kind(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Salary", kind="income"
    )
    assert cat.kind == "income"


def test_create_category_rejects_invalid_kind(db_session):
    with pytest.raises(ValueError, match="kind"):
        category_service.create_category(
            db_session, user_id=1, name="Bad", kind="loan"
        )


def test_create_savings_category_accepted(db_session):
    from decimal import Decimal
    cat = category_service.create_category(
        db_session, user_id=1, name="Pillar 3a", kind="savings"
    )
    assert cat.kind == "savings"
    assert cat.target_amount is None
    assert cat.target_date is None


def test_create_savings_category_with_target(db_session):
    from datetime import date
    from decimal import Decimal
    cat = category_service.create_category(
        db_session,
        user_id=1,
        name="Vacation 2027",
        kind="savings",
        target_amount=Decimal("3000.00"),
        target_date=date(2027, 6, 30),
    )
    assert cat.target_amount == Decimal("3000.00")
    assert cat.target_date == date(2027, 6, 30)


def test_create_category_rejects_target_on_expense(db_session):
    from decimal import Decimal
    with pytest.raises(ValueError, match="target.*savings"):
        category_service.create_category(
            db_session,
            user_id=1,
            name="Groceries",
            kind="expense",
            target_amount=Decimal("100.00"),
        )
