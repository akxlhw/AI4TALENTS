"""
Global exception handlers and custom exceptions.
统一异常处理机制 - v1.4
"""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.logging_config import get_logger

logger = get_logger(__name__)


# ============ Custom Exceptions ============


class AppException(Exception):
    """Base exception for application-specific errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, resource: str, identifier: str | int | None = None) -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """Resource conflict error (e.g., duplicate entry)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status.HTTP_409_CONFLICT, details)


class BadRequestError(AppException):
    """Bad request error (invalid input)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class UnauthorizedError(AppException):
    """Authentication error."""

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    """Authorization error."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ExternalServiceError(AppException):
    """External service error (e.g., LLM, OpenAlex API)."""

    def __init__(self, service: str, message: str | None = None) -> None:
        msg = f"External service error: {service}"
        if message:
            msg = f"{msg} - {message}"
        super().__init__(msg, status.HTTP_502_BAD_GATEWAY)


# ============ Error Response Builder ============


def build_error_response(
    status_code: int,
    message: str,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build standardized error response."""
    response: dict[str, Any] = {
        "detail": message,
    }
    if request_id:
        response["request_id"] = request_id
    if details:
        response["details"] = details
    return response


# ============ Exception Handlers ============


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application-specific exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        f"App exception: {exc.message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(
            exc.status_code,
            exc.message,
            request_id,
            exc.details,
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # Log client errors (4xx) as warning, server errors (5xx) as error
    log_level = "warning" if 400 <= exc.status_code < 500 else "error"
    getattr(logger, log_level)(
        f"HTTP exception: {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(
            exc.status_code,
            str(exc.detail),
            request_id,
        ),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    request_id = getattr(request.state, "request_id", None)

    # Format validation errors
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        f"Validation error: {len(errors)} errors",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
            request_id,
            {"errors": errors},
        ),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    request_id = getattr(request.state, "request_id", None)

    # Determine specific error type
    if isinstance(exc, IntegrityError):
        status_code = status.HTTP_409_CONFLICT
        message = "Database constraint violation"
        details = {"type": "integrity_error"}
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Database error"
        details = None

    logger.error(
        f"Database error: {exc}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status_code,
        content=build_error_response(status_code, message, request_id, details),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            request_id,
        ),
    )


# ============ Register Handlers ============


def register_exception_handlers(app: Any) -> None:
    """Register all exception handlers with the FastAPI app."""
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("app must be a FastAPI instance")

    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")
