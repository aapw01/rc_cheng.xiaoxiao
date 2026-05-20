from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models import NotificationStatus


class NotificationCreate(BaseModel):
    provider_code: str = Field(min_length=1, max_length=64)
    event_type: str = Field(min_length=1, max_length=128)
    event_id: str = Field(min_length=1, max_length=256)
    occurred_at: datetime | None = None
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 32:
            raise ValueError("metadata must contain at most 32 fields")
        too_long = [key for key, item in value.items() if isinstance(item, str) and len(item) > 1024]
        if too_long:
            raise ValueError("metadata string values must be at most 1024 characters")
        return value


class NotificationResponse(BaseModel):
    id: UUID
    provider_code: str
    event_type: str
    event_id: str
    status: NotificationStatus
    attempt_count: int
    last_error: str | None
    payload: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class IdempotencyResponse(BaseModel):
    deduplicated: bool
    conflict: bool = False


class NotificationSubmitResponse(NotificationResponse):
    idempotency: IdempotencyResponse


class ApiResponse(BaseModel):
    code: int | str = 0
    message: str = "ok"
    data: Any
