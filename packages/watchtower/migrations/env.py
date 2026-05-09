"""Alembic environment.

Migrations are raw SQL — no async needed. We use a synchronous engine here so
the script works both from the alembic CLI (no event loop) and from inside the
FastAPI lifespan (event loop already running).

The DATABASE_URL env var may be the async form (`sqlite+aiosqlite://...`) used
by the app at runtime; we strip the async driver suffix for the sync engine.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./agentsentry.db",
)


def _to_sync_url(url: str) -> str:
    # Strip async driver suffixes that alembic's sync runner can't use.
    if url.startswith("sqlite+aiosqlite://"):
        return "sqlite://" + url[len("sqlite+aiosqlite://"):]
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://"):]
    return url


sync_url = _to_sync_url(database_url)
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    context.configure(
        url=sync_url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        context.configure(
            connection=conn,
            target_metadata=None,
            render_as_batch=conn.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
