"""健康检查路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
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
async def readiness_check():
    """就绪检查接口。"""

    return format_response(
        data={"status": "ready"},
        message="服务已就绪",
    )


@router.get("/live")
async def liveness_check():
    """存活检查接口。"""

    return format_response(
        data={"status": "alive"},
        message="服务存活",
    )
