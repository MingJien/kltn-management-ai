r"""Export readable PostgreSQL schema and a fresh-db baseline from kltn_ai.

Run from D:\KLTN: .\.venv\Scripts\python.exe -m tools.export_database_sql
Both outputs are schema products. The baseline additionally seeds the technical
Alembic marker and draft Mẫu 6 rubric; it contains no student/thesis records.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.db.validate_schema import load_env


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"


def pg_dump_path() -> str:
    configured = os.environ.get("PG_DUMP")
    candidates = [configured, shutil.which("pg_dump"), r"D:\PostgreSQL\17\bin\pg_dump.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise RuntimeError("Không tìm thấy pg_dump; đặt biến PG_DUMP đến pg_dump.exe của PostgreSQL 17.")


def clean_schema(raw: str) -> str:
    """Keep DDL, drop psql control commands and pg_dump presentation noise."""
    kept = []
    for line in raw.splitlines():
        stripped = line.strip()
        if (not stripped or stripped.startswith("--") or stripped.startswith("\\")
                or stripped.startswith("SET ") or stripped.startswith("SELECT pg_catalog.set_config(")
                or stripped == "CREATE SCHEMA public;"):
            if not stripped and kept and kept[-1] != "":
                kept.append("")
            continue
        kept.append(line)
    body = "\n".join(kept).strip()
    body = re.sub(r"\bpublic\.", "", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    tables = re.findall(r"^CREATE TABLE ([a-z_]+) \(", body, re.MULTILINE)
    if len(tables) != 63 or len(set(tables)) != 63:
        raise RuntimeError(f"pg_dump phải có đúng 63 CREATE TABLE khác nhau, thấy {len(tables)}")
    if re.search(r"ALTER TABLE[^;]*ADD (?:COLUMN|\w+ COLUMN)", body, re.I | re.S):
        raise RuntimeError("Schema xuất vẫn có ALTER TABLE ADD COLUMN; chưa thể nộp bản gộp")
    if "discipline_status" in body or "criminal_case_status" in body:
        raise RuntimeError("Schema còn chứa chi tiết kỷ luật/án tích")
    if "passed_credit_ratio" not in body or "gpa_4" not in body:
        raise RuntimeError("Schema thiếu tỷ lệ tín chỉ hoặc GPA")
    return body + "\n"


def rubric_seed() -> str:
    source = ROOT / "backend/migrations/versions/20260925_0006_mau6_baseline.py"
    spec = importlib.util.spec_from_file_location("kltn_rubric_0006", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Không tải được migration rubric 0006")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    quote = lambda value: "'" + value.replace("'", "''") + "'"
    lines = [
        "-- Dữ liệu kỹ thuật Mẫu 6 DRAFT, cùng mã ổn định với migration 0006.",
        "INSERT INTO rubric_template (id, code, name, version_no, source_ref, state) VALUES "
        f"({quote(module.TEMPLATE_ID)}, {quote(module.TEMPLATE_CODE)}, "
        "'Mẫu 6 - Phiếu đánh giá Hội đồng', 1, 'SRC-MAU-06', 'DRAFT');",
    ]
    for order_no, (code, parent, label, maximum, kind) in enumerate(module.CRITERIA, 1):
        parent_sql = quote(module._id(parent)) if parent else "NULL"
        lines.append(
            "INSERT INTO rubric_criterion "
            "(id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES "
            f"({quote(module._id(code))}, {quote(module.TEMPLATE_ID)}, {parent_sql}, "
            f"{quote(code)}, {quote(label)}, {maximum}, {quote(kind)}, {order_no});"
        )
    if len(lines) != 18:
        raise RuntimeError("Rubric Mẫu 6 không có đúng 16 tiêu chí")
    return "\n".join(lines) + "\n"


def main() -> None:
    load_env()
    url = make_url(os.environ["DATABASE_URL"])
    if url.database != "kltn_ai":
        raise RuntimeError("Chỉ xuất từ database chính kltn_ai; không tự chọn kltn_dev")
    engine = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})
    with engine.connect() as connection:
        if connection.execute(text("select current_database()")).scalar_one() != "kltn_ai":
            raise RuntimeError("Kết nối sai database")
        revision = connection.execute(text("select version_num from alembic_version")).scalar_one()
    engine.dispose()
    if revision != "20261004_0011":
        raise RuntimeError(f"Cần nâng kltn_ai đến 20261004_0011 trước khi xuất; hiện {revision}")

    env = os.environ.copy()
    env.update(PGHOST=url.host or "localhost", PGPORT=str(url.port or 5432),
               PGUSER=url.username or "", PGPASSWORD=url.password or "")
    command = [pg_dump_path(), "--schema-only", "--no-owner", "--no-privileges",
               "--no-comments", "--schema=public", "--dbname=kltn_ai"]
    result = subprocess.run(command, env=env, capture_output=True, check=True)
    ddl = clean_schema(result.stdout.decode("utf-8"))
    header = (
        "-- KLTN PostgreSQL public schema; pg_dump --schema-only from kltn_ai.\n"
        f"-- Alembic {revision}; 62 bảng nghiệp vụ + alembic_version. Không chứa dữ liệu.\n"
        "-- Mỗi bảng có đủ cột hiện hành trong một CREATE TABLE; khóa FK/PK ở phần ALTER TABLE.\n"
        "-- Chỉ dùng để xem/nộp thiết kế; không chạy trên database đang có bảng.\n\n"
    )
    schema = header + ddl
    baseline = (
        "-- KLTN PostgreSQL baseline dùng một lần trên database mới, trống.\n"
        f"-- Alembic {revision}; không chạy lại trên kltn_ai/kltn_dev đã có bảng.\n"
        "-- Tạo bảng/khóa rồi nạp duy nhất marker Alembic và rubric Mẫu 6 DRAFT.\n\n"
        "BEGIN;\n\n" + ddl + "\n"
        f"INSERT INTO alembic_version (version_num) VALUES ('{revision}');\n\n"
        + rubric_seed() + "\nCOMMIT;\n"
    )
    (DATABASE / "kltn-schema-consolidated.sql").write_text(schema, encoding="utf-8")
    (DATABASE / "kltn-db-baseline.sql").write_text(baseline, encoding="utf-8")
    print(f"PASS pg_dump schema-only kltn_ai; revision={revision}; 63 CREATE TABLE; no business data")


if __name__ == "__main__":
    main()
