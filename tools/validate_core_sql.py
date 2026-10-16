"""Compatibility entry point for read-only validation of kltn_management."""
from backend.db.validate_schema import load_env
from tools.validate_official_database import main

if __name__ == "__main__":
    load_env()
    raise SystemExit(main())
