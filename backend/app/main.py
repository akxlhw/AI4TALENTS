"""
FastAPI application entry point.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api_router import api_router
from app.core.cache import close_cache_connection, get_cache_connection
from app.core.config import settings
from app.core.database import async_engine, async_session_factory
from app.core.logging_config import get_logger, setup_logging

# Setup logging first
setup_logging()
logger = get_logger(__name__)


async def init_proxy_config() -> None:
    """Initialize proxy configuration from database."""
    from app.domains.shared.services.common.http_client import HttpClientFactory
    from app.domains.shared.services.config_service import ConfigService

    try:
        async with async_session_factory() as session:
            config_service = ConfigService(session)
            proxy_config = await config_service.get_proxy_config()

            if proxy_config.enabled and proxy_config.url:
                HttpClientFactory.configure(
                    proxy_url=proxy_config.url,
                    proxy_username=proxy_config.username or None,
                    proxy_password=proxy_config.password or None,
                    no_proxy=proxy_config.no_proxy or None,
                    ssl_verify=proxy_config.ssl_verify,
                )
                logger.info(f"Proxy configuration loaded: {proxy_config.url}")
            else:
                logger.info("Proxy not enabled, using direct connection")
    except Exception as e:
        logger.warning(f"Failed to load proxy configuration: {e}")


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

    # Initialize proxy configuration
    await init_proxy_config()

    # Auto-resume loop for rate-limited open-source collect tasks
    from app.domains.open_source.services.os_collection_service import rate_limit_resume_loop

    resume_task = asyncio.create_task(rate_limit_resume_loop())

    yield

    # Shutdown
    resume_task.cancel()
    logger.info(f"Shutting down {settings.APP_NAME}")
    await close_cache_connection()
    await async_engine.dispose()


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="智能人才库 V2.0.4 API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    # Note: allow_credentials=True cannot be used with allow_origins=["*"]
    # Since we use JWT tokens in Authorization header (not cookies), we can disable credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
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

    # Register global exception handlers
    from app.core.exceptions import register_exception_handlers

    register_exception_handlers(app)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Static files for uploads
    upload_path = Path("uploads")
    upload_path.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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
