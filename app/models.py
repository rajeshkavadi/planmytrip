from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .domain import Crowd, Intent


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(80))
    region: Mapped[str] = mapped_column(String(80))  # e.g. "himalayas", "south"
    summary: Mapped[str] = mapped_column(Text, default="")
    hero_gradient: Mapped[str] = mapped_column(String(40), default="hills")
    base_cost_inr: Mapped[int] = mapped_column(Integer)  # typical per-person, mid trip
    tags: Mapped[list] = mapped_column(JSON, default=list)
    # Bargaining etiquette differs sharply by region — surfaced in the shopping guide.
    bargaining_norm: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    # A PostGIS `geom geography(Point,4326)` column is added at the DB level in
    # database.init_db() when running on Postgres (for "retreats within 50km",
    # clustering, routing). lat/lon above stay the portable source of truth.

    intent_fits: Mapped[list["IntentFit"]] = relationship(
        back_populates="destination", cascade="all, delete-orphan"
    )
    seasons: Mapped[list["SeasonMonth"]] = relationship(
        back_populates="destination", cascade="all, delete-orphan"
    )
    shopping: Mapped[list["ShoppingItem"]] = relationship(
        back_populates="destination", cascade="all, delete-orphan"
    )
    retreats: Mapped[list["WellnessRetreat"]] = relationship(
        back_populates="destination"
    )
    places: Mapped[list["Place"]] = relationship(
        back_populates="destination", cascade="all, delete-orphan"
    )


class IntentFit(Base):
    """How well a destination serves a given travel intent (0–100)."""

    __tablename__ = "intent_fits"
    __table_args__ = (UniqueConstraint("destination_id", "intent"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"), index=True
    )
    intent: Mapped[Intent] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer)

    destination: Mapped[Destination] = relationship(back_populates="intent_fits")


class SeasonMonth(Base):
    """Season intelligence: one row per destination per month (12 each)."""

    __tablename__ = "season_months"
    __table_args__ = (UniqueConstraint("destination_id", "month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"), index=True
    )
    month: Mapped[int] = mapped_column(Integer)  # 1–12
    # Base desirability of the weather/experience this month (0–100), before crowds.
    weather_score: Mapped[int] = mapped_column(Integer)
    crowd: Mapped[Crowd] = mapped_column(String(12))
    avg_temp_c: Mapped[int] = mapped_column(Integer)
    rainfall_mm: Mapped[int] = mapped_column(Integer)
    festival: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")

    destination: Mapped[Destination] = relationship(back_populates="seasons")


class WellnessRetreat(Base):
    """Judged on credentials, not review stars."""

    __tablename__ = "wellness_retreats"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(160))
    destination_id: Mapped[int | None] = mapped_column(
        ForeignKey("destinations.id"), nullable=True, index=True
    )
    tradition: Mapped[str] = mapped_column(String(120))  # Ayurveda, Sowa-Rigpa...
    program: Mapped[str] = mapped_column(String(160))
    price_inr_week: Mapped[int] = mapped_column(Integer)
    accredited: Mapped[bool] = mapped_column(Boolean, default=False)  # e.g. NABH
    physician_led: Mapped[bool] = mapped_column(Boolean, default=False)
    silent_option: Mapped[bool] = mapped_column(Boolean, default=False)
    credentials: Mapped[list] = mapped_column(JSON, default=list)

    destination: Mapped[Destination | None] = relationship(back_populates="retreats")


class Place(Base):
    """A schedulable activity/attraction — the raw material for itineraries."""

    __tablename__ = "places"

    id: Mapped[int] = mapped_column(primary_key=True)
    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    visit_minutes: Mapped[int] = mapped_column(Integer, default=90)
    open_hour: Mapped[int] = mapped_column(Integer, default=0)   # 24h
    close_hour: Mapped[int] = mapped_column(Integer, default=24)
    intensity: Mapped[str] = mapped_column(String(10), default="medium")
    time_of_day: Mapped[str] = mapped_column(String(12), default="any")
    weather_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    note: Mapped[str] = mapped_column(Text, default="")

    destination: Mapped[Destination] = relationship(back_populates="places")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    trips: Mapped[list["SavedTrip"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SavedTrip(Base):
    """A saved plan and its living trip document.

    `itinerary` and `snapshot` hold a self-contained JSON payload the client
    caches for offline use; `replan` regenerates them when a flight moves.
    """

    __tablename__ = "saved_trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    destination_slug: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    intent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nights: Mapped[int] = mapped_column(Integer, default=3)
    party_size: Mapped[int] = mapped_column(Integer, default=1)
    budget_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flight_arrival: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Chosen booking options (from the Plan screen). Nullable so the cost
    # engine falls back to defaults when nothing is selected yet.
    flight_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stay_per_night_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flight_desc: Mapped[str] = mapped_column(String(120), default="")
    hotel_name: Mapped[str] = mapped_column(String(160), default="")
    itinerary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="trips")


class ShoppingItem(Base):
    """What a place is genuinely known for — GI tags, authenticity, where to buy."""

    __tablename__ = "shopping_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80))
    gi_tagged: Mapped[bool] = mapped_column(Boolean, default=False)
    where_to_buy: Mapped[str] = mapped_column(Text, default="")
    authenticity_note: Mapped[str] = mapped_column(Text, default="")

    destination: Mapped[Destination] = relationship(back_populates="shopping")
