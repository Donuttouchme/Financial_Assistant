DEFAULT_USER_ID = 1


def get_current_user_id() -> int:
    """Single-user mode: always returns 1. Replace with auth integration later."""
    return DEFAULT_USER_ID
