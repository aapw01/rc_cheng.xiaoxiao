"""Dramatiq actors for notification delivery.

Worker queues are loaded from the `providers` table at startup so that the
queue set is driven by data rather than hardcoded module constants. Newly
added providers require a worker restart to pick up the new queue (see SPEC
§8 for the explicit "no runtime queue mutation" constraint).
"""

import asyncio
import logging
import os
from uuid import UUID

import dramatiq

from app.db import AsyncSessionLocal, dispose_engine
from app.services.delivery import deliver_notification

from .broker import redis_broker as redis_broker

logger = logging.getLogger(__name__)

MIN_RETRY_BACKOFF_MS = 60_000
MAX_RETRY_BACKOFF_MS = 3_600_000

_actor_registry: dict[str, dramatiq.Actor] = {}


def _max_retries() -> int | None:
    from app.config import get_settings

    attempts = get_settings().default_max_attempts
    if attempts == -1:
        return None
    return max(attempts - 1, 0)


def _actor_time_limit_ms() -> int:
    from app.config import get_settings

    return int(get_settings().actor_time_limit_seconds * 1000)


async def _deliver(notification_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await deliver_notification(session, UUID(notification_id))


def register_provider_actor(queue_name: str) -> dramatiq.Actor:
    """Register a Dramatiq actor bound to a provider queue (idempotent)."""
    if queue_name in _actor_registry:
        return _actor_registry[queue_name]
    actor = dramatiq.actor(
        queue_name=queue_name,
        actor_name=f"deliver_{queue_name}",
        max_retries=_max_retries(),
        min_backoff=MIN_RETRY_BACKOFF_MS,
        max_backoff=MAX_RETRY_BACKOFF_MS,
        time_limit=_actor_time_limit_ms(),
    )(_deliver)
    _actor_registry[queue_name] = actor
    return actor


def actor_for_queue(queue_name: str) -> dramatiq.Actor:
    """Resolve a provider queue's actor, registering it on first use.

    API processes call this on each enqueue. The actor is reused on subsequent
    sends. Worker processes additionally pre-register every enabled queue via
    `bootstrap_actors_from_db` so the Dramatiq CLI can start listening to them.
    """
    return register_provider_actor(queue_name)


async def _load_enabled_queue_names() -> list[str]:
    from sqlalchemy import select

    from app.models import Provider

    async with AsyncSessionLocal() as session:
        rows = await session.scalars(
            select(Provider.queue_name).where(Provider.enabled.is_(True)).distinct()
        )
        return list(rows)


def bootstrap_actors_from_db() -> list[str]:
    """Read enabled provider queues from the database and register an actor for each.

    Worker entry points must call this before handing control to the Dramatiq
    CLI; otherwise no queues are declared and the worker has nothing to listen
    on. API processes do not need to call this — `actor_for_queue` registers
    actors lazily during enqueue.
    """
    queues = asyncio.run(_load_enabled_queue_names())
    for queue_name in queues:
        register_provider_actor(queue_name)
    asyncio.run(dispose_engine())
    logger.info("provider_queues_registered count=%d queues=%s", len(queues), queues)
    return queues


if os.getenv("DRAMATIQ_BOOTSTRAP_PROVIDER_ACTORS") == "1":
    bootstrap_actors_from_db()
