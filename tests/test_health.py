import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.errors import install_error_handlers
from app.main import app


def test_health_returns_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ops_ui_serves_spa_index():
    client = TestClient(app)

    response = client.get("/ops")

    assert response.status_code == 200
    assert "Notification Ops" in response.text


def test_unhandled_error_uses_api_response_shape():
    isolated_app = FastAPI()
    install_error_handlers(isolated_app)

    @isolated_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    client = TestClient(isolated_app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"code": "internal_error", "message": "Internal server error", "data": None}


def test_unknown_route_returns_api_response_shape():
    client = TestClient(app)

    response = client.get("/api/this-route-does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"code", "message", "data"}
    assert body["code"] == "http_error"


def test_production_rejects_default_api_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_KEY", "dev-api-key")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="API_KEY"), TestClient(app):
        pass

    get_settings.cache_clear()


def test_production_rejects_default_provider_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_KEY", "prod-rotated-key")
    monkeypatch.setenv("PROVIDER_CRM_API_KEY", "dev-crm-key")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="PROVIDER_CRM_API_KEY"), TestClient(app):
        pass

    get_settings.cache_clear()


def test_production_cors_defaults_do_not_allow_localhost():
    settings = Settings(app_env="production", api_key="prod-key")

    assert settings.effective_cors_allowed_origins() == []
