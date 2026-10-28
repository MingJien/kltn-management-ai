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
from tools.validate_official_database import HEAD

ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = ROOT / "database" / "tai-khoan-demo.local.csv"
ACCOUNT_KEYS = ("sv1", "sv2", "sv3", "gv", "tbm", "gv2")
GV2_CREDENTIALS_PATH = ROOT / "local" / "tai-khoan-gv2-demo.csv"
DEMO_TOPIC_DESCRIPTION = (
    "Xây dựng hệ thống hỗ trợ Khoa quản lý toàn bộ quá trình thực hiện khóa luận tốt nghiệp, "
    "từ công bố đề tài, sinh viên đăng ký cá nhân hoặc theo nhóm, bộ môn xét duyệt, giảng viên "
    "tiếp nhận đến theo dõi các mốc thực hiện và hồ sơ tài liệu. Hệ thống cần phân quyền theo "
    "vai trò và phân công thực tế; mỗi thao tác quan trọng được lưu lịch sử để thuận tiện kiểm tra. "
    "Giai đoạn thử nghiệm tập trung vào luồng đăng ký đề tài và theo dõi tiến độ trên dữ liệu giả lập."
)


def load_demo_credentials(database: str) -> list[tuple[str, str]]:
    """Read local-only demo logins; never put credentials in application source."""
    if not CREDENTIALS_PATH.is_file():
        raise ValueError(f"Missing local demo credential file: {CREDENTIALS_PATH}")
    with CREDENTIALS_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    if [row.get("tai_khoan_demo") for row in rows] != list(ACCOUNT_KEYS):
        raise ValueError("Demo credential file must contain sv1, sv2, sv3, gv, tbm, gv2 in order")
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


def add_gv2_only(engine, now: datetime) -> None:
    """Add a second ordinary lecturer without resetting existing demo passwords."""
    GV2_CREDENTIALS_PATH.parent.mkdir(exist_ok=True)
    if GV2_CREDENTIALS_PATH.exists():
        with GV2_CREDENTIALS_PATH.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        if len(rows) != 1 or rows[0].get("email_dang_nhap") != "gv2@demo.test":
            raise ValueError("The local GV2 credential file has an unexpected format")
        password = rows[0]["mat_khau_demo"]
    else:
        password = secrets.token_urlsafe(18)
        with GV2_CREDENTIALS_PATH.open("x", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["tai_khoan_demo", "email_dang_nhap", "mat_khau_demo", "database"], delimiter=";")
            writer.writeheader()
            writer.writerow({"tai_khoan_demo": "gv2", "email_dang_nhap": "gv2@demo.test",
                             "mat_khau_demo": password, "database": "kltn_management"})
    with Session(engine) as session, session.begin():
        version = session.execute(text("select version_num from alembic_version")).scalar_one()
        if version != HEAD:
            raise ValueError(f"Upgrade the isolated official DB to {HEAD} first")
        head = session.get(m.LecturerProfile, uid("lecturer-2"))
        if head is None:
            raise ValueError("Seed the existing demo accounts before adding GV2")
        head.lecturer_code = "SYN-DEMO-TBM"
        head.display_name = "Trưởng bộ môn giả lập"
        user = ensure(session, m.UserAccount, "user-lecturer-3",
                      external_subject="synthetic-demo-lecturer-3", base_role="LECTURER", status="ACTIVE")
        user.email = "gv2@demo.test"
        user.password_hash = hash_password(password)
        user.email_verified_at = now
        user.status = "ACTIVE"
        user.row_version += 1
        ensure(session, m.LecturerProfile, "lecturer-3", user_id=user.id,
               lecturer_code="SYN-DEMO-GV-2", department_id=head.department_id,
               display_name="Giảng viên giả lập 2")
    print("Added GV2 to the local demo without changing other account passwords.")
    print(f"GV2 email/password is stored only in: {GV2_CREDENTIALS_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually insert synthetic demo records")
    parser.add_argument("--add-gv2-only", action="store_true", help="Add GV2 without reseeding other demo accounts")
    parser.add_argument("--create-credentials", action="store_true", help="Create the ignored local credential file if absent; never overwrite it")
    parser.add_argument(
        "--database", choices=("kltn_management",), default="kltn_management",
        help="Official database; use only an isolated test instance for synthetic records",
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
    database_url = make_url(os.environ["DATABASE_URL"])
    if database_url.database != "kltn_management" or os.getenv("KLTN_ALLOW_SYNTHETIC_SEED") != "true":
        parser.error("Synthetic seed requires kltn_management and KLTN_ALLOW_SYNTHETIC_SEED=true")
    if args.add_gv2_only:
        engine = create_engine(database_url)
        try:
            add_gv2_only(engine, datetime.now(timezone.utc))
        finally:
            engine.dispose()
        return
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
    engine = create_engine(database_url)
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session, session.begin():
        version = session.execute(text("select version_num from alembic_version")).scalar_one()
        if version != HEAD:
            parser.error(f"Upgrade the isolated official DB to {HEAD} first")
        faculty = ensure(session, m.Faculty, "faculty", code="SYN-DEMO-FAC", name="Khoa giả lập")
        department = ensure(session, m.Department, "department", faculty_id=faculty.id,
                            code="SYN-DEMO-DEP", name="Bộ môn giả lập")
        ensure(session, m.DepartmentMajor, "department-major-cntt", department_id=department.id,
               code="7480201", name="Công nghệ thông tin", active=True)
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
            for i in range(1, 4)
        ]
        for kind in ("PROPOSAL", "PLAN", "SUPPORTING"):
            deadline = ensure(session, m.DocumentDeadline, f"document-deadline-{kind.lower()}",
                round_id=round_.id, document_type=kind, due_at=now+timedelta(days=60),
                state="OPEN", set_by=lecturer_users[1].id, reason="SYNTHETIC E2E SCHEDULE")
            deadline.due_at = now+timedelta(days=60)
            deadline.state = "OPEN"
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
        lecturers = []
        for i, user in enumerate(lecturer_users, 1):
            code = "SYN-DEMO-TBM" if i == 2 else f"SYN-DEMO-GV-{1 if i == 1 else 2}"
            name = "Trưởng bộ môn giả lập" if i == 2 else f"Giảng viên giả lập {1 if i == 1 else 2}"
            lecturer = ensure(session, m.LecturerProfile, f"lecturer-{i}", user_id=user.id,
                              lecturer_code=code, department_id=department.id, display_name=name)
            lecturer.lecturer_code = code
            lecturer.display_name = name
            lecturers.append(lecturer)
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
                   evidence_ref="SYNTHETIC_DEMO",
                   captured_at=now, confirmed_by=lecturer_users[1].id,
                   confirmed_at=now, state="CONFIRMED")
        demo_topic = ensure(session, m.Topic, "topic", round_id=round_.id, department_id=department.id,
               code=allocate_topic_code(session, round_), receiving_lecturer_id=lecturers[0].id,
               proposer_user_id=lecturer_users[0].id, proposer_type="LECTURER",
               current_title="Đề tài quản lý KLTN giả lập", description=DEMO_TOPIC_DESCRIPTION,
               max_students=3, state="APPROVED")
        # Keep the first synthetic topic useful for testing the list preview after an idempotent reseed.
        demo_topic.description = DEMO_TOPIC_DESCRIPTION
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
