"""Compatibility entry point for local environment loading and DB validation.

The active structural checks live in ``tools.validate_official_database``.
This module performs no seed, DDL, or data mutation.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    """Load local ``.env`` values without replacing environment overrides."""
    path = ROOT / ".env"
    if not path.exists():
        if os.getenv("DATABASE_URL"):
            return
        raise RuntimeError("Missing local .env or DATABASE_URL")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env()
    from tools.validate_official_database import main as validate_official_database

    return validate_official_database()


if __name__ == "__main__":
    raise SystemExit(main())
