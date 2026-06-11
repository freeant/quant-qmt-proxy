from __future__ import annotations

from typing import Any

from app.config import Settings, XTQuantMode
from app.services.redis_stream_sink import RedisStreamSink
from app.services.trading_session_manager import TradingSessionManager
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


def evaluate_xttrader_readiness(
    settings: Settings,
    trading_manager: TradingSessionManager | None,
) -> dict[str, Any]:
    if trading_manager is None:
        if settings.xtquant.mode == XTQuantMode.MOCK:
            return {
                "status": "mock",
                "ready": True,
                "required": False,
                "reason": None,
                "active_sessions": 0,
                "connected_sessions": 0,
            }
        path = (settings.xtquant.data.qmt_userdata_path or "").strip()
        if not path:
            return {
                "status": "misconfigured",
                "ready": False,
                "required": True,
                "reason": "qmt_userdata_path is not configured",
                "active_sessions": 0,
                "connected_sessions": 0,
            }
        return {
            "status": "idle",
            "ready": True,
            "required": True,
            "reason": None,
            "qmt_userdata_path": path,
            "active_sessions": 0,
            "connected_sessions": 0,
        }
    return trading_manager.get_readiness_snapshot()


def evaluate_qmt_readiness(
    settings: Settings,
    gateway: XtDataGateway,
    trading_manager: TradingSessionManager | None = None,
) -> dict[str, Any]:
    xtdata = evaluate_xtdata_readiness(settings, gateway)
    xttrader = evaluate_xttrader_readiness(settings, trading_manager)

    if settings.xtquant.mode == XTQuantMode.MOCK:
        return {
            "ready": True,
            "status": "mock",
            "required": False,
            "xtdata": xtdata,
            "xttrader": xttrader,
        }

    ready = bool(xtdata.get("ready")) and bool(xttrader.get("ready"))
    if ready:
        status = "healthy"
    elif not xtdata.get("ready"):
        status = "not_ready"
    else:
        status = xttrader.get("status") or "not_ready"

    return {
        "ready": ready,
        "status": status,
        "required": True,
        "xtdata": xtdata,
        "xttrader": xttrader,
    }


def evaluate_redis_readiness(settings: Settings, redis_sink: RedisStreamSink | None) -> dict[str, Any]:
    if not settings.redis.enabled:
        return {"status": "disabled", "ready": True, "required": False}

    if redis_sink is None:
        return {
            "status": "unavailable",
            "ready": False,
            "required": True,
            "reason": "redis sink is not initialized",
        }

    stats = redis_sink.get_stats()
    if redis_sink.ping():
        return {"status": "ok", "ready": True, "required": True, "metrics": stats}

    payload = {
        "status": "degraded",
        "ready": False,
        "required": True,
        "reason": "redis ping failed",
        "metrics": stats,
    }
    if stats.get("circuit_open"):
        payload["reason"] = "redis circuit breaker is open"
    return payload


def evaluate_runtime_readiness(
    settings: Settings,
    gateway: XtDataGateway,
    redis_sink: RedisStreamSink | None = None,
    trading_manager: TradingSessionManager | None = None,
) -> tuple[bool, dict[str, Any]]:
    qmt = evaluate_qmt_readiness(settings, gateway, trading_manager)
    ready = bool(qmt.get("ready"))
    checks: dict[str, Any] = {"qmt": qmt}
    checks["redis"] = evaluate_redis_readiness(settings, redis_sink)
    return ready, checks
