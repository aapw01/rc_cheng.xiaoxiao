from app.tasks.delivery import actor_for_queue, max_retries


def test_actor_for_queue_returns_provider_specific_actor():
    assert actor_for_queue("notifications_crm").actor_name == "deliver_crm_notification"
    assert actor_for_queue("notifications_ads").actor_name == "deliver_ads_notification"
    assert actor_for_queue("notifications_inventory").actor_name == "deliver_inventory_notification"


def test_delivery_actors_use_spec_backoff_window():
    actor = actor_for_queue("notifications_crm")

    assert actor.options["min_backoff"] == 60_000
    assert actor.options["max_backoff"] == 3_600_000


def test_max_retries_is_unlimited_when_attempts_is_minus_one(monkeypatch):
    monkeypatch.setenv("DEFAULT_MAX_ATTEMPTS", "-1")
    from app.config import get_settings

    get_settings.cache_clear()

    assert max_retries() is None
    get_settings.cache_clear()
