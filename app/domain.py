"""Core vocabulary shared across the app.

Kept free of any framework or database import so the scoring logic in
`scoring.py` can be unit-tested without a database or web server.
"""
from __future__ import annotations

from enum import Enum


class Intent(str, Enum):
    """How a traveller wants to *feel* — the wedge of purpose-based discovery.

    The booking apps start from a destination; we start from an intent and
    rank destinations against it.
    """

    RECHARGE = "recharge"
    SPIRITUAL = "spiritual"
    ADVENTURE = "adventure"
    WELLNESS = "wellness"
    SHOPPING = "shopping"
    DETOX = "detox"          # digital detox / off-grid
    FOODIE = "foodie"


class Intensity(str, Enum):
    """How much energy an activity costs — the input to pacing."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


INTENSITY_POINTS: dict["Intensity", int] = {}  # filled below


class TimeOfDay(str, Enum):
    """When an activity is best done — drives ordering within a day."""

    SUNRISE = "sunrise"
    MORNING = "morning"
    ANY = "any"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class Crowd(str, Enum):
    """Crowd density for a destination in a given month."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    PEAK = "peak"


# How much each crowd level pulls a month's suitability down. Crowds are a
# real cost of travel that price-first apps never surface.
CROWD_PENALTY: dict[Crowd, float] = {
    Crowd.VERY_LOW: 0.0,
    Crowd.LOW: 2.0,
    Crowd.MODERATE: 6.0,
    Crowd.HIGH: 14.0,
    Crowd.PEAK: 22.0,
}

INTENSITY_POINTS.update({
    Intensity.LOW: 1,
    Intensity.MEDIUM: 2,
    Intensity.HIGH: 3,
})

# Preferred ordering of activities across a day.
TIME_OF_DAY_ORDER: dict[TimeOfDay, int] = {
    TimeOfDay.SUNRISE: 0,
    TimeOfDay.MORNING: 1,
    TimeOfDay.ANY: 2,
    TimeOfDay.AFTERNOON: 3,
    TimeOfDay.EVENING: 4,
}

MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def month_name(month: int) -> str:
    return MONTH_ABBR[(month - 1) % 12]
