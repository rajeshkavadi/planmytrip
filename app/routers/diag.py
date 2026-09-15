"""Diagnostics for the live booking integration.

Open these in a browser once RAPIDAPI_KEY is set, then paste the JSON back so
the field mapping can be finalised against real responses. Returns raw upstream
data (truncated) plus what the parser made of it. The API key is never echoed.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..providers.booking_live import get_client
from ..providers.weather import ProviderError
from ..routers.booking import _dest

router = APIRouter(prefix="/diag", tags=["diagnostics"])
_CAP = 6000  # cap raw payloads so the page stays pasteable


@router.get("/status")
def status():
    return {
        "rapidapi_key_configured": settings.booking_live_enabled,
        "rapidapi_host": settings.rapidapi_host,
        "hint": "" if settings.booking_live_enabled else
                "Set RAPIDAPI_KEY (e.g. in %LOCALAPPDATA%/PlanMyTrip/planmytrip.env) and restart.",
    }


@router.get("/flights-raw")
def flights_raw(
    slug: str = Query(default="jaipur"),
    origin: str = Query(default="BLR"),
    date: str = Query(default="2026-10-12"),
    adults: int = Query(default=1, ge=1, le=9),
    db: Session = Depends(get_db),
):
    if not settings.booking_live_enabled:
        return {"error": "No RAPIDAPI_KEY configured — this shows sample data only."}
    d = _dest(db, slug)
    client = get_client()
    out: dict = {"slug": slug, "origin": origin.upper(), "dest_iata": d.iata, "date": date}
    try:
        out["airport_ids"] = {
            origin.upper(): client._airport_ids(origin.upper()),
            d.iata: client._airport_ids(d.iata),
        }
    except ProviderError as e:
        out["airport_lookup_error"] = str(e)
        return out
    try:
        raw = client.raw_flights(origin.upper(), d.iata, date, adults)
        out["raw_truncated"] = json.dumps(raw)[:_CAP]
        try:
            out["parsed_count"] = len(client.flight_offers(origin.upper(), d.iata, date, adults))
        except ProviderError as e:
            out["parse_error"] = str(e)
    except ProviderError as e:
        out["search_error"] = str(e)
    return out


@router.get("/hotels-raw")
def hotels_raw(
    slug: str = Query(default="jaipur"),
    checkin: str = Query(default="2026-10-12"),
    checkout: str = Query(default="2026-10-17"),
    adults: int = Query(default=2, ge=1, le=9),
    db: Session = Depends(get_db),
):
    if not settings.booking_live_enabled:
        return {"error": "No RAPIDAPI_KEY configured — this shows sample data only."}
    d = _dest(db, slug)
    client = get_client()
    out: dict = {"slug": slug, "query": d.name, "checkin": checkin, "checkout": checkout}
    try:
        out["hotel_entity"] = client._hotel_entity(d.name)
        raw = client.raw_hotels(d.name, checkin, checkout, adults)
        out["raw_truncated"] = json.dumps(raw)[:_CAP]
    except ProviderError as e:
        out["error"] = str(e)
    return out
