"""Opt-in synthetic demo identities for the React prototype.

Run only on a disposable development database:
python -m tools.seed_demo --execute
"""
from __future__ import annotations

import argparse
import csv
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend.api.dependencies import load_local_env
from backend.db.models import entities as m
from backend.services.passwords import hash_password
from backend.services.topics import allocate_topic_code

ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = ROOT / "database" / "tai-khoan-demo.local.csv"
ACCOUNT_KEYS = ("sv1", "sv2", "sv3", "gv", "tbm")


def load_demo_credentials(database: str) -> list[tuple[str, str]]:
    """Read local-only demo logins; never put credentials in application source."""
    if not CREDENTIALS_PATH.is_file():
        raise ValueError(f"Missing local demo credential file: {CREDENTIALS_PATH}")
    with CREDENTIALS_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    if [row.get("tai_khoan_demo") for row in rows] != list(ACCOUNT_KEYS):
        raise ValueError("Demo credential file must contain sv1, sv2, sv3, gv, tbm in order")
    emails = [row.get("email_dang_nhap", "").strip().lower() for row in rows]
    passwords = [row.get("mat_khau_demo", "") for row in rows]
    if any(row.get("database") != database for row in rows):
        raise ValueError("Demo credential file is for a different database")
    if len(set(emails)) != len(emails) or any("@" not in email for email in emails):
        raise ValueError("Demo account emails must be distinct and valid")
    if any(len(password) < 12 for password in passwords):
        raise ValueError("Demo passwords must be at least 12 characters")
    return list(zip(emails, passwords))


def uid(name: str):
    return uuid5(NAMESPACE_URL, "kltn-synthetic-demo-v1/" + name)


