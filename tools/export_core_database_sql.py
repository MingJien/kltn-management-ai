"""Compatibility entry point for exporting the current official schema.

The historic core-slice exporter based on kltn_ai has been retired. This command
now writes only database/official/kltn-management-schema.sql from the official
Alembic revision; it does not inspect a database or recreate legacy SQL files.
"""
from tools.export_official_schema_sql import main

if __name__ == "__main__":
    main()
