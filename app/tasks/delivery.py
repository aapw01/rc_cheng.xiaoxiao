from uuid import UUID

import dramatiq

from app.db import AsyncSessionLocal
from app.services.delivery import deliver_notification

from .broker import redis_broker as redis_broker


def max_retries() -> int | None:
    from app.config import get_settings

    attempts = get_settings().default_max_attempts
    if attempts == -1:
        return None
    return max(attempts - 1, 0)


async def _deliver(notification_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await deliver_notification(session, UUID(notification_id))


@dramatiq.actor(queue_name="notifications_crm", max_retries=max_retries())
async def deliver_crm_notification(notification_id: str) -> None:
    await _deliver(notification_id)


@dramatiq.actor(queue_name="notifications_ads", max_retries=max_retries())
async def deliver_ads_notification(notification_id: str) -> None:
    await _deliver(notification_id)


@dramatiq.actor(queue_name="notifications_inventory", max_retries=max_retries())
async def deliver_inventory_notification(notification_id: str) -> None:
    await _deliver(notification_id)


def actor_for_queue(queue_name: str):
    actors = {
        "notifications_crm": deliver_crm_notification,
        "notifications_ads": deliver_ads_notification,
        "notifications_inventory": deliver_inventory_notification,
    }
    return actors[queue_name]
