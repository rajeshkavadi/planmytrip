"""Destination detail, season intelligence and shopping guide."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from ..adapters import to_place_input, to_scoring_input
from ..database import get_db
from ..itinerary import build_itinerary
from ..models import Destination
from ..schemas import (
    DestinationCard,
    DestinationDetail,
    RetreatOut,
    SeasonMonthOut,
    SeasonReport,
    ShoppingGuide,
    ShoppingItemOut,
)
from ..scoring import season_report, season_suitability

router = APIRouter(prefix="/destinations", tags=["destinations"])


def _load(db: Session, slug: str) -> Destination:
    dest = (
        db.query(Destination)
        .options(
            selectinload(Destination.intent_fits),
            selectinload(Destination.seasons),
            selectinload(Destination.shopping),
            selectinload(Destination.retreats),
            selectinload(Destination.places),
        )
        .filter(Destination.slug == slug)
        .first()
    )
    if not dest:
        raise HTTPException(404, f"Unknown destination '{slug}'")
    return dest


@router.get("", response_model=list[DestinationCard])
def list_destinations(db: Session = Depends(get_db)):
    dests = db.query(Destination).order_by(Destination.name).all()
    return [
        DestinationCard(
            slug=d.slug, name=d.name, state=d.state, region=d.region,
            summary=d.summary, hero_gradient=d.hero_gradient,
            base_cost_inr=d.base_cost_inr, tags=d.tags,
            latitude=d.latitude, longitude=d.longitude,
        )
        for d in dests
    ]


@router.get("/{slug}", response_model=DestinationDetail)
def get_destination(slug: str, db: Session = Depends(get_db)):
    d = _load(db, slug)
    inp = to_scoring_input(d)
    seasons = [
        SeasonMonthOut(
            month=s.month, weather_score=s.weather_score, crowd=s.crowd,
            avg_temp_c=s.avg_temp_c, rainfall_mm=s.rainfall_mm,
            festival=s.festival, note=s.note,
            suitability=round(season_suitability(inp.season_for(s.month)), 1),
        )
        for s in sorted(d.seasons, key=lambda x: x.month)
    ]
    return DestinationDetail(
        slug=d.slug, name=d.name, state=d.state, region=d.region,
        summary=d.summary, hero_gradient=d.hero_gradient,
        base_cost_inr=d.base_cost_inr, tags=d.tags,
        latitude=d.latitude, longitude=d.longitude,
        bargaining_norm=d.bargaining_norm, seasons=seasons,
        intent_fits={f.intent: f.score for f in d.intent_fits},
        shopping=[
            ShoppingItemOut(
                name=i.name, category=i.category, gi_tagged=i.gi_tagged,
                where_to_buy=i.where_to_buy, authenticity_note=i.authenticity_note,
            )
            for i in d.shopping
        ],
        retreats=[
            RetreatOut(
                id=r.id, name=r.name, location=r.location, tradition=r.tradition,
                program=r.program, price_inr_week=r.price_inr_week,
                accredited=r.accredited, physician_led=r.physician_led,
                silent_option=r.silent_option, credentials=r.credentials,
            )
            for r in d.retreats
        ],
    )


@router.get("/{slug}/season", response_model=SeasonReport)
def get_season(
    slug: str,
    month: int = Query(default=0, ge=0, le=12, description="1–12; 0 = current month."),
    db: Session = Depends(get_db),
):
    d = _load(db, slug)
    month = month or date.today().month
    return SeasonReport(**season_report(to_scoring_input(d), month))


@router.get("/{slug}/itinerary")
def get_itinerary(
    slug: str,
    days: int = Query(default=2, ge=1, le=14),
    db: Session = Depends(get_db),
):
    """A paced, day-by-day plan built from this destination's activities.

    Respects opening hours, real travel time between stops, and a daily energy
    budget with rests, a lunch break and a midday-heat gap.
    """
    d = _load(db, slug)
    places = [to_place_input(p) for p in d.places]
    if not places:
        raise HTTPException(404, f"No activities seeded for '{slug}' yet.")
    plan = build_itinerary(places, days=days)
    plan["destination"] = d.name
    return plan


@router.get("/{slug}/shopping", response_model=ShoppingGuide)
def get_shopping(slug: str, db: Session = Depends(get_db)):
    d = _load(db, slug)
    return ShoppingGuide(
        destination=d.name,
        bargaining_norm=d.bargaining_norm,
        items=[
            ShoppingItemOut(
                name=i.name, category=i.category, gi_tagged=i.gi_tagged,
                where_to_buy=i.where_to_buy, authenticity_note=i.authenticity_note,
            )
            for i in d.shopping
        ],
    )
