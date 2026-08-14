from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://planmytrip:planmytrip@localhost:5432/planmytrip"
    )
    app_env: str = "development"


settings = Settings()
