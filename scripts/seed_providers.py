import asyncio

from sqlalchemy import select

from app.db import create_session
from app.models import Provider

PROVIDER_SEEDS = [
    {
        "provider_code": "crm",
        "display_name": "CRM",
        "queue_name": "notifications_crm",
        "enabled": True,
        "paused": False,
    },
    {
        "provider_code": "ads",
        "display_name": "Ads",
        "queue_name": "notifications_ads",
        "enabled": True,
        "paused": False,
    },
    {
        "provider_code": "inventory",
        "display_name": "Inventory",
        "queue_name": "notifications_inventory",
        "enabled": True,
        "paused": False,
    },
]


async def seed() -> None:
    async with create_session() as session:
        for item in PROVIDER_SEEDS:
            provider = await session.scalar(select(Provider).where(Provider.provider_code == item["provider_code"]))
            if provider is None:
                session.add(Provider(**item))
            else:
                provider.display_name = item["display_name"]
                provider.queue_name = item["queue_name"]
                provider.enabled = item["enabled"]
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
