"""Standard API response helpers."""

from datetime import UTC, datetime
from typing import Any

from fastapi import Request


def response_meta(request: Request) -> dict[str, str]:
    """Build metadata shared by API responses."""
    request_id = getattr(request.state, "request_id", "")
    return {
        "request_id": request_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def success_response(request: Request, data: Any) -> dict[str, Any]:
    """Return a standardized success payload."""
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": response_meta(request),
    }


def error_response(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    """Return a standardized error payload."""
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "meta": response_meta(request),
    }
