from __future__ import annotations

from typing import Any

from app.config import Settings, XTQuantMode
from app.services.xtdata_gateway import XtDataGateway


def evaluate_xtdata_readiness(settings: Settings, gateway: XtDataGateway) -> dict[str, Any]:
    snapshot = gateway.get_readiness_snapshot()
    if settings.xtquant.mode == XTQuantMode.MOCK:
        snapshot["required"] = False
        snapshot["ready"] = True
        snapshot["status"] = "mock"
    else:
        snapshot["required"] = True
    return snapshot


def evaluate_runtime_readiness(settings: Settings, gateway: XtDataGateway) -> tuple[bool, dict[str, Any]]:
    xtdata = evaluate_xtdata_readiness(settings, gateway)
    ready = bool(xtdata.get("ready"))
    return ready, {"xtdata": xtdata}
