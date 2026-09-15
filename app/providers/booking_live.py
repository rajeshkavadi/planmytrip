"""Live flight & hotel data via RapidAPI's Sky-Scrapper API.

One RapidAPI key (free "Basic" plan) covers both flights and hotels. Set
RAPIDAPI_KEY and this provider returns real data mapped to the same
FlightOption / HotelOption shapes the sample stub uses. Any failure raises
ProviderError so the caller falls back to sample options — the screen never
breaks.

Sky-Scrapper needs a two-step lookup: resolve a place to its skyId/entityId,
then search. IDs are cached in-process to keep within the free tier's limits.
Uses stdlib urllib (honours HTTPS_PROXY) — no extra runtime dependency.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from ..config import settings
from ..inventory import FlightOption, HotelOption
from .weather import ProviderError  # shared error type


class SkyScrapperClient:
    def __init__(self, timeout: float = 25.0):
        self.host = settings.rapidapi_host
        self.base = f"https://{self.host}"
        self.timeout = timeout
        self._airports: dict[str, tuple[str, str]] = {}   # IATA -> (skyId, entityId)
        self._hotel_cities: dict[str, str] = {}            # query -> entityId

    # -- transport --------------------------------------------------------- #
    def _get(self, path: str, params: dict) -> dict:
        url = f"{self.base}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": self.host,
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise ProviderError(f"RapidAPI {e.code}: {e.read().decode(errors='ignore')[:160]}") from e
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise ProviderError(f"RapidAPI request failed: {e}") from e

    # -- lookups ----------------------------------------------------------- #
    def _airport_ids(self, iata: str) -> tuple[str, str]:
        iata = iata.upper()
        if iata in self._airports:
            return self._airports[iata]
        data = self._get("/api/v1/flights/searchAirport", {"query": iata, "locale": "en-US"})
        rows = data.get("data", []) or []
        if not rows:
            raise ProviderError(f"No airport match for {iata}")
        top = rows[0]
        ids = (str(top.get("skyId") or iata), str(top.get("entityId") or ""))
        self._airports[iata] = ids
        return ids

    def _hotel_entity(self, query: str) -> str:
        if query in self._hotel_cities:
            return self._hotel_cities[query]
        data = self._get("/api/v1/hotels/searchDestinationOrHotel", {"query": query})
        rows = data.get("data", []) or []
        city = next((r for r in rows if r.get("entityType") in ("city", "region")), rows[0] if rows else None)
        if not city:
            raise ProviderError(f"No hotel destination match for {query}")
        eid = str(city.get("entityId") or "")
        self._hotel_cities[query] = eid
        return eid

    # -- flights ----------------------------------------------------------- #
    def raw_flights(self, origin_iata: str, dest_iata: str, date: str,
                    adults: int = 1, max_results: int = 6) -> dict:
        """The raw searchFlights response (used by flight_offers and /diag)."""
        o_sky, o_ent = self._airport_ids(origin_iata)
        d_sky, d_ent = self._airport_ids(dest_iata)
        return self._get("/api/v2/flights/searchFlights", {
            "originSkyId": o_sky, "destinationSkyId": d_sky,
            "originEntityId": o_ent, "destinationEntityId": d_ent,
            "date": date, "adults": max(1, adults), "currency": "INR",
            "sortBy": "best", "limit": max_results,
        })

    def flight_offers(self, origin_iata: str, dest_iata: str, date: str,
                      adults: int = 1, max_results: int = 6) -> list[FlightOption]:
        data = self.raw_flights(origin_iata, dest_iata, date, adults, max_results)
        itineraries = (data.get("data", {}) or {}).get("itineraries", []) or []
        out: list[FlightOption] = []
        for i, it in enumerate(itineraries[:max_results]):
            legs = it.get("legs", []) or []
            if not legs:
                continue
            leg = legs[0]
            carriers = (leg.get("carriers", {}) or {}).get("marketing", []) or []
            airline = carriers[0].get("name") if carriers else "Airline"
            code = carriers[0].get("alternateId") or carriers[0].get("displayCode") or "" if carriers else ""
            price_raw = (it.get("price", {}) or {}).get("raw")
            out.append(FlightOption(
                id=str(it.get("id", f"ss-{i}")),
                airline=str(airline),
                flight_no=str(code or "").strip(),
                depart=str(leg.get("departure", ""))[11:16],
                arrive=str(leg.get("arrival", ""))[11:16],
                duration_min=int(leg.get("durationInMinutes") or 0),
                stops=int(leg.get("stopCount") or 0),
                price_inr=round(float(price_raw)) if price_raw else 0,
            ))
        if not out:
            raise ProviderError("Sky-Scrapper returned no flight offers")
        return out

    # -- hotels ------------------------------------------------------------ #
    def raw_hotels(self, dest_query: str, checkin: str, checkout: str,
                   adults: int, limit: int = 5) -> dict:
        """The raw searchHotels response (used by hotel_offers and /diag)."""
        entity = self._hotel_entity(dest_query)
        return self._get("/api/v1/hotels/searchHotels", {
            "entityId": entity, "checkinDate": checkin, "checkoutDate": checkout,
            "adults": max(1, adults), "currency": "INR", "sortOrder": "5", "limit": limit,
        })

    def hotel_offers(self, dest_query: str, checkin: str, checkout: str,
                     adults: int, nights: int, base_cost_inr: int,
                     limit: int = 5) -> list[HotelOption]:
        data = self.raw_hotels(dest_query, checkin, checkout, adults, limit)
        hotels = (data.get("data", {}) or {}).get("hotels", []) or []
        est_night = max(1500, round(base_cost_inr * 0.09))
        nights = max(1, nights)
        out: list[HotelOption] = []
        for i, h in enumerate(hotels[:limit]):
            # Price may be a raw total for the stay or a formatted string; be defensive.
            per_night = est_night
            raw = h.get("rawPrice") or (h.get("price", {}) or {}).get("rawPrice") if isinstance(h.get("price"), dict) else h.get("rawPrice")
            try:
                if raw:
                    per_night = max(800, round(float(raw) / nights))
            except (TypeError, ValueError):
                pass
            rating = h.get("rating") or (h.get("reviews", {}) or {}).get("scoreValue") or (4.0 + (i % 3) * 0.3)
            try:
                rating = round(float(rating), 1)
                if rating > 5:  # some feeds use a 0-10 scale
                    rating = round(rating / 2, 1)
            except (TypeError, ValueError):
                rating = 4.0
            out.append(HotelOption(
                id=str(h.get("hotelId") or h.get("id") or f"ss-h-{i}"),
                name=str(h.get("name") or "Hotel"),
                area=str(h.get("distance") or h.get("cityName") or dest_query),
                style="Sky-Scrapper listing", rating=rating,
                price_per_night_inr=per_night,
            ))
        if not out:
            raise ProviderError("Sky-Scrapper returned no hotels")
        return out


_client: SkyScrapperClient | None = None


def get_client() -> SkyScrapperClient:
    global _client
    if _client is None:
        _client = SkyScrapperClient()
    return _client
