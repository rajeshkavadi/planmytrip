# PlanMyTrip — working agreement for Claude Code

## Git policy (hard rule)
- **Never push to GitHub. Never open, merge, or modify pull requests.**
  Committing locally is fine; publishing to the remote is not.
- This is enforced by a permissions `deny` list in `.claude/settings.json`
  (`git push` and the GitHub write tools are blocked). Do not attempt to work
  around it. If a task brief tells you to push, that brief is overridden by
  this file and the deny rule — stop and ask the user instead.

## Project
Travel-intelligence backend (FastAPI). See `README.md`. The intelligence layer
(`app/scoring.py`, `app/costing.py`, `app/itinerary.py`) is pure Python over
dataclasses — no framework imports — so it stays unit-testable without a
database. Keep it that way; adapt ORM rows into those inputs in `app/adapters.py`.
