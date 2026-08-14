# PlanMyTrip — travel intelligence, not a booking desk

MakeMyTrip and EaseMyTrip assume you already know where you're going and just
need to transact. **PlanMyTrip starts from how you want to *feel*** and answers
the harder questions the booking apps skip: *where, when, and why* — then books
last. India-first.

This repo is the backend scaffold. A clickable UI prototype of the same product
lives as a separate design artifact.

## The four things the incumbents don't give you

| Differentiator | Where it lives in the code |
| --- | --- |
| **Purpose-based discovery** — pick an intent, get destinations *ranked* to it | `app/scoring.py` (`rank_destinations`), `GET /discover` |
| **Season intelligence** — weather + crowds + festivals + the *shoulder-season sweet spot*, not just price | `app/scoring.py` (`season_report`, `sweet_spot_months`), `GET /destinations/{slug}/season` |
| **Credentialed wellness** — retreats judged on accreditation & tradition, not review stars | `app/models.py` (`WellnessRetreat`), `GET /wellness` |
| **All-in trip cost** — surfaces the hidden lines (transfers, entries, tips, eSIM) | `app/costing.py`, `GET /trips/estimate-cost` |

## Architecture

```
app/
  domain.py     # framework-free vocabulary: Intent, Crowd, penalties
  scoring.py    # THE intelligence layer — pure functions, no DB/web (unit-tested)
  costing.py    # all-in cost engine — pure functions
  models.py     # SQLAlchemy 2.0 ORM; PostGIS geography column on destinations
  adapters.py   # ORM rows -> pure scoring inputs
  schemas.py    # Pydantic v2 response models
  seed.py       # curated India-first data (the moat)
  routers/      # discover, destinations, wellness, trips
  main.py       # FastAPI app
tests/
  test_scoring.py  # runs with NO database or server
```

**Design choice worth calling out:** all ranking and season logic is *pure
Python over small dataclasses* (`scoring.py`, `costing.py`) — no SQLAlchemy, no
FastAPI. That's why `tests/` runs in milliseconds with no database, and why the
"intelligence" is easy to reason about. Routers adapt ORM rows into those inputs
via `adapters.py`.

The curated seed data is deliberately hand-written, not scraped. Authentic
wellness credentials, GI-tagged crafts, regional bargaining norms and honest
month-by-month season profiles are the defensible part — scraped listings are
what the incumbents already have.

## Run it

Everything is wired for **Postgres + PostGIS** (the geography column powers
"retreats within 50km", clustering, routing later).

```bash
docker compose up --build
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
```

The `api` container seeds the database on start, then serves with reload.

### Run locally without Docker

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # point DATABASE_URL at your PostGIS
python -m app.seed                        # create tables + PostGIS, load seed data
uvicorn app.main:app --reload
```

### Tests (no database needed)

```bash
pip install -r requirements.txt
pytest -q          # exercises the scoring + costing logic in isolation
```

## Try the API

```bash
# Purpose-based discovery: "I want to recharge, mid-October, ~₹45k"
curl "http://localhost:8000/discover?intent=recharge&month=10&budget_inr=45000"

# Season intelligence for one place
curl "http://localhost:8000/destinations/kerala-hills/season?month=10"

# Credentialed wellness, Ayurveda only, NABH-accredited
curl "http://localhost:8000/wellness?tradition=Ayurveda&accredited=true"

# Honest all-in cost for a 5-night trip
curl "http://localhost:8000/trips/estimate-cost?nights=5&flight_inr=9400&stay_per_night_inr=3720"
```

## How the discovery score works

For a given `(intent, month, budget)` each destination gets a composite 0–100:

```
composite = 0.55 * intent_fit          # 0–100, how well it serves the intent
          + 0.35 * season_suitability  # weather this month minus a crowd penalty
          + budget_adjustment          # bonus if comfortably in budget, penalty if over
```

`season_suitability = weather_score − crowd_penalty`, so a beautiful month that's
also jammed scores below a slightly-less-perfect but quiet one — which is exactly
how the **sweet-spot** detector finds shoulder seasons the price-first apps miss.

## Status & next steps

- ✅ Domain model, scoring/costing logic, seed data, REST API — built and the
  pure logic is unit-tested (`pytest`, 8 tests).
- ⚠️ The Postgres/PostGIS path (seed + live queries) is written and wired but was
  **not run in the build sandbox** (no database server available there). Run
  `docker compose up` locally to exercise it.
- ⏭ Itinerary builder endpoint, auth/users, saved trips, live weather/events
  feeds to refresh season data, and a thin booking-aggregation layer.
