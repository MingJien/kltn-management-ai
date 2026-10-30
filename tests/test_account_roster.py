from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
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
from backend.api.account_admin import (
    AccountChangeReason, StaffEmailCorrection, StudentEmailCorrection, correct_staff_email,
    correct_student_email, disable_account, reissue_link, restore_account,
)
from backend.db.models import entities as m
from backend.services.account_tokens import make_token
from backend.services.passwords import hash_password, verify_password
from backend.services.registration import confirmed_student_ids
from backend.services.roster import import_roster, parse_roster, require_assignment, validate_rows


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


def test_vietnamese_roster_template_imports_and_word_is_rejected():
    template = (Path(__file__).resolve().parents[1] / "frontend" / "public" / "templates"
                / "danh-sach-sinh-vien-kltn-mau.xlsx")
    rows, _ = parse_roster(template.name, template.read_bytes())
    assert len(rows) == 4
    assert rows[0].student_code == "SV-MAU-001"
    assert rows[0].email.endswith("@example.invalid")
    assert rows[0].department_code == "BM-CNTT"
    csv_data = ("MSSV,Họ tên,Email,Mã bộ môn,Lớp,Mã ngành\n"
                "SYN-004,Sinh viên mẫu,sv-mau@example.test,SYN-DEMO-DEP,CNTT-01,7480201\n").encode("utf-8-sig")
    parsed, _ = parse_roster("danh-sach.csv", csv_data)
    assert parsed[0].display_name == "Sinh viên mẫu"
    semicolon_csv = ("Mã số sinh viên;Họ và tên;E-mail;Bộ môn;Tên lớp;Ngành học\n"
                     "SYN-005;Sinh viên thử;sv-thu@example.test;SYN-DEMO-DEP;CNTT-02;7480201\n").encode("utf-8-sig")
    semicolon_rows, _ = parse_roster("danh-sach.csv", semicolon_csv)
    assert semicolon_rows[0].student_code == "SYN-005"
    assert semicolon_rows[0].class_name == "CNTT-02"
    with pytest.raises(HTTPException) as duplicate:
        parse_roster("danh-sach.csv", ("MSSV,student_code,Họ tên,Email,Mã bộ môn,Lớp,Mã ngành\n"
            "SYN-004,SYN-004,Sinh viên mẫu,sv-mau@example.test,SYN-DEMO-DEP,CNTT-01,7480201\n").encode())
    assert duplicate.value.status_code == 422
    with pytest.raises(HTTPException) as word:
        parse_roster("danh-sach.docx", b"Word table")
    assert word.value.status_code == 422


