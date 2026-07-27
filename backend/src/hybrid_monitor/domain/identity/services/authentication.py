"""Authentication use cases for the Micael Monitor Identity domain."""

from dataclasses import dataclass
from uuid import UUID

from hybrid_monitor.core.security import (
    InvalidSecurityTokenError,
    TokenExpiredError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_and_update_password,
    verify_password,
)
from hybrid_monitor.core.settings import Settings, get_settings
from hybrid_monitor.domain.identity.models import User
from hybrid_monitor.domain.identity.repositories import UserRepository

_DUMMY_PASSWORD_HASH = hash_password("micael-monitor-authentication-timing-placeholder")


class AuthenticationError(ValueError):
    """Base class for authentication use-case failures."""


class InvalidCredentialsError(AuthenticationError):
    """Raised when an email/password pair cannot be authenticated."""


class InactiveUserError(AuthenticationError):
    """Raised when valid credentials belong to a disabled user."""


class InvalidRefreshTokenError(AuthenticationError):
    """Raised when a refresh token cannot establish a valid session."""


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Access and refresh credentials issued together."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    """Authenticated user and the credentials issued for the session."""

    user: User
    tokens: TokenPair


class AuthenticationService:
    """Authenticate users and rotate refresh credentials."""

    def __init__(
        self,
        users: UserRepository,
        settings: Settings | None = None,
    ) -> None:
        self._users = users
        self._settings = settings or get_settings()

    @staticmethod
    def normalize_email(email: str) -> str:
        """Return the canonical representation used for identity lookups."""
        return email.strip().casefold()

    def _issue_token_pair(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user.id, settings=self._settings),
            refresh_token=create_refresh_token(user.id, settings=self._settings),
            expires_in=self._settings.access_token_ttl_minutes * 60,
        )

    async def authenticate(self, email: str, password: str) -> AuthenticatedSession:
        """Authenticate a user without revealing which credential was incorrect."""
        normalized_email = self.normalize_email(email)
        user = await self._users.get_by_email(normalized_email)
        if user is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError("Invalid email or password")

        valid, replacement_hash = verify_and_update_password(password, user.password_hash)
        if not valid:
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InactiveUserError("User account is inactive")
        if replacement_hash is not None:
            await self._users.update_password_hash(user, replacement_hash)

        return AuthenticatedSession(user=user, tokens=self._issue_token_pair(user))

    async def refresh(self, refresh_token: str) -> AuthenticatedSession:
        """Rotate a valid refresh token and issue a new token pair."""
        try:
            claims = decode_token(
                refresh_token,
                expected_type=TokenType.REFRESH,
                settings=self._settings,
            )
            user_id = UUID(claims.sub)
        except (InvalidSecurityTokenError, TokenExpiredError, ValueError) as exc:
            raise InvalidRefreshTokenError("Refresh token is invalid") from exc

        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("Refresh token is invalid")

        return AuthenticatedSession(user=user, tokens=self._issue_token_pair(user))
