from app.tasks.delivery import (
    MAX_RETRY_BACKOFF_MS,
    MIN_RETRY_BACKOFF_MS,
    _actor_registry,
    _max_retries,
    actor_for_queue,
    register_provider_actor,
)


def test_actor_for_queue_registers_on_first_use():
    queue_name = "notifications_unit_test_dynamic_queue"
    _actor_registry.pop(queue_name, None)

    actor = actor_for_queue(queue_name)

    assert actor.queue_name == queue_name
    assert actor.actor_name == f"deliver_{queue_name}"


def test_actor_registration_is_idempotent():
    queue_name = "notifications_unit_test_idempotent_queue"
    _actor_registry.pop(queue_name, None)

    first = register_provider_actor(queue_name)
    second = register_provider_actor(queue_name)

    assert first is second


def test_delivery_actor_uses_spec_backoff_window():
    queue_name = "notifications_unit_test_backoff_queue"
    _actor_registry.pop(queue_name, None)

    actor = actor_for_queue(queue_name)

    assert actor.options["min_backoff"] == MIN_RETRY_BACKOFF_MS
    assert actor.options["max_backoff"] == MAX_RETRY_BACKOFF_MS


def test_delivery_actor_includes_time_limit(monkeypatch):
    monkeypatch.setenv("ACTOR_TIME_LIMIT_SECONDS", "45")
    from app.config import get_settings

    get_settings.cache_clear()
    queue_name = "notifications_unit_test_time_limit_queue"
    _actor_registry.pop(queue_name, None)

    actor = actor_for_queue(queue_name)

    assert actor.options["time_limit"] == 45_000
    get_settings.cache_clear()


def test_max_retries_is_unlimited_when_attempts_is_minus_one(monkeypatch):
    monkeypatch.setenv("DEFAULT_MAX_ATTEMPTS", "-1")
    from app.config import get_settings

    get_settings.cache_clear()

    assert _max_retries() is None
    get_settings.cache_clear()
