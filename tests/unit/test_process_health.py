from __future__ import annotations

import time

from app.services import process_health as process_health_module
from app.services.process_health import ensure_heartbeat_loop, get_liveness_snapshot, touch_heartbeat


def test_touch_heartbeat_updates_snapshot():
    before = get_liveness_snapshot()["last_heartbeat_ms"]
    time.sleep(0.01)
    touch_heartbeat()
    after = get_liveness_snapshot()["last_heartbeat_ms"]
    assert after >= before


def test_ensure_heartbeat_loop_is_idempotent():
    ensure_heartbeat_loop(interval_seconds=0.05)
    first = process_health_module._HEARTBEAT_THREAD
    ensure_heartbeat_loop(interval_seconds=0.05)
    second = process_health_module._HEARTBEAT_THREAD
    assert first is second
    assert first is not None
    assert first.is_alive()
