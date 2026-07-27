"""Async SQLAlchemy engine configuration."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from hybrid_monitor.core.settings import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
)


async def dispose_database_engine() -> None:
    """Dispose the database connection pool during application shutdown."""

    await engine.dispose()
