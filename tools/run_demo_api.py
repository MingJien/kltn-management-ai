"""Run the local prototype API against the verified kltn_management database."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

import uvicorn
from backend.api.dependencies import database_url, load_local_env
from tools.validate_official_database import main as validate_official_database


def main() -> None:
    load_local_env()
    os.environ["DATABASE_URL"] = database_url()
    validate_official_database()
    if not os.getenv("QDRANT_URL") and not os.getenv("QDRANT_LOCAL_PATH"):
        os.environ["QDRANT_LOCAL_PATH"] = "tmp/qdrant-prototype"
    os.environ["KLTN_ENV"] = "development"
    # Browser demo uses scoped sessions; UUID headers remain opt-in for automated tests.
    os.environ["KLTN_DEV_AUTH"] = "false"
    if not os.getenv("AUTH_SESSION_SECRET"):
        secret_file = Path(__file__).resolve().parents[1] / "local" / "demo-session-secret.txt"
        secret_file.parent.mkdir(exist_ok=True)
        if not secret_file.exists():
            secret_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        os.environ["AUTH_SESSION_SECRET"] = secret_file.read_text(encoding="utf-8").strip()
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
