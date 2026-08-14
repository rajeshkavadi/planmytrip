"""Tests for the itinerary builder — opening hours, travel, pacing, replan."""
from __future__ import annotations

from app.domain import Intensity, TimeOfDay
from app.itinerary import (
    DAY_END,
    PlaceInput,
    apply_flight_arrival,
    build_itinerary,
)


def _p(id, name, lat, lon, **kw):
    return PlaceInput(id=id, name=name, category="test", lat=lat, lon=lon,
                      visit_minutes=kw.pop("visit", 60), **kw)


def _visits(day):
    return [s for s in day["stops"] if s["kind"] == "visit"]


def _mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def test_stops_never_scheduled_before_opening():
    # A place that opens at 11:00 must not be visited earlier.
    places = [_p("a", "Late Opener", 26.92, 75.82, open_hour=11, close_hour=18,
                 time_of_day=TimeOfDay.MORNING)]
    plan = build_itinerary(places, days=1)
    v = _visits(plan["days"][0])[0]
    assert _mins(v["start"]) >= 11 * 60


def test_travel_stop_inserted_between_distant_places():
    places = [
        _p("a", "Fort", 26.9855, 75.8513, priority=90),
        _p("b", "Palace", 26.7590, 75.8440, priority=80),  # ~25km south
    ]
    plan = build_itinerary(places, days=1)
    kinds = [s["kind"] for s in plan["days"][0]["stops"]]
    assert "travel" in kinds


def test_energy_budget_splits_across_days():
    # Three HIGH-intensity places = 9 points > daily cap of 6, so they can't
    # all land on one day.
    places = [
        _p(f"h{i}", f"Hard {i}", 26.92 + i * 0.01, 75.82, intensity=Intensity.HIGH,
           priority=90 - i)
        for i in range(3)
    ]
    plan = build_itinerary(places, days=3)
    per_day = [len(_visits(d)) for d in plan["days"]]
    assert max(per_day) <= 2          # never 3 HIGH on one day
    assert sum(per_day) == 3


def test_rest_follows_high_intensity():
    places = [_p("a", "Trek", 26.92, 75.82, intensity=Intensity.HIGH)]
    plan = build_itinerary(places, days=1)
    kinds = [s["kind"] for s in plan["days"][0]["stops"]]
    assert kinds.index("visit") < kinds.index("rest")


def test_weather_sensitive_pushed_past_midday_heat():
    # A sun-exposed 60-min stop should not run during 13:00-15:30.
    places = [_p("a", "Open Fort", 26.92, 75.82, weather_sensitive=True,
                 time_of_day=TimeOfDay.AFTERNOON, open_hour=9, close_hour=19)]
    plan = build_itinerary(places, days=1)
    v = _visits(plan["days"][0])[0]
    s, e = _mins(v["start"]), _mins(v["end"])
    # No overlap with the 13:00-15:30 heat window.
    assert not (s < 15 * 60 + 30 and 13 * 60 < e)


def test_nothing_scheduled_past_day_end():
    places = [_p(f"p{i}", f"P{i}", 26.92 + i * 0.02, 75.82, visit=90,
                 intensity=Intensity.LOW, priority=90 - i) for i in range(6)]
    plan = build_itinerary(places, days=1)
    for s in plan["days"][0]["stops"]:
        assert _mins(s["end"]) <= DAY_END


def test_flight_arrival_drops_morning_stops():
    places = [
        _p("m", "Morning Museum", 26.92, 75.82, time_of_day=TimeOfDay.MORNING, priority=90),
        _p("e", "Evening Bazaar", 26.921, 75.821, time_of_day=TimeOfDay.EVENING, priority=80),
    ]
    plan = build_itinerary(places, days=1)
    replanned = apply_flight_arrival(plan, "15:00")
    titles = [s["title"] for s in replanned["days"][0]["stops"] if s["kind"] == "visit"]
    assert "Morning Museum" not in titles      # started before 15:00 + buffer
    assert any("dropped" in c.lower() or "Dropped" in c for c in replanned["changes"])
