from sqlalchemy import select

from app.models import Notification, NotificationStatus, Provider
from app.security import require_api_key


async def test_submit_notification_returns_accepted(api_client, monkeypatch, caplog):
    sent_messages = []

    class FakeActor:
        @staticmethod
        def send(notification_id: str) -> None:
            sent_messages.append(notification_id)

    monkeypatch.setattr("app.services.notifications.actor_for_queue", lambda queue_name: FakeActor)

    with caplog.at_level("INFO", logger="app.services.notifications"):
        response = await api_client.post(
            "/api/notifications",
            json={
                "provider_code": "crm",
                "event_type": "subscription_paid",
                "event_id": "evt_1",
                "payload": {
                    "user_id": "u_123",
                    "email": "alice@example.com",
                    "subscription_id": "sub_1",
                    "amount": 19900,
                    "currency": "USD",
                    "paid_at": "2026-05-19T10:00:00Z",
                },
                "metadata": {"source_system": "billing", "trace_id": "trace_1"},
            },
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["provider_code"] == "crm"
    assert data["status"] == "pending"
    assert data["event_id"] == "evt_1"
    assert sent_messages == [data["id"]]
    enqueue_records = [r for r in caplog.records if r.message.startswith("notification_enqueued ")]
    assert len(enqueue_records) == 1
    assert f"notification_id={data['id']}" in enqueue_records[0].message
    assert "trace_id=trace_1" in enqueue_records[0].message


async def test_submit_notification_marks_failed_when_enqueue_fails(api_client, db_session, monkeypatch):
    class BrokenActor:
        @staticmethod
        def send(notification_id: str) -> None:
            raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.services.notifications.actor_for_queue", lambda queue_name: BrokenActor)

    response = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "crm",
            "event_type": "subscription_paid",
            "event_id": "evt_enqueue_failed",
            "payload": {
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
            },
        },
    )

    assert response.status_code == 503
    assert response.json()["code"] == "enqueue_failed"
    notification = await db_session.scalar(select(Notification).where(Notification.event_id == "evt_enqueue_failed"))
    assert notification.status == NotificationStatus.failed
    assert notification.last_error == "enqueue_failed"


async def test_duplicate_submission_returns_existing_notification(api_client):
    payload = {
        "provider_code": "crm",
        "event_type": "subscription_paid",
        "event_id": "evt_dup",
        "payload": {
            "user_id": "u_123",
            "email": "alice@example.com",
            "subscription_id": "sub_1",
            "amount": 19900,
            "currency": "USD",
            "paid_at": "2026-05-19T10:00:00Z",
        },
    }

    first = await api_client.post("/api/notifications", json=payload)
    second = await api_client.post("/api/notifications", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["data"]["id"] == first.json()["data"]["id"]


async def test_unknown_provider_is_rejected(api_client):
    response = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "missing",
            "event_type": "subscription_paid",
            "event_id": "evt_missing",
            "payload": {},
        },
    )

    assert response.status_code == 404
    assert response.json()["code"] == "provider_not_found"


async def test_invalid_api_key_is_rejected(api_client):
    response = await api_client.get(
        "/api/notifications/00000000-0000-0000-0000-000000000000",
        headers={"X-API-Key": "bad-key"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_api_key_comparison_uses_compare_digest(monkeypatch):
    compared = {}

    def fake_compare_digest(left: str, right: str) -> bool:
        compared["args"] = (left, right)
        return True

    monkeypatch.setattr("secrets.compare_digest", fake_compare_digest)

    await require_api_key("dev-api-key")

    assert compared["args"] == ("dev-api-key", "dev-api-key")


async def test_validation_error_uses_api_response_shape(api_client):
    response = await api_client.post("/api/notifications", json={"provider_code": "crm"})

    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "data"}
    assert response.json()["code"] == "validation_error"


async def test_payload_too_large_is_rejected(api_client, monkeypatch):
    monkeypatch.setenv("MAX_PAYLOAD_BYTES", "128")
    from app.config import get_settings

    get_settings.cache_clear()
    response = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "crm",
            "event_type": "subscription_paid",
            "event_id": "evt_too_large",
            "payload": {
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
                "padding": "x" * 300,
            },
        },
    )

    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"
    get_settings.cache_clear()


async def test_metadata_field_count_is_limited(api_client):
    response = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "crm",
            "event_type": "subscription_paid",
            "event_id": "evt_metadata_many_fields",
            "payload": {
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
            },
            "metadata": {f"k{i}": "v" for i in range(33)},
        },
    )

    assert response.status_code == 422


async def test_metadata_string_value_length_is_limited(api_client):
    response = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "crm",
            "event_type": "subscription_paid",
            "event_id": "evt_metadata_value_too_long",
            "payload": {
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
            },
            "metadata": {"trace_id": "x" * 1025},
        },
    )

    assert response.status_code == 422


async def test_paused_provider_blocks_only_new_submissions(api_client, db_session):
    provider = await db_session.scalar(select(Provider).where(Provider.provider_code == "crm"))
    provider.paused = True
    await db_session.commit()

    payload = {
        "provider_code": "crm",
        "event_type": "subscription_paid",
        "event_id": "evt_paused",
        "payload": {
            "user_id": "u_123",
            "email": "alice@example.com",
            "subscription_id": "sub_1",
            "amount": 19900,
            "currency": "USD",
            "paid_at": "2026-05-19T10:00:00Z",
        },
    }

    blocked = await api_client.post("/api/notifications", json=payload)

    assert blocked.status_code == 409
    assert blocked.json()["code"] == "provider_paused"


async def test_get_notification_status(api_client):
    created = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "ads",
            "event_type": "user_registered",
            "event_id": "evt_status",
            "payload": {
                "user_id": "u_123",
                "registered_at": "2026-05-19T10:00:00Z",
            },
        },
    )
    notification_id = created.json()["data"]["id"]

    response = await api_client.get(f"/api/notifications/{notification_id}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == notification_id
    assert response.json()["data"]["status"] == "pending"
