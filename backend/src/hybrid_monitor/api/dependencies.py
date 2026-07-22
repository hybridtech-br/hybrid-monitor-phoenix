"""Shared FastAPI dependencies."""

from collections.abc import AsyncIterator

from fastapi import Request


async def get_request_id(request: Request) -> str:
    """Return the request identifier assigned by the middleware."""
    return getattr(request.state, "request_id", "")


async def get_db_session() -> AsyncIterator[None]:
    """Placeholder database session dependency.

    This will be replaced by the SQLAlchemy Async session provider
    during the persistence implementation.
    """
    yield None
