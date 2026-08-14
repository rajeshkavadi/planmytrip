from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import __version__
from .routers import destinations, discover, trips, users, wellness

app = FastAPI(
    title="PlanMyTrip API",
    version=__version__,
    summary="Travel intelligence — purpose-based discovery, season intelligence, "
            "credentialed wellness, honest all-in cost. India-first.",
)

# Open CORS for local testing: the mobile UI can call the API whether it's
# served from here (same origin) or opened straight from a file. Tighten
# `allow_origins` before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(discover.router)
app.include_router(destinations.router)
app.include_router(wellness.router)
app.include_router(users.router)
app.include_router(trips.router)

WEB_DIR = Path(__file__).parent / "web"


@app.get("/", include_in_schema=False)
def home():
    """Serve the wired mobile UI."""
    index = WEB_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "PlanMyTrip API. UI not bundled; see /docs."}


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}
