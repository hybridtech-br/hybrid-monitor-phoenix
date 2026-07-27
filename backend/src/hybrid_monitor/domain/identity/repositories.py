"""Identity repository contracts and SQLAlchemy implementations."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hybrid_monitor.domain.identity.models import Role, User


class UserRepository(Protocol):
    """Persistence operations required by authentication and authorization."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user and its authorization graph by identifier."""
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Return a user and its authorization graph by normalized email."""
        ...

    async def update_password_hash(self, user: User, password_hash: str) -> None:
        """Persist a replacement password hash in the current transaction."""
        ...


class SQLAlchemyUserRepository:
    """SQLAlchemy-backed implementation of the user repository contract."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        statement = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update_password_hash(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        await self._session.flush()
