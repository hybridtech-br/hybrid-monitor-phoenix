"""Authentication-service unit tests."""

from uuid import UUID, uuid4

import pytest

from hybrid_monitor.core.security import TokenType, decode_token, hash_password
from hybrid_monitor.core.settings import Settings
from hybrid_monitor.domain.identity.models import Permission, Role, User
from hybrid_monitor.domain.identity.services import (
    AuthenticationService,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

TEST_JWT_SECRET = "authentication-test-secret-that-is-long-enough"


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.updated_hash: str | None = None

    async def get_by_id(self, user_id: UUID) -> User | None:
        if self.user is not None and self.user.id == user_id:
            return self.user
        return None

    async def get_by_email(self, email: str) -> User | None:
        if self.user is not None and self.user.email == email:
            return self.user
        return None

    async def update_password_hash(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        self.updated_hash = password_hash


def build_user(*, active: bool = True) -> User:
    permission = Permission(
        id=uuid4(),
        code="cameras.read",
        description="View cameras",
    )
    role = Role(
        id=uuid4(),
        name="Operator",
        description="Operations user",
    )
    role.permissions = [permission]
    user = User(
        id=uuid4(),
        name="Micael Operator",
        email="operator@hybrid.local",
        password_hash=hash_password("correct-password"),
        is_active=active,
    )
    user.roles = [role]
    return user


def test_normalize_email_is_deterministic() -> None:
    assert (
        AuthenticationService.normalize_email("  Operator@HYBRID.Local ")
        == "operator@hybrid.local"
    )


@pytest.mark.asyncio
async def test_authenticate_issues_access_and_refresh_tokens() -> None:
    user = build_user()
    repository = FakeUserRepository(user)
    settings = Settings(environment="test", jwt_secret_key=TEST_JWT_SECRET)
    service = AuthenticationService(repository, settings)

    session = await service.authenticate(" Operator@HYBRID.Local ", "correct-password")

    access = decode_token(
        session.tokens.access_token,
        expected_type=TokenType.ACCESS,
        settings=settings,
    )
    refresh = decode_token(
        session.tokens.refresh_token,
        expected_type=TokenType.REFRESH,
        settings=settings,
    )
    assert session.user is user
    assert access.sub == str(user.id)
    assert refresh.sub == str(user.id)
    assert session.tokens.expires_in == settings.access_token_ttl_minutes * 60


@pytest.mark.asyncio
async def test_authenticate_rejects_unknown_user_and_wrong_password() -> None:
    settings = Settings(environment="test", jwt_secret_key=TEST_JWT_SECRET)

    with pytest.raises(InvalidCredentialsError):
        await AuthenticationService(FakeUserRepository(None), settings).authenticate(
            "missing@hybrid.local",
            "anything",
        )

    user = build_user()
    with pytest.raises(InvalidCredentialsError):
        await AuthenticationService(FakeUserRepository(user), settings).authenticate(
            user.email,
            "wrong-password",
        )


@pytest.mark.asyncio
async def test_authenticate_rejects_inactive_user() -> None:
    user = build_user(active=False)
    settings = Settings(environment="test", jwt_secret_key=TEST_JWT_SECRET)

    with pytest.raises(InactiveUserError):
        await AuthenticationService(FakeUserRepository(user), settings).authenticate(
            user.email,
            "correct-password",
        )


@pytest.mark.asyncio
async def test_refresh_rotates_tokens_for_an_active_user() -> None:
    user = build_user()
    repository = FakeUserRepository(user)
    settings = Settings(environment="test", jwt_secret_key=TEST_JWT_SECRET)
    service = AuthenticationService(repository, settings)
    initial = await service.authenticate(user.email, "correct-password")

    rotated = await service.refresh(initial.tokens.refresh_token)

    assert rotated.user is user
    assert rotated.tokens.access_token != initial.tokens.access_token
    assert rotated.tokens.refresh_token != initial.tokens.refresh_token


@pytest.mark.asyncio
async def test_refresh_rejects_access_token() -> None:
    user = build_user()
    repository = FakeUserRepository(user)
    settings = Settings(environment="test", jwt_secret_key=TEST_JWT_SECRET)
    service = AuthenticationService(repository, settings)
    initial = await service.authenticate(user.email, "correct-password")

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(initial.tokens.access_token)
