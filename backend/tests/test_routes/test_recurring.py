from datetime import date
from decimal import Decimal


def _make_recurring_tx(client, *, amount="500.00", tx_date="2026-02-01", description="Rent"):
    cat_id = client.post("/api/categories", json={"name": description}).json()["id"]
    client.post(
        "/api/transactions",
        json={
            "amount": amount,
            "date": tx_date,
            "category_id": cat_id,
            "description": description,
            "is_recurring": True,
        },
    )
    return cat_id


def test_list_recurring_returns_user_schedules(client, db_session):
    """GET /api/recurring returns the current user's schedules and not other users'."""
    from app.services import category_service, transaction_service

    _make_recurring_tx(client)
    # Seed a schedule for a different user that must be hidden.
    cat2 = category_service.create_category(db_session, user_id=2, name="Rent (u2)")
    transaction_service.create_transaction(
        db_session, user_id=2, amount=Decimal("400"), tx_date=date(2026, 4, 1),
        category_id=cat2.id, description="Rent (u2)", is_recurring=True,
    )

    response = client.get("/api/recurring")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["description"] == "Rent"
    assert body[0]["frequency"] == "monthly"
    assert body[0]["start_date"] == "2026-02-01"
    assert body[0]["next_occurrence_date"] == "2026-03-01"


def test_get_recurring_returns_schedule(client):
    _make_recurring_tx(client)
    listed = client.get("/api/recurring").json()
    sched_id = listed[0]["id"]

    response = client.get(f"/api/recurring/{sched_id}")
    assert response.status_code == 200
    assert response.json()["id"] == sched_id


def test_get_recurring_404_for_unknown_or_other_user_schedule(client, db_session):
    from app.services import category_service, transaction_service

    # Unknown id.
    assert client.get("/api/recurring/9999").status_code == 404

    # Other user's id must also return 404 for the current user.
    cat2 = category_service.create_category(db_session, user_id=2, name="Rent (u2)")
    transaction_service.create_transaction(
        db_session, user_id=2, amount=Decimal("400"), tx_date=date(2026, 4, 1),
        category_id=cat2.id, description="Rent (u2)", is_recurring=True,
    )
    from app.services import recurring_service
    other = recurring_service.list_schedules(db_session, user_id=2)[0]

    response = client.get(f"/api/recurring/{other.id}")
    assert response.status_code == 404


def test_update_recurring_returns_updated_payload(client):
    _make_recurring_tx(client)
    sched_id = client.get("/api/recurring").json()[0]["id"]

    response = client.patch(
        f"/api/recurring/{sched_id}",
        json={"amount": "600.00", "description": "Rent (raised)"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == sched_id
    assert body["amount"] == "600.00"
    assert body["description"] == "Rent (raised)"


def test_update_recurring_404_for_unknown_id(client):
    response = client.patch("/api/recurring/9999", json={"amount": "1.00"})
    assert response.status_code == 404


def test_delete_recurring_returns_204_then_404_on_subsequent_get(client):
    _make_recurring_tx(client)
    sched_id = client.get("/api/recurring").json()[0]["id"]

    response = client.delete(f"/api/recurring/{sched_id}")
    assert response.status_code == 204

    assert client.get(f"/api/recurring/{sched_id}").status_code == 404


def test_delete_recurring_nulls_child_schedule_id(client, db_session):
    """Deleting a schedule detaches already-materialised child transactions
    by nulling their `schedule_id` rather than cascading the delete."""
    from app.services import recurring_service
    from app.models.transaction import Transaction

    _make_recurring_tx(client, tx_date="2026-02-01")
    sched_id = client.get("/api/recurring").json()[0]["id"]

    # Materialise children up to 2026-05-15: Feb, Mar, Apr, May -> schedule's
    # original seed tx is at 2026-02-01 (a regular tx, no schedule_id) plus
    # subsequent materialisations on Mar 1, Apr 1, May 1 with schedule_id set.
    recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))

    child_ids = [
        row.id
        for row in db_session.query(Transaction)
        .filter(Transaction.schedule_id == sched_id)
        .all()
    ]
    assert len(child_ids) >= 1

    response = client.delete(f"/api/recurring/{sched_id}")
    assert response.status_code == 204

    db_session.expire_all()
    for cid in child_ids:
        child = db_session.get(Transaction, cid)
        assert child is not None, f"child {cid} should not have been cascaded away"
        assert child.schedule_id is None


def test_update_amount_typed_as_decimal_roundtrips_correctly(client):
    """Decimal amounts must serialise as a quoted string preserving 2dp,
    matching the project's convention (see TransactionRead tests)."""
    _make_recurring_tx(client)
    sched_id = client.get("/api/recurring").json()[0]["id"]

    response = client.patch(
        f"/api/recurring/{sched_id}",
        json={"amount": "600.00"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "600.00"
    assert isinstance(body["amount"], str)
