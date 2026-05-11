from sqlalchemy import text


def test_db_session_fixture_provides_working_connection(db_session):
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1
