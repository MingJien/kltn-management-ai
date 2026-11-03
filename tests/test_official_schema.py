"""Fail-closed checks for the permanent phase-one schema."""
from pathlib import Path

import pytest
from alembic.config import Config

from backend.api.dependencies import database_url
from backend.db.metadata import target_metadata
from tools.official_schema import SELECTED_TABLES
from tools.export_official_schema_sql import build_sql


def test_official_metadata_excludes_later_phase_tables():
    assert set(target_metadata.tables) == SELECTED_TABLES
    assert len(target_metadata.tables) == 43
    assert "council" not in target_metadata.tables
    for table in target_metadata.tables.values():
        for foreign_key in table.foreign_keys:
            assert foreign_key.column.table.name in SELECTED_TABLES


def test_official_migration_is_independent_of_legacy_history():
    revision = Path(__file__).resolve().parents[1] / "backend/migrations_official/versions/20261015_0001_official.py"
    source = revision.read_text(encoding="utf-8")
    assert "down_revision = None" in source
    assert "20261004_0011" not in source
    assert "create_all" not in source


def test_default_alembic_config_uses_official_migrations():
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert config.get_main_option("script_location").endswith("/backend/migrations_official")


def test_review_sql_matches_official_database_table_set():
    import re

    sql = build_sql()
    names = re.findall(r"^CREATE TABLE (\w+)", sql, re.MULTILINE)
    assert set(names) == SELECTED_TABLES | {"alembic_version"}
    assert len(names) == 44
    assert "version_num VARCHAR(32) NOT NULL" in sql
    assert "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)" in sql
    assert not re.search(r"^\s*ALTER TABLE\b", sql, re.IGNORECASE | re.MULTILINE)


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://user:password@localhost/kltn_ai",
    "postgresql+psycopg://user:password@localhost/kltn_dev",
    "sqlite:///kltn_management",
])
def test_runtime_refuses_nonofficial_database(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(RuntimeError, match="kltn_management"):
        database_url()
