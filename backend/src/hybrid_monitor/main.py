"""Application entrypoint for HYBRID Monitor Phoenix."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import AsyncIterator

import structlog
from fastapi import FastAPI

from hybrid_monitor.api.middleware import RequestContextMiddleware
from hybrid_monitor.api.v1.router import router as api_v1_router
from hybrid_monitor.core.logging import configure_logging
from hybrid_monitor.core.settings import get_settings

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown events."""
    logger.info(
        "application_started",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
    yield
    logger.info("application_stopped", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Core API da plataforma de Inteligencia Situacional HYBRID Monitor, "
        "integrante da familia Micael."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.include_router(api_v1_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Return service health information."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/version", tags=["system"])
async def version() -> dict[str, str]:
    """Return application version metadata."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/runtime", tags=["system"])
async def runtime() -> dict[str, str | int]:
    """Return non-sensitive runtime configuration."""
    return {
        "api_prefix": settings.api_prefix,
        "host": settings.host,
        "port": settings.port,
        "log_level": settings.log_level,
    }
