from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.notifications import serialize_notification
from app.db import get_session
from app.errors import AppError
from app.models import DeliveryAttempt, Notification, NotificationStatus, OperatorAction, Provider
from app.schemas import ApiResponse
from app.security import require_api_key
from app.services.metrics import dashboard_metrics
from app.tasks.delivery import actor_for_queue

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_api_key)])
ProviderCodeQuery = Annotated[str | None, Query()]
StatusQuery = Annotated[NotificationStatus | None, Query()]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]


@router.get("/metrics", response_model=ApiResponse)
async def get_metrics(session: Annotated[AsyncSession, Depends(get_session)]) -> ApiResponse:
    return ApiResponse(data=await dashboard_metrics(session))


@router.get("/providers", response_model=ApiResponse)
async def list_providers(session: Annotated[AsyncSession, Depends(get_session)]) -> ApiResponse:
    providers = await session.scalars(select(Provider).order_by(Provider.provider_code))
    return ApiResponse(
        data=[
            {
                "provider_code": provider.provider_code,
                "display_name": provider.display_name,
                "enabled": provider.enabled,
                "paused": provider.paused,
                "queue_name": provider.queue_name,
            }
            for provider in providers
        ]
    )


@router.post("/providers/{provider_code}/pause", response_model=ApiResponse)
async def pause_provider(provider_code: str, session: Annotated[AsyncSession, Depends(get_session)]) -> ApiResponse:
    provider = await get_provider(session, provider_code)
    previous = {"paused": provider.paused}
    provider.paused = True
    session.add(
        OperatorAction(
            action_type="provider_pause",
            target_type="provider",
            target_id=provider_code,
            previous_state=previous,
            new_state={"paused": True},
            actor="api",
        )
    )
    await session.commit()
    return ApiResponse(data={"provider_code": provider_code, "paused": True})


@router.post("/providers/{provider_code}/resume", response_model=ApiResponse)
async def resume_provider(provider_code: str, session: Annotated[AsyncSession, Depends(get_session)]) -> ApiResponse:
    provider = await get_provider(session, provider_code)
    previous = {"paused": provider.paused}
    provider.paused = False
    session.add(
        OperatorAction(
            action_type="provider_resume",
            target_type="provider",
            target_id=provider_code,
            previous_state=previous,
            new_state={"paused": False},
            actor="api",
        )
    )
    await session.commit()
    return ApiResponse(data={"provider_code": provider_code, "paused": False})


@router.get("/notifications", response_model=ApiResponse)
async def list_notifications(
    session: Annotated[AsyncSession, Depends(get_session)],
    provider_code: ProviderCodeQuery = None,
    status: StatusQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> ApiResponse:
    query = select(Notification).order_by(Notification.created_at.desc())
    count_query = select(func.count()).select_from(Notification)
    if provider_code is not None:
        query = query.where(Notification.provider_code == provider_code)
        count_query = count_query.where(Notification.provider_code == provider_code)
    if status is not None:
        query = query.where(Notification.status == status)
        count_query = count_query.where(Notification.status == status)
    notifications = await session.scalars(query.limit(limit).offset(offset))
    total = await session.scalar(count_query)
    return ApiResponse(
        data={
            "items": [serialize_notification(item).model_dump(mode="json") for item in notifications],
            "total": total or 0,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/notifications/{notification_id}", response_model=ApiResponse)
async def notification_detail(
    notification_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    notification = await session.scalar(
        select(Notification)
        .where(Notification.id == notification_id)
        .options(selectinload(Notification.attempts))
    )
    if notification is None:
        raise AppError(status_code=404, code="notification_not_found", message="Notification not found")
    data = serialize_notification(notification).model_dump(mode="json")
    data["attempts"] = [serialize_attempt(attempt) for attempt in notification.attempts]
    return ApiResponse(data=data)


@router.post("/notifications/{notification_id}/retry", response_model=ApiResponse)
async def retry_notification(
    notification_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise AppError(status_code=404, code="notification_not_found", message="Notification not found")
    if notification.status != NotificationStatus.failed:
        raise AppError(status_code=409, code="notification_not_failed", message="Only failed notifications can retry")
    provider = await get_provider(session, notification.provider_code)
    previous = {"status": notification.status.value}
    notification.status = NotificationStatus.pending
    notification.last_error = None
    session.add(
        OperatorAction(
            action_type="notification_retry",
            target_type="notification",
            target_id=str(notification_id),
            previous_state=previous,
            new_state={"status": "pending"},
            actor="api",
        )
    )
    await session.commit()
    actor_for_queue(provider.queue_name).send(str(notification_id))
    return ApiResponse(data=serialize_notification(notification).model_dump(mode="json"))


async def get_provider(session: AsyncSession, provider_code: str) -> Provider:
    provider = await session.scalar(select(Provider).where(Provider.provider_code == provider_code))
    if provider is None:
        raise AppError(status_code=404, code="provider_not_found", message="Provider not found")
    return provider


def serialize_attempt(attempt: DeliveryAttempt) -> dict:
    return {
        "id": str(attempt.id),
        "attempt_number": attempt.attempt_number,
        "request_method": attempt.request_method,
        "request_url": attempt.request_url,
        "response_status": attempt.response_status,
        "error_type": attempt.error_type,
        "error_message": attempt.error_message,
        "started_at": attempt.started_at.isoformat(),
        "finished_at": attempt.finished_at.isoformat() if attempt.finished_at else None,
    }
