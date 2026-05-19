from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import app
from app.models import Base, Provider


@pytest.fixture(autouse=True)
def disable_dramatiq_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    class NoopActor:
        @staticmethod
        def send(notification_id: str) -> None:
            return None

    monkeypatch.setattr("app.services.notifications.actor_for_queue", lambda queue_name: NoopActor)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session.add_all(
            [
                Provider(
                    provider_code="crm",
                    display_name="CRM",
                    enabled=True,
                    paused=False,
                    queue_name="notifications_crm",
                ),
                Provider(
                    provider_code="ads",
                    display_name="Ads",
                    enabled=True,
                    paused=False,
                    queue_name="notifications_ads",
                ),
                Provider(
                    provider_code="inventory",
                    display_name="Inventory",
                    enabled=True,
                    paused=False,
                    queue_name="notifications_inventory",
                ),
            ]
        )
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
async def api_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"X-API-Key": "dev-api-key"},
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
