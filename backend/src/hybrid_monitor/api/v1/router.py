"""Top-level router for version 1 of the HYBRID Monitor API."""

from datetime import UTC, datetime

from fastapi import APIRouter

from hybrid_monitor.core.settings import get_settings

settings = get_settings()
router = APIRouter()


@router.get("/health", tags=["system"])
async def api_health() -> dict[str, str]:
    """Return versioned API health information."""

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
    }
