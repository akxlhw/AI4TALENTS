"""
Health check endpoint.
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache_connection
from app.core.config import settings
from app.core.database import async_engine, get_async_session

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
        dict: Health status of the service, database, and cache.
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
            "pool_size": 0,
            "pool_overflow": 0,
        },
        "cache": {
            "enabled": settings.REDIS_ENABLED,
            "status": "disabled",
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

    # Get database pool status
    if hasattr(async_engine, "pool"):
        pool = async_engine.pool
        if hasattr(pool, "size"):
            health_status["database"]["pool_size"] = pool.size()
        if hasattr(pool, "overflow"):
            health_status["database"]["pool_overflow"] = pool.overflow()

    # Check cache connection
    if settings.REDIS_ENABLED:
        cache_conn = await get_cache_connection()
        if cache_conn.is_available:
            health_status["cache"]["status"] = "connected"
            # Get cache stats
            try:
                client = cache_conn.client
                if client:
                    info = await client.info("memory")
                    health_status["cache"]["memory_used"] = info.get("used_memory_human", "unknown")

                    db_size = await client.dbsize()
                    health_status["cache"]["key_count"] = db_size
            except Exception:
                pass
        else:
            health_status["cache"]["status"] = "disconnected"
            # Cache unavailable is not critical, service still works
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"

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

    Checks if the service is ready to receive requests.
    Database must be available. Cache is optional.
    """
    checks = {
        "database": False,
        "cache": True,  # Cache is optional
    }

    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    # Check cache (optional)
    if settings.REDIS_ENABLED:
        cache_conn = await get_cache_connection()
        checks["cache"] = cache_conn.is_available

    # Service is ready if database is available
    is_ready = checks["database"]

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
    }


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
