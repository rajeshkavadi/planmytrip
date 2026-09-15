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

    # Amadeus Self-Service API — real flight & hotel data. Free keys at
    # https://developers.amadeus.com. Leave blank to use generated sample
    # options. Base URL: test.api.amadeus.com (free tier) or api.amadeus.com.
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    amadeus_base_url: str = "https://test.api.amadeus.com"

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def amadeus_enabled(self) -> bool:
        return bool(self.amadeus_client_id and self.amadeus_client_secret)


settings = Settings()
