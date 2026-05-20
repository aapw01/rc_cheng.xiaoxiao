import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_engine_by_loop: dict[int, AsyncEngine] = {}
_sessionmaker_by_loop: dict[int, async_sessionmaker[AsyncSession]] = {}


def _loop_key() -> int:
    return id(asyncio.get_running_loop())


def get_engine() -> AsyncEngine:
    loop_key = _loop_key()
    engine = _engine_by_loop.get(loop_key)
    if engine is None:
        engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
        _engine_by_loop[loop_key] = engine
    return engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    loop_key = _loop_key()
    sessionmaker = _sessionmaker_by_loop.get(loop_key)
    if sessionmaker is None:
        sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
        _sessionmaker_by_loop[loop_key] = sessionmaker
    return sessionmaker


async def dispose_engine() -> None:
    loop_key = _loop_key()
    engine = _engine_by_loop.pop(loop_key, None)
    _sessionmaker_by_loop.pop(loop_key, None)
    if engine is not None:
        await engine.dispose()


def create_session() -> AsyncSession:
    return get_sessionmaker()()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
