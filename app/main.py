from __future__ import annotations

from fastapi import FastAPI

from . import __version__
from .routers import destinations, discover, trips, wellness

app = FastAPI(
    title="PlanMyTrip API",
    version=__version__,
    summary="Travel intelligence — purpose-based discovery, season intelligence, "
            "credentialed wellness, honest all-in cost. India-first.",
)

app.include_router(discover.router)
app.include_router(destinations.router)
app.include_router(wellness.router)
app.include_router(trips.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}
