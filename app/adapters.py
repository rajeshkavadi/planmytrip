"""Translate ORM rows into the framework-free inputs the scorer expects."""
from __future__ import annotations

from .domain import Crowd, Intensity, Intent, TimeOfDay
from .itinerary import PlaceInput
from .models import Destination, Place
from .scoring import DestinationInput, MonthSeason


def to_scoring_input(dest: Destination) -> DestinationInput:
    return DestinationInput(
        slug=dest.slug,
        name=dest.name,
        base_cost_inr=dest.base_cost_inr,
        intent_fits={Intent(f.intent): f.score for f in dest.intent_fits},
        seasons=[
            MonthSeason(
                month=s.month,
                weather_score=s.weather_score,
                crowd=Crowd(s.crowd),
                avg_temp_c=s.avg_temp_c,
                rainfall_mm=s.rainfall_mm,
                festival=s.festival,
                note=s.note,
            )
            for s in dest.seasons
        ],
    )


def to_place_input(p: Place) -> PlaceInput:
    return PlaceInput(
        id=str(p.id),
        name=p.name,
        category=p.category,
        lat=p.latitude,
        lon=p.longitude,
        visit_minutes=p.visit_minutes,
        open_hour=p.open_hour,
        close_hour=p.close_hour,
        intensity=Intensity(p.intensity),
        time_of_day=TimeOfDay(p.time_of_day),
        weather_sensitive=p.weather_sensitive,
        priority=p.priority,
        note=p.note,
    )
