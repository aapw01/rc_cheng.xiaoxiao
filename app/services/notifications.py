import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.models import Notification, NotificationStatus, Provider
from app.providers.base import ProviderAdapterError
from app.providers.registry import get_adapter
from app.schemas import NotificationCreate
from app.tasks.delivery import actor_for_queue

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationSubmitResult:
    notification: Notification
    deduplicated: bool


async def submit_notification(session: AsyncSession, payload: NotificationCreate) -> NotificationSubmitResult:
    existing = await find_existing_notification(session, payload)
    if existing is not None:
        ensure_idempotent_payload_matches(existing, payload)
        return NotificationSubmitResult(notification=existing, deduplicated=True)

    provider = await session.scalar(select(Provider).where(Provider.provider_code == payload.provider_code))
    if provider is None:
        raise AppError(status_code=404, code="provider_not_found", message="Provider not found")
    if not provider.enabled:
        raise AppError(status_code=409, code="provider_disabled", message="Provider is disabled")
    if provider.paused:
        raise AppError(status_code=409, code="provider_paused", message="Provider is paused")

    validate_adapter(payload)
    notification = Notification(
        provider_code=payload.provider_code,
        event_type=payload.event_type,
        event_id=payload.event_id,
        occurred_at=payload.occurred_at,
        payload=payload.payload,
        metadata_=payload.metadata,
    )
    session.add(notification)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await find_existing_notification(session, payload)
        if existing is not None:
            ensure_idempotent_payload_matches(existing, payload)
            return NotificationSubmitResult(notification=existing, deduplicated=True)
        raise
    await session.refresh(notification)
    trace_id = payload.metadata.get("trace_id")
    try:
        actor_for_queue(provider.queue_name).send(str(notification.id))
    except Exception as exc:
        notification.status = NotificationStatus.failed
        notification.last_error = "enqueue_failed"
        await session.commit()
        logger.exception(
            "notification_enqueue_failed notification_id=%s provider=%s event=%s trace_id=%s",
            notification.id,
            notification.provider_code,
            notification.event_type,
            trace_id,
        )
        raise AppError(status_code=503, code="enqueue_failed", message="Failed to enqueue notification") from exc
    logger.info(
        "notification_enqueued notification_id=%s provider=%s event=%s trace_id=%s",
        notification.id,
        notification.provider_code,
        notification.event_type,
        trace_id,
    )
    return NotificationSubmitResult(notification=notification, deduplicated=False)


async def find_existing_notification(session: AsyncSession, payload: NotificationCreate) -> Notification | None:
    return await session.scalar(
        select(Notification).where(
            Notification.provider_code == payload.provider_code,
            Notification.event_type == payload.event_type,
            Notification.event_id == payload.event_id,
        )
    )


async def get_notification(session: AsyncSession, notification_id: UUID) -> Notification:
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise AppError(status_code=404, code="notification_not_found", message="Notification not found")
    return notification


def validate_adapter(payload: NotificationCreate) -> None:
    try:
        adapter = get_adapter(payload.provider_code)
        adapter.build_request(payload.event_type, payload.payload)
    except ProviderAdapterError as exc:
        raise AppError(status_code=400, code="invalid_event", message=str(exc)) from exc


def ensure_idempotent_payload_matches(existing: Notification, payload: NotificationCreate) -> None:
    if existing.payload == payload.payload and existing.metadata_ == payload.metadata:
        return
    raise AppError(
        status_code=409,
        code="idempotency_conflict",
        message=(
            "A notification with the same provider_code, event_type and event_id already exists with different "
            "payload or metadata"
        ),
        data={
            "existing_notification_id": str(existing.id),
            "provider_code": existing.provider_code,
            "event_type": existing.event_type,
            "event_id": existing.event_id,
        },
    )
