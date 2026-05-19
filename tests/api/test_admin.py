from sqlalchemy import select

from app.models import DeliveryAttempt, NotificationStatus, Provider
from app.schemas import NotificationCreate
from app.services.notifications import submit_notification


async def create_notification(db_session, provider_code: str = "crm", event_id: str = "evt_admin"):
    payload = {
        "crm": {
            "provider_code": "crm",
            "event_type": "subscription_paid",
            "payload": {
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
            },
        },
        "ads": {
            "provider_code": "ads",
            "event_type": "user_registered",
            "payload": {"user_id": "u_123", "registered_at": "2026-05-19T10:00:00Z"},
        },
    }[provider_code]
    return await submit_notification(db_session, NotificationCreate(event_id=event_id, **payload))


async def test_admin_metrics_aggregates_statuses(api_client, db_session):
    notification = await create_notification(db_session)
    notification.status = NotificationStatus.failed
    await db_session.commit()

    response = await api_client.get("/api/admin/metrics")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["by_status"]["failed"] == 1


async def test_admin_providers_pause_and_resume(api_client, db_session):
    pause = await api_client.post("/api/admin/providers/crm/pause")
    provider = await db_session.scalar(select(Provider).where(Provider.provider_code == "crm"))

    assert pause.status_code == 200
    assert provider.paused is True

    resume = await api_client.post("/api/admin/providers/crm/resume")
    await db_session.refresh(provider)

    assert resume.status_code == 200
    assert provider.paused is False


async def test_admin_notifications_list_filter(api_client, db_session):
    await create_notification(db_session, provider_code="crm", event_id="evt_crm")
    await create_notification(db_session, provider_code="ads", event_id="evt_ads")

    response = await api_client.get("/api/admin/notifications?provider_code=ads")

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["provider_code"] == "ads"


async def test_admin_notifications_list_paginates(api_client, db_session):
    await create_notification(db_session, provider_code="crm", event_id="evt_page_1")
    await create_notification(db_session, provider_code="crm", event_id="evt_page_2")
    await create_notification(db_session, provider_code="ads", event_id="evt_page_3")

    response = await api_client.get("/api/admin/notifications?limit=2&offset=1")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["items"]) == 2


async def test_admin_notification_detail_includes_attempts(api_client, db_session):
    notification = await create_notification(db_session)
    notification.last_error = "HTTP 500"
    db_session.add(
        DeliveryAttempt(
            notification_id=notification.id,
            attempt_number=1,
            request_method="POST",
            request_url="https://crm.vendor.test/api",
            response_status=500,
            error_type="http_status",
            error_message="down",
        )
    )
    await db_session.commit()

    response = await api_client.get(f"/api/admin/notifications/{notification.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(notification.id)
    assert data["last_error"] == "HTTP 500"
    assert data["attempts"][0]["response_status"] == 500


async def test_admin_retry_failed_notification(api_client, db_session, monkeypatch):
    sent_messages = []

    class FakeActor:
        @staticmethod
        def send(notification_id: str) -> None:
            sent_messages.append(notification_id)

    monkeypatch.setattr("app.api.admin.actor_for_queue", lambda queue_name: FakeActor)
    notification = await create_notification(db_session)
    notification.status = NotificationStatus.failed
    await db_session.commit()

    response = await api_client.post(f"/api/admin/notifications/{notification.id}/retry")
    await db_session.refresh(notification)

    assert response.status_code == 200
    assert notification.status == NotificationStatus.pending
    assert sent_messages == [str(notification.id)]
