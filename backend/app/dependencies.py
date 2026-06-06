DEFAULT_USER_ID = 1


def get_current_user_id() -> int:
    """Single-user mode: always returns 1. Replace with auth integration later."""
    return DEFAULT_USER_ID


from datetime import datetime, timezone


def get_current_month() -> str:
    """Return today's UTC month as 'YYYY-MM'.

    Injected as a FastAPI dependency so tests can override it via
    ``app.dependency_overrides[get_current_month]`` and pin behavior to a
    known calendar month without monkey-patching the clock.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m")
