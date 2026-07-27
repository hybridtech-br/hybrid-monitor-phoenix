"""Centralized application settings for Micael Monitor."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = "development-only-change-before-production"
MINIMUM_HMAC_SECRET_BYTES = 32


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and optional .env files."""

    app_name: str = "Micael Monitor"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://phoenix:phoenix@localhost:5432/phoenix"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    jwt_secret_key: SecretStr = SecretStr(DEVELOPMENT_JWT_SECRET)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "micael-monitor"
    jwt_audience: str = "micael-monitor-api"
    access_token_ttl_minutes: int = Field(default=15, gt=0, le=1440)
    refresh_token_ttl_days: int = Field(default=7, gt=0, le=90)

    model_config = SettingsConfigDict(
        env_prefix="PHOENIX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> Self:
        """Reject weak HMAC secrets and prevent default-secret use outside safe environments."""
        secret = self.jwt_secret_key.get_secret_value()
        if len(secret.encode("utf-8")) < MINIMUM_HMAC_SECRET_BYTES:
            raise ValueError(
                f"PHOENIX_JWT_SECRET_KEY must contain at least {MINIMUM_HMAC_SECRET_BYTES} bytes"
            )

        safe_environments = {"development", "test"}
        uses_default_secret = secret == DEVELOPMENT_JWT_SECRET
        if self.environment.lower() not in safe_environments and uses_default_secret:
            raise ValueError("PHOENIX_JWT_SECRET_KEY must be configured outside development/test")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""

    return Settings()
