from uuid import UUID

import pytest
from sqlalchemy import select

from app.models import DeliveryAttempt, Notification, NotificationStatus
from app.schemas import NotificationCreate
from app.services.delivery import DeliveryFailedError, deliver_notification
from app.services.notifications import submit_notification


async def create_crm_notification(db_session, event_id: str = "evt_delivery") -> UUID:
    notification = await submit_notification(
        db_session,
        NotificationCreate(
            provider_code="crm",
            event_type="subscription_paid",
            event_id=event_id,
            payload={
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
            },
        ),
    )
    return notification.id


async def test_deliver_notification_marks_success(db_session, httpx_mock, disable_dramatiq_enqueue, caplog):
    notification_id = await create_crm_notification(db_session)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    with caplog.at_level("INFO", logger="app.services.delivery"):
        await deliver_notification(db_session, notification_id)

    notification = await db_session.get(Notification, notification_id)
    attempts = (await db_session.scalars(select(DeliveryAttempt))).all()
    assert notification.status == NotificationStatus.delivered
    assert notification.attempt_count == 1
    assert len(attempts) == 1
    assert attempts[0].response_status == 200
    assert any(record.message == "notification_delivery_succeeded" for record in caplog.records)


async def test_deliver_notification_records_failure_and_raises(db_session, httpx_mock, disable_dramatiq_enqueue):
    notification_id = await create_crm_notification(db_session)
    httpx_mock.add_response(status_code=500, text="vendor down")

    with pytest.raises(DeliveryFailedError):
        await deliver_notification(db_session, notification_id)

    notification = await db_session.get(Notification, notification_id)
    attempt = await db_session.scalar(select(DeliveryAttempt))
    assert notification.status == NotificationStatus.retrying
    assert notification.attempt_count == 1
    assert attempt.response_status == 500
    assert attempt.error_type == "http_status"


async def test_deliver_notification_marks_adapter_error_failed_without_retry(db_session, disable_dramatiq_enqueue):
    notification_id = await create_crm_notification(db_session)
    notification = await db_session.get(Notification, notification_id)
    notification.payload = {"email": "alice@example.com"}
    await db_session.commit()

    await deliver_notification(db_session, notification_id)

    await db_session.refresh(notification)
    attempt = await db_session.scalar(select(DeliveryAttempt))
    assert notification.status == NotificationStatus.failed
    assert notification.attempt_count == 1
    assert attempt.error_type == "adapter_error"


async def test_deliver_notification_marks_failed_at_max_attempts(
    db_session, httpx_mock, monkeypatch, disable_dramatiq_enqueue
):
    notification_id = await create_crm_notification(db_session)
    monkeypatch.setenv("DEFAULT_MAX_ATTEMPTS", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    httpx_mock.add_response(status_code=500, text="vendor down")

    with pytest.raises(DeliveryFailedError):
        await deliver_notification(db_session, notification_id)

    notification = await db_session.get(Notification, notification_id)
    assert notification.status == NotificationStatus.failed
    get_settings.cache_clear()


async def test_deliver_notification_retries_forever_without_marking_failed(
    db_session, httpx_mock, monkeypatch, disable_dramatiq_enqueue
):
    notification_id = await create_crm_notification(db_session)
    monkeypatch.setenv("DEFAULT_MAX_ATTEMPTS", "-1")
    from app.config import get_settings

    get_settings.cache_clear()
    httpx_mock.add_response(status_code=500, text="vendor down")

    with pytest.raises(DeliveryFailedError):
        await deliver_notification(db_session, notification_id)

    notification = await db_session.get(Notification, notification_id)
    assert notification.status == NotificationStatus.retrying
    assert notification.attempt_count == 1
    get_settings.cache_clear()


async def test_deliver_notification_exits_when_already_delivered(db_session, httpx_mock, disable_dramatiq_enqueue):
    notification_id = await create_crm_notification(db_session)
    notification = await db_session.get(Notification, notification_id)
    notification.status = NotificationStatus.delivered
    await db_session.commit()

    await deliver_notification(db_session, notification_id)

    attempts = (await db_session.scalars(select(DeliveryAttempt))).all()
    assert attempts == []
