"""
Metrics endpoint for Prometheus scraping.
"""
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from app.core.cache import get_cache_connection
from app.core.database import async_engine
from app.core.metrics import metrics

router = APIRouter(tags=["Metrics"])


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus 指标",
    description="返回 Prometheus 格式的应用指标",
)
async def get_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format including:
    - HTTP request counts and latencies
    - Database connection pool status
    - Cache hit/miss rates
    - Error counts
    """
    # Update database pool metrics
    if hasattr(async_engine, "pool"):
        pool = async_engine.pool
        metrics.gauge("db_connections_active").set(pool.status() if hasattr(pool, "status") else 0)

    # Update cache metrics
    cache_conn = await get_cache_connection()
    if cache_conn.is_available:
        metrics.gauge("cache_available").set(1)
        try:
            # Get Redis info for more detailed metrics
            client = cache_conn.client
            if client:
                info = await client.info("memory")
                if "used_memory" in info:
                    metrics.gauge("cache_memory_bytes").set(info["used_memory"])

                info_stats = await client.info("stats")
                if "keyspace_hits" in info_stats and "keyspace_misses" in info_stats:
                    # These are cumulative since Redis start
                    pass
        except Exception:
            pass
    else:
        metrics.gauge("cache_available").set(0)

    # Export metrics in Prometheus format
    metrics_text = metrics.export_prometheus()

    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get(
    "/metrics/json",
    summary="JSON 格式指标",
    description="返回 JSON 格式的应用指标（便于调试）",
)
async def get_metrics_json():
    """
    JSON metrics endpoint for debugging.

    Returns the same metrics as /metrics but in JSON format.
    """
    # Collect metrics into a dictionary
    result = {
        "http_requests": {},
        "cache": {
            "available": False,
            "hits": 0,
            "misses": 0,
        },
        "database": {
            "connections_active": 0,
        },
        "collection": {
            "tasks_active": 0,
        },
    }

    # Get cache status
    cache_conn = await get_cache_connection()
    result["cache"]["available"] = cache_conn.is_available

    # Get database pool status
    if hasattr(async_engine, "pool"):
        pool = async_engine.pool
        result["database"]["connections_active"] = pool.status() if hasattr(pool, "status") else 0

    return result
