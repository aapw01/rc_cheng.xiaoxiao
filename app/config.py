from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    api_key: str = "dev-api-key"
    ops_password: str = "dev-ops-password"
    cors_allowed_origins: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/notifications"
    redis_url: str = "redis://localhost:6379/0"
    default_max_attempts: int = Field(default=6, ge=-1)
    http_request_timeout_seconds: float = Field(default=10.0, gt=0)
    actor_time_limit_seconds: float = Field(default=30.0, gt=0)
    max_payload_bytes: int = Field(default=65_536, gt=0)

    provider_crm_api_key: str = "dev-crm-key"
    provider_crm_base_url: str = "https://crm.vendor.test"
    provider_ads_bearer_token: str = "dev-ads-token"
    provider_ads_base_url: str = "https://ads.vendor.test"
    provider_inventory_api_key: str = "dev-inventory-key"
    provider_inventory_base_url: str = "https://inventory.vendor.test"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_allowed_origins")
    @classmethod
    def _reject_wildcard_cors(cls, value: str) -> str:
        # Starlette's CORSMiddleware silently drops credentials when origin is "*",
        # which would break the ops UI session cookie. Fail fast instead of producing
        # a misconfigured deployment.
        origins = [item.strip() for item in value.split(",") if item.strip()]
        if "*" in origins:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS cannot contain '*' because allow_credentials=True "
                "requires explicit origins. List each frontend origin explicitly."
            )
        return value

    def effective_cors_allowed_origins(self) -> list[str]:
        configured = [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
        if configured:
            return configured
        if self.app_env == "production":
            return []
        return ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
