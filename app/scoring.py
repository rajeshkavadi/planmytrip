"""The intelligence layer: purpose-based ranking + season intelligence.

Everything here is pure Python over small dataclasses — no SQLAlchemy, no
FastAPI — so it can be reasoned about and unit-tested in isolation. Routers
adapt ORM rows into these inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .domain import CROWD_PENALTY, Crowd, Intent, month_name

# Weights for the composite discovery score. Intent is the wedge, so it leads;
# season is a strong second because "great place, wrong month" is a bad trip.
W_INTENT = 0.55
W_SEASON = 0.35
DEFAULT_INTENT_FIT = 30  # a destination with no declared fit for the intent


@dataclass(frozen=True)
class MonthSeason:
    month: int  # 1–12
    weather_score: int  # 0–100, desirability before crowds
    crowd: Crowd
    avg_temp_c: int = 0
    rainfall_mm: int = 0
    festival: str | None = None
    note: str = ""


@dataclass(frozen=True)
class DestinationInput:
    slug: str
    name: str
    base_cost_inr: int
    intent_fits: dict[Intent, int] = field(default_factory=dict)
    seasons: list[MonthSeason] = field(default_factory=list)  # ideally 12 entries

    def season_for(self, month: int) -> MonthSeason | None:
        for s in self.seasons:
            if s.month == month:
                return s
        return None


@dataclass(frozen=True)
class ScoredDestination:
    slug: str
    name: str
    composite: float          # 0–100 overall fit for (intent, month, budget)
    intent_fit: int           # 0–100
    season_suitability: float # 0–100 for the requested month
    over_budget: bool
    base_cost_inr: int
    why: str                  # one-line human rationale


# --------------------------------------------------------------------------- #
# Season intelligence
# --------------------------------------------------------------------------- #
def season_suitability(s: MonthSeason) -> float:
    """A month's real desirability = weather minus the cost of crowds."""
    return max(0.0, s.weather_score - CROWD_PENALTY[s.crowd])


def best_windows(seasons: list[MonthSeason], threshold: float = 70.0) -> list[str]:
    """Contiguous month ranges whose suitability clears `threshold`.

    Wraps around the year boundary (e.g. Oct–Mar) so winter windows read
    naturally rather than splitting into two.
    """
    if not seasons:
        return []
    by_month = {s.month: season_suitability(s) for s in seasons}
    good = [m for m in range(1, 13) if by_month.get(m, 0) >= threshold]
    if not good:
        return []
    if len(good) == 12:
        return ["Year-round"]

    good_set = set(good)
    # Rotate so we don't start mid-window; find a month whose predecessor is bad.
    start = next(m for m in range(1, 13) if m in good_set and (m - 2) % 12 + 1 not in good_set)
    order = [(start - 1 + i) % 12 + 1 for i in range(12)]

    windows: list[list[int]] = []
    run: list[int] = []
    for m in order:
        if m in good_set:
            run.append(m)
        elif run:
            windows.append(run)
            run = []
    if run:
        windows.append(run)
    return [
        month_name(w[0]) if len(w) == 1 else f"{month_name(w[0])}–{month_name(w[-1])}"
        for w in windows
    ]


def sweet_spot_months(seasons: list[MonthSeason]) -> list[int]:
    """Shoulder-season gems: near-peak experience, below-peak crowds.

    This is the recommendation the price-first apps can't make — the month
    where the hills are green, the rates are soft, and the crowds haven't
    arrived yet.
    """
    if not seasons:
        return []
    suit = {s.month: season_suitability(s) for s in seasons}
    crowd = {s.month: s.crowd for s in seasons}
    peak = max(suit.values())
    peak_crowd = max(CROWD_PENALTY[c] for c in crowd.values())
    out = []
    for m, sc in suit.items():
        near_best = sc >= peak - 12
        quieter = CROWD_PENALTY[crowd[m]] <= max(0.0, peak_crowd - 6)
        if near_best and quieter:
            out.append(m)
    return sorted(out)


