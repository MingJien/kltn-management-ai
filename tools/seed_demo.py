"""Opt-in synthetic demo identities for the React prototype.

Run only on a disposable development database:
python -m tools.seed_demo --execute
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.api.dependencies import load_local_env
from backend.db.models import entities as m


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
    args = parser.parse_args()
    load_local_env()
    if not args.execute:
        print("Dry run only. Add --execute for synthetic records in the configured DB.")
        return
    if os.getenv("KLTN_ENV") not in {"development", "test"}:
        parser.error("KLTN_ENV must be development or test")
    if not os.getenv("DATABASE_URL"):
        parser.error("DATABASE_URL is missing")
    engine = create_engine(os.environ["DATABASE_URL"])
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session, session.begin():
        version = session.execute(text("select version_num from alembic_version")).scalar_one()
        if version != "20260925_0007":
            parser.error("Upgrade the configured development DB to 20260925_0007 first")
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
            ensure(session, m.EligibilitySnapshot, f"eligibility-{i}",
                   student_id=student.id, round_id=round_.id, version=1,
                   passed_credit_ratio=0.8, gpa_4=3.0, discipline_status="CLEAR",
                   criminal_case_status="CLEAR", evidence_ref="SYNTHETIC_DEMO",
                   captured_at=now, confirmed_by=lecturer_users[1].id,
                   confirmed_at=now, state="CONFIRMED")
        ensure(session, m.Topic, "topic", round_id=round_.id, department_id=department.id,
               proposer_user_id=lecturer_users[0].id, proposer_type="LECTURER",
               current_title="Đề tài quản lý KLTN giả lập", max_students=3, state="APPROVED")
    engine.dispose()
    print("Synthetic demo users only:")
    for label, user in [
        ("SV 1", student_users[0]), ("SV 2", student_users[1]),
        ("SV 3", student_users[2]), ("GV de xuat", lecturer_users[0]),
        ("Truong Bo mon", lecturer_users[1]),
    ]:
        print(label, user.id)


if __name__ == "__main__":
    main()
