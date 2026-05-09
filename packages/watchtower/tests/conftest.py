"""Shared test fixtures.

Tests run against a real on-disk SQLite database in a tempdir so we exercise
the same code path as production (WAL mode, file locking, alembic migrations).
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest_asyncio.fixture(scope="session")
async def engine():
    tmpdir = Path(tempfile.mkdtemp(prefix="watchtower-test-"))
    db_path = tmpdir / "test.db"
    url = f"sqlite+aiosqlite:///{db_path}"

    # Point the app config at this DB before its singleton is built.
    os.environ["DATABASE_URL"] = url
    import watchtower.config as cfg_mod
    cfg_mod.config.database_url = url

    # Run migrations against the temp DB.
    from alembic import command
    from alembic.config import Config as AlembicConfig

    pkg_root = Path(__file__).resolve().parent.parent
    cfg = AlembicConfig(str(pkg_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(pkg_root / "migrations"))
    command.upgrade(cfg, "head")

    e = create_async_engine(url)
    yield e
    await e.dispose()
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(engine):
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM tool_calls"))
        await conn.execute(text("DELETE FROM messages"))
        await conn.execute(text("DELETE FROM sessions"))
    yield


@pytest_asyncio.fixture(scope="session")
async def client(engine):
    import watchtower.db as db_module

    db_module._engine = engine

    from watchtower.__main__ import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
