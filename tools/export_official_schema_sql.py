"""Export the initial official Alembic revision as a single schema-only SQL file.

The export is useful for reviewing or testing the DDL on a disposable, empty
PostgreSQL database. Initialize the permanent kltn_management database with
Alembic so its version history remains authoritative.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex

from tools.official_schema import SELECTED_TABLES
from tools.validate_official_database import HEAD
from backend.db.metadata import target_metadata


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "backend" / "migrations_official" / "versions" / "20261015_0001_official.py"
CATALOG_MIGRATION = ROOT / "backend" / "migrations_official" / "versions" / "20261021_0004_department_major.py"
DEADLINE_MIGRATION = ROOT / "backend" / "migrations_official" / "versions" / "20261022_0005_document_deadlines.py"
FORM_MIGRATION = ROOT / "backend" / "migrations_official" / "versions" / "20261026_0007_registration_forms.py"
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
    initial_tables = SELECTED_TABLES - {"user_notification", "department_major", "document_deadline", "registration_form_version", "progress_review_annotation", "official_form", "official_form_version", "thesis_review", "defense_eligibility_check"}
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
    audit_index = next(index for index, statement in enumerate(statements)
                       if statement.startswith("CREATE TABLE audit_event ("))
    statements[audit_index] = statements[audit_index].replace("\tCONSTRAINT pk_audit_event PRIMARY KEY",
        "\tsource_reference VARCHAR(500),\n\tCONSTRAINT pk_audit_event PRIMARY KEY")
    statements.append("CREATE INDEX ix_audit_event_occurred_id ON audit_event (occurred_at, id);")
    notification_table = target_metadata.tables["user_notification"]
    statements.append(str(CreateTable(notification_table).compile(dialect=postgresql.dialect())).strip() + ";")
    statements.extend(str(CreateIndex(index).compile(dialect=postgresql.dialect())).strip() + ";"
                      for index in notification_table.indexes)
    catalog_source = CATALOG_MIGRATION.read_text(encoding="utf-8")
    catalog_ddl = re.findall(r'CREATE TABLE department_major\b[\s\S]*?;', catalog_source)
    if len(catalog_ddl) != 1:
        raise RuntimeError("Department-major migration DDL changed; update snapshot projection")
    department_index = next(index for index, statement in enumerate(statements)
                            if statement.startswith("CREATE TABLE department ("))
    statements.insert(department_index + 1, catalog_ddl[0])
    student_index = next(index for index, statement in enumerate(statements)
                         if statement.startswith("CREATE TABLE student_profile ("))
    student_ddl = statements[student_index]
    if student_ddl.count("\n);") != 1:
        raise RuntimeError("Student profile DDL changed; update catalog FK projection")
    statements[student_index] = student_ddl.replace("\n);",
        ",\n\tCONSTRAINT fk_student_profile_department_major FOREIGN KEY (department_id, major_code) REFERENCES department_major (department_id, code) ON DELETE RESTRICT\n);")
    deadline_source = DEADLINE_MIGRATION.read_text(encoding="utf-8")
    deadline_ddl = re.findall(r'CREATE TABLE document_deadline\b[\s\S]*?;', deadline_source)
    if len(deadline_ddl) != 1:
        raise RuntimeError("Document-deadline migration DDL changed; update snapshot projection")
    deadline_check = next(constraint for constraint in target_metadata.tables["document_deadline"].constraints
                          if constraint.name == "ck_document_deadline_document_type")
    deadline_ddl[0], changed = re.subn(r"CONSTRAINT ck_document_deadline_document_type CHECK \([^\n]+\)",
        f"CONSTRAINT ck_document_deadline_document_type CHECK ({deadline_check.sqltext})", deadline_ddl[0])
    if changed != 1:
        raise RuntimeError("Document-deadline CHECK changed; update snapshot projection")
    round_index = next(index for index, statement in enumerate(statements)
                       if statement.startswith("CREATE TABLE thesis_round ("))
    statements.insert(round_index + 1, deadline_ddl[0])
    for table_name in ("proposal_version", "document_version"):
        version_index = next(index for index, statement in enumerate(statements)
                             if statement.startswith(f"CREATE TABLE {table_name} ("))
        needle = f"\tCONSTRAINT pk_{table_name} PRIMARY KEY"
        if statements[version_index].count(needle) != 1:
            raise RuntimeError(f"{table_name} DDL changed; update snapshot projection")
        statements[version_index] = statements[version_index].replace(needle,
            "\tdue_at_at_submission TIMESTAMP WITH TIME ZONE,\n" + needle)
    form_ddl = re.findall(r'CREATE TABLE registration_form_version\b[\s\S]*?;', FORM_MIGRATION.read_text(encoding="utf-8"))
    if len(form_ddl) != 1:
        raise RuntimeError("Registration-form migration DDL changed; update snapshot projection")
    statements.append(form_ddl[0])
    topic_index = next(i for i, statement in enumerate(statements) if statement.startswith("CREATE TABLE topic ("))
    statements[topic_index] = str(CreateTable(target_metadata.tables["topic"]).compile(dialect=postgresql.dialect())).strip() + ";"
    annotation_table = target_metadata.tables["progress_review_annotation"]
    statements.append(str(CreateTable(annotation_table).compile(dialect=postgresql.dialect())).strip() + ";")
    statements.extend(str(CreateIndex(index).compile(dialect=postgresql.dialect())).strip() + ";" for index in annotation_table.indexes)
    reviewer_index = next(i for i, statement in enumerate(statements) if statement.startswith("CREATE TABLE reviewer_assignment ("))
    statements[reviewer_index] = str(CreateTable(target_metadata.tables["reviewer_assignment"]).compile(dialect=postgresql.dialect())).strip() + ";"
    for name in ("official_form", "official_form_version", "thesis_review", "defense_eligibility_check"):
        table = target_metadata.tables[name]
        statements.append(str(CreateTable(table).compile(dialect=postgresql.dialect())).strip() + ";")
        statements.extend(str(CreateIndex(index).compile(dialect=postgresql.dialect())).strip() + ";" for index in table.indexes)
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
