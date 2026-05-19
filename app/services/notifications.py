from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.models import Notification, Provider
from app.providers.base import ProviderAdapterError
from app.providers.registry import get_adapter
from app.schemas import NotificationCreate


async def submit_notification(session: AsyncSession, payload: NotificationCreate) -> Notification:
    existing = await find_existing_notification(session, payload)
    if existing is not None:
        return existing

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
            return existing
        raise
    await session.refresh(notification)
    return notification


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

