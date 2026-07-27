"""Pydantic contracts exposed by the Identity API."""

from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator

from hybrid_monitor.domain.identity.models import User
from hybrid_monitor.domain.identity.services.authentication import (
    AuthenticatedSession,
    TokenPair,
)


class LoginRequest(BaseModel):
    """Email/password credentials accepted by the login endpoint."""

    email: str = Field(min_length=3, max_length=255)
    password: SecretStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if "@" not in normalized:
            raise ValueError("Email address is invalid")
        return normalized


class RefreshTokenRequest(BaseModel):
    """Refresh credential accepted during token rotation."""

    refresh_token: str = Field(min_length=20, max_length=4096)


class TokenPairResponse(BaseModel):
    """Bearer credentials returned to an authenticated client."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenPairResponse":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            token_type=pair.token_type,
            expires_in=pair.expires_in,
        )


class CurrentUserResponse(BaseModel):
    """Safe identity and effective authorization data for the current session."""

    id: UUID
    name: str
    email: str
    is_active: bool
    roles: list[str]
    permissions: list[str]

    @classmethod
    def from_user(cls, user: User) -> "CurrentUserResponse":
        permissions = {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active,
            roles=sorted(role.name for role in user.roles),
            permissions=sorted(permissions),
        )


class AuthenticatedSessionResponse(BaseModel):
    """Safe login/refresh payload returned inside the API success envelope."""

    user: CurrentUserResponse
    tokens: TokenPairResponse

    @classmethod
    def from_session(cls, session: AuthenticatedSession) -> "AuthenticatedSessionResponse":
        return cls(
            user=CurrentUserResponse.from_user(session.user),
            tokens=TokenPairResponse.from_pair(session.tokens),
        )
