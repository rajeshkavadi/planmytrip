# PlanMyTrip — working agreement for Claude Code

## Git policy
- **Pushing to GitHub is allowed** (owner enabled it on 2026-08-19 to use CI
  for building the Windows `.exe`). Push feature-branch work as needed.
- The earlier `git push` deny rule in `.claude/settings.json` has been lifted.
- Pull requests: only open/merge one when the owner explicitly asks.

## Project
Travel-intelligence backend (FastAPI). See `README.md`. The intelligence layer
(`app/scoring.py`, `app/costing.py`, `app/itinerary.py`) is pure Python over
dataclasses — no framework imports — so it stays unit-testable without a
database. Keep it that way; adapt ORM rows into those inputs in `app/adapters.py`.
