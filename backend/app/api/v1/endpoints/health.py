"""
Health check endpoint.
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="健康检查",
    description="检查服务和数据库连接状态",
)
async def health_check(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Health check endpoint.

    Returns:
        dict: Health status of the service and database.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
        "database": {
            "status": "unknown",
        },
    }

    # Check database connection
    try:
        result = await session.execute(text("SELECT 1"))
        if result.scalar() == 1:
            health_status["database"]["status"] = "connected"
        else:
            health_status["database"]["status"] = "error"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["database"]["status"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status


@router.get(
    "/health/ready",
    summary="就绪检查",
    description="检查服务是否准备好接收请求",
)
async def readiness_check(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Readiness check endpoint.

    Returns:
        dict: Readiness status.
    """
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


@router.get(
    "/health/live",
    summary="存活检查",
    description="检查服务是否存活",
)
async def liveness_check():
    """
    Liveness check endpoint.

    Returns:
        dict: Liveness status.
    """
    return {"status": "alive"}
