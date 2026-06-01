from __future__ import annotations

from typing import Any

from app.config import Settings, XTQuantMode
from app.services.redis_stream_sink import RedisStreamSink
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
) -> tuple[bool, dict[str, Any]]:
    xtdata = evaluate_xtdata_readiness(settings, gateway)
    ready = bool(xtdata.get("ready"))
    checks: dict[str, Any] = {"xtdata": xtdata}
    checks["redis"] = evaluate_redis_readiness(settings, redis_sink)
    return ready, checks
