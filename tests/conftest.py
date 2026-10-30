"""Run database tests in a newly migrated, owned schema; never inspect real records."""
import os
import re
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    from backend.db.validate_schema import load_env
    load_env()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        yield
        return
    url = make_url(raw)
    if url.database != "kltn_management" or not url.drivername.startswith("postgresql"):
        raise RuntimeError("Integration tests require PostgreSQL kltn_management")
    schema = "pytest_nv6_" + uuid4().hex[:16]
    assert re.fullmatch(r"pytest_nv6_[0-9a-f]{16}", schema)
    root_engine = create_engine(url)
    created = False
    old_values = {key: os.environ.get(key) for key in ("DATABASE_URL", "KLTN_SMTP_HOST", "KLTN_SMTP_USER", "KLTN_SMTP_PASSWORD", "KLTN_MAIL_FROM")}
    try:
        with root_engine.begin() as conn:
            assert conn.scalar(text("select count(*) from pg_namespace where nspname=:s"), {"s": schema}) == 0
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            created = True
        options = dict(url.query)
        options["options"] = "-csearch_path=" + schema
        os.environ["DATABASE_URL"] = url.set(query=options).render_as_string(hide_password=False)
        for key in old_values.keys()-{"DATABASE_URL"}:
            os.environ[key] = ""
        command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if created:
            with root_engine.begin() as conn:
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root_engine.dispose()
