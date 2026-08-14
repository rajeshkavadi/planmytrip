# PlanMyTrip — travel intelligence, not a booking desk

MakeMyTrip and EaseMyTrip assume you already know where you're going and just
need to transact. **PlanMyTrip starts from how you want to *feel*** and answers
the harder questions the booking apps skip: *where, when, and why* — then books
last. India-first.

This repo is the backend **and** a mobile UI wired to it. Open `/` on the running
server for the live app (`app/web/index.html`); `design/prototype.html` is the
original standalone mock (demo data, no server needed).

> **Runs with zero setup.** The default database is a local SQLite file, so
> `python -m app.seed && uvicorn app.main:app` just works — no Postgres, no
> Docker. Then open <http://localhost:8000/>. Windows users can double-click
> `install-windows.bat` to run it, or `build-exe.bat` to produce a standalone
> `PlanMyTrip.exe`. Point `DATABASE_URL` at Postgres to switch on PostGIS.

## What the incumbents don't give you

| Differentiator | Where it lives |
| --- | --- |
| **Purpose-based discovery** — pick an intent, get destinations *ranked* to it | `scoring.py` → `GET /discover` |
| **Season intelligence** — weather + crowds + festivals + shoulder-season *sweet spot*, kept fresh from a live climate feed | `scoring.py`, `providers/weather.py` → `GET /destinations/{slug}/season` |
| **Itinerary builder** — day-by-day plan that respects opening hours, travel time & energy pacing | `itinerary.py` → `GET /destinations/{slug}/itinerary` |
| **Credentialed wellness** — retreats judged on accreditation & tradition, not stars | `models.py` → `GET /wellness` |
| **All-in trip cost** — surfaces the hidden lines (transfers, entries, tips, eSIM) | `costing.py` → `GET /trips/estimate-cost` |
| **Living trip doc** — one offline-ready payload that *re-plans when a flight slips* | `trip_doc.py`, `itinerary.py` → `POST /trips`, `POST /trips/{id}/replan` |

## Architecture

```
app/
  domain.py       # framework-free vocabulary: Intent, Crowd, Intensity, TimeOfDay
  scoring.py      # ranking + season intelligence + comfort model (pure, tested)
  costing.py      # all-in cost engine (pure, tested)
  itinerary.py    # day-by-day builder + flight re-planning (pure, tested)
  geo.py          # haversine + travel-time (pure)
  models.py       # SQLAlchemy 2.0 ORM; PostGIS geography added at DB level on Postgres
  adapters.py     # ORM rows -> pure inputs
  auth.py         # X-API-Key dependency
  trip_doc.py     # assembles the living trip document
  providers/
    weather.py    # live climate feed (Open-Meteo) with graceful fallback
  refresh.py      # CLI: refresh season data from the live feed
  schemas.py      # Pydantic v2 models
  seed.py         # curated India-first data (the moat)
  routers/        # discover, destinations, wellness, users, trips
  main.py         # FastAPI app
tests/            # runs with NO database or server (15 tests)
```

**Design choice worth calling out:** all the intelligence — ranking, season
logic, itinerary building, cost, flight re-planning — is *pure Python over small
dataclasses*, no SQLAlchemy or FastAPI imports. That's why `tests/` runs in
milliseconds with no database, and why the logic is easy to reason about.
Routers adapt ORM rows into those inputs via `adapters.py`.

The curated seed data is deliberately hand-written, not scraped — authentic
wellness credentials, GI-tagged crafts, regional bargaining norms and honest
season profiles are the defensible part. The live climate feed then keeps the
factual weather half fresh without touching that curation.

## Run it

### Quick start (SQLite, no external services)

```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed                               # creates planmytrip.db + seed data
python -m app.refresh                            # optional: pull live climate (safe offline)
uvicorn app.main:app --reload
# Docs: http://localhost:8000/docs
```

### Windows

- **Run it:** double-click **`install-windows.bat`** (or `install-windows.ps1`).
  It checks for Python, creates the venv, installs, seeds SQLite, refreshes
  weather, and opens the app.
- **Build a standalone `.exe`:** double-click **`build-exe.bat`**. It runs
  PyInstaller (per `PlanMyTrip.spec`, entrypoint `desktop.py`) and produces
  `dist\PlanMyTrip.exe` — a single self-contained executable that bundles the
  UI, seeds a SQLite DB under `%LOCALAPPDATA%\PlanMyTrip`, and opens the browser.
  A real Windows `.exe` must be built on Windows; PyInstaller isn't a
  cross-compiler.

