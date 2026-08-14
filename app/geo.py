"""Portable distance/travel-time helpers.

Pure Python so the itinerary builder works identically on SQLite and Postgres.
When running on PostGIS the same distances are available in-database for
larger spatial queries (nearest retreats, clustering); this module covers the
point-to-point maths the planner needs.
"""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_KM = 6371.0

# Effective door-to-door city speed (km/h), well below road speed once you
# account for parking, traffic and the walk at each end.
CITY_SPEED_KMH = 22.0
MIN_HOP_MINUTES = 8  # even a "next door" stop costs some minutes


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_KM * asin(sqrt(a))


def travel_minutes(lat1: float, lon1: float, lat2: float, lon2: float,
                   speed_kmh: float = CITY_SPEED_KMH) -> int:
    km = haversine_km(lat1, lon1, lat2, lon2)
    minutes = km / speed_kmh * 60
    return max(MIN_HOP_MINUTES, round(minutes)) if km > 0 else 0
