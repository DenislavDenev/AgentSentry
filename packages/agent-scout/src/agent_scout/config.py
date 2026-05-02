from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_data_dir: Path = Path("/data/agent-logs")
    state_dir: Path = Path("/var/lib/agentsentry/scout")
    watchtower_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    emit_timeout_seconds: int = 10
