import logging

import uvicorn
from fastapi import FastAPI

from watchtower.config import config
from watchtower.db import shutdown, startup
from watchtower.router import ingest, models, projects, sessions, stats, tools

logging.basicConfig(level=config.log_level.upper())

app = FastAPI(title="Watchtower", version="0.1.0")

app.include_router(ingest.router)
app.include_router(sessions.router)
app.include_router(projects.router)
app.include_router(stats.router)
app.include_router(models.router)
app.include_router(tools.router)


@app.on_event("startup")
async def _startup() -> None:
    await startup()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await shutdown()


def main() -> None:
    uvicorn.run("watchtower.__main__:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    main()
