from pathlib import Path

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # Default points at a local SQLite file. Production deploys override via env.
    database_url: str = "sqlite+aiosqlite:///./agentsentry.db"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Scout (in-process JSONL watcher) settings.
    # Set AGENT_DATA_DIR to enable; scout is skipped if the path does not exist.
    agent_data_dir: Path | None = None
    state_dir: Path = Path("/var/lib/agentsentry/scout")

    # Dashboard (Vite SPA static build).
    # Set DASHBOARD_DIR to serve the built dist/ folder.
    # When set, all /api/* routes are served by FastAPI; all other paths serve index.html.
    dashboard_dir: Path | None = None

    model_config = {"env_file": ".env", "extra": "ignore"}


config = Config()