def test_admin_corrects_staff_email_without_creating_a_new_account(monkeypatch):
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
        admin = m.UserAccount(id=uuid4(), external_subject=f"admin-{suffix}",
                              base_role="ADMIN", status="ACTIVE")
        lecturer = m.UserAccount(id=uuid4(), external_subject=f"lecturer-{suffix}",
            base_role="LECTURER", email=f"old-{suffix}@example.test", email_verified_at=now,
            status="ACTIVE", password_hash=hash_password("old-password-123456"))
        manager = m.UserAccount(id=uuid4(), external_subject=f"manager-{suffix}",
                                base_role="LECTURER", status="ACTIVE")
        session.add_all([admin, lecturer, manager])
        session.flush()
        old_reset_link = make_token(lecturer, "reset")
        monkeypatch.setattr("backend.api.account_admin.mail_delivery_ready", lambda: True)
        sent = []
        monkeypatch.setattr("backend.api.account_admin._mail_link",
                            lambda user, purpose: sent.append((user.id, purpose)))
        with pytest.raises(HTTPException) as own_email:
            correct_staff_email(admin.id, StaffEmailCorrection(email=f"admin-{suffix}@example.test",
                basis_ref="KHOA-2026-EMAIL", reason="Try to change own mailbox"), admin, session)
        assert own_email.value.status_code == 409
        with pytest.raises(HTTPException) as not_admin:
            correct_staff_email(lecturer.id, StaffEmailCorrection(
                email=f"new-{suffix}@example.test", basis_ref="KHOA-2026-EMAIL",
                reason="Lecturer lost mailbox access"), manager, session)
        assert not_admin.value.status_code == 403
        corrected = correct_staff_email(lecturer.id, StaffEmailCorrection(
            email=f"new-{suffix}@example.test", basis_ref="KHOA-2026-EMAIL",
            reason="Lecturer lost mailbox access"), admin, session)
        assert corrected["activation_required"] and corrected["activation_sent"]
        assert sent == [(lecturer.id, "activate")]
        assert lecturer.email == f"new-{suffix}@example.test"
        assert lecturer.status == "DISABLED" and not lecturer.email_verified_at
        assert not verify_password(lecturer.password_hash, "old-password-123456")
        with pytest.raises(HTTPException) as invalidated:
            password_reset(LinkPassword(token=old_reset_link, password="new-password-123456"),
                           post_request(), session)
        assert invalidated.value.status_code == 400
        audit = session.scalar(select(m.AuditEvent).where(
            m.AuditEvent.action == "ACCOUNT_EMAIL_CORRECTED",
            m.AuditEvent.resource_id == lecturer.id))
        assert audit.actor_id == admin.id and audit.source_reference == "KHOA-2026-EMAIL"
        assert audit.reason == "Lecturer lost mailbox access"
        assert audit.before_hash != audit.after_hash
        activate(LinkPassword(token=make_token(lecturer, "activate"), password="new-password-123456"),
                 post_request(), session)
        assert lecturer.status == "ACTIVE" and lecturer.email_verified_at
        assert verify_password(lecturer.password_hash, "new-password-123456")
    finally:
        session.close()
        outer.rollback()
        conn.close()
        engine.dispose()


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
        session.add_all([
            m.DepartmentMajor(id=uuid4(), department_id=department.id,
                code="7480201", name="Công nghệ thông tin", active=True),
            m.DepartmentMajor(id=uuid4(), department_id=department.id,
                code="7480101", name="Khoa học máy tính", active=True),
        ])
        session.flush()
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
        second_major, _ = parse_roster("roster.csv", content.replace(b"7480201", b"7480101"))
        assert validate_rows(session, second_major)[department.code].id == department.id
        wrong_major, _ = parse_roster("roster.csv", content.replace(b"7480201", b"7540101"))
        with pytest.raises(HTTPException) as mismatched:
            validate_rows(session, wrong_major)
        assert mismatched.value.status_code == 422
        result = import_roster(session, staff, round_.id, rows, "KHOA-2026-TEST")
        assert result["new_accounts"] == 1 and result["confirmed"] == 1
        student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.student_code == student_code))
        account = session.get(m.UserAccount, student.user_id)
        assert student.class_name == "CS-01" and student.major_code == "7480201"
        assert account.status == "DISABLED" and not account.email_verified_at
        assert account.password_hash.startswith("!")
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
        assert again["new_accounts"] == 0 and again["confirmed"] == 1
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
        monkeypatch.setattr("backend.api.account_admin.mail_delivery_ready", lambda: True)
        sent_links = []
        monkeypatch.setattr("backend.api.account_admin._mail_link", lambda user, purpose: sent_links.append((user.id, purpose)))
        correction = correct_student(round_.id, student.id, CorrectStudent(
            student_code=student_code, display_name="Synthetic corrected student",
            class_name="CS-02", major_code="7480201",
            basis_ref="KHOA-2026-CORRECTION", reason="Official email correction"),
            staff, session)
        assert correction["student_id"] == str(student.id)
        assert account.status == "ACTIVE"
        old_reset_link = make_token(account, "reset")
        manager = m.UserAccount(id=uuid4(), external_subject=f"staff-{suffix}",
            base_role="LECTURER", status="ACTIVE")
        session.add(manager)
        session.flush()
        session.add(m.ResourceAssignment(id=uuid4(), assignment_type="ELIGIBILITY_VERIFIER",
            user_id=manager.id, round_id=round_.id, effective_from=now, state="ACTIVE"))
        session.flush()
        correction_input = StudentEmailCorrection(round_id=round_.id, student_code=student_code,
            email=f"corrected-{suffix}@example.test", basis_ref="KHOA-2026-CORRECTION",
            reason="Official email correction")
        with pytest.raises(HTTPException) as verifier_cannot_edit_email:
            correct_student_email(account.id, correction_input, manager, session)
        assert verifier_cannot_edit_email.value.status_code == 403
        session.add(m.ResourceAssignment(id=uuid4(), assignment_type="ACCOUNT_MANAGER",
            user_id=manager.id, round_id=round_.id, effective_from=now, state="ACTIVE"))
        session.flush()
        corrected = correct_student_email(account.id, StudentEmailCorrection(
            round_id=round_.id, student_code=student_code,
            email=f"corrected-{suffix}@example.test", basis_ref="KHOA-2026-CORRECTION",
            reason="Official email correction"), manager, session)
        assert corrected["activation_required"] and corrected["activation_sent"]
        assert sent_links == [(account.id, "activate")]
        with pytest.raises(HTTPException) as invalidated_link:
            password_reset(LinkPassword(token=old_reset_link, password="another-password-123"),
                post_request(), session)
        assert invalidated_link.value.status_code == 400
        correction_audit = session.scalar(select(m.AuditEvent).where(
            m.AuditEvent.action == "ACCOUNT_EMAIL_CORRECTED", m.AuditEvent.resource_id == account.id))
        assert correction_audit.actor_id == manager.id and correction_audit.before_hash != correction_audit.after_hash
        assert account.status == "DISABLED"
        assert not verify_password(account.password_hash, "third-password-123456")
        assert student.class_name == "CS-02" and student.display_name == "Synthetic corrected student"
        recovered_tasks = BackgroundTasks()
        activation_request(ActivationRequest(identifier=student_code, email=account.email),
                           post_request(), recovered_tasks, session)
        assert len(recovered_tasks.tasks) == 1
        activate(LinkPassword(token=make_token(account, "activate"), password="restored-password-123"),
            post_request(), session)
        issued = reissue_link(account.id, AccountChangeReason(reason="Student requested new reset link"),
            manager, session)
        assert issued == {"link_sent": True, "purpose": "reset"}
        assert sent_links[-1] == (account.id, "reset")
        disable_account(account.id, AccountChangeReason(reason="Faculty temporarily disabled access"), manager, session)
        assert account.status == "DISABLED" and student.user_id == account.id
        restore_account(account.id, AccountChangeReason(reason="Faculty restored access"), manager, session)
        assert account.status == "ACTIVE" and student.user_id == account.id
        revoke_eligibility(round_.id, RevokeStudent(student_id=student.id,
            reason="Synthetic later correction", basis_ref="KHOA-2026-CORRECTION-2"), staff, session)
        assert student.id not in confirmed_student_ids(session, round_.id, [student.id])
    finally:
        session.close()
        outer.rollback()
        conn.close()
        engine.dispose()
