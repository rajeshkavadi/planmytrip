"""A thin booking-inventory stub: flight and hotel options.

Real fare/room feeds would slot in behind these functions; for now they
generate stable, plausible options from the destination so the Plan screen has
something concrete to choose from. Deterministic (seeded by slug) so the same
destination always shows the same options. Pure Python — no DB, no web.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import md5


@dataclass(frozen=True)
class FlightOption:
    id: str
    airline: str
    flight_no: str
    depart: str          # "HH:MM" from the origin
    arrive: str          # "HH:MM" local
    duration_min: int
    stops: int
    price_inr: int

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class HotelOption:
    id: str
    name: str
    area: str
    style: str
    rating: float
    price_per_night_inr: int

    def as_dict(self) -> dict:
        return asdict(self)


_AIRLINES = [("IndiGo", "6E"), ("Air India", "AI"), ("Vistara", "UK"),
             ("Akasa Air", "QP"), ("SpiceJet", "SG")]

# Three fixed dayparts; arrival times matter because they drive Day 1 pacing.
_FLIGHT_SLOTS = [
    ("06:10", "08:20", 130, 0, 1.30, "early nonstop"),
    ("11:30", "15:05", 215, 1, 0.85, "midday, 1 stop"),
    ("19:40", "21:55", 135, 0, 1.10, "evening nonstop"),
]
_HOTEL_TIERS = [
    ("Heritage / boutique", 4.7, 1.9),
    ("Mid-range comfort", 4.2, 1.0),
    ("Smart budget", 3.9, 0.6),
]


def _seed(*parts: str) -> int:
    return int(md5("|".join(parts).encode()).hexdigest()[:8], 16)


def flight_options(slug: str, origin: str, base_cost_inr: int, date: str | None = None) -> list[FlightOption]:
    base_fare = max(2500, round(base_cost_inr * 0.22))
    out: list[FlightOption] = []
    for i, (dep, arr, dur, stops, mult, _label) in enumerate(_FLIGHT_SLOTS):
        s = _seed(slug, origin, str(i), date or "")
        airline, code = _AIRLINES[s % len(_AIRLINES)]
        price = round(base_fare * mult / 100) * 100 + (s % 6) * 100
        out.append(FlightOption(
            id=f"{slug}-fl-{i}", airline=airline, flight_no=f"{code}-{1000 + (s % 8999)}",
            depart=dep, arrive=arr, duration_min=dur, stops=stops, price_inr=price,
        ))
    return out


def hotel_options(slug: str, dest_name: str, base_cost_inr: int) -> list[HotelOption]:
    base_night = max(1200, round(base_cost_inr * 0.09))
    areas = ["Old town", "Lakeside", "Near the centre"]
    out: list[HotelOption] = []
    for i, (style, rating, mult) in enumerate(_HOTEL_TIERS):
        s = _seed(slug, "hotel", str(i))
        price = round(base_night * mult / 100) * 100 + (s % 5) * 100
        out.append(HotelOption(
            id=f"{slug}-ht-{i}", name=f"The {dest_name.split(' ')[0]} {['Residency','House','Stay'][i]}",
            area=areas[i % len(areas)], style=style, rating=rating,
            price_per_night_inr=price,
        ))
    return out
