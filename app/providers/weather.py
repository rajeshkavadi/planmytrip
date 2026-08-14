"""Live climate feed — turns static season rows into fresh ones.

`OpenMeteoProvider` pulls multi-year daily history from Open-Meteo's free,
key-less archive API and aggregates it to monthly climate normals (mean
temperature, mean monthly rainfall). The refresh job feeds those into
`comfort_score` so the weather half of season intelligence tracks reality
while the curated crowd/festival knowledge stays put.

Everything degrades gracefully: any network/parse failure raises
`ProviderError`, and the caller keeps the existing curated data.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Protocol

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class MonthClimate:
    month: int
    avg_temp_c: float
    rainfall_mm: float  # average total for the month


class SeasonProvider(Protocol):
    def monthly_climate(self, lat: float, lon: float) -> dict[int, MonthClimate]:
        ...


class StaticProvider:
    """No-op provider — used as a fallback so refresh is always safe to run."""

    def monthly_climate(self, lat: float, lon: float) -> dict[int, MonthClimate]:
        return {}


class OpenMeteoProvider:
    """Monthly climate normals from Open-Meteo's archive (ERA5)."""

    def __init__(self, years_back: int = 5, timeout: float = 20.0):
        self.years_back = years_back
        self.timeout = timeout

    def _fetch(self, lat: float, lon: float) -> dict:
        end = date.today().replace(day=1)
        start = end.replace(year=end.year - self.years_back)
        params = (
            f"?latitude={lat:.4f}&longitude={lon:.4f}"
            f"&start_date={start.isoformat()}&end_date={end.isoformat()}"
            "&daily=temperature_2m_mean,precipitation_sum&timezone=auto"
        )
        url = ARCHIVE_URL + params
        try:
            # Honors HTTPS_PROXY / http(s)_proxy from the environment.
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise ProviderError(f"Open-Meteo fetch failed: {e}") from e

    def monthly_climate(self, lat: float, lon: float) -> dict[int, MonthClimate]:
        data = self._fetch(lat, lon)
        daily = data.get("daily", {})
        times = daily.get("time", [])
        temps = daily.get("temperature_2m_mean", [])
        rain = daily.get("precipitation_sum", [])
        if not times:
            raise ProviderError("Open-Meteo returned no daily data")

        # Accumulate per calendar month across all years.
        temp_sum: dict[int, float] = {}
        temp_n: dict[int, int] = {}
        rain_by_ym: dict[tuple[int, int], float] = {}
        for t, tp, rn in zip(times, temps, rain):
            year, month = int(t[0:4]), int(t[5:7])
            if tp is not None:
                temp_sum[month] = temp_sum.get(month, 0.0) + tp
                temp_n[month] = temp_n.get(month, 0) + 1
            if rn is not None:
                rain_by_ym[(year, month)] = rain_by_ym.get((year, month), 0.0) + rn

        # Average monthly rainfall = mean of each year's monthly total.
        rain_tot: dict[int, float] = {}
        rain_yrs: dict[int, int] = {}
        for (_, month), total in rain_by_ym.items():
            rain_tot[month] = rain_tot.get(month, 0.0) + total
            rain_yrs[month] = rain_yrs.get(month, 0) + 1

        out: dict[int, MonthClimate] = {}
        for m in range(1, 13):
            if temp_n.get(m):
                out[m] = MonthClimate(
                    month=m,
                    avg_temp_c=round(temp_sum[m] / temp_n[m], 1),
                    rainfall_mm=round(rain_tot.get(m, 0.0) / max(1, rain_yrs.get(m, 1)), 1),
                )
        return out
