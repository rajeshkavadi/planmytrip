"""Purpose-based discovery — the wedge endpoint."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload

from ..adapters import to_scoring_input
from ..database import get_db
from ..domain import Intent
from ..models import Destination
from ..schemas import DiscoverResponse, ScoredCard
from ..scoring import rank_destinations

router = APIRouter(tags=["discover"])


@router.get("/discover", response_model=DiscoverResponse)
def discover(
    intent: Intent = Query(..., description="How you want to feel."),
    month: int = Query(default=0, ge=0, le=12, description="1–12; 0 = current month."),
    budget_inr: int | None = Query(default=None, ge=0),
    limit: int = Query(default=5, ge=1, le=20),
    include_over_budget: bool = False,
    db: Session = Depends(get_db),
):
    """Given an intent, a month and a budget, return destinations ranked to fit."""
    month = month or date.today().month

    dests = (
        db.query(Destination)
        .options(selectinload(Destination.intent_fits), selectinload(Destination.seasons))
        .all()
    )
    by_slug = {d.slug: d for d in dests}
    inputs = [to_scoring_input(d) for d in dests]
    scored = rank_destinations(
        inputs, intent=intent, month=month, budget=budget_inr,
        limit=limit, include_over_budget=include_over_budget,
    )

    cards = []
    for s in scored:
        d = by_slug[s.slug]
        cards.append(ScoredCard(
            slug=d.slug, name=d.name, state=d.state, region=d.region,
            summary=d.summary, hero_gradient=d.hero_gradient,
            base_cost_inr=d.base_cost_inr, tags=d.tags,
            latitude=d.latitude, longitude=d.longitude,
            composite=s.composite, intent_fit=s.intent_fit,
            season_suitability=s.season_suitability, over_budget=s.over_budget,
            why=s.why,
        ))
    return DiscoverResponse(
        intent=intent, month=month, budget_inr=budget_inr,
        count=len(cards), results=cards,
    )
