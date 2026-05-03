from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from watchtower.config import config

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(config.database_url, poolclass=NullPool)
    return _engine


async def get_conn() -> AsyncGenerator[AsyncConnection, None]:
    async with get_engine().connect() as conn:
        yield conn


async def startup() -> None:
    get_engine()


async def shutdown() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
