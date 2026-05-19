import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

router = APIRouter()


@router.get("/test/unhandled-error")
async def unhandled_error():
    raise RuntimeError("boom")


app.include_router(router)


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
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/test/unhandled-error")

    assert response.status_code == 500
    assert response.json() == {"code": "internal_error", "message": "Internal server error", "data": None}


def test_production_rejects_default_api_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_KEY", "dev-api-key")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="API_KEY"), TestClient(app):
        pass

    get_settings.cache_clear()
