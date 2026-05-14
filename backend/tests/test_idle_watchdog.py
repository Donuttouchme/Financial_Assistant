import asyncio
import time
from unittest.mock import patch

import pytest

from app import idle


@pytest.fixture(autouse=True)
def reset_idle_state():
    idle._last_activity = time.monotonic()
    yield


def test_record_activity_updates_timestamp():
    before = idle._last_activity
    time.sleep(0.01)
    idle.record_activity()
    assert idle._last_activity > before


def test_seconds_since_activity_increases_with_time():
    idle.record_activity()
    time.sleep(0.05)
    elapsed = idle.seconds_since_activity()
    assert elapsed >= 0.05


@pytest.mark.asyncio
async def test_watchdog_does_not_shutdown_when_active():
    idle.record_activity()
    with patch("app.idle._trigger_shutdown") as mock_shutdown:
        # Loop with a 50 ms check interval and a 1 s idle threshold.
        # Run for 150 ms — well under threshold; record activity midway.
        task = asyncio.create_task(
            idle._watchdog_loop(check_interval=0.05, idle_threshold=1.0)
        )
        await asyncio.sleep(0.07)
        idle.record_activity()
        await asyncio.sleep(0.07)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        mock_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_watchdog_triggers_shutdown_after_threshold():
    # Force the idle timestamp into the past.
    idle._last_activity = time.monotonic() - 100.0
    with patch("app.idle._trigger_shutdown") as mock_shutdown:
        task = asyncio.create_task(
            idle._watchdog_loop(check_interval=0.05, idle_threshold=1.0)
        )
        # Watchdog should fire on first or second tick.
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert mock_shutdown.called
