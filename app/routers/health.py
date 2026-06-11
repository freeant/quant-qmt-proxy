"""健康检查路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.dependencies import get_redis_stream_sink, get_trading_session_manager, get_xtdata_gateway
from app.services.redis_stream_sink import RedisStreamSink
from app.services.process_health import get_liveness_snapshot, touch_heartbeat
from app.services.runtime_health import evaluate_qmt_readiness, evaluate_runtime_readiness
from app.services.trading_session_manager import TradingSessionManager
from app.services.xtdata_gateway import XtDataGateway
from app.utils.helpers import format_response

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("/")
async def health_check(
    settings: Settings = Depends(get_settings),
    gateway: XtDataGateway = Depends(get_xtdata_gateway),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    """健康检查接口。"""

    qmt = evaluate_qmt_readiness(settings, gateway, trading_manager)
    qmt_ready = bool(qmt.get("ready"))

    return format_response(
        data={
            "status": "healthy" if qmt_ready else "degraded",
            "app_name": settings.app.name,
            "app_version": settings.app.version,
            "xtquant_mode": settings.xtquant.mode.value,
            "qmt": qmt,
            "timestamp": datetime.now().isoformat(),
        },
        message="服务运行正常" if qmt_ready else "服务运行中，QMT 未就绪",
    )


@router.get("/ready")
async def readiness_check(
    settings: Settings = Depends(get_settings),
    gateway: XtDataGateway = Depends(get_xtdata_gateway),
    redis_sink: RedisStreamSink | None = Depends(get_redis_stream_sink),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    """就绪检查：mock 始终就绪；dev/prod 要求 QMT（xtdata/xttrader）就绪；Redis 旁路单独报告。"""

    ready, checks = evaluate_runtime_readiness(settings, gateway, redis_sink, trading_manager)
    payload = format_response(
        data={
            "status": "ready" if ready else "not_ready",
            "xtquant_mode": settings.xtquant.mode.value,
            "checks": checks,
        },
        message="服务已就绪" if ready else "服务未就绪",
        success=ready,
    )
    if ready:
        return payload
    return JSONResponse(status_code=503, content=payload)


@router.get("/live")
async def liveness_check():
    """存活检查接口；含进程心跳，供外部 watchdog 判断僵死。"""

    touch_heartbeat()
    return format_response(
        data=get_liveness_snapshot(),
        message="服务存活",
    )
