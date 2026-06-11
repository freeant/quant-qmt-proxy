"""In-process liveness heartbeat for external watchdog probes."""

from __future__ import annotations

import os
import threading
import time

_LOCK = threading.RLock()
_STARTED_AT_MONO = time.monotonic()
_STARTED_AT_MS = int(time.time() * 1000)
_LAST_HEARTBEAT_MS = _STARTED_AT_MS
_HEARTBEAT_THREAD: threading.Thread | None = None
_HEARTBEAT_INTERVAL_SECONDS = 10.0


def touch_heartbeat() -> None:
    global _LAST_HEARTBEAT_MS
    with _LOCK:
        _LAST_HEARTBEAT_MS = int(time.time() * 1000)


def ensure_heartbeat_loop(interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS) -> None:
    global _HEARTBEAT_THREAD

    touch_heartbeat()
    with _LOCK:
        if _HEARTBEAT_THREAD is not None and _HEARTBEAT_THREAD.is_alive():
            return

        def _loop() -> None:
            while True:
                time.sleep(interval_seconds)
                touch_heartbeat()

        thread = threading.Thread(target=_loop, daemon=True, name="process-heartbeat")
        _HEARTBEAT_THREAD = thread
        thread.start()


def get_liveness_snapshot() -> dict[str, int | float | str]:
    now_ms = int(time.time() * 1000)
    with _LOCK:
        last_heartbeat_ms = _LAST_HEARTBEAT_MS
        started_at_ms = _STARTED_AT_MS
    uptime_seconds = round(time.monotonic() - _STARTED_AT_MONO, 3)
    heartbeat_age_seconds = round(max(0, now_ms - last_heartbeat_ms) / 1000.0, 3)
    return {
        "status": "alive",
        "pid": os.getpid(),
        "started_at_ms": started_at_ms,
        "last_heartbeat_ms": last_heartbeat_ms,
        "uptime_seconds": uptime_seconds,
        "heartbeat_age_seconds": heartbeat_age_seconds,
    }
