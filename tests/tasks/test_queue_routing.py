from app.tasks.delivery import actor_for_queue


def test_actor_for_queue_returns_provider_specific_actor():
    assert actor_for_queue("notifications_crm").actor_name == "deliver_crm_notification"
    assert actor_for_queue("notifications_ads").actor_name == "deliver_ads_notification"
    assert actor_for_queue("notifications_inventory").actor_name == "deliver_inventory_notification"


def test_delivery_actors_use_spec_backoff_window():
    actor = actor_for_queue("notifications_crm")

    assert actor.options["min_backoff"] == 60_000
    assert actor.options["max_backoff"] == 3_600_000
