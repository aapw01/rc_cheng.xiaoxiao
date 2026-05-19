from typing import Any

from app.config import get_settings
from app.providers.base import AdapterRequest, ProviderAdapter


class AdsAdapter(ProviderAdapter):
    provider_code = "ads"
    supported_event_types = {"user_registered"}

    def __init__(self, base_url: str = "https://ads.vendor.test", bearer_token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token or get_settings().provider_ads_bearer_token

    def build_request(self, event_type: str, payload: dict[str, Any]) -> AdapterRequest:
        self.ensure_supported(event_type)
        self.require_fields(payload, {"user_id", "registered_at"})
        return AdapterRequest(
            method="POST",
            url=f"{self.base_url}/conversions",
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
            },
            json={
                "external_user_id": payload["user_id"],
                "event_name": "user_registered",
                "timestamp": payload["registered_at"],
                "campaign_id": payload.get("campaign_id"),
            },
        )

