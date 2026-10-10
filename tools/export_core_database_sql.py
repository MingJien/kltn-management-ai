r"""Export the KLTN core slice from the verified live kltn_ai schema.

Run: .\.venv\Scripts\python.exe -m tools.export_core_database_sql
The generated SQL is for a new, empty PostgreSQL database only.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import CheckConstraint, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.db.base import Base
from backend.db.models import entities  # noqa: F401 - register all tables
from backend.db.validate_schema import load_env


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "database" / "core" / "kltn-core-schema.sql"
SOURCE_DATABASE = "kltn_ai"
SOURCE_REVISION = "20261010_0013"

# Dependency order also follows the first delivered business flow.
TABLES = (
    "faculty", "department", "user_account", "audit_event", "student_profile", "lecturer_profile",
    "organizational_position", "position_assignment", "academic_year", "thesis_round",
    "round_policy", "eligibility_snapshot", "topic", "topic_title_version", "topic_requirement", "stored_file", "topic_registration",
    "registration_member", "thesis", "thesis_member", "advisor_assignment",
    "council", "resource_assignment", "proposal", "proposal_version",
    "reviewer_assignment", "proposal_review", "progress_milestone", "progress_report",
    "progress_review", "document", "document_version",
)


def validate_live_schema(connection) -> None:
    inspector = inspect(connection)
    live_tables = set(inspector.get_table_names(schema="public"))
    missing = set(TABLES) - live_tables
    if missing:
        raise RuntimeError(f"Thiếu bảng ở {SOURCE_DATABASE}: {', '.join(sorted(missing))}")
    revision = connection.scalar(text("SELECT version_num FROM public.alembic_version"))
    if revision != SOURCE_REVISION:
        raise RuntimeError(f"Revision cần {SOURCE_REVISION}, hiện có {revision}")

    seen = set()
    for name in TABLES:
        model = Base.metadata.tables[name]
        live_columns = inspector.get_columns(name, schema="public")
        model_columns = list(model.columns)
        if {c["name"]: (c["nullable"], str(c["type"].compile(dialect=connection.engine.dialect)))
            for c in live_columns} != {
            c.name: (c.nullable, str(c.type.compile(dialect=connection.engine.dialect)))
            for c in model_columns
        }:
            raise RuntimeError(f"Cột/kiểu/nullable của {name} khác SQLAlchemy metadata")
        live_pk = set(inspector.get_pk_constraint(name, schema="public")["constrained_columns"])
        model_pk = {c.name for c in model.primary_key.columns}
        if live_pk != model_pk:
            raise RuntimeError(f"PK của {name} khác SQLAlchemy metadata")
        live_fks = {
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in inspector.get_foreign_keys(name, schema="public")
        }
        model_fks = {
            (tuple(c.name for c in fk.columns), fk.referred_table.name,
             tuple(e.column.name for e in fk.elements))
            for fk in model.foreign_key_constraints
        }
        if live_fks != model_fks:
            raise RuntimeError(f"FK của {name} khác SQLAlchemy metadata")
        outside = {fk.referred_table.name for fk in model.foreign_key_constraints} - seen
        if outside:
            raise RuntimeError(f"Bảng {name} có FK tới bảng chưa tạo: {', '.join(sorted(outside))}")
        live_unique = {
            tuple(u["column_names"]) for u in inspector.get_unique_constraints(name, schema="public")
        }
        model_unique = {
            tuple(c.name for c in u.columns) for u in model.constraints
            if u.__class__.__name__ == "UniqueConstraint"
        }
        if live_unique != model_unique:
            raise RuntimeError(f"UNIQUE của {name} khác SQLAlchemy metadata")
        live_checks = {c["name"] for c in inspector.get_check_constraints(name, schema="public")}
        model_checks = {c.name for c in model.constraints if isinstance(c, CheckConstraint)}
        if live_checks != model_checks:
            raise RuntimeError(f"CHECK của {name} khác SQLAlchemy metadata")
        live_indexes = {
            item["name"] for item in inspector.get_indexes(name, schema="public")
            if not item.get("duplicates_constraint")
        }
        model_indexes = {item.name for item in model.indexes}
        if live_indexes != model_indexes:
            raise RuntimeError(f"Index của {name} khác SQLAlchemy metadata")
        seen.add(name)


def build_sql(dialect) -> str:
    lines = [
        "-- KLTN: CSDL loi theo gop y GV, uu tien tai khoan, dot, dieu kien, de tai, dang ky, khoa luan, GVHD, de cuong, tien do, tai lieu.",
        f"-- Nguon: PostgreSQL {SOURCE_DATABASE}, Alembic {SOURCE_REVISION}; doi chieu metadata truoc khi xuat.",
        "-- Chi chay MOT LAN tren database PostgreSQL MOI, TRONG (de xuat ten: kltn_core).",
        "-- Khong chay tren kltn_ai/kltn_dev. Khong chua du lieu sinh vien, de tai hay mat khau.",
        "-- Ban 62 bang o kltn_ai duoc giu lam tham chieu cho cac giai doan sau.",
        "-- council chi dong vai tro FK cho resource_assignment; KHONG dung council cho buoi gop y de cuong/tien do.",
        "",
        "BEGIN;",
        "SET LOCAL search_path = public;",
        "DO $check_empty$",
        "BEGIN",
        "    IF EXISTS (",
        "        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace",
        "        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')",
        "    ) THEN",
        "        RAISE EXCEPTION 'Database must be empty; do not run this file on kltn_ai or kltn_dev';",
        "    END IF;",
        "END $check_empty$;",
        "",
    ]
    for number, name in enumerate(TABLES, 1):
        table = Base.metadata.tables[name]
        lines += [
            f"-- {number:02d}. {name}",
            str(CreateTable(table).compile(dialect=dialect)).strip() + ";",
            "",
        ]
    for name in TABLES:
        for index in sorted(Base.metadata.tables[name].indexes, key=lambda value: value.name):
            lines.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    lines += ["", "COMMIT;", ""]
    # SQLAlchemy emits spaces after commas; normalize the submission snapshot.
    return "\n".join(line.rstrip() for line in "\n".join(lines).splitlines()) + "\n"


def main() -> None:
    load_env()
    url = make_url(os.environ["DATABASE_URL"])
    if url.database != SOURCE_DATABASE:
        raise RuntimeError(f"Cần kết nối database nguồn {SOURCE_DATABASE}, hiện là {url.database}")
    engine = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT current_database()")) != SOURCE_DATABASE:
                raise RuntimeError("Kết nối sai database nguồn")
            validate_live_schema(connection)
            sql = build_sql(engine.dialect)
    finally:
        engine.dispose()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(sql, encoding="utf-8", newline="\n")
    print(f"PASS {len(TABLES)} tables -> {OUTPUT.relative_to(ROOT)}; source={SOURCE_DATABASE}; revision={SOURCE_REVISION}")


if __name__ == "__main__":
    main()
