"""Apply database/kltn-init-empty.sql to a new temporary schema only."""
from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import uuid4

import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from backend.db.validate_schema import load_env


def main() -> int:
    load_env()
    url = make_url(os.environ["DATABASE_URL"])
    name = "nv4_sqltest_" + uuid4().hex[:12]
    assert re.fullmatch(r"nv4_sqltest_[0-9a-f]{12}", name)
    engine = create_engine(url)
    with engine.begin() as conn:
        assert conn.execute(text("select count(*) from pg_namespace where nspname=:n"), {"n": name}).scalar_one() == 0
        conn.execute(text(f'CREATE SCHEMA "{name}"'))
    try:
        script = Path("database/kltn-init-empty.sql").read_text(encoding="utf-8-sig")
        with psycopg.connect(
            host=url.host, port=url.port, dbname=url.database,
            user=url.username, password=url.password,
            options=f"-csearch_path={name}",
            autocommit=True,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(script, prepare=False)
                cursor.execute("SELECT version_num FROM alembic_version")
                assert cursor.fetchone()[0] == "20260925_0007"
                cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema=%s", (name,))
                assert cursor.fetchone()[0] == 63
                cursor.execute("SELECT id, state FROM rubric_template WHERE code='MAU-06-HOIDONG' AND version_no=1")
                template_id, state = cursor.fetchone()
                assert state == "DRAFT"
                cursor.execute("SELECT count(*) FROM rubric_criterion WHERE rubric_template_id=%s", (template_id,))
                assert cursor.fetchone()[0] == 16
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name='registration_member' AND column_name IN ('consent_status','responded_by_user_id','responded_at')", (name,))
                assert len(cursor.fetchall()) == 3
        print("PASS init SQL on empty disposable schema: 63 tables, head 20260925_0007")
        return 0
    finally:
        with engine.begin() as conn:
            owner = conn.execute(text("select nspowner::regrole::text from pg_namespace where nspname=:n"), {"n": name}).scalar_one_or_none()
            current = conn.execute(text("select current_user")).scalar_one()
            if owner != current:
                raise RuntimeError("Unexpected owner; refusing to remove disposable schema")
            conn.execute(text(f'DROP SCHEMA "{name}" CASCADE'))
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
