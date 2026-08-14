from __future__ import annotations

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
