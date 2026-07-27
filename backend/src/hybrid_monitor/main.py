"""Application entrypoint for Micael Monitor."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, AsyncIterator

import structlog
from fastapi import FastAPI, Request

from hybrid_monitor.api.exceptions import register_exception_handlers
from hybrid_monitor.api.middleware import RequestContextMiddleware
from hybrid_monitor.api.responses import success_response
from hybrid_monitor.api.v1.router import router as api_v1_router
from hybrid_monitor.core.database import dispose_database_engine
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
    try:
        yield
    finally:
        await dispose_database_engine()
        logger.info("application_stopped", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Core API da plataforma de inteligência situacional Micael Monitor, "
        "integrante da família Micael."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)
app.include_router(api_v1_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
async def health(request: Request) -> dict[str, Any]:
    """Return service health information."""
    return success_response(
        request,
        {
            "status": "ok",
            "service": settings.app_name,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.get("/version", tags=["system"])
async def version(request: Request) -> dict[str, Any]:
    """Return application version metadata."""
    return success_response(
        request,
        {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
    )


@app.get("/runtime", tags=["system"])
async def runtime(request: Request) -> dict[str, Any]:
    """Return non-sensitive runtime configuration."""
    return success_response(
        request,
        {
            "api_prefix": settings.api_prefix,
            "host": settings.host,
            "port": settings.port,
            "log_level": settings.log_level,
        },
    )
