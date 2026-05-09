from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # Default points at a local SQLite file. Production deploys override via env.
    database_url: str = "sqlite+aiosqlite:///./agentsentry.db"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


config = Config()
