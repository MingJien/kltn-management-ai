"""Exercise migrations in a new, uniquely named schema in the configured test DB.

Only the schema created by this process is removed. No public objects are touched.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.db.validate_schema import load_env


def main() -> int:
    load_env()
    original = os.getenv("DATABASE_URL")
    if not original:
        print("DATABASE_URL missing")
        return 2
    # seed_demo intentionally targets kltn_dev, so the disposable schema must
    # live in that database too. Credentials stay in process memory.
    original = make_url(original).set(database="kltn_dev").render_as_string(hide_password=False)
    name = "nv4_disposable_" + uuid4().hex[:12]
    assert re.fullmatch(r"nv4_disposable_[0-9a-f]{12}", name)
    engine = create_engine(original)
    created = False
    with engine.begin() as conn:
        assert conn.execute(text("select count(*) from pg_namespace where nspname=:n"), {"n": name}).scalar_one() == 0
        conn.execute(text(f'CREATE SCHEMA "{name}"'))
        created = True
    query = dict(make_url(original).query)
    query["options"] = f"-csearch_path={name}"
    private_url = make_url(original).set(query=query).render_as_string(hide_password=False)
    env = os.environ.copy()
    env["DATABASE_URL"] = private_url
    env["KLTN_ENV"] = "test"
    env["KLTN_DEV_AUTH"] = "true"
    env["PYTHONIOENCODING"] = "utf-8"
    demo_credentials = Path(__file__).resolve().parents[1] / "database" / "tai-khoan-demo.local.csv"
    created_credentials = not demo_credentials.exists()
    commands = [
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "-m", "alembic", "check"],
        [sys.executable, "-m", "backend.db.validate_schema"],
        [sys.executable, "-m", "tools.seed_demo", "--execute", "--create-credentials"],
    ]
    try:
        for command in commands:
            result = subprocess.run(command, env=env, text=True, capture_output=True, errors="replace")
            label = " ".join(command[2:])
            if result.returncode:
                print("FAIL", label, result.stdout[-1000:], result.stderr[-1000:])
                return result.returncode
            print("PASS", label)
        blocked = subprocess.run([sys.executable, "-m", "alembic", "downgrade", "-1"], env=env, text=True, capture_output=True)
        if blocked.returncode == 0 or "do not discard" not in blocked.stderr:
            print("FAIL forward-only migration guard")
            return 1
        print("PASS 0013 forward-only guard preserves imported class and major")
        return 0
    finally:
        if created_credentials and demo_credentials.is_file():
            demo_credentials.unlink()
        if created:
            # A random schema created in this run cannot contain pre-existing user data.
            with engine.begin() as conn:
                owner = conn.execute(text("select nspowner::regrole::text from pg_namespace where nspname=:n"), {"n": name}).scalar_one_or_none()
                current = conn.execute(text("select current_user")).scalar_one()
                if owner != current:
                    raise RuntimeError("Refusing to remove a disposable schema with unexpected owner")
                conn.execute(text(f'DROP SCHEMA "{name}" CASCADE'))
            print("Removed only disposable test schema")
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
