"""Read-only structural verification of the permanent PostgreSQL schema.

Reads DATABASE_URL from the process environment or local .env and requires
PostgreSQL kltn_management. It never seeds data or runs DDL.
"""
from __future__ import annotations

import os

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend.db.metadata import target_metadata
from backend.db.validate_schema import load_env
from tools.official_schema import SELECTED_TABLES

HEAD = "20261030_0017"


def main() -> int:
    load_env()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        raise RuntimeError("Set DATABASE_URL to kltn_management")
    url = make_url(raw)
    if url.database != "kltn_management" or not url.drivername.startswith("postgresql"):
        raise RuntimeError("Refusing to inspect a database other than PostgreSQL kltn_management")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT current_database()")).scalar_one() != "kltn_management":
                raise AssertionError("Connected to the wrong database")
            inspector = inspect(connection)
            actual = set(inspector.get_table_names())
            assert actual == SELECTED_TABLES | {"alembic_version"}, (
                sorted(SELECTED_TABLES - actual), sorted(actual - SELECTED_TABLES - {"alembic_version"}))
            head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert head == HEAD, head
            fk_count = check_count = unique_count = index_count = 0
            for table in target_metadata.tables.values():
                name = table.name
                columns = {column["name"]: column for column in inspector.get_columns(name)}
                assert set(columns) == set(table.columns.keys()), name
                for column in table.columns:
                    assert columns[column.name]["nullable"] == column.nullable, (name, column.name)
                assert set(inspector.get_pk_constraint(name)["constrained_columns"]) == set(
                    column.name for column in table.primary_key.columns), name
                actual_fks = {(
                    tuple(item["constrained_columns"]), item["referred_table"],
                    tuple(item["referred_columns"])) for item in inspector.get_foreign_keys(name)}
                model_fks = {(
                    tuple(element.parent.name for element in constraint.elements),
                    constraint.elements[0].column.table.name,
                    tuple(element.column.name for element in constraint.elements))
                    for constraint in table.constraints if isinstance(constraint, ForeignKeyConstraint)}
                assert actual_fks == model_fks, (name, actual_fks ^ model_fks)
                assert all(parent in SELECTED_TABLES for _, parent, _ in actual_fks), name
                fk_count += len(actual_fks)
                actual_checks = {item["name"] for item in inspector.get_check_constraints(name)}
                model_checks = {item.name for item in table.constraints if isinstance(item, CheckConstraint)}
                assert actual_checks == model_checks, (name, actual_checks ^ model_checks)
                check_count += len(actual_checks)
                actual_uniques = {item["name"] for item in inspector.get_unique_constraints(name)}
                model_uniques = {item.name for item in table.constraints if isinstance(item, UniqueConstraint)}
                assert actual_uniques == model_uniques, (name, actual_uniques ^ model_uniques)
                unique_count += len(actual_uniques)
                actual_indexes = {item["name"] for item in inspector.get_indexes(name)}
                model_indexes = {item.name for item in table.indexes}
                assert model_indexes <= actual_indexes, (name, model_indexes - actual_indexes)
                index_count += len(model_indexes)
            print(f"PASS database=kltn_management head={head} business_tables={len(SELECTED_TABLES)} "
                  f"FK={fk_count} CHECK={check_count} UNIQUE={unique_count} explicit_index={index_count}")
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
