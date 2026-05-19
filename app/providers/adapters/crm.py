from typing import Any

from app.config import get_settings
from app.providers.base import AdapterRequest, ProviderAdapter


class CRMAdapter(ProviderAdapter):
    provider_code = "crm"
    supported_event_types = {"subscription_paid", "user_registered"}

    def __init__(self, base_url: str = "https://crm.vendor.test", api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or get_settings().provider_crm_api_key

    def build_request(self, event_type: str, payload: dict[str, Any]) -> AdapterRequest:
        self.ensure_supported(event_type)
        if event_type == "subscription_paid":
            self.require_fields(payload, {"email", "subscription_id", "amount", "currency", "paid_at"})
            return AdapterRequest(
                method="POST",
                url=f"{self.base_url}/api/contacts/subscription-paid",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "contactEmail": payload["email"],
                    "lifecycleStage": "customer",
                    "subscriptionId": payload["subscription_id"],
                    "amountCents": payload["amount"],
                    "currency": payload["currency"],
                    "lastPaymentAt": payload["paid_at"],
                },
            )
        self.require_fields(payload, {"user_id", "email", "registered_at"})
        return AdapterRequest(
            method="POST",
            url=f"{self.base_url}/api/contacts/registered",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "externalUserId": payload["user_id"],
                "contactEmail": payload["email"],
                "registeredAt": payload["registered_at"],
            },
        )

