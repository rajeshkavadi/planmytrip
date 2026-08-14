"""Day-by-day itinerary builder.

Turns a bag of candidate places into a paced schedule that respects three
things the "list of things to do" apps ignore:

1. **Opening hours** — a stop is only scheduled inside its open window.
2. **Travel time** — real haversine hops between consecutive stops, with a
   short rest after a long transfer.
3. **Energy pacing** — a per-day intensity budget, a rest after anything
   strenuous, a lunch break, and a midday-heat gap for sun-exposed stops.

Pure Python over dataclasses — no DB, no web — so it is fully unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .domain import (
    INTENSITY_POINTS,
    TIME_OF_DAY_ORDER,
    Intensity,
    TimeOfDay,
)
from .geo import travel_minutes

# --- day shape (minutes from midnight) ---
DAY_START = 8 * 60 + 30       # 08:30
DAY_END = 20 * 60             # 20:00
LUNCH_EARLIEST = 12 * 60 + 30 # 12:30
LUNCH_MINUTES = 45
HEAT_START = 13 * 60          # 13:00
HEAT_END = 15 * 60 + 30       # 15:30

MAX_INTENSITY_POINTS = 6      # e.g. two HIGH + one MEDIUM per day
REST_AFTER_HIGH = 30
LONG_TRANSFER_MIN = 75
REST_AFTER_TRANSFER = 20


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


@dataclass(frozen=True)
class PlaceInput:
    id: str
    name: str
    category: str
    lat: float
    lon: float
    visit_minutes: int
    open_hour: int = 0          # 24h; 0 => always open
    close_hour: int = 24
    intensity: Intensity = Intensity.MEDIUM
    time_of_day: TimeOfDay = TimeOfDay.ANY
    weather_sensitive: bool = False   # exposed to sun/heat
    priority: int = 50               # 0–100; higher = schedule first
    note: str = ""


@dataclass
class Stop:
    kind: str            # "visit" | "travel" | "rest" | "meal"
    start: int           # minutes from midnight
    end: int
    title: str
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "start": _hhmm(self.start),
            "end": _hhmm(self.end),
            "title": self.title,
            "detail": self.detail,
        }


@dataclass
class DaySchedule:
    day: int
    stops: list[Stop] = field(default_factory=list)

    @property
    def active_minutes(self) -> int:
        return sum(s.end - s.start for s in self.stops if s.kind == "visit")

    @property
    def intensity_points(self) -> int:
        return getattr(self, "_pts", 0)

    def as_dict(self) -> dict:
        return {
            "day": self.day,
            "active_minutes": self.active_minutes,
            "intensity_points": self.intensity_points,
            "stops": [s.as_dict() for s in self.stops],
        }


def _points(p: PlaceInput) -> int:
    return INTENSITY_POINTS[p.intensity]


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _assign_days(places: list[PlaceInput], days: int) -> tuple[list[list[PlaceInput]], list[PlaceInput]]:
    """Greedily fill days up to the intensity budget, priority first."""
    ordered = sorted(places, key=lambda p: -p.priority)
    buckets: list[list[PlaceInput]] = [[] for _ in range(days)]
    points = [0] * days
    leftover: list[PlaceInput] = []
    for p in ordered:
        for d in range(days):
            if points[d] + _points(p) <= MAX_INTENSITY_POINTS:
                buckets[d].append(p)
                points[d] += _points(p)
                break
        else:
            leftover.append(p)
    return buckets, leftover


def _schedule_day(day_num: int, places: list[PlaceInput]) -> tuple[DaySchedule, list[PlaceInput]]:
    """Lay out one day's places on the clock. Returns (schedule, overflow)."""
    # Order by time-of-day intent, then priority.
    places = sorted(places, key=lambda p: (TIME_OF_DAY_ORDER[p.time_of_day], -p.priority))
    day = DaySchedule(day=day_num)
    overflow: list[PlaceInput] = []
    t = DAY_START
    loc: tuple[float, float] | None = None
    had_lunch = False
    pts = 0

    for p in places:
        # 1) travel from previous stop
        if loc is not None:
            tt = travel_minutes(loc[0], loc[1], p.lat, p.lon)
            if tt > 0:
                day.stops.append(Stop("travel", t, t + tt, f"Travel to {p.name}",
                                      f"~{tt} min"))
                t += tt
                if tt >= LONG_TRANSFER_MIN:  # pacing: breather after a long hop
                    day.stops.append(Stop("rest", t, t + REST_AFTER_TRANSFER,
                                          "Breather", "Long transfer — short rest"))
                    t += REST_AFTER_TRANSFER

        # 2) lunch break once we're into the window
        if not had_lunch and t >= LUNCH_EARLIEST:
            day.stops.append(Stop("meal", t, t + LUNCH_MINUTES, "Lunch",
                                  "Paced in, not skipped"))
            t += LUNCH_MINUTES
            had_lunch = True

        # 3) opening hours: wait for open
        open_m = p.open_hour * 60
        note = p.note
        if t < open_m:
            if open_m >= DAY_END:
                overflow.append(p)
                continue
            note = (note + " · " if note else "") + f"opens {p.open_hour:02d}:00"
            t = open_m

        # 4) midday heat: push sun-exposed stops past the heat window
        if p.weather_sensitive and _overlaps(t, t + p.visit_minutes, HEAT_START, HEAT_END):
            t = HEAT_END
            note = (note + " · " if note else "") + "shifted past midday heat"

        start_visit = t
        end_visit = t + p.visit_minutes
        close_m = p.close_hour * 60

        # 5) must fit inside opening hours and the day
        if end_visit > close_m or end_visit > DAY_END:
            overflow.append(p)
            continue

        tod = "" if p.time_of_day == TimeOfDay.ANY else f"{p.time_of_day.value} · "
        day.stops.append(Stop("visit", start_visit, end_visit, p.name,
                              f"{tod}{p.category}" + (f" · {note}" if note else "")))
        t = end_visit
        pts += _points(p)
        loc = (p.lat, p.lon)

        # 6) pacing: rest after a strenuous stop
        if p.intensity == Intensity.HIGH and t + REST_AFTER_HIGH <= DAY_END:
            day.stops.append(Stop("rest", t, t + REST_AFTER_HIGH, "Rest",
                                  "Recovery after a high-intensity stop"))
            t += REST_AFTER_HIGH

    day._pts = pts  # type: ignore[attr-defined]
    return day, overflow