def ensure(session: Session, cls, identity_key: str, **values):
    item = session.get(cls, uid(identity_key))
    if item is None:
        item = cls(id=uid(identity_key), **values)
        session.add(item)
        session.flush()
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually insert synthetic demo records")
    parser.add_argument("--create-credentials", action="store_true", help="Create the ignored local credential file if absent; never overwrite it")
    parser.add_argument(
        "--database", choices=("kltn_dev",), default="kltn_dev",
        help="Development database that receives demo records (default: kltn_dev)",
    )
    args = parser.parse_args()
    load_local_env()
    if not args.execute:
        print("Dry run only. Add --execute for synthetic records in the configured DB.")
        return
    if os.getenv("KLTN_ENV") not in {"development", "test"}:
        parser.error("KLTN_ENV must be development or test")
    if not os.getenv("DATABASE_URL"):
        parser.error("DATABASE_URL is missing")
    if args.create_credentials and not CREDENTIALS_PATH.exists():
        with CREDENTIALS_PATH.open('x', newline='', encoding='utf-8-sig') as handle:
            writer = csv.DictWriter(handle, fieldnames=['tai_khoan_demo','email_dang_nhap','mat_khau_demo','database'], delimiter=';')
            writer.writeheader()
            for key in ACCOUNT_KEYS:
                writer.writerow({'tai_khoan_demo':key,'email_dang_nhap':f'{key}@demo.test',
                    'mat_khau_demo':secrets.token_urlsafe(18),'database':args.database})
    try:
        demo_credentials = load_demo_credentials(args.database)
    except ValueError as exc:
        parser.error(str(exc))
    database_url = make_url(os.environ["DATABASE_URL"]).set(database=args.database)
    engine = create_engine(database_url)
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session, session.begin():
        version = session.execute(text("select version_num from alembic_version")).scalar_one()
        if version != "20261004_0012":
            parser.error("Upgrade the configured development DB to 20261004_0012 first")
        faculty = ensure(session, m.Faculty, "faculty", code="SYN-DEMO-FAC", name="Khoa giả lập")
        department = ensure(session, m.Department, "department", faculty_id=faculty.id,
                            code="SYN-DEMO-DEP", name="Bộ môn giả lập")
        year = ensure(session, m.AcademicYear, "year", code="SYN-DEMO-2026",
                      starts_on=date(2026, 9, 1), ends_on=date(2027, 8, 31), state="ACTIVE")
        round_ = ensure(session, m.ThesisRound, "round", academic_year_id=year.id,
                        code="SYN-DEMO", round_type="MAIN", opens_at=now-timedelta(days=1),
                        closes_at=now+timedelta(days=90), state="OPEN")
        round_.opens_at = now-timedelta(days=1)
        round_.closes_at = now+timedelta(days=90)
        round_.state = "OPEN"
        student_users = [
            ensure(session, m.UserAccount, f"user-student-{i}",
                   external_subject=f"synthetic-demo-student-{i}", base_role="STUDENT", status="ACTIVE")
            for i in range(1, 4)
        ]
        lecturer_users = [
            ensure(session, m.UserAccount, f"user-lecturer-{i}",
                   external_subject=f"synthetic-demo-lecturer-{i}", base_role="LECTURER", status="ACTIVE")
            for i in range(1, 3)
        ]
        for user, (email, password) in zip([*student_users, *lecturer_users], demo_credentials):
            user.email = email
            user.password_hash = hash_password(password)
            user.email_verified_at = now
            user.status = "ACTIVE"
            user.row_version += 1
        students = [
            ensure(session, m.StudentProfile, f"student-{i}", user_id=user.id,
                   student_code=f"SYN-DEMO-SV-{i}", department_id=department.id,
                   display_name=f"Sinh viên giả lập {i}")
            for i, user in enumerate(student_users, 1)
        ]
        lecturers = [
            ensure(session, m.LecturerProfile, f"lecturer-{i}", user_id=user.id,
                   lecturer_code=f"SYN-DEMO-GV-{i}", department_id=department.id,
                   display_name=f"Giảng viên giả lập {i}")
            for i, user in enumerate(lecturer_users, 1)
        ]
        head_position = session.scalar(select(m.OrganizationalPosition).where(
            m.OrganizationalPosition.code == "DEPARTMENT_HEAD"
        ))
        if head_position is None:
            head_position = ensure(session, m.OrganizationalPosition, "head-position",
                                   code="DEPARTMENT_HEAD", name="Trưởng Bộ môn")
        ensure(session, m.PositionAssignment, "head-assignment",
               lecturer_id=lecturers[1].id, position_id=head_position.id,
               department_id=department.id, effective_from=now-timedelta(days=1), state="ACTIVE")
        for i, student in enumerate(students, 1):
            snapshot = ensure(session, m.EligibilitySnapshot, f"eligibility-{i}",
                   student_id=student.id, round_id=round_.id, version=1,
                   passed_credit_ratio=0.8, gpa_4=3.0,
                   evidence_ref="SYNTHETIC_DEMO",
                   captured_at=now, confirmed_by=lecturer_users[1].id,
                   confirmed_at=now, state="CONFIRMED")
            if snapshot.evidence_ref == "SYNTHETIC_DEMO":
                snapshot.passed_credit_ratio = 0.8
                snapshot.gpa_4 = 3.0
        ensure(session, m.Topic, "topic", round_id=round_.id, department_id=department.id,
               code=allocate_topic_code(session, round_), receiving_lecturer_id=lecturers[0].id,
               proposer_user_id=lecturer_users[0].id, proposer_type="LECTURER",
               current_title="Đề tài quản lý KLTN giả lập", max_students=3, state="APPROVED")
        examples = [
            ("topic-individual", "Website tra cứu tài liệu học tập", 1, "Xây dựng danh mục và bộ lọc tài liệu công khai.",
                [("SKILL", "HTML/CSS, JavaScript", None)]),
            ("topic-pair", "Ứng dụng theo dõi tiến độ đồ án", 2, "Đăng ký đề tài, kế hoạch công việc và báo cáo tiến độ.",
                [("PREFERRED_GPA", "Có thể đính kèm bảng điểm đã lược bỏ thông tin không cần thiết", 3.0), ("TECHNOLOGY", "Python, PostgreSQL", None)]),
            ("topic-team", "Hệ thống quản lý mượn tài liệu", 3, "Quản lý tài liệu, đăng ký mượn và lịch trả.",
                [("KNOWLEDGE", "Phân tích thiết kế hệ thống", None), ("OTHER", "Chủ động trao đổi và báo cáo hằng tuần", None)]),
        ]
        for key, title, capacity, description, requirements in examples:
            new = session.get(m.Topic, uid(key)) is None
            topic = ensure(session, m.Topic, key, code=allocate_topic_code(session, round_), round_id=round_.id,
                department_id=department.id, receiving_lecturer_id=lecturers[0].id,
                proposer_user_id=lecturer_users[0].id, proposer_type="LECTURER", current_title=title,
                description=description, max_students=capacity, state="APPROVED")
            if new:
                session.add(m.TopicTitleVersion(id=uid(key+"-title"), topic_id=topic.id, version_no=1,
                    title=title, changed_by=lecturer_users[0].id, change_reason="Synthetic demo fixture"))
                for index, (kind, description, gpa) in enumerate(requirements):
                    session.add(m.TopicRequirement(id=uid(f"{key}-requirement-{index}"), topic_id=topic.id,
                        requirement_type=kind, value_text=description, preferred_gpa=gpa, enforcement="DESIRED"))
    engine.dispose()
    print(f"Seeded synthetic demo accounts in {args.database}.")
    print(f"Demo credentials loaded from local Git-ignored file: {CREDENTIALS_PATH}")


if __name__ == "__main__":
    main()
