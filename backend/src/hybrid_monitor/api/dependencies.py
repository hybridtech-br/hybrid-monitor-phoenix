"""Shared FastAPI dependencies."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from hybrid_monitor.core.security import (
    InvalidSecurityTokenError,
    TokenExpiredError,
    TokenType,
    decode_token,
)
from hybrid_monitor.core.session import session_scope
from hybrid_monitor.domain.identity.models import User
from hybrid_monitor.domain.identity.repositories import (
    SQLAlchemyUserRepository,
    UserRepository,
)
from hybrid_monitor.domain.identity.services import AuthenticationService

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_request_id(request: Request) -> str:
    """Return the request identifier assigned by the middleware."""

    return getattr(request.state, "request_id", "")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a transactional SQLAlchemy session for the current request."""

    async for session in session_scope():
        yield session


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    """Return the request-scoped Identity repository."""
    return SQLAlchemyUserRepository(session)


def get_authentication_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthenticationService:
    """Return the request-scoped authentication service."""
    return AuthenticationService(users)


def _unauthorized(detail: str = "Authentication credentials are invalid") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Resolve and validate the active user represented by an access token."""
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _unauthorized("Bearer access token is required")

    try:
        claims = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
        user_id = UUID(claims.sub)
    except TokenExpiredError as exc:
        raise _unauthorized("Access token has expired") from exc
    except (InvalidSecurityTokenError, ValueError) as exc:
        raise _unauthorized() from exc

    user = await users.get_by_id(user_id)
    if user is None:
        raise _unauthorized()
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


def require_permissions(*permission_codes: str) -> Callable[..., Awaitable[User]]:
    """Create a dependency that requires every listed effective permission."""
    required = frozenset(permission_codes)

    async def dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        effective = {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
        if not required.issubset(effective):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Required permission is missing",
                    "required": sorted(required),
                },
            )
        return user

    return dependency