def build_itinerary(places: list[PlaceInput], days: int) -> dict:
    """Build a `days`-day plan. Returns a JSON-friendly dict."""
    days = max(1, days)
    buckets, leftover = _assign_days(places, days)
    schedules: list[DaySchedule] = []
    overflow_all: list[PlaceInput] = list(leftover)
    for d in range(days):
        sched, overflow = _schedule_day(d + 1, buckets[d])
        schedules.append(sched)
        overflow_all.extend(overflow)

    return {
        "days": [s.as_dict() for s in schedules],
        "unscheduled": [
            {"id": p.id, "name": p.name,
             "reason": "exceeds daily energy budget or opening-hour fit"}
            for p in overflow_all
        ],
    }


def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def apply_flight_arrival(plan: dict, arrival_hhmm: str, buffer_minutes: int = 60) -> dict:
    """Re-plan Day 1 around a (possibly delayed) flight arrival.

    Anything on Day 1 that starts before arrival + a transfer buffer is dropped
    and recorded, so a slipped flight doesn't leave the traveller with a plan
    that already sailed. Later days are untouched. Returns a new plan dict with
    a `changes` log. Pure — no DB.
    """
    import copy

    plan = copy.deepcopy(plan)
    cutoff = _to_minutes(arrival_hhmm) + buffer_minutes
    changes: list[str] = []
    if plan.get("days"):
        day1 = plan["days"][0]
        kept, dropped = [], []
        for stop in day1["stops"]:
            if stop["kind"] == "visit" and _to_minutes(stop["start"]) < cutoff:
                dropped.append(stop)
            else:
                kept.append(stop)
        # Trim leading travel/rest/meal stops now stranded before the first kept visit.
        first_visit = next((i for i, s in enumerate(kept) if s["kind"] == "visit"), None)
        if first_visit is not None:
            kept = kept[first_visit:]
        elif not kept:
            kept = [{
                "kind": "rest", "start": arrival_hhmm, "end": arrival_hhmm,
                "title": "Arrive & settle in",
                "detail": "Flight lands late — Day 1 kept as arrival + rest",
            }]
        day1["stops"] = kept
        day1["active_minutes"] = sum(
            _to_minutes(s["end"]) - _to_minutes(s["start"])
            for s in kept if s["kind"] == "visit"
        )
        for s in dropped:
            changes.append(f"Dropped '{s['title']}' (started {s['start']}, before arrival {arrival_hhmm})")
    plan["arrival"] = arrival_hhmm
    plan["changes"] = changes or ["Flight arrival still fits the plan — no changes."]
    return plan
