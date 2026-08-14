"""Refresh season intelligence from a live climate feed.

Run: ``python -m app.refresh``

For each destination it fetches monthly climate normals and updates each
month's temperature, rainfall and derived ``weather_score`` (via
``comfort_score``). Curated crowd levels and festivals are preserved. If the
feed is unreachable, the destination is skipped and its curated data is left
intact — the app never ends up worse than its seed.
"""
from __future__ import annotations

import sys

from .database import SessionLocal
from .models import Destination, SeasonMonth
from .providers.weather import OpenMeteoProvider, ProviderError, SeasonProvider
from .scoring import comfort_score


def refresh(provider: SeasonProvider | None = None) -> dict:
    provider = provider or OpenMeteoProvider()
    db = SessionLocal()
    updated, skipped = [], []
    try:
        for dest in db.query(Destination).all():
            try:
                climate = provider.monthly_climate(dest.latitude, dest.longitude)
            except ProviderError as e:
                skipped.append((dest.slug, str(e)))
                continue
            if not climate:
                skipped.append((dest.slug, "no data"))
                continue

            months = {s.month: s for s in db.query(SeasonMonth)
                      .filter(SeasonMonth.destination_id == dest.id).all()}
            changed = 0
            for m, c in climate.items():
                row = months.get(m)
                if row is None:
                    continue
                row.avg_temp_c = round(c.avg_temp_c)
                row.rainfall_mm = round(c.rainfall_mm)
                row.weather_score = comfort_score(c.avg_temp_c, c.rainfall_mm)
                changed += 1
            db.commit()
            updated.append((dest.slug, changed))
    finally:
        db.close()

    for slug, n in updated:
        print(f"  ✓ {slug}: refreshed {n} months")
    for slug, why in skipped:
        print(f"  – {slug}: kept curated data ({why})")
    return {"updated": updated, "skipped": skipped}


if __name__ == "__main__":
    result = refresh()
    if not result["updated"]:
        print("\nNo destinations refreshed (feed unreachable?). Curated data intact.",
              file=sys.stderr)
