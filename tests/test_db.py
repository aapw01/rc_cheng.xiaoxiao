import asyncio

from app.db import dispose_engine, get_engine


def test_async_engine_is_scoped_per_event_loop() -> None:
    first_engine = asyncio.run(_get_engine_for_current_loop())
    second_engine = asyncio.run(_get_engine_for_current_loop())

    assert first_engine is not second_engine


async def _get_engine_for_current_loop():
    engine = get_engine()
    await dispose_engine()
    return engine