Only prerequisite either way: [Python 3.11+](https://www.python.org/downloads/)
with "Add to PATH" ticked.

### Postgres + PostGIS (production shape)

```bash
docker compose up --build     # api seeds on start; PostGIS geography enabled
```

Or point `DATABASE_URL` at your own Postgres in `.env` (see `.env.example`).
`init_db()` enables the extension and adds a `geom geography(Point,4326)` column
mirrored from lat/lon for spatial queries.

### Tests (no database needed)

```bash
pip install -r requirements.txt
pytest -q          # 15 tests across scoring, costing and itinerary logic
```

## Try the API

```bash
# Purpose-based discovery: "I want to recharge, mid-October, ~₹45k"
curl "http://localhost:8000/discover?intent=recharge&month=10&budget_inr=45000"

# Season intelligence (sweet spot + monsoon caveats)
curl "http://localhost:8000/destinations/kerala-hills/season?month=7"

# Paced day-by-day itinerary
curl "http://localhost:8000/destinations/jaipur/itinerary?days=2"

# Honest all-in cost
curl "http://localhost:8000/trips/estimate-cost?nights=5&flight_inr=9400&stay_per_night_inr=3720"

# Users + saved trips + living doc + re-plan on a flight change
KEY=$(curl -s -XPOST localhost:8000/users -H 'content-type: application/json' \
      -d '{"email":"me@example.com"}' | python -c "import sys,json;print(json.load(sys.stdin)['api_key'])")
curl -s -XPOST localhost:8000/trips -H "X-API-Key: $KEY" -H 'content-type: application/json' \
  -d '{"destination_slug":"jaipur","month":11,"nights":2,"party_size":2,"flight_arrival":"2026-11-10T09:00:00"}'
# ...then re-plan when the flight slips:
curl -s -XPOST localhost:8000/trips/1/replan -H "X-API-Key: $KEY" -H 'content-type: application/json' \
  -d '{"flight_arrival":"2026-11-10T15:30:00"}'
```

## How the pieces work

**Discovery score** — for `(intent, month, budget)`, each destination gets a
composite 0–100:

```
composite = 0.55 * intent_fit          # how well it serves the intent
          + 0.35 * season_suitability  # weather this month minus a crowd penalty
          + budget_adjustment          # bonus if in budget, penalty if over
```

`season_suitability = weather_score − crowd_penalty`, so a beautiful-but-jammed
month scores below a slightly-less-perfect quiet one — which is how the
**sweet-spot** detector finds shoulder seasons the price-first apps miss.

**Itinerary builder** — greedily fills days up to a daily *energy budget*
(intensity points), orders stops by time-of-day, then lays them on the clock
with real travel time between them, waits for opening hours, breaks for lunch,
pushes sun-exposed stops past the midday heat, and rests after anything
strenuous. Anything that won't fit comes back as `unscheduled`.

**Living trip doc & re-plan** — `POST /trips` stores a plan and returns one
self-contained document (destination + season + cost + itinerary + shopping)
the client caches offline. `POST /trips/{id}/replan` takes a new flight arrival
and rebuilds Day 1 around it, dropping stops that already sailed and telling you
exactly what changed.

**Live feed** — `python -m app.refresh` pulls multi-year monthly climate normals
from Open-Meteo (free, no key) and recomputes each month's temperature, rainfall
and `weather_score`. Crowd levels and festivals stay curated. If the feed is
unreachable, curated data is left untouched.

## Status & next steps

- ✅ Discovery, season intelligence, itinerary builder, credentialed wellness,
  all-in cost, users + saved trips + living trip doc with flight re-planning,
  and a live climate feed — **built and verified end-to-end on SQLite** (seed +
  every endpoint exercised). 15 unit tests pass.
- ✅ Runs with zero setup (SQLite) and ships a Windows installer.
- ⚠️ The PostGIS path (`docker compose up`) is wired but was not run in the build
  sandbox (no Docker there). The app itself is verified on SQLite.
- ⏭ Real flight/hotel fare feeds, an events/festivals API to complement climate,
  OAuth/JWT to replace the API-key stub, and a thin booking-aggregation layer.

## Note on git
This repo carries a hard **no-push** policy — see `CLAUDE.md` and the deny rule
in `.claude/settings.json`. Commits stay local unless the owner pushes.
