"""Authentication API contract tests."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from hybrid_monitor.api.dependencies import (
    get_authentication_service,
    get_current_user,
)
from hybrid_monitor.core.security import hash_password
from hybrid_monitor.core.settings import Settings
from hybrid_monitor.domain.identity.models import Permission, Role, User
from hybrid_monitor.domain.identity.services import AuthenticationService
from hybrid_monitor.main import app

TEST_JWT_SECRET = "authentication-api-secret-that-is-long-enough"
client = TestClient(app)


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user

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


def build_user() -> User:
    permission = Permission(id=uuid4(), code="cameras.read", description="View cameras")
    role = Role(id=uuid4(), name="Operator", description="Operations user")
    role.permissions = [permission]
    user = User(
        id=uuid4(),
        name="Micael Operator",
        email="operator@hybrid.local",
        password_hash=hash_password("correct-password"),
        is_active=True,
    )
    user.roles = [role]
    return user


def test_login_returns_standard_session_envelope() -> None:
    user = build_user()
    settings = Settings(environment="test", jwt_secret_key=TEST_JWT_SECRET)
    service = AuthenticationService(FakeUserRepository(user), settings)
    app.dependency_overrides[get_authentication_service] = lambda: service
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": " Operator@HYBRID.Local ", "password": "correct-password"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["user"]["email"] == user.email
    assert payload["data"]["user"]["roles"] == ["Operator"]
    assert payload["data"]["user"]["permissions"] == ["cameras.read"]
    assert payload["data"]["tokens"]["token_type"] == "bearer"
    assert "password" not in str(payload)


def test_login_rejects_invalid_credentials_without_account_disclosure() -> None:
    settings = Settings(environment="test", jwt_secret_key=TEST_JWT_SECRET)
    service = AuthenticationService(FakeUserRepository(None), settings)
    app.dependency_overrides[get_authentication_service] = lambda: service
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@hybrid.local", "password": "wrong-password"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "http_401"
    assert payload["error"]["message"] == "Invalid email or password"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_current_session_returns_effective_authorization_context() -> None:
    user = build_user()
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = client.get("/api/v1/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(user.id)
    assert data["roles"] == ["Operator"]
    assert data["permissions"] == ["cameras.read"]
