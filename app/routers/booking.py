"""Flight & hotel options for a destination (booking-inventory stub)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..inventory import flight_options, hotel_options
from ..models import Destination

router = APIRouter(prefix="/destinations", tags=["booking"])


def _dest(db: Session, slug: str) -> Destination:
    d = db.query(Destination).filter(Destination.slug == slug).first()
    if not d:
        raise HTTPException(404, f"Unknown destination '{slug}'")
    return d


@router.get("/{slug}/flights")
def get_flights(
    slug: str,
    origin: str = Query(default="BLR", description="Origin airport code."),
    date: str | None = Query(default=None, description="Departure date YYYY-MM-DD."),
    db: Session = Depends(get_db),
):
    d = _dest(db, slug)
    return {
        "destination": d.name, "origin": origin, "date": date,
        "options": [f.as_dict() for f in flight_options(d.slug, origin, d.base_cost_inr, date)],
    }


@router.get("/{slug}/hotels")
def get_hotels(slug: str, db: Session = Depends(get_db)):
    d = _dest(db, slug)
    return {
        "destination": d.name,
        "options": [h.as_dict() for h in hotel_options(d.slug, d.name, d.base_cost_inr)],
    }
