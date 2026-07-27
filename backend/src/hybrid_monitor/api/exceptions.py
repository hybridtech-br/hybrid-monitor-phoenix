"""Global exception handlers for the Micael Monitor API."""

from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from hybrid_monitor.api.responses import error_response

logger = structlog.get_logger(__name__)


def _http_error_code(status_code: int) -> str:
    """Return a stable machine-readable code for an HTTP status."""
    return f"http_{status_code}"


def _json_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a JSON-safe response using the shared API error envelope."""
    payload = error_response(
        request,
        code=code,
        message=message,
        details=details,
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Serialize FastAPI HTTP exceptions using the standard API envelope."""
    message = exc.detail if isinstance(exc.detail, str) else "HTTP request failed"
    details: Any | None = None if isinstance(exc.detail, str) else exc.detail
    return _json_error_response(
        request,
        status_code=exc.status_code,
        code=_http_error_code(exc.status_code),
        message=message,
        details=details,
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Serialize request validation errors using the standard API envelope."""
    return _json_error_response(
        request,
        status_code=422,
        code="request_validation_error",
        message="Request validation failed",
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected errors and return a safe generic response."""
    logger.exception(
        "unhandled_exception",
        request_id=getattr(request.state, "request_id", ""),
        method=request.method,
        path=request.url.path,
        exception_type=type(exc).__name__,
    )
    return _json_error_response(
        request,
        status_code=500,
        code="internal_server_error",
        message="An unexpected error occurred",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the application."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
