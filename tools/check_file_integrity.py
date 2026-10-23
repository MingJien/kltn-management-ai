"""Read-only reconciliation between stored-file metadata and the upload folders.

Command: python -m tools.check_file_integrity [--json] [--skip-hash]

The report lists:
  * metadata rows whose file is missing on disk;
  * files on disk that no metadata row points at;
  * byte-size or SHA-256 mismatches;
  * storage keys outside the known roots.

Nothing is deleted, moved or overwritten. Every row and every version is kept so
a person can decide what to restore.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = {
    "documents/": ("KLTN_DOCUMENT_DIR", ROOT / "local" / "uploads" / "documents"),
    "proposals/": ("KLTN_PROPOSAL_DIR", ROOT / "local" / "uploads" / "proposals"),
    "registration/": ("KLTN_EVIDENCE_DIR", ROOT / "local" / "uploads" / "registration"),
}


def roots() -> dict[str, Path]:
    result = {}
    for prefix, (variable, default) in PREFIXES.items():
        result[prefix] = Path(os.getenv(variable, str(default))).resolve()
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    from backend.db.models import entities as m
    from backend.db.validate_schema import load_env

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--skip-hash", action="store_true", help="only compare sizes")
    arguments = parser.parse_args()
    load_env()
    if not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is not configured")
    engine = create_engine(os.environ["DATABASE_URL"])
    locations = roots()
    report = {"missing_file": [], "orphan_file": [], "size_mismatch": [], "hash_mismatch": [],
              "unknown_storage_key": [], "by_scan_state": {}, "checked": 0}

    with Session(engine) as session:
        rows = session.scalars(select(m.StoredFile)).all()
        known: set[tuple[str, str]] = set()
        for row in rows:
            prefix = next((item for item in locations if row.storage_key.startswith(item)), None)
            if prefix is None:
                report["unknown_storage_key"].append({"id": str(row.id), "storage_key": row.storage_key})
                continue
            report["by_scan_state"][row.scan_state] = report["by_scan_state"].get(row.scan_state, 0) + 1
            relative = row.storage_key.removeprefix(prefix)
            path = (locations[prefix] / relative).resolve()
            known.add((prefix, relative))
            if path.parent != locations[prefix] or not path.is_file():
                report["missing_file"].append({"id": str(row.id), "storage_key": row.storage_key,
                                               "original_name": row.original_name})
                continue
            report["checked"] += 1
            if path.stat().st_size != row.byte_size:
                report["size_mismatch"].append({"id": str(row.id), "storage_key": row.storage_key,
                                                "expected": row.byte_size, "actual": path.stat().st_size})
                continue
            if not arguments.skip_hash and sha256(path) != row.sha256:
                report["hash_mismatch"].append({"id": str(row.id), "storage_key": row.storage_key})

    for prefix, root in locations.items():
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if (prefix, relative) not in known:
                report["orphan_file"].append({"storage_key": prefix + relative})

    problems = sum(len(report[key]) for key in
                   ("missing_file", "orphan_file", "size_mismatch", "hash_mismatch", "unknown_storage_key"))
    report["problem_count"] = problems
    if arguments.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Đã đối chiếu {report['checked']} tệp có metadata.")
        print("Trạng thái quét:", ", ".join(f"{key}={value}" for key, value in sorted(report["by_scan_state"].items())) or "không có")
        for key, label in (("missing_file", "Metadata thiếu tệp"),
                           ("orphan_file", "Tệp không có metadata"),
                           ("size_mismatch", "Sai kích thước"),
                           ("hash_mismatch", "Sai SHA-256"),
                           ("unknown_storage_key", "Khóa lưu trữ lạ")):
            if report[key]:
                print(f"\n{label} ({len(report[key])}):")
                for item in report[key]:
                    detail = item.get("storage_key", item.get("id"))
                    print("  -", detail, item.get("original_name", ""))
        print("\nKhông xóa hay sửa tệp nào. Cần người phụ trách quyết định phục hồi." if problems
              else "\nKhông phát hiện lệch metadata/tệp.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
