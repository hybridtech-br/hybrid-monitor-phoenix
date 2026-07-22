"""Shared FastAPI dependencies."""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from hybrid_monitor.core.session import session_scope


async def get_request_id(request: Request) -> str:
    """Return the request identifier assigned by the middleware."""

    return getattr(request.state, "request_id", "")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a transactional SQLAlchemy session for the current request."""

    async for session in session_scope():
        yield session
