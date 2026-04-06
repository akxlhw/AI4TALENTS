"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.cache import close_cache_connection, get_cache_connection
from app.core.config import settings
from app.core.database import async_engine
from app.core.logging_config import get_logger, setup_logging

# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events handler."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_ENABLED}")

    # Initialize cache connection
    cache_conn = await get_cache_connection()
    if cache_conn.is_available:
        logger.info("Cache layer enabled: Redis connected")
    else:
        logger.info("Cache layer disabled: running in direct database mode")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")
    await close_cache_connection()
    await async_engine.dispose()


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="智能人才库 - 学术人才子系统 MVP API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Metrics middleware (must be early to capture all requests)
    from app.middleware.metrics import MetricsMiddleware
    app.add_middleware(MetricsMiddleware)

    # Rate limiting middleware (must be added before request logging)
    if settings.RATE_LIMIT_ENABLED:
        from app.middleware.rate_limit import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)

    # Request logging middleware
    from app.middleware.request_logging import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled exception: {exc}",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
        )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()


@app.get("/", tags=["Root"])
async def root(request: Request):
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
