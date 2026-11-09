"""Export the current official metadata as a single schema-only SQL file.

The export is useful for reviewing or testing the DDL on a disposable, empty
PostgreSQL database. Initialize the permanent kltn_management database with
Alembic so its version history remains authoritative.
"""

from __future__ import annotations

import re
from pathlib import Path
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex

from tools.official_schema import SELECTED_TABLES
from tools.validate_official_database import HEAD
from backend.db.metadata import target_metadata


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "database" / "official" / "kltn-management-schema.sql"


def initial_ddl() -> list[str]:
    # Export the current reviewed metadata only; runtime changes use Alembic.
    dialect=postgresql.dialect()
    if set(target_metadata.tables)!=SELECTED_TABLES:
        raise RuntimeError("Official metadata and selection differ")
    statements=[]
    for table in target_metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip()+";")
        statements.extend(str(CreateIndex(index).compile(dialect=dialect)).strip()+";" for index in sorted(table.indexes,key=lambda i:i.name))
    statements.append("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));")
    return statements


def build_sql() -> str:
    statements = initial_ddl()
    lines = [
        f"-- Schema-only review snapshot at Alembic revision {HEAD}.",
        f"-- {len(SELECTED_TABLES)} business tables plus alembic_version; each table has one complete CREATE TABLE statement.",
        "-- Columns, primary/foreign keys, UNIQUE, and CHECK constraints are defined in that statement.",
        "-- CREATE INDEX statements follow their tables; this file contains no ALTER TABLE statements.",
        "-- For an expendable empty PostgreSQL database only; this snapshot has no business data.",
        "-- Initialize the permanent kltn_management database with Alembic, not this export.",
        "",
        "BEGIN;",
        "SET LOCAL search_path = public;",
        "DO $guard_empty_schema$",
        "BEGIN",
        "    IF EXISTS (",
        "        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace",
        "        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')",
        "    ) THEN",
        "        RAISE EXCEPTION 'Schema must be empty; use Alembic for the permanent database';",
        "    END IF;",
        "END $guard_empty_schema$;",
        "",
    ]
    for statement in statements:
        lines.extend((statement, ""))
    lines.append("COMMIT;")
    return "\n".join(line.rstrip() for line in "\n".join(lines).splitlines()) + "\n"


def main() -> None:
    sql = build_sql()
    emitted_tables = re.findall(r"^CREATE\s+TABLE\s+(\w+)\b", sql, re.IGNORECASE | re.MULTILINE)
    expected_tables = SELECTED_TABLES | {"alembic_version"}
    if len(emitted_tables) != len(expected_tables) or set(emitted_tables) != expected_tables:
        raise RuntimeError("Export table set does not match official metadata")
    if re.search(r"^\s*ALTER\s+TABLE\b", sql, re.IGNORECASE | re.MULTILINE):
        raise RuntimeError("Export must not alter tables after creation")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as output:
        output.write(sql)
    print(f"PASS official schema export -> {OUTPUT.relative_to(ROOT)} ({len(SELECTED_TABLES)} business tables)")


if __name__ == "__main__":
    main()
