from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    api_key: str = "dev-api-key"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/notifications"
    redis_url: str = "redis://localhost:6379/0"
    default_max_attempts: int = Field(default=6, ge=-1)
    http_request_timeout_seconds: float = Field(default=10.0, gt=0)
    max_payload_bytes: int = Field(default=65_536, gt=0)

    provider_crm_api_key: str = "dev-crm-key"
    provider_ads_bearer_token: str = "dev-ads-token"
    provider_inventory_api_key: str = "dev-inventory-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

