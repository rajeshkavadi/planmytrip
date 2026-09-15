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


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE lines into the environment (without overriding
    anything already set). Lets .exe users drop API keys in a file instead of
    setting Windows environment variables. Blank lines and #comments ignored.
    """
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass
    except OSError:
        pass


# Load optional credentials (e.g. RAPIDAPI_KEY for live flights/hotels) from a
# file next to the DB, then point the app at a stable, writable DB — both
# before importing settings.
_load_env_file(_data_dir() / "planmytrip.env")
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
