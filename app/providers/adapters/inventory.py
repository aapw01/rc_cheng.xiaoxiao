from typing import Any

from app.config import get_settings
from app.providers.base import AdapterRequest, ProviderAdapter


class InventoryAdapter(ProviderAdapter):
    provider_code = "inventory"
    supported_event_types = {"order_created"}

    def __init__(self, base_url: str = "https://inventory.vendor.test", api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or get_settings().provider_inventory_api_key

    def build_request(self, event_type: str, payload: dict[str, Any]) -> AdapterRequest:
        self.ensure_supported(event_type)
        self.require_fields(payload, {"order_id", "items", "created_at"})
        return AdapterRequest(
            method="POST",
            url=f"{self.base_url}/api/orders",
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
            json={
                "orderId": payload["order_id"],
                "items": payload["items"],
                "createdAt": payload["created_at"],
            },
        )

