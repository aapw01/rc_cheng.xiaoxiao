from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, Provider


async def dashboard_metrics(session: AsyncSession) -> dict:
    status_rows = await session.execute(select(Notification.status, func.count()).group_by(Notification.status))
    provider_rows = await session.execute(
        select(Notification.provider_code, Notification.status, func.count()).group_by(
            Notification.provider_code, Notification.status
        )
    )
    providers = await session.scalars(select(Provider))
    by_status = {status.value: count for status, count in status_rows}
    by_provider: dict[str, dict[str, int]] = {}
    for provider_code, status, count in provider_rows:
        by_provider.setdefault(provider_code, {})[status.value] = count

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_provider": by_provider,
        "providers": [
            {
                "provider_code": provider.provider_code,
                "display_name": provider.display_name,
                "enabled": provider.enabled,
                "paused": provider.paused,
                "queue_name": provider.queue_name,
            }
            for provider in providers
        ],
    }

