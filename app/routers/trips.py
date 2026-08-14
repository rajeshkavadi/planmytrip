"""All-in trip cost — the numbers the booking apps hide until checkout."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..costing import estimate_trip_cost
from ..schemas import CostEstimateOut

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
