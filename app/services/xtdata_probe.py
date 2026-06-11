"""Background xtdata connectivity probe and auto-reconnect."""

from __future__ import annotations

import threading
import time

from app.config import Settings, XTQuantMode
from app.services.xtdata_gateway import XtDataGateway
from app.utils.logger import logger

_PROBE_LOCK = threading.RLock()
_PROBE_THREAD: threading.Thread | None = None


def ensure_xtdata_probe_loop(gateway: XtDataGateway, settings: Settings) -> None:
    if settings.xtquant.mode == XTQuantMode.MOCK:
        return

    interval_seconds = float(settings.xtquant.data.probe_interval_seconds)
    if interval_seconds <= 0:
        return

    global _PROBE_THREAD
    with _PROBE_LOCK:
        if _PROBE_THREAD is not None and not _PROBE_THREAD.is_alive():
            _PROBE_THREAD = None
        if _PROBE_THREAD is not None and _PROBE_THREAD.is_alive():
            return

        def _loop() -> None:
            while True:
                time.sleep(interval_seconds)
                try:
                    result = gateway.probe_connection()
                    if result.get("healthy"):
                        if result.get("action") not in (None, "none"):
                            logger.info("xtdata probe recovered: {}", result)
                    else:
                        logger.warning("xtdata probe unhealthy: {}", result)
                except Exception as exc:
                    logger.warning(f"xtdata probe loop error: {exc}")

        thread = threading.Thread(target=_loop, daemon=True, name="xtdata-probe")
        _PROBE_THREAD = thread
        thread.start()
        logger.info(
            "xtdata probe loop started: interval_seconds={}, probe_timeout_seconds={}",
            interval_seconds,
            settings.xtquant.data.probe_timeout_seconds,
        )
