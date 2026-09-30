"""Run the local prototype API against the isolated kltn_dev demo database."""
from __future__ import annotations

import os

import uvicorn
from sqlalchemy.engine import make_url

from backend.api.dependencies import load_local_env


def main() -> None:
    load_local_env()
    configured_url = os.getenv("DATABASE_URL")
    if not configured_url:
        raise SystemExit("DATABASE_URL is missing; configure the local .env first")

    # Keep the main kltn_ai database as configured in .env; this process alone
    # connects to kltn_dev for the synthetic prototype demonstration.
    os.environ["DATABASE_URL"] = make_url(configured_url).set(
        database="kltn_dev"
    ).render_as_string(hide_password=False)
    if not os.getenv("QDRANT_URL") and not os.getenv("QDRANT_LOCAL_PATH"):
        os.environ["QDRANT_LOCAL_PATH"] = "tmp/qdrant-prototype"
    os.environ["KLTN_ENV"] = "development"
    os.environ["KLTN_DEV_AUTH"] = "true"
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
