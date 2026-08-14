"""All-in trip cost — including the rows MMT/EMT never show before checkout.

Booking apps quote flight + hotel and let the rest ambush the traveller at
the destination. We estimate the whole thing and flag which lines are the
ones the incumbents hide.
"""
from __future__ import annotations

from dataclasses import dataclass

# Rough per-person daily rates (INR), tuned for domestic India mid-range travel.
LOCAL_TRANSPORT_PER_DAY = 1000
FOOD_PER_DAY = 900
DATA_TIPS_PER_DAY = 150
ENTRIES_PER_DAY = 250


@dataclass(frozen=True)
class CostLine:
    label: str
    amount_inr: int
    hidden: bool  # True = a line the booking apps don't show at checkout


@dataclass(frozen=True)
class CostEstimate:
    lines: list[CostLine]
    total_inr: int
    hidden_total_inr: int  # how much the "hidden" lines add up to

    def as_dict(self) -> dict:
        return {
            "lines": [
                {"label": l.label, "amount_inr": l.amount_inr, "hidden": l.hidden}
                for l in self.lines
            ],
            "total_inr": self.total_inr,
            "hidden_total_inr": self.hidden_total_inr,
        }


def estimate_trip_cost(
    *,
    nights: int,
    flight_inr: int,
    stay_per_night_inr: int,
) -> CostEstimate:
    """Build a full per-person breakdown for a `nights`-night trip.

    `flight_inr` and stay are the only two lines the incumbents would quote;
    everything else here is the gap we close.
    """
    days = nights + 1
    lines = [
        CostLine("Flights (return)", flight_inr, hidden=False),
        CostLine(f"Stays · {nights} nights", stay_per_night_inr * nights, hidden=False),
        CostLine("Local transport & transfers", LOCAL_TRANSPORT_PER_DAY * days, hidden=True),
        CostLine("Entries, activities & permits", ENTRIES_PER_DAY * days, hidden=True),
        CostLine("Data (eSIM) & tips", DATA_TIPS_PER_DAY * days, hidden=True),
        CostLine("Food (estimate)", FOOD_PER_DAY * days, hidden=False),
    ]
    total = sum(l.amount_inr for l in lines)
    hidden_total = sum(l.amount_inr for l in lines if l.hidden)
    return CostEstimate(lines=lines, total_inr=total, hidden_total_inr=hidden_total)
