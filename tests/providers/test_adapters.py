import pytest

from app.providers.base import ProviderAdapterError
from app.providers.registry import get_adapter


def test_crm_subscription_paid_request():
    adapter = get_adapter("crm")

    request = adapter.build_request(
        "subscription_paid",
        {
            "user_id": "u_123",
            "email": "alice@example.com",
            "subscription_id": "sub_001",
            "amount": 19900,
            "currency": "USD",
            "paid_at": "2026-05-19T10:00:00Z",
        },
    )

    assert request.method == "POST"
    assert request.url == "https://crm.vendor.test/api/contacts/subscription-paid"
    assert request.headers["Authorization"] == "Bearer dev-crm-key"
    assert request.json["contactEmail"] == "alice@example.com"
    assert request.json["lifecycleStage"] == "customer"
    assert request.json["amountCents"] == 19900


def test_ads_user_registered_request():
    adapter = get_adapter("ads")

    request = adapter.build_request(
        "user_registered",
        {
            "user_id": "u_999",
            "email": "bob@example.com",
            "registered_at": "2026-05-19T10:00:00Z",
            "campaign_id": "cmp_1",
        },
    )

    assert request.method == "POST"
    assert request.url == "https://ads.vendor.test/conversions"
    assert request.headers["Authorization"] == "Bearer dev-ads-token"
    assert request.json["external_user_id"] == "u_999"
    assert request.json["event_name"] == "user_registered"


def test_inventory_order_created_request():
    adapter = get_adapter("inventory")

    request = adapter.build_request(
        "order_created",
        {
            "order_id": "ord_1",
            "items": [
                {"sku": "sku_a", "quantity": 2},
                {"sku": "sku_b", "quantity": 1},
            ],
            "created_at": "2026-05-19T10:00:00Z",
        },
    )

    assert request.method == "POST"
    assert request.url == "https://inventory.vendor.test/api/orders"
    assert request.headers["X-API-Key"] == "dev-inventory-key"
    assert request.json["orderId"] == "ord_1"
    assert request.json["items"][0] == {"sku": "sku_a", "quantity": 2}


def test_adapter_rejects_unsupported_event_type():
    adapter = get_adapter("crm")

    with pytest.raises(ProviderAdapterError, match="Unsupported event_type"):
        adapter.build_request("order_created", {"order_id": "ord_1"})


def test_adapter_success_policy_defaults_to_2xx():
    adapter = get_adapter("crm")

    assert adapter.is_success(200, b"ok") is True
    assert adapter.is_success(299, b"ok") is True
    assert adapter.is_success(300, b"redirect") is False
    assert adapter.is_success(500, b"error") is False
