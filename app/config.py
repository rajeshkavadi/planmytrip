from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Zero-config default: a local SQLite file, so `python -m app.seed` and the
    # Windows installer work with no database server. Point this at a
    # postgresql+psycopg URL (see .env.example / docker-compose) to enable the
    # PostGIS geography column and spatial queries.
    database_url: str = "sqlite:///./planmytrip.db"
    app_env: str = "development"

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


settings = Settings()
