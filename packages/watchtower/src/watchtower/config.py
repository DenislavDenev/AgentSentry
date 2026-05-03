from pydantic_settings import BaseSettings


class Config(BaseSettings):
    database_url: str = "postgresql+asyncpg://agentsentry:changeme@localhost:5432/agentsentry"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


config = Config()
