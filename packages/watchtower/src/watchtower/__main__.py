import logging
import os
import sys
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from watchtower.config import config
from watchtower.db import shutdown, startup
from watchtower.router import ingest, models, projects, prompts, sessions, stats, tools

logger = logging.getLogger("watchtower")
logging.basicConfig(level=config.log_level.upper())


def _alembic_config_path() -> Path:
    """Locate alembic.ini at runtime.

    Order:
      1. WATCHTOWER_ALEMBIC_INI env var (explicit override).
      2. Editable install / source tree: <pkg>/../../alembic.ini.
      3. Installed wheel: package data via importlib.resources (future).

    Fails closed if none of these resolve. The previous fallback to a warning
    let installs start with no schema and only fail on the first request.
    """
    env_path = os.environ.get("WATCHTOWER_ALEMBIC_INI")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    pkg_root = Path(__file__).resolve().parent.parent.parent
    candidate = pkg_root / "alembic.ini"
    if candidate.exists():
        return candidate

    raise RuntimeError(
        "Could not locate alembic.ini. Set WATCHTOWER_ALEMBIC_INI or run from the "
        "watchtower package directory. Refusing to start without applied schema."
    )


@contextmanager
def _migration_lock():
    """Cross-process file lock so concurrent worker startups don't race on
    Alembic's version table or DDL. Linux only — falls back to a no-op on
    Windows (where multi-worker uvicorn isn't a typical deploy target).
    """
    if sys.platform == "win32":
        yield
        return

    import fcntl

    lock_path = Path(os.environ.get("WATCHTOWER_LOCK_DIR", "/tmp")) / "agentsentry-migrate.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _run_migrations() -> None:
    """Run `alembic upgrade head` synchronously at startup, under a file lock.

    Multi-worker deployments are safe because the file lock serialises the
    Alembic version-table update across processes — only one runs the actual
    DDL; the rest acquire the lock, find head already current, and continue.
    """
    from alembic import command
    from alembic.config import Config as AlembicConfig

    cfg_path = _alembic_config_path()
    pkg_root = cfg_path.parent
    cfg = AlembicConfig(str(cfg_path))
    os.environ.setdefault("DATABASE_URL", config.database_url)
    cfg.set_main_option("script_location", str(pkg_root / "migrations"))

    with _migration_lock():
        logger.info("Running alembic upgrade head against %s", config.database_url)
        command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _run_migrations()
    await startup()
    try:
        yield
    finally:
        await shutdown()


app = FastAPI(title="Watchtower", version="0.1.0", lifespan=lifespan)

app.include_router(ingest.router)
app.include_router(sessions.router)
app.include_router(projects.router)
app.include_router(stats.router)
app.include_router(models.router)
app.include_router(tools.router)
app.include_router(prompts.router)


def main() -> None:
    uvicorn.run("watchtower.__main__:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    main()
