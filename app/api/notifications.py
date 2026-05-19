from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import ApiResponse, NotificationCreate, NotificationResponse
from app.security import require_api_key
from app.services.notifications import get_notification, submit_notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"], dependencies=[Depends(require_api_key)])


def serialize_notification(notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        provider_code=notification.provider_code,
        event_type=notification.event_type,
        event_id=notification.event_id,
        status=notification.status,
        attempt_count=notification.attempt_count,
        last_error=notification.last_error,
        payload=notification.payload,
        metadata=notification.metadata_,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=ApiResponse)
async def create_notification(
    payload: NotificationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    notification = await submit_notification(session, payload)
    return ApiResponse(data=serialize_notification(notification).model_dump(mode="json"))


@router.get("/{notification_id}", response_model=ApiResponse)
async def read_notification(
    notification_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    notification = await get_notification(session, notification_id)
    return ApiResponse(data=serialize_notification(notification).model_dump(mode="json"))
