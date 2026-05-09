import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from watchtower.config import config
from watchtower.db import shutdown, startup
from watchtower.router import ingest, models, projects, prompts, sessions, stats, tools

logger = logging.getLogger("watchtower")
logging.basicConfig(level=config.log_level.upper())


def _run_migrations() -> None:
    """Run `alembic upgrade head` synchronously at startup.

    Uses the Alembic Python API rather than shelling out so the install is
    self-contained — no need for the alembic CLI on the runtime PATH.
    """
    from alembic import command
    from alembic.config import Config as AlembicConfig

    pkg_root = Path(__file__).resolve().parent.parent.parent
    cfg_path = pkg_root / "alembic.ini"
    if not cfg_path.exists():
        logger.warning("alembic.ini not found at %s; skipping migrations", cfg_path)
        return

    cfg = AlembicConfig(str(cfg_path))
    # Make the configured DATABASE_URL visible to env.py.
    os.environ.setdefault("DATABASE_URL", config.database_url)
    cfg.set_main_option("script_location", str(pkg_root / "migrations"))
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
