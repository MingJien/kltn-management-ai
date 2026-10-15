"""Export the initial official Alembic revision as a single schema-only SQL file.

The export is useful for reviewing or testing the DDL on a disposable, empty
PostgreSQL database. Initialize the permanent kltn_management database with
Alembic so its version history remains authoritative.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from tools.official_schema import SELECTED_TABLES


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "backend" / "migrations_official" / "versions" / "20261015_0001_official.py"
OUTPUT = ROOT / "database" / "official" / "kltn-management-schema.sql"


def initial_ddl() -> list[str]:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"), filename=str(MIGRATION))
    statements: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "execute" or not isinstance(node.func.value, ast.Name) or node.func.value.id != "op":
            continue
        if len(node.args) != 1 or not isinstance(node.args[0], ast.Call):
            continue
        text_call = node.args[0]
        if not isinstance(text_call.func, ast.Attribute) or text_call.func.attr != "text" or len(text_call.args) != 1:
            continue
        value = text_call.args[0]
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        ddl = "\n".join(line.rstrip() for line in value.value.strip().splitlines()).rstrip(";")
        statement = ddl + ";"
        if re.match(r"^CREATE\s+(TABLE|(?:UNIQUE\s+)?INDEX)\b", statement, re.IGNORECASE):
            statements.append(statement)

    tables = [
        match.group(1)
        for statement in statements
        if (match := re.match(r"^CREATE\s+TABLE\s+(\w+)\b", statement, re.IGNORECASE))
    ]
    if len(tables) != len(SELECTED_TABLES) or set(tables) != set(SELECTED_TABLES):
        raise RuntimeError(
            "Initial migration does not match the official selection: "
            f"missing={sorted(set(SELECTED_TABLES) - set(tables))}, "
            f"unexpected={sorted(set(tables) - set(SELECTED_TABLES))}, count={len(tables)}"
        )
    if len(tables) != len(set(tables)):
        raise RuntimeError("Initial migration creates a business table more than once")
    return statements


def build_sql() -> str:
    statements = initial_ddl()
    lines = [
        "-- Schema-only export generated from Alembic revision 20261015_0001_official.",
        f"-- {len(SELECTED_TABLES)} business tables; each table has one complete CREATE TABLE statement.",
        "-- Columns, primary/foreign keys, UNIQUE, and CHECK constraints are defined in that statement.",
        "-- CREATE INDEX statements follow their tables; this file contains no ALTER TABLE statements.",
        "-- For an expendable empty PostgreSQL database only. It does not create alembic_version.",
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
    return "\n".join(lines) + "\n"


def main() -> None:
    sql = build_sql()
    emitted_tables = re.findall(r"^CREATE\s+TABLE\s+(\w+)\b", sql, re.IGNORECASE | re.MULTILINE)
    if len(emitted_tables) != len(SELECTED_TABLES) or len(set(emitted_tables)) != len(emitted_tables):
        raise RuntimeError("Export must contain exactly one CREATE TABLE for every selected business table")
    if re.search(r"^\s*ALTER\s+TABLE\b", sql, re.IGNORECASE | re.MULTILINE):
        raise RuntimeError("Export must not alter tables after creation")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as output:
        output.write(sql)
    print(f"PASS official schema export -> {OUTPUT.relative_to(ROOT)} ({len(SELECTED_TABLES)} business tables)")


if __name__ == "__main__":
    main()
