from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.api.account import (
    ActivationRequest, EmailRequest, LinkPassword, PasswordChange,
    activate, activation_request, password_change, password_reset, password_reset_request,
)
from backend.api.roster import CorrectStudent, ConfirmRows, RevokeStudent, confirm_roster, correct_student, revoke_eligibility
from backend.db.models import entities as m
from backend.services.account_tokens import make_token
from backend.services.passwords import verify_password
from backend.services.registration import confirmed_student_ids
from backend.services.roster import import_roster, parse_roster, require_assignment


def post_request() -> Request:
    return Request({"type":"http", "headers":[], "method":"POST", "path":"/",
                    "query_string":b"", "session":{}, "client":("127.0.0.1", 5000)})


def test_roster_rejects_duplicate_formula_and_missing_columns():
    valid = ("student_code,display_name,email,department_code,class_name,major_code\n"
             "SYN-001,Sinh vien mau,student@example.test,SYN-CS,CNTT-01,7480201\n").encode()
    rows, digest = parse_roster("students.csv", valid)
    assert rows[0].class_name == "CNTT-01" and len(digest) == 64
    for data in (
        valid + b"SYN-001,Other,other@example.test,SYN-CS,CNTT-01,7480201\n",
        valid.replace(b"Sinh vien mau", b"=2+2"),
        valid.replace(b",class_name,major_code", b""),
    ):
        with pytest.raises(HTTPException) as error:
            parse_roster("students.csv", data)
        assert error.value.status_code == 422


def test_import_confirm_activate_revoke_and_password_lifecycle(monkeypatch):
    from backend.api.dependencies import database_url
    monkeypatch.setenv("KLTN_ENV", "test")
    monkeypatch.setenv("AUTH_SESSION_SECRET", "test-secret-for-account-lifecycle-20261010-123456789")
    engine = create_engine(database_url())
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        now = datetime.now(timezone.utc)
        suffix = uuid4().hex[:8]
        faculty = m.Faculty(id=uuid4(), code=f"SYN-{suffix}", name="Synthetic faculty")
        year = m.AcademicYear(id=uuid4(), code=f"SYN-{suffix}", starts_on=date(2026,9,1),
                              ends_on=date(2027,8,31), state="ACTIVE")
        staff = m.UserAccount(id=uuid4(), external_subject=f"test-{suffix}",
                              base_role="ADMIN", status="ACTIVE")
        session.add_all([faculty, year, staff]); session.flush()
        department = m.Department(id=uuid4(), faculty_id=faculty.id, code=f"SYN-{suffix}",
                                  name="Synthetic department", major_code="7480201")
        round_ = m.ThesisRound(id=uuid4(), academic_year_id=year.id, code="ONE",
            round_type="MAIN", opens_at=now-timedelta(days=1),
            closes_at=now+timedelta(days=7), state="OPEN")
        session.add_all([department, round_]); session.flush()
        with pytest.raises(HTTPException) as no_implicit_permission:
            require_assignment(session, staff, round_.id, "ELIGIBILITY_VERIFIER")
        assert no_implicit_permission.value.status_code == 403
        for kind in ("ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER"):
            session.add(m.ResourceAssignment(id=uuid4(), assignment_type=kind,
                user_id=staff.id, round_id=round_.id, effective_from=now, state="ACTIVE"))
        session.flush()
        student_code = f"SYN-{suffix}"
        email = f"{suffix}@example.test"
        content = ("student_code,display_name,email,department_code,class_name,major_code\n"
                   f"{student_code},Synthetic student,{email},{department.code},CS-01,7480201\n").encode()
        rows, _ = parse_roster("roster.csv", content)
        result = import_roster(session, staff, round_.id, rows, "KHOA-2026-TEST")
        assert result["new_accounts"] == 1 and result["submitted"] == 1
        student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.student_code == student_code))
        account = session.get(m.UserAccount, student.user_id)
        assert student.class_name == "CS-01" and student.major_code == "7480201"
        assert account.status == "DISABLED" and not account.email_verified_at
        assert account.password_hash.startswith("!")
        assert not confirmed_student_ids(session, round_.id, [student.id])
        confirm_roster(round_.id, ConfirmRows(snapshot_ids=result["snapshot_ids"],
            basis_ref="KHOA-2026-TEST"), staff, session)
        assert student.id in confirmed_student_ids(session, round_.id, [student.id])
        tasks = BackgroundTasks()
        activation_request(ActivationRequest(identifier=student_code, email=email), post_request(), tasks, session)
        assert len(tasks.tasks) == 1
        token = make_token(account, "activate")
        revoke_eligibility(round_.id, RevokeStudent(student_id=student.id,
            reason="Synthetic correction", basis_ref="KHOA-2026-CORRECTION"), staff, session)
        with pytest.raises(HTTPException) as revoked:
            activate(LinkPassword(token=token, password="strong-password-123"), post_request(), session)
        assert revoked.value.status_code == 403
        again = import_roster(session, staff, round_.id, rows, "KHOA-2026-TEST-2")
        assert again["new_accounts"] == 0 and again["submitted"] == 1
        confirm_roster(round_.id, ConfirmRows(snapshot_ids=again["snapshot_ids"],
            basis_ref="KHOA-2026-TEST-2"), staff, session)
        activate(LinkPassword(token=token, password="strong-password-123"), post_request(), session)
        assert account.status == "ACTIVE" and account.email_verified_at
        assert verify_password(account.password_hash, "strong-password-123")
        with pytest.raises(HTTPException) as reused:
            activate(LinkPassword(token=token, password="other-password-123"), post_request(), session)
        assert reused.value.status_code == 400
        reset_tasks = BackgroundTasks()
        password_reset_request(EmailRequest(email=email), post_request(), reset_tasks, session)
        assert len(reset_tasks.tasks) == 1
        reset_token = make_token(account, "reset")
        password_reset(LinkPassword(token=reset_token, password="new-password-123456"), post_request(), session)
        assert not verify_password(account.password_hash, "strong-password-123")
        assert verify_password(account.password_hash, "new-password-123456")
        password_change(PasswordChange(current_password="new-password-123456",
            new_password="third-password-123456"), post_request(), account, session)
        assert verify_password(account.password_hash, "third-password-123456")
        round_.state = "CLOSED"
        monkeypatch.setattr("backend.api.roster.mail_delivery_ready", lambda: True)
        correction_tasks = BackgroundTasks()
        correction = correct_student(round_.id, student.id, CorrectStudent(
            student_code=student_code, display_name="Synthetic corrected student",
            email=f"corrected-{suffix}@example.test", class_name="CS-02", major_code="7480201",
            basis_ref="KHOA-2026-CORRECTION", reason="Official email correction"),
            correction_tasks, staff, session)
        assert correction["activation_required"] and correction["activation_sent"]
        assert len(correction_tasks.tasks) == 1
        assert correction_tasks.tasks[0].args[0] is account
        assert account.status == "DISABLED"
        assert not verify_password(account.password_hash, "third-password-123456")
        assert student.class_name == "CS-02" and student.display_name == "Synthetic corrected student"
        recovered_tasks = BackgroundTasks()
        activation_request(ActivationRequest(identifier=student_code, email=account.email),
                           post_request(), recovered_tasks, session)
        assert len(recovered_tasks.tasks) == 1
        revoke_eligibility(round_.id, RevokeStudent(student_id=student.id,
            reason="Synthetic later correction", basis_ref="KHOA-2026-CORRECTION-2"), staff, session)
        assert student.id not in confirmed_student_ids(session, round_.id, [student.id])
    finally:
        session.close()
        outer.rollback()
        conn.close()
        engine.dispose()
