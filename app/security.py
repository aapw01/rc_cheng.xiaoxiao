import secrets
from typing import Annotated

from fastapi import Header

from app.config import get_settings
from app.errors import AppError


async def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if x_api_key is None or not secrets.compare_digest(x_api_key, get_settings().api_key):
        raise AppError(status_code=401, code="unauthorized", message="Invalid API key")
