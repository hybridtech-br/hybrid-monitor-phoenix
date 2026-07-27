"""System endpoint and API-envelope regression tests."""

from fastapi.testclient import TestClient

from hybrid_monitor.main import app

client = TestClient(app)


def test_root_health_uses_standard_success_envelope() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["service"] == "Micael Monitor"
    assert payload["error"] is None
    assert payload["meta"]["request_id"] == response.headers["X-Request-ID"]
    assert float(response.headers["X-Process-Time-Ms"]) >= 0


def test_versioned_health_exposes_version_metadata() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["service"] == "Micael Monitor"
    assert payload["data"]["version"] == "0.1.0"


def test_request_id_is_preserved_when_client_supplies_one() -> None:
    request_id = "micael-monitor-test-request"
    response = client.get("/version", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["meta"]["request_id"] == request_id


def test_not_found_uses_standard_error_envelope() -> None:
    response = client.get("/resource-that-does-not-exist")

    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] == "http_404"
    assert payload["error"]["message"] == "Not Found"
    assert payload["meta"]["request_id"] == response.headers["X-Request-ID"]


def test_runtime_does_not_expose_database_credentials() -> None:
    response = client.get("/runtime")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["api_prefix"] == "/api/v1"
    assert "database_url" not in data
    assert "password" not in data
