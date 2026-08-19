from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .domain import Crowd, Intent


class SeasonMonthOut(BaseModel):
    month: int
    weather_score: int
    crowd: Crowd
    avg_temp_c: int
    rainfall_mm: int
    festival: str | None = None
    note: str = ""
    suitability: float


class DestinationCard(BaseModel):
    slug: str
    name: str
    state: str
    region: str
    summary: str
    hero_gradient: str
    base_cost_inr: int
    tags: list[str]
    latitude: float
    longitude: float


class ScoredCard(DestinationCard):
    composite: float
    intent_fit: int
    season_suitability: float
    over_budget: bool
    why: str


class DiscoverResponse(BaseModel):
    intent: Intent
    month: int
    budget_inr: int | None
    count: int
    results: list[ScoredCard]


class SeasonReport(BaseModel):
    month: str
    verdict: str
    suitability: float
    best_windows: list[str]
    sweet_spot: list[str]
    in_sweet_spot: bool
    caveats: list[str]


class RetreatOut(BaseModel):
    id: int
    name: str
    location: str
    tradition: str
    program: str
    price_inr_week: int
    accredited: bool
    physician_led: bool
    silent_option: bool
    credentials: list[str]


class ShoppingItemOut(BaseModel):
    name: str
    category: str
    gi_tagged: bool
    where_to_buy: str
    authenticity_note: str


class ShoppingGuide(BaseModel):
    destination: str
    bargaining_norm: str
    items: list[ShoppingItemOut]


class CostLineOut(BaseModel):
    label: str
    amount_inr: int
    hidden: bool


class CostEstimateOut(BaseModel):
    lines: list[CostLineOut]
    total_inr: int
    hidden_total_inr: int


class DestinationDetail(DestinationCard):
    bargaining_norm: str
    seasons: list[SeasonMonthOut]
    intent_fits: dict[str, int]
    shopping: list[ShoppingItemOut]
    retreats: list[RetreatOut]


# ---- users & saved trips ----
class UserCreate(BaseModel):
    email: str


class UserOut(BaseModel):
    id: int
    email: str
    api_key: str  # returned once on creation; the client stores it


class SavedTripCreate(BaseModel):
    destination_slug: str
    title: str = ""
    intent: Intent | None = None
    month: int | None = None
    nights: int = 3
    party_size: int = 1
    budget_inr: int | None = None
    flight_arrival: datetime | None = None
    flight_inr: int | None = None
    stay_per_night_inr: int | None = None
    flight_desc: str = ""
    hotel_name: str = ""


class SavedTripSummary(BaseModel):
    id: int
    destination_slug: str
    title: str
    nights: int
    party_size: int
    status: str
    updated_at: datetime


class ReplanRequest(BaseModel):
    flight_arrival: datetime  # new arrival after a schedule change
