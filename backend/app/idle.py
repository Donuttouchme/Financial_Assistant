"""Idle-shutdown watchdog.

The frontend posts /api/heartbeat every 5 minutes while a tab is open.
A middleware updates ``_last_activity`` on every HTTP request (heartbeat or
otherwise). A background asyncio task started from the FastAPI lifespan
checks every minute whether more than ``IDLE_THRESHOLD_SECONDS`` have passed
since the last activity; if so, it raises SIGINT in this process. Uvicorn
handles the signal by closing connections gracefully and exiting.
"""

from __future__ import annotations

import asyncio
import os
import signal
import time

IDLE_THRESHOLD_SECONDS = 60 * 60
CHECK_INTERVAL_SECONDS = 60

_last_activity: float = time.monotonic()


def record_activity() -> None:
    global _last_activity
    _last_activity = time.monotonic()


def seconds_since_activity() -> float:
    return time.monotonic() - _last_activity


def _trigger_shutdown() -> None:
    # SIGINT triggers uvicorn's graceful shutdown path on both POSIX and
    # Windows (Python 3.x supports raising signals in the current process
    # on Windows since 3.8).
    os.kill(os.getpid(), signal.SIGINT)


async def _watchdog_loop(
    check_interval: float = CHECK_INTERVAL_SECONDS,
    idle_threshold: float = IDLE_THRESHOLD_SECONDS,
) -> None:
    while True:
        await asyncio.sleep(check_interval)
        if seconds_since_activity() > idle_threshold:
            _trigger_shutdown()
            return


def start_watchdog() -> asyncio.Task:
    return asyncio.create_task(_watchdog_loop())
