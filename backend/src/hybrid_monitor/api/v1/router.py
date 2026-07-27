"""Top-level router for version 1 of the Micael Monitor API."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from hybrid_monitor.api.responses import success_response
from hybrid_monitor.core.settings import get_settings

settings = get_settings()
router = APIRouter()


@router.get("/health", tags=["system"])
async def api_health(request: Request) -> dict[str, Any]:
    """Return versioned API health information."""

    return success_response(
        request,
        {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
