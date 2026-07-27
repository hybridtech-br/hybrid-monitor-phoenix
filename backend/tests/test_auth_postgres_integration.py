"""End-to-end Identity smoke test against the CI PostgreSQL service."""

import os

import pytest
from fastapi.testclient import TestClient

from hybrid_monitor.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PHOENIX_RUN_POSTGRES_TESTS") != "1",
        reason="PostgreSQL integration test is disabled",
    ),
]


def test_bootstrapped_administrator_can_login_refresh_and_read_session() -> None:
    email = os.environ["PHOENIX_BOOTSTRAP_ADMIN_EMAIL"]
    password = os.environ["PHOENIX_BOOTSTRAP_ADMIN_PASSWORD"]

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        login_data = login.json()["data"]
        access_token = login_data["tokens"]["access_token"]
        refresh_token = login_data["tokens"]["refresh_token"]
        assert "Administrator" in login_data["user"]["roles"]
        assert "system.admin" in login_data["user"]["permissions"]

        current = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert current.status_code == 200, current.text
        assert current.json()["data"]["email"] == email

        refreshed = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refreshed.status_code == 200, refreshed.text
        refreshed_tokens = refreshed.json()["data"]["tokens"]
        assert refreshed_tokens["access_token"] != access_token
        assert refreshed_tokens["refresh_token"] != refresh_token
