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
NOTIFICATION_MIGRATION = ROOT / "backend" / "migrations_official" / "versions" / "20261021_0003_user_notification.py"
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
    initial_tables = SELECTED_TABLES - {"user_notification"}
    if len(tables) != len(initial_tables) or set(tables) != initial_tables:
        raise RuntimeError(
            "Initial migration does not match the official selection: "
            f"missing={sorted(initial_tables - set(tables))}, "
            f"unexpected={sorted(set(tables) - initial_tables)}, count={len(tables)}"
        )
    if len(tables) != len(set(tables)):
        raise RuntimeError("Initial migration creates a business table more than once")
    # Project the additive 0002 migration into the review snapshot. The live
    # database still gets this change only through Alembic; the snapshot keeps
    # one complete CREATE TABLE per table and never appends ALTER statements.
    for index, statement in enumerate(statements):
        if statement.startswith("CREATE TABLE progress_report ("):
            needle = "\tCONSTRAINT pk_progress_report PRIMARY KEY"
            if statement.count(needle) != 1:
                raise RuntimeError("Progress report DDL changed; update snapshot projection")
            statements[index] = statement.replace(needle,
                "\tdue_at_at_submission TIMESTAMP WITH TIME ZONE,\n" + needle)
            break
    else:
        raise RuntimeError("Progress report table missing from initial migration")
    notification_source = NOTIFICATION_MIGRATION.read_text(encoding="utf-8")
    additions = re.findall(r'CREATE (?:TABLE|INDEX) user_notification\b[\s\S]*?;', notification_source)
    if len(additions) != 1:
        # The index name differs from the table name; match it separately.
        additions = re.findall(r'CREATE TABLE user_notification\b[\s\S]*?;', notification_source)
    indexes = re.findall(r'CREATE INDEX ix_user_notification_recipient_created\b[\s\S]*?;', notification_source)
    if len(additions) != 1 or len(indexes) != 1:
        raise RuntimeError("Notification migration DDL changed; update snapshot projection")
    statements.extend([additions[0], indexes[0]])
    statements.append(
        "CREATE TABLE alembic_version (\n"
        "    version_num VARCHAR(32) NOT NULL,\n"
        "    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)\n"
        ");"
    )
    return statements


def build_sql() -> str:
    statements = initial_ddl()
    lines = [
        "-- Schema-only review snapshot at Alembic revision 20261021_0003.",
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
    return "\n".join(lines) + "\n"


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
