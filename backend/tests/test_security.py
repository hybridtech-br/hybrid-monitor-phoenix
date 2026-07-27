"""Password and signed-token security regression tests."""

from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from hybrid_monitor.core.security import (
    InvalidSecurityTokenError,
    TokenExpiredError,
    TokenType,
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    verify_and_update_password,
    verify_password,
)
from hybrid_monitor.core.settings import Settings
from hybrid_monitor.core.time import utc_now


def test_password_hash_is_salted_and_verifiable() -> None:
    password = "Micael-Monitor-Test-Password"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash) is True
    assert verify_password("wrong-password", first_hash) is False


def test_password_verification_rejects_unknown_hashes_safely() -> None:
    assert verify_password("password", "not-a-recognized-hash") is False
    assert verify_and_update_password("password", "not-a-recognized-hash") == (False, None)


def test_access_token_contains_required_claims() -> None:
    settings = Settings(environment="test", jwt_secret_key="test-secret-key")
    subject = uuid4()

    token = create_access_token(subject, settings=settings)
    claims = decode_token(token, expected_type=TokenType.ACCESS, settings=settings)

    assert claims.sub == str(subject)
    assert claims.token_type is TokenType.ACCESS
    assert claims.iss == settings.jwt_issuer
    assert claims.aud == settings.jwt_audience
    assert claims.exp > claims.iat


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    settings = Settings(environment="test", jwt_secret_key="test-secret-key")
    token = create_refresh_token(uuid4(), settings=settings)

    with pytest.raises(InvalidSecurityTokenError, match="Expected an access token"):
        decode_token(token, expected_type=TokenType.ACCESS, settings=settings)


def test_expired_token_is_reported_separately() -> None:
    settings = Settings(environment="test", jwt_secret_key="test-secret-key")
    token = create_token(
        uuid4(),
        TokenType.ACCESS,
        timedelta(seconds=1),
        settings=settings,
        issued_at=utc_now() - timedelta(minutes=1),
    )

    with pytest.raises(TokenExpiredError):
        decode_token(token, settings=settings)


def test_tampered_token_is_rejected() -> None:
    settings = Settings(environment="test", jwt_secret_key="test-secret-key")
    token = create_access_token(uuid4(), settings=settings)
    replacement = "a" if token[-1] != "a" else "b"
    tampered = f"{token[:-1]}{replacement}"

    with pytest.raises(InvalidSecurityTokenError):
        decode_token(tampered, settings=settings)


def test_production_rejects_repository_development_secret() -> None:
    with pytest.raises(ValidationError, match="PHOENIX_JWT_SECRET_KEY"):
        Settings(environment="production")


def test_production_accepts_explicit_secret() -> None:
    settings = Settings(
        environment="production",
        jwt_secret_key="replace-with-a-secret-from-the-deployment-vault",
    )

    assert settings.environment == "production"
