"""Desktop launcher — the entrypoint bundled into PlanMyTrip.exe.

Boots the API with the bundled UI on a local port, seeds a SQLite database in
the user's home folder on first run, and opens the browser. Double-clicking the
built .exe gives a self-contained local app: no Python, no Postgres, no Docker.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = int(os.environ.get("PLANMYTRIP_PORT", "8000"))


def _data_dir() -> Path:
    """A writable per-user folder for the database (survives app restarts)."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home()
    d = root / "PlanMyTrip"
    d.mkdir(parents=True, exist_ok=True)
    return d


# Point the app at a stable, writable DB *before* importing anything that reads
# settings — unless the user has overridden DATABASE_URL themselves.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(_data_dir() / 'planmytrip.db').as_posix()}")


def _ensure_seed() -> None:
    from app.database import SessionLocal, init_db
    from app.models import Destination

    init_db()
    db = SessionLocal()
    try:
        if db.query(Destination).count() == 0:
            from app.seed import seed
            seed()
    finally:
        db.close()


def main() -> None:
    print("PlanMyTrip — preparing local database…")
    _ensure_seed()

    def _open_browser() -> None:
        time.sleep(1.5)
        webbrowser.open(f"http://{HOST}:{PORT}/")

    threading.Thread(target=_open_browser, daemon=True).start()

    import uvicorn
    from app.main import app

    print(f"PlanMyTrip is running at http://{HOST}:{PORT}/  (close this window to stop)")
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
    except KeyboardInterrupt:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
