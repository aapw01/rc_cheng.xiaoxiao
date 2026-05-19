from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import DeliveryAttempt, Notification, NotificationStatus
from app.providers.base import ProviderAdapterError
from app.providers.registry import get_adapter


class DeliveryFailedError(Exception):
    pass


async def deliver_notification(session: AsyncSession, notification_id: UUID | str) -> None:
    notification_id = UUID(str(notification_id))
    notification = await claim_notification(session, notification_id)
    if notification is None:
        return

    attempt_number = notification.attempt_count + 1
    attempt = DeliveryAttempt(
        notification_id=notification.id,
        attempt_number=attempt_number,
        started_at=datetime.now(UTC),
    )
    session.add(attempt)
    adapter = get_adapter(notification.provider_code)
    try:
        request = adapter.build_request(notification.event_type, notification.payload)
    except ProviderAdapterError as exc:
        attempt.error_type = "adapter_error"
        attempt.error_message = str(exc)
        attempt.finished_at = datetime.now(UTC)
        notification.attempt_count = attempt_number
        notification.status = NotificationStatus.failed
        notification.last_error = str(exc)
        await session.commit()
        return
    attempt.request_method = request.method
    attempt.request_url = request.url

    try:
        async with httpx.AsyncClient(timeout=get_settings().http_request_timeout_seconds) as client:
            response = await client.request(
                request.method,
                request.url,
                headers=request.headers,
                json=request.json,
            )
        attempt.response_status = response.status_code
        attempt.finished_at = datetime.now(UTC)
        notification.attempt_count = attempt_number
        if adapter.is_success(response.status_code, response.content):
            notification.status = NotificationStatus.delivered
            notification.last_error = None
            await session.commit()
            return
        attempt.error_type = "http_status"
        attempt.error_message = response.text[:1000]
        mark_failed_or_retrying(notification, attempt_number, f"HTTP {response.status_code}")
        await session.commit()
        raise DeliveryFailedError(f"Vendor returned HTTP {response.status_code}")
    except httpx.TimeoutException as exc:
        attempt.error_type = "timeout"
        attempt.error_message = str(exc)
        attempt.finished_at = datetime.now(UTC)
        notification.attempt_count = attempt_number
        mark_failed_or_retrying(notification, attempt_number, "timeout")
        await session.commit()
        raise DeliveryFailedError("Vendor request timed out") from exc
    except httpx.HTTPError as exc:
        attempt.error_type = "network"
        attempt.error_message = str(exc)
        attempt.finished_at = datetime.now(UTC)
        notification.attempt_count = attempt_number
        mark_failed_or_retrying(notification, attempt_number, str(exc))
        await session.commit()
        raise DeliveryFailedError("Vendor request failed") from exc


async def claim_notification(session: AsyncSession, notification_id: UUID) -> Notification | None:
    result = await session.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.status.in_([NotificationStatus.pending, NotificationStatus.retrying]),
        )
        .values(status=NotificationStatus.delivering, updated_at=datetime.now(UTC))
        .returning(Notification)
    )
    await session.commit()
    return result.scalar_one_or_none()


def mark_failed_or_retrying(notification: Notification, attempt_number: int, error: str) -> None:
    max_attempts = get_settings().default_max_attempts
    notification.last_error = error
    if max_attempts != -1 and attempt_number >= max_attempts:
        notification.status = NotificationStatus.failed
    else:
        notification.status = NotificationStatus.retrying
