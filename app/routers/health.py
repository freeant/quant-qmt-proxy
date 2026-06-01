"""健康检查路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.dependencies import get_xtdata_gateway
from app.services.runtime_health import evaluate_runtime_readiness
from app.services.xtdata_gateway import XtDataGateway
from app.utils.helpers import format_response

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("/")
async def health_check(settings: Settings = Depends(get_settings)):
    """健康检查接口。"""

    return format_response(
        data={
            "status": "healthy",
            "app_name": settings.app.name,
            "app_version": settings.app.version,
            "xtquant_mode": settings.xtquant.mode.value,
            "timestamp": datetime.now().isoformat(),
        },
        message="服务运行正常",
    )


@router.get("/ready")
async def readiness_check(
    settings: Settings = Depends(get_settings),
    gateway: XtDataGateway = Depends(get_xtdata_gateway),
):
    """就绪检查：mock 始终就绪；dev/prod 要求 xtdata 已连接。"""

    ready, checks = evaluate_runtime_readiness(settings, gateway)
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
    """存活检查接口。"""

    return format_response(
        data={"status": "alive"},
        message="服务存活",
    )
