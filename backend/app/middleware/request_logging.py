"""
Request Logging Middleware

Logs incoming requests with timing and status information.
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all incoming requests.

    Logs include:
    - Request ID (unique per request)
    - Method and path
    - Response status code
    - Processing time in milliseconds
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Store request ID in state for access in handlers
        request.state.request_id = request_id

        # Log incoming request
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log completed request
        logger.info(
            f"Request completed: {request.method} {request.url.path} - "
            f"{response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
