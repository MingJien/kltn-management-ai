"""Fail-closed checks for the permanent phase-one schema."""
from pathlib import Path

import pytest

from backend.api.dependencies import database_url
from backend.db.base import LegacyBase
from backend.db.metadata import target_metadata
from tools.official_schema import SELECTED_TABLES


def test_official_metadata_excludes_later_phase_tables():
    assert set(target_metadata.tables) == SELECTED_TABLES
    assert len(target_metadata.tables) == 32
    assert "council" in LegacyBase.metadata.tables
    for table in target_metadata.tables.values():
        for foreign_key in table.foreign_keys:
            assert foreign_key.column.table.name in SELECTED_TABLES


def test_official_migration_is_independent_of_legacy_history():
    revision = Path(__file__).resolve().parents[1] / "backend/migrations_official/versions/20261015_0001_official.py"
    source = revision.read_text(encoding="utf-8")
    assert "down_revision = None" in source
    assert "20261004_0011" not in source
    assert "create_all" not in source


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://user:password@localhost/kltn_ai",
    "postgresql+psycopg://user:password@localhost/kltn_dev",
    "sqlite:///kltn_management",
])
def test_runtime_refuses_nonofficial_database(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(RuntimeError, match="kltn_management"):
        database_url()