def season_report(dest: DestinationInput, month: int) -> dict:
    """Full season-intelligence answer for a destination in a given month."""
    s = dest.season_for(month)
    windows = best_windows(dest.seasons)
    sweet = sweet_spot_months(dest.seasons)
    caveats: list[str] = []
    verdict = "unknown"
    suitability = 0.0

    if s is not None:
        suitability = round(season_suitability(s), 1)
        if suitability >= 78:
            verdict = "excellent"
        elif suitability >= 60:
            verdict = "good"
        elif suitability >= 40:
            verdict = "workable"
        else:
            verdict = "avoid"

        if s.rainfall_mm >= 150:
            caveats.append(
                f"Heavy rain likely ({s.rainfall_mm}mm avg) — monsoon tail; pack layers."
            )
        elif s.rainfall_mm >= 60:
            caveats.append(f"Some showers possible ({s.rainfall_mm}mm avg).")
        if s.crowd in (Crowd.HIGH, Crowd.PEAK):
            caveats.append(f"Crowded this month ({s.crowd.value.replace('_', ' ')}) — book early.")
        if s.festival:
            caveats.append(f"{s.festival} — vivid, but rooms spike; reserve ahead.")

    return {
        "month": month_name(month),
        "verdict": verdict,
        "suitability": suitability,
        "best_windows": windows,
        "sweet_spot": [month_name(m) for m in sweet],
        "in_sweet_spot": month in sweet,
        "caveats": caveats,
    }


# --------------------------------------------------------------------------- #
# Budget + composite ranking (purpose-based discovery)
# --------------------------------------------------------------------------- #
def budget_adjustment(base_cost: int, budget: int | None) -> tuple[float, bool]:
    """Nudge the score by how the trip sits against the traveller's budget.

    Comfortably under budget earns a small bonus; over budget takes a penalty
    that scales with the overshoot. Returns (delta, over_budget).
    """
    if not budget:
        return 0.0, False
    if base_cost <= budget:
        headroom = (budget - base_cost) / budget  # 0..1
        return min(6.0, headroom * 12.0), False
    overshoot = (base_cost - budget) / budget  # >0
    return -min(30.0, overshoot * 45.0), True


def score_destination(
    dest: DestinationInput, intent: Intent, month: int, budget: int | None
) -> ScoredDestination:
    intent_fit = dest.intent_fits.get(intent, DEFAULT_INTENT_FIT)
    s = dest.season_for(month)
    season = season_suitability(s) if s else 50.0
    budget_delta, over = budget_adjustment(dest.base_cost_inr, budget)

    composite = W_INTENT * intent_fit + W_SEASON * season + budget_delta
    composite = round(max(0.0, min(100.0, composite)), 1)

    bits = [f"{intent_fit}/100 for {intent.value}"]
    if s:
        bits.append(f"{month_name(month)} is {round(season)}/100 here")
    if over:
        bits.append("over budget")
    elif budget_delta > 0:
        bits.append("comfortably in budget")
    why = " · ".join(bits)

    return ScoredDestination(
        slug=dest.slug,
        name=dest.name,
        composite=composite,
        intent_fit=intent_fit,
        season_suitability=round(season, 1),
        over_budget=over,
        base_cost_inr=dest.base_cost_inr,
        why=why,
    )


def rank_destinations(
    dests: list[DestinationInput],
    intent: Intent,
    month: int,
    budget: int | None = None,
    limit: int = 5,
    include_over_budget: bool = False,
) -> list[ScoredDestination]:
    """The Discover engine: intent + month + budget in, ranked destinations out."""
    scored = [score_destination(d, intent, month, budget) for d in dests]
    if not include_over_budget:
        scored = [s for s in scored if not s.over_budget]
    scored.sort(key=lambda s: s.composite, reverse=True)
    return scored[:limit]
