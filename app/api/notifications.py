from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import (
    ApiResponse,
    NotificationCreate,
    serialize_notification,
    serialize_submit_notification,
)
from app.security import require_api_key
from app.services.notifications import get_notification, submit_notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"], dependencies=[Depends(require_api_key)])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=ApiResponse)
async def create_notification(
    payload: NotificationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
) -> ApiResponse:
    result = await submit_notification(session, payload)
    if result.deduplicated:
        response.status_code = status.HTTP_200_OK
        message = "duplicate_accepted"
    else:
        message = "accepted"
    return ApiResponse(
        message=message,
        data=serialize_submit_notification(
            result.notification, deduplicated=result.deduplicated
        ).model_dump(mode="json"),
    )


@router.get("/{notification_id}", response_model=ApiResponse)
async def read_notification(
    notification_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    notification = await get_notification(session, notification_id)
    return ApiResponse(data=serialize_notification(notification).model_dump(mode="json"))
