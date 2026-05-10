import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

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


async def _start_scout():
    """Start the in-process JSONL watcher if AGENT_DATA_DIR is configured.

    Returns the Scout instance (caller must call stop() on shutdown), or None
    if the scout is disabled or the data directory does not exist.
    """
    from watchtower.scout.state import StateStore
    from watchtower.scout.watcher import Scout

    agent_data_dir = config.agent_data_dir
    if agent_data_dir is None:
        logger.info("Scout disabled — set AGENT_DATA_DIR to enable")
        return None
    if not agent_data_dir.exists():
        logger.warning("Scout: AGENT_DATA_DIR does not exist: %s (skipping)", agent_data_dir)
        return None

    loop = asyncio.get_event_loop()
    state = StateStore(config.state_dir)
    scout = Scout(agent_data_dir, state, loop)
    await scout.initial_scan_async()
    scout.start()
    return scout


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _run_migrations()
    await startup()
    scout = await _start_scout()
    try:
        yield
    finally:
        if scout is not None:
            scout.stop()
        await shutdown()


app = FastAPI(title="Watchtower", version="0.1.0", lifespan=lifespan)

# All JSON endpoints live under /api so the Vite SPA can fetch /api/* and
# FastAPI routes don't collide with the SPA's client-side paths.
app.include_router(ingest.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")


@app.exception_handler(StarletteHTTPException)
async def spa_fallback(request: Request, exc: StarletteHTTPException):
    """Serve index.html for 404s on non-API paths (SPA client-side routing).

    For /api/* paths (or non-404 errors) the standard JSON error body is returned.
    StaticFiles raises 404 for every path the SPA owns (/sessions/:id, etc.);
    this handler intercepts those and returns index.html so React Router takes over.
    Note: cannot re-raise inside a Starlette exception handler — must return a response.
    """
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        if config.dashboard_dir is not None:
            index = config.dashboard_dir / "index.html"
            if index.exists():
                return FileResponse(index)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Mount static files last so /api/* routes shadow correctly.
# check_dir=False: on CT 111 the dir is built by the install script; on dev
# workstations dashboard_dir is None so the mount is skipped entirely.
if config.dashboard_dir is not None and config.dashboard_dir.exists():
    app.mount("/", StaticFiles(directory=str(config.dashboard_dir), html=False), name="spa")


def main() -> None:
    uvicorn.run("watchtower.__main__:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    main()
