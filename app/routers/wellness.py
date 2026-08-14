"""Retreats & wellness — ranked by credentials, not review stars."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import WellnessRetreat
from ..schemas import RetreatOut

router = APIRouter(prefix="/wellness", tags=["wellness"])


@router.get("", response_model=list[RetreatOut])
def list_retreats(
    tradition: str | None = Query(default=None, description="Substring, e.g. 'Ayurveda'."),
    accredited: bool | None = None,
    silent: bool | None = None,
    max_price_inr_week: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(WellnessRetreat)
    if tradition:
        q = q.filter(WellnessRetreat.tradition.ilike(f"%{tradition}%"))
    if accredited is not None:
        q = q.filter(WellnessRetreat.accredited.is_(accredited))
    if silent is not None:
        q = q.filter(WellnessRetreat.silent_option.is_(silent))
    if max_price_inr_week is not None:
        q = q.filter(WellnessRetreat.price_inr_week <= max_price_inr_week)

    # Credentialed first: accredited + physician-led float to the top.
    retreats = q.all()
    retreats.sort(
        key=lambda r: (r.accredited, r.physician_led, -r.price_inr_week), reverse=True
    )
    return [
        RetreatOut(
            id=r.id, name=r.name, location=r.location, tradition=r.tradition,
            program=r.program, price_inr_week=r.price_inr_week,
            accredited=r.accredited, physician_led=r.physician_led,
            silent_option=r.silent_option, credentials=r.credentials,
        )
        for r in retreats
    ]
