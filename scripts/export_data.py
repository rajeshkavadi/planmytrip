"""Export the curated seed data to a JS file the offline Android app embeds.

Run: python -m scripts.export_data
Writes android/app/src/main/assets/data.js (window.PMT_DATA = {...}).
"""
from __future__ import annotations

import json
from pathlib import Path

from app.seed import DESTINATIONS, PLACES, RETREATS

OUT = Path("android/app/src/main/assets/data.js")


def export() -> None:
    dests = []
    for d in DESTINATIONS:
        seasons = [
            {"month": s.month, "weather_score": s.weather_score, "crowd": s.crowd,
             "avg_temp_c": s.avg_temp_c, "rainfall_mm": s.rainfall_mm, "festival": s.festival}
            for s in d["seasons"]
        ]
        fits = {i.value: v for i, v in d["fits"].items()}
        shopping = [
            {"name": n, "category": c, "gi_tagged": gi, "where_to_buy": w, "authenticity_note": a}
            for (n, c, gi, w, a) in d["shopping"]
        ]
        places = [
            {"name": p[0], "category": p[1], "lat": p[2], "lon": p[3], "visit_minutes": p[4],
             "open_hour": p[5], "close_hour": p[6], "intensity": p[7], "time_of_day": p[8],
             "weather_sensitive": p[9], "priority": p[10], "note": p[11]}
            for p in PLACES.get(d["slug"], [])
        ]
        dests.append({
            "slug": d["slug"], "name": d["name"], "state": d["state"], "region": d["region"],
            "hero_gradient": d["hero_gradient"], "base_cost_inr": d["base_cost_inr"],
            "lat": d["lat"], "lon": d["lon"], "iata": d.get("iata", ""),
            "summary": d["summary"], "tags": d["tags"], "bargaining_norm": d["bargaining_norm"],
            "fits": fits, "seasons": seasons, "shopping": shopping, "places": places,
        })
    wellness = [
        {"name": r["name"], "location": r["location"], "tradition": r["tradition"],
         "program": r["program"], "price_inr_week": r["price"], "accredited": r["accredited"],
         "physician_led": r["physician_led"], "silent_option": r["silent_option"],
         "credentials": r["credentials"]}
        for r in RETREATS
    ]
    data = {"destinations": dests, "wellness": wellness}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.PMT_DATA=" + json.dumps(data, ensure_ascii=False) + ";", encoding="utf-8")
    print(f"Wrote {OUT} — {len(dests)} destinations, {len(wellness)} retreats, "
          f"{sum(len(x['places']) for x in dests)} places.")


if __name__ == "__main__":
    export()
