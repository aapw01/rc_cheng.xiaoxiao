from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import NotificationStatus


class NotificationCreate(BaseModel):
    provider_code: str = Field(min_length=1, max_length=64)
    event_type: str = Field(min_length=1, max_length=128)
    event_id: str = Field(min_length=1, max_length=256)
    occurred_at: datetime | None = None
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    id: UUID
    provider_code: str
    event_type: str
    event_id: str
    status: NotificationStatus
    attempt_count: int
    payload: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ApiResponse(BaseModel):
    code: int | str = 0
    message: str = "ok"
    data: Any

