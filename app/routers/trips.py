"""All-in trip cost, saved trips, and the living trip document."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import current_user
from ..costing import estimate_trip_cost
from ..database import get_db
from ..models import Destination, SavedTrip, User
from ..schemas import (
    CostEstimateOut,
    ReplanRequest,
    SavedTripCreate,
    SavedTripSummary,
)
from ..trip_doc import build_trip_doc

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/estimate-cost", response_model=CostEstimateOut)
def estimate_cost(
    nights: int = Query(..., ge=1, le=60),
    flight_inr: int = Query(..., ge=0),
    stay_per_night_inr: int = Query(..., ge=0),
):
    """Return a full per-person breakdown, flagging the 'hidden' lines."""
    est = estimate_trip_cost(
        nights=nights, flight_inr=flight_inr, stay_per_night_inr=stay_per_night_inr
    )
    return CostEstimateOut(**est.as_dict())


def _owned_trip(trip_id: int, user: User, db: Session) -> SavedTrip:
    trip = db.query(SavedTrip).filter(
        SavedTrip.id == trip_id, SavedTrip.user_id == user.id
    ).first()
    if not trip:
        raise HTTPException(404, "Trip not found.")
    return trip


@router.post("", status_code=201)
def save_trip(
    body: SavedTripCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Save a trip and return its living document."""
    if not db.query(Destination).filter(Destination.slug == body.destination_slug).first():
        raise HTTPException(404, f"Unknown destination '{body.destination_slug}'")
    trip = SavedTrip(
        user_id=user.id,
        destination_slug=body.destination_slug,
        title=body.title,
        intent=body.intent.value if body.intent else None,
        month=body.month,
        nights=body.nights,
        party_size=body.party_size,
        budget_inr=body.budget_inr,
        flight_arrival=body.flight_arrival,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    doc = build_trip_doc(db, trip)
    trip.itinerary = doc.get("itinerary", {})
    db.commit()
    return doc


@router.get("", response_model=list[SavedTripSummary])
def list_trips(user: User = Depends(current_user), db: Session = Depends(get_db)):
    trips = (
        db.query(SavedTrip)
        .filter(SavedTrip.user_id == user.id)
        .order_by(SavedTrip.updated_at.desc())
        .all()
    )
    return [
        SavedTripSummary(
            id=t.id, destination_slug=t.destination_slug, title=t.title or t.destination_slug,
            nights=t.nights, party_size=t.party_size, status=t.status, updated_at=t.updated_at,
        )
        for t in trips
    ]


@router.get("/{trip_id}")
def get_trip(
    trip_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """The living trip document — everything the client needs, offline-ready."""
    return build_trip_doc(db, _owned_trip(trip_id, user, db))


@router.post("/{trip_id}/replan")
def replan_trip(
    trip_id: int,
    body: ReplanRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Flight moved? Store the new arrival and rebuild the plan around it."""
    trip = _owned_trip(trip_id, user, db)
    trip.flight_arrival = body.flight_arrival
    trip.status = "replanned"
    db.commit()
    doc = build_trip_doc(db, trip)
    trip.itinerary = doc.get("itinerary", {})
    db.commit()
    return doc
