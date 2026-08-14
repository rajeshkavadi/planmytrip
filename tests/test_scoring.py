"""Unit tests for the intelligence layer — no DB, no server required."""
from __future__ import annotations

from app.costing import estimate_trip_cost
from app.domain import Crowd, Intent
from app.scoring import (
    DestinationInput,
    MonthSeason,
    best_windows,
    budget_adjustment,
    rank_destinations,
    season_report,
    season_suitability,
    sweet_spot_months,
)


def _season(month, weather, crowd, rain=0, festival=None):
    return MonthSeason(month=month, weather_score=weather, crowd=crowd,
                       rainfall_mm=rain, festival=festival)


def _winter_hill():
    """High Oct–Feb, monsoon-dead Jun–Aug."""
    rows = []
    for m in range(1, 13):
        if m == 12:
            rows.append(_season(m, 95, Crowd.PEAK))  # December rush
        elif m in (10, 11, 1, 2):
            rows.append(_season(m, 88, Crowd.MODERATE))
        elif m in (6, 7, 8):
            rows.append(_season(m, 30, Crowd.VERY_LOW, rain=600))
        else:
            rows.append(_season(m, 60, Crowd.LOW))
    return rows


def test_crowd_lowers_suitability():
    calm = _season(1, 80, Crowd.VERY_LOW)
    packed = _season(1, 80, Crowd.PEAK)
    assert season_suitability(calm) > season_suitability(packed)
    assert season_suitability(packed) == 80 - 22  # PEAK penalty


def test_best_windows_wrap_year_boundary():
    windows = best_windows(_winter_hill(), threshold=70)
    # Oct–Feb should read as one wrapped window, not two.
    assert windows == ["Oct–Feb"]


def test_sweet_spot_is_quieter_than_peak():
    # Two near-best months: one MODERATE crowd, one PEAK. Only the calm one qualifies.
    rows = [_season(m, 40, Crowd.LOW) for m in range(1, 11)]
    rows.append(_season(11, 90, Crowd.MODERATE))  # green + quiet
    rows.append(_season(12, 92, Crowd.PEAK))       # slightly better but jammed
    sweet = sweet_spot_months(rows)
    assert 11 in sweet
    assert 12 not in sweet


def test_budget_penalises_overshoot_and_flags():
    delta, over = budget_adjustment(base_cost=60000, budget=40000)
    assert over is True
    assert delta < 0
    delta2, over2 = budget_adjustment(base_cost=25000, budget=50000)
    assert over2 is False
    assert delta2 > 0


def test_rank_puts_intent_fit_first():
    spiritual = DestinationInput(
        slug="temple-town", name="Temple Town", base_cost_inr=20000,
        intent_fits={Intent.SPIRITUAL: 95}, seasons=[_season(1, 80, Crowd.LOW)])
    beach = DestinationInput(
        slug="party-beach", name="Party Beach", base_cost_inr=20000,
        intent_fits={Intent.SPIRITUAL: 20}, seasons=[_season(1, 90, Crowd.LOW)])
    ranked = rank_destinations([beach, spiritual], Intent.SPIRITUAL, month=1, budget=50000)
    assert ranked[0].slug == "temple-town"


def test_rank_excludes_over_budget_by_default():
    cheap = DestinationInput("cheap", "Cheap", 20000, {Intent.RECHARGE: 80},
                             [_season(1, 80, Crowd.LOW)])
    lux = DestinationInput("lux", "Lux", 200000, {Intent.RECHARGE: 99},
                           [_season(1, 90, Crowd.LOW)])
    ranked = rank_destinations([cheap, lux], Intent.RECHARGE, month=1, budget=50000)
    assert [r.slug for r in ranked] == ["cheap"]
    ranked_incl = rank_destinations([cheap, lux], Intent.RECHARGE, month=1,
                                    budget=50000, include_over_budget=True)
    assert {r.slug for r in ranked_incl} == {"cheap", "lux"}


def test_season_report_flags_monsoon_and_sweet_spot():
    rep = season_report(
        DestinationInput("x", "X", 30000, {}, _winter_hill()), month=7)
    assert rep["verdict"] == "avoid"
    assert any("rain" in c.lower() for c in rep["caveats"])
    # November is a shoulder sweet spot on this profile.
    rep_nov = season_report(
        DestinationInput("x", "X", 30000, {}, _winter_hill()), month=11)
    assert "Nov" in rep_nov["sweet_spot"]


def test_all_in_cost_surfaces_hidden_lines():
    est = estimate_trip_cost(nights=5, flight_inr=9400, stay_per_night_inr=3720)
    assert est.hidden_total_inr > 0
    assert est.total_inr == sum(l.amount_inr for l in est.lines)
    # The hidden lines are exactly the ones a booking app wouldn't quote.
    hidden_labels = {l.label for l in est.lines if l.hidden}
    assert "Local transport & transfers" in hidden_labels
    assert "Flights (return)" not in hidden_labels
