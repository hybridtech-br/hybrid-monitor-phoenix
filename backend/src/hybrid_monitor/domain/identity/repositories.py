"""Identity repository contracts and SQLAlchemy implementations."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hybrid_monitor.core.time import utc_now
from hybrid_monitor.domain.identity.models import AuthSession, Role, User


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


class AuthSessionRepository(Protocol):
    """Persistence operations required for refresh-session lifecycle management."""

    async def create(
        self,
        *,
        user_id: UUID,
        refresh_jti: UUID,
        expires_at: datetime,
    ) -> AuthSession:
        """Create and persist a refresh-token session."""
        ...

    async def get_by_jti(self, refresh_jti: UUID) -> AuthSession | None:
        """Return a session by the refresh-token identifier."""
        ...

    async def touch(self, session: AuthSession, *, used_at: datetime | None = None) -> None:
        """Record the most recent successful use of a session."""
        ...

    async def revoke(
        self,
        session: AuthSession,
        *,
        reason: str,
        revoked_at: datetime | None = None,
    ) -> None:
        """Revoke one session idempotently."""
        ...

    async def revoke_all(
        self,
        user_id: UUID,
        *,
        reason: str,
        revoked_at: datetime | None = None,
    ) -> int:
        """Revoke every active session belonging to a user."""
        ...

    async def delete_expired(self, *, before: datetime | None = None) -> int:
        """Delete sessions expired before the supplied timestamp."""
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


class SQLAlchemyAuthSessionRepository:
    """SQLAlchemy-backed authentication-session repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        refresh_jti: UUID,
        expires_at: datetime,
    ) -> AuthSession:
        auth_session = AuthSession(
            user_id=user_id,
            refresh_jti=refresh_jti,
            expires_at=expires_at,
        )
        self._session.add(auth_session)
        await self._session.flush()
        return auth_session

    async def get_by_jti(self, refresh_jti: UUID) -> AuthSession | None:
        result = await self._session.execute(
            select(AuthSession).where(AuthSession.refresh_jti == refresh_jti)
        )
        return result.scalar_one_or_none()

    async def touch(self, session: AuthSession, *, used_at: datetime | None = None) -> None:
        session.last_used_at = used_at or utc_now()
        await self._session.flush()

    async def revoke(
        self,
        session: AuthSession,
        *,
        reason: str,
        revoked_at: datetime | None = None,
    ) -> None:
        if session.revoked_at is None:
            session.revoked_at = revoked_at or utc_now()
            session.revocation_reason = reason
            await self._session.flush()

    async def revoke_all(
        self,
        user_id: UUID,
        *,
        reason: str,
        revoked_at: datetime | None = None,
    ) -> int:
        result = await self._session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(
                revoked_at=revoked_at or utc_now(),
                revocation_reason=reason,
            )
        )
        return int(result.rowcount or 0)

    async def delete_expired(self, *, before: datetime | None = None) -> int:
        result = await self._session.execute(
            delete(AuthSession).where(AuthSession.expires_at < (before or utc_now()))
        )
        return int(result.rowcount or 0)
