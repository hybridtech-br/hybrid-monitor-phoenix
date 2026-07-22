"""Async SQLAlchemy session management."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hybrid_monitor.core.database import engine

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def session_scope() -> AsyncIterator[AsyncSession]:
    """Yield a transactional database session.

    The transaction is committed on success and rolled back when an exception
    escapes the request or service boundary.
    """

    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
