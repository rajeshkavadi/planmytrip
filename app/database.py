from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url, echo=False, future=True, connect_args=_connect_args
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. On Postgres, also enable PostGIS and add a geography
    column mirrored from lat/lon (used for spatial queries). Safe to re-run.
    """
    # Import models so they register on Base.metadata before create_all.
    from . import models  # noqa: F401

    if settings.is_postgres:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)

    if settings.is_postgres:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE destinations "
                "ADD COLUMN IF NOT EXISTS geom geography(Point,4326)"
            ))
            # Keep geom in sync with the portable lat/lon source of truth.
            conn.execute(text(
                "UPDATE destinations "
                "SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography "
                "WHERE geom IS NULL"
            ))

    # Best-effort forward migration for columns added after a DB already exists
    # (the .exe keeps its SQLite file across upgrades). Additive and idempotent.
    _ensure_columns("saved_trips", {
        "flight_inr": "INTEGER",
        "stay_per_night_inr": "INTEGER",
        "flight_desc": "VARCHAR(120)",
        "hotel_name": "VARCHAR(160)",
    })


def _ensure_columns(table: str, columns: dict[str, str]) -> None:
    """Add any missing columns to an existing table. Additive only."""
    with engine.begin() as conn:
        if settings.is_postgres:
            for name, sqltype in columns.items():
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {sqltype}"))
        else:
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for name, sqltype in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}"))
