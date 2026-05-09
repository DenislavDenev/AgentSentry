"""SQLite + aiosqlite via SQLAlchemy core.

Concurrency notes:
- SQLite serialises writers at the file level. For a single-process FastAPI app,
  WAL mode + a generous busy_timeout is enough — we don't need a writer queue
  until a second in-process writer arrives in Stage 2 (watchdog thread).
- `BEGIN IMMEDIATE` is used implicitly by SQLAlchemy when we open `conn.begin()`
  and the very first statement is a write. To be safe under concurrent reads, we
  rely on WAL so readers don't block writers.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from watchtower.config import config

_engine: AsyncEngine | None = None


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite") or "sqlite" in url.split("://", 1)[0]


def _attach_sqlite_pragmas(engine: AsyncEngine) -> None:
    """Apply WAL / busy_timeout / foreign_keys on every new connection."""

    sync_engine = engine.sync_engine

    @event.listens_for(sync_engine, "connect")
    def _set_pragmas(dbapi_conn, _conn_record):  # type: ignore[no-untyped-def]
        cur = dbapi_conn.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.execute("PRAGMA foreign_keys=ON")
        finally:
            cur.close()


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = config.database_url
        # NullPool keeps each request on its own connection — simpler with SQLite's
        # per-connection pragmas and one-writer-at-a-time semantics.
        _engine = create_async_engine(url, poolclass=NullPool)
        if _is_sqlite(url):
            _attach_sqlite_pragmas(_engine)
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
