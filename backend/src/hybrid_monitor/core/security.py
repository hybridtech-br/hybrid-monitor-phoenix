"""Password hashing and signed-token primitives for Micael Monitor."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

import jwt
from jwt import ExpiredSignatureError
from jwt import InvalidTokenError as PyJWTInvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pydantic import BaseModel, ValidationError

from hybrid_monitor.core.settings import Settings, get_settings
from hybrid_monitor.core.time import utc_now

_password_hash = PasswordHash.recommended()


class TokenType(StrEnum):
    """Kinds of bearer tokens issued by the platform."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenClaims(BaseModel):
    """Validated claims required in every Micael Monitor token."""

    sub: str
    token_type: TokenType
    jti: UUID
    iat: datetime
    nbf: datetime
    exp: datetime
    iss: str
    aud: str


class SecurityTokenError(ValueError):
    """Base class for signed-token validation errors."""


class TokenExpiredError(SecurityTokenError):
    """Raised when a token is correctly signed but expired."""


class InvalidSecurityTokenError(SecurityTokenError):
    """Raised when a token cannot be trusted or parsed."""


def hash_password(password: str) -> str:
    """Hash a non-empty password with the recommended Argon2 configuration."""
    if not password:
        raise ValueError("Password must not be empty")
    return _password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    """Return whether a plaintext password matches a recognized encoded hash."""
    if not password or not encoded_hash:
        return False
    try:
        return _password_hash.verify(password, encoded_hash)
    except UnknownHashError:
        return False


def verify_and_update_password(password: str, encoded_hash: str) -> tuple[bool, str | None]:
    """Verify a password and return a replacement hash when parameters are outdated."""
    if not password or not encoded_hash:
        return False, None
    try:
        return _password_hash.verify_and_update(password, encoded_hash)
    except UnknownHashError:
        return False, None


def _require_aware_utc(value: datetime) -> datetime:
    """Normalize a timezone-aware timestamp to UTC."""
    if value.tzinfo is None:
        raise ValueError("Token timestamps must be timezone-aware")
    return value.astimezone(UTC)


def create_token(
    subject: UUID | str,
    token_type: TokenType,
    lifetime: timedelta,
    *,
    settings: Settings | None = None,
    issued_at: datetime | None = None,
) -> str:
    """Create a signed JWT with the platform's mandatory claims."""
    if lifetime <= timedelta(0):
        raise ValueError("Token lifetime must be positive")

    runtime_settings = settings or get_settings()
    now = _require_aware_utc(issued_at or utc_now())
    expires_at = now + lifetime
    payload = {
        "sub": str(subject),
        "token_type": token_type.value,
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "iss": runtime_settings.jwt_issuer,
        "aud": runtime_settings.jwt_audience,
    }
    return jwt.encode(
        payload,
        runtime_settings.jwt_secret_key.get_secret_value(),
        algorithm=runtime_settings.jwt_algorithm,
    )


def create_access_token(
    subject: UUID | str,
    *,
    settings: Settings | None = None,
    issued_at: datetime | None = None,
) -> str:
    """Create a short-lived access token."""
    runtime_settings = settings or get_settings()
    return create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=runtime_settings.access_token_ttl_minutes),
        settings=runtime_settings,
        issued_at=issued_at,
    )


def create_refresh_token(
    subject: UUID | str,
    *,
    settings: Settings | None = None,
    issued_at: datetime | None = None,
) -> str:
    """Create a longer-lived refresh token."""
    runtime_settings = settings or get_settings()
    return create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=runtime_settings.refresh_token_ttl_days),
        settings=runtime_settings,
        issued_at=issued_at,
    )


def decode_token(
    token: str,
    *,
    expected_type: TokenType | None = None,
    settings: Settings | None = None,
) -> TokenClaims:
    """Verify a JWT signature and return strongly validated claims."""
    runtime_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            runtime_settings.jwt_secret_key.get_secret_value(),
            algorithms=[runtime_settings.jwt_algorithm],
            audience=runtime_settings.jwt_audience,
            issuer=runtime_settings.jwt_issuer,
            options={
                "require": [
                    "sub",
                    "token_type",
                    "jti",
                    "iat",
                    "nbf",
                    "exp",
                    "iss",
                    "aud",
                ]
            },
        )
        claims = TokenClaims.model_validate(payload)
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except (PyJWTInvalidTokenError, ValidationError, ValueError, TypeError) as exc:
        raise InvalidSecurityTokenError("Token is invalid") from exc

    if expected_type is not None and claims.token_type is not expected_type:
        raise InvalidSecurityTokenError(
            f"Expected a {expected_type.value} token, received {claims.token_type.value}"
        )
    return claims
