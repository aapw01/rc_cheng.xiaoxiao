from app.providers.adapters.ads import AdsAdapter
from app.providers.adapters.crm import CRMAdapter
from app.providers.adapters.inventory import InventoryAdapter
from app.providers.base import ProviderAdapter, ProviderAdapterError

ADAPTERS: dict[str, type[ProviderAdapter]] = {
    CRMAdapter.provider_code: CRMAdapter,
    AdsAdapter.provider_code: AdsAdapter,
    InventoryAdapter.provider_code: InventoryAdapter,
}

QUEUE_TO_PROVIDER: dict[str, str] = {
    "notifications_crm": "crm",
    "notifications_ads": "ads",
    "notifications_inventory": "inventory",
}


def get_adapter(provider_code: str) -> ProviderAdapter:
    adapter_type = ADAPTERS.get(provider_code)
    if adapter_type is None:
        raise ProviderAdapterError(f"Unknown provider_code: {provider_code}")
    return adapter_type()


def supported_provider_codes() -> set[str]:
    return set(ADAPTERS)
