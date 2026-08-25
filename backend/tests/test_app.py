"""API startup and endpoint tests."""

from fastapi import FastAPI


def test_application_startup(client):
    from app.main import app

    assert isinstance(app, FastAPI)
    assert app.title == "AeroGuard"


def test_health_endpoint(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "healthy"
    assert response.headers["X-Correlation-ID"]


def test_system_info_endpoint(client):
    response = client.get("/api/v1/system/info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["application"] == "AeroGuard"
    assert payload["version"] == "0.1.0"
    assert payload["python_version"]
    assert payload["platform"]