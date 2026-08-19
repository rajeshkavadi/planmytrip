"""Assemble the living trip document.

One self-contained payload — destination, season intelligence, all-in cost,
paced itinerary, and shopping guide — that the client caches for offline use
and that `replan` refreshes when a flight moves.
"""
from __future__ import annotations

from sqlalchemy.orm import Session, selectinload

from .adapters import to_place_input, to_scoring_input
from .costing import estimate_trip_cost
from .domain import Intent
from .itinerary import apply_flight_arrival, build_itinerary
from .models import Destination, SavedTrip
from .scoring import season_report

# Rough domestic-India defaults for the cost estimate; a real client would let
# the user override these from live fares.
DEFAULT_FLIGHT_INR = 9000
DEFAULT_STAY_PER_NIGHT_INR = 3500


def _load_destination(db: Session, slug: str) -> Destination | None:
    return (
        db.query(Destination)
        .options(
            selectinload(Destination.intent_fits),
            selectinload(Destination.seasons),
            selectinload(Destination.shopping),
            selectinload(Destination.places),
        )
        .filter(Destination.slug == slug)
        .first()
    )


def build_trip_doc(db: Session, trip: SavedTrip) -> dict:
    dest = _load_destination(db, trip.destination_slug)
    if dest is None:
        return {"error": f"Unknown destination '{trip.destination_slug}'"}

    # Itinerary (paced), re-planned around the flight arrival if we have one.
    plan: dict = {"days": [], "unscheduled": []}
    if dest.places:
        plan = build_itinerary([to_place_input(p) for p in dest.places],
                               days=max(1, trip.nights))
        if trip.flight_arrival is not None:
            arrival_hhmm = trip.flight_arrival.strftime("%H:%M")
            plan = apply_flight_arrival(plan, arrival_hhmm)

    # Season intelligence for the chosen month.
    season = None
    if trip.month:
        season = season_report(to_scoring_input(dest), trip.month)

    # All-in cost (per person), using the chosen flight/hotel when present.
    cost = estimate_trip_cost(
        nights=trip.nights,
        flight_inr=trip.flight_inr or DEFAULT_FLIGHT_INR,
        stay_per_night_inr=trip.stay_per_night_inr or DEFAULT_STAY_PER_NIGHT_INR,
    ).as_dict()
    cost["party_size"] = trip.party_size
    cost["trip_total_inr"] = cost["total_inr"] * trip.party_size

    return {
        "trip_id": trip.id,
        "title": trip.title or dest.name,
        "status": trip.status,
        "destination": {
            "slug": dest.slug, "name": dest.name, "state": dest.state,
            "summary": dest.summary, "tags": dest.tags,
        },
        "intent": trip.intent,
        "month": trip.month,
        "nights": trip.nights,
        "party_size": trip.party_size,
        "flight_arrival": trip.flight_arrival.isoformat() if trip.flight_arrival else None,
        "booking": {"flight": trip.flight_desc or None, "hotel": trip.hotel_name or None},
        "season": season,
        "cost": cost,
        "itinerary": plan,
        "shopping": {
            "bargaining_norm": dest.bargaining_norm,
            "items": [
                {"name": i.name, "category": i.category, "gi_tagged": i.gi_tagged,
                 "where_to_buy": i.where_to_buy, "authenticity_note": i.authenticity_note}
                for i in dest.shopping
            ],
        },
        "offline_ready": True,
    }
