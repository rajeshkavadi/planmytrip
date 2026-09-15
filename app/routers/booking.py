"""Flight & hotel options for a destination.

Uses real data from RapidAPI's Sky-Scrapper when a key is configured
(settings.booking_live_enabled); otherwise returns generated sample options.
Either way the response includes a `source` field ("live" or "sample") so the
UI can label it honestly, plus a `note` when a live lookup fell back.
"""
from __future__ import annotations

from datetime import date as date_cls, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..inventory import flight_options, hotel_options
from ..models import Destination
from ..providers.booking_live import get_client
from ..providers.weather import ProviderError

router = APIRouter(prefix="/destinations", tags=["booking"])


def _dest(db: Session, slug: str) -> Destination:
    d = db.query(Destination).filter(Destination.slug == slug).first()
    if not d:
        raise HTTPException(404, f"Unknown destination '{slug}'")
    return d


@router.get("/{slug}/flights")
def get_flights(
    slug: str,
    origin: str = Query(default="BLR", min_length=3, max_length=3),
    date: str | None = Query(default=None, description="Departure date YYYY-MM-DD."),
    adults: int = Query(default=1, ge=1, le=9),
    db: Session = Depends(get_db),
):
    d = _dest(db, slug)
    dep_date = date or (date_cls.today() + timedelta(days=21)).isoformat()

    if settings.booking_live_enabled and d.iata:
        try:
            opts = get_client().flight_offers(origin.upper(), d.iata, dep_date, adults)
            return {"destination": d.name, "origin": origin.upper(), "date": dep_date,
                    "source": "live", "options": [f.as_dict() for f in opts]}
        except ProviderError as e:
            fallback_note = str(e)
    else:
        fallback_note = None

    opts = flight_options(d.slug, origin.upper(), d.base_cost_inr, dep_date)
    return {"destination": d.name, "origin": origin.upper(), "date": dep_date,
            "source": "sample", "note": fallback_note,
            "options": [f.as_dict() for f in opts]}


@router.get("/{slug}/hotels")
def get_hotels(
    slug: str,
    checkin: str | None = Query(default=None, description="Check-in date YYYY-MM-DD."),
    nights: int = Query(default=3, ge=1, le=60),
    adults: int = Query(default=2, ge=1, le=9),
    db: Session = Depends(get_db),
):
    d = _dest(db, slug)
    ci = checkin or (date_cls.today() + timedelta(days=21)).isoformat()
    try:
        co = (datetime.strptime(ci, "%Y-%m-%d") + timedelta(days=nights)).strftime("%Y-%m-%d")
    except ValueError:
        ci = (date_cls.today() + timedelta(days=21)).isoformat()
        co = (date_cls.today() + timedelta(days=21 + nights)).isoformat()

    if settings.booking_live_enabled and d.iata:
        try:
            opts = get_client().hotel_offers(d.name, ci, co, adults, nights, d.base_cost_inr)
            return {"destination": d.name, "source": "live",
                    "options": [h.as_dict() for h in opts]}
        except ProviderError as e:
            fallback_note = str(e)
    else:
        fallback_note = None

    opts = hotel_options(d.slug, d.name, d.base_cost_inr)
    return {"destination": d.name, "source": "sample", "note": fallback_note,
            "options": [h.as_dict() for h in opts]}
