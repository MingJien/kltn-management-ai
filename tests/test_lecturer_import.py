"""Lecturer XLSX provisioning and delivery against real PostgreSQL transactions."""
import hashlib
from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from test_registration import hdr, scenario
from backend.db.models import entities as m
from backend.services.lecturer_roster import HEADERS, create_accounts, parse_file
from backend.services.account_tokens import make_token, token_account

BASE = "/api/v1/admin/lecturers"


def excel(rows, headers=HEADERS):
    book = Workbook()
    sheet = book.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


@pytest.fixture
def setup(scenario, monkeypatch):
    client, users, students, lecturers, topic, session = scenario
    admin = m.UserAccount(id=uuid4(), external_subject="lecturer-import-" + uuid4().hex,
                          base_role="ADMIN", status="ACTIVE")
    session.add(admin)
    session.commit()
    monkeypatch.setenv("AUTH_SESSION_SECRET", "test-lecturer-import-secret-at-least-32-characters")
    sent = []
    monkeypatch.setattr("backend.api.lecturer_import._mail_link", lambda account, purpose: sent.append((account.email, purpose)))
    monkeypatch.setattr("backend.api.lecturer_import.mail_delivery_ready", lambda: True)
    department = session.get(m.Department, topic.department_id)
    suffix = uuid4().hex[:8]
    rows = [(f"IMP-{suffix}-{i}", name, f"imp-{suffix}-{i}@demo.test", department.code)
            for i, name in enumerate(("Lê Quang Huy", "Nguyễn Thu Hà", "Phạm Văn Khang"), 1)]
    headers = {**hdr(admin), "X-File-Name": "giang-vien.xlsx", "Content-Type": "application/octet-stream"}
    return client, users, admin, session, rows, headers, sent


def test_xlsx_parser_rejects_formula_multiple_sheets_and_preserves_zero_code():
    rows, _, errors = parse_file("test.xlsx", excel([("000123", "Nguyễn Văn An", "an@demo.test", "BM-CNTT")]))
    assert rows[0].lecturer_code == "000123" and not errors[2]
    _, _, numeric = parse_file("test.xlsx", excel([(123, "Nguyễn Văn An", "an@demo.test", "BM-CNTT")]))
    assert any("Text" in message for message in numeric[2])
    for name, content in [("test.csv", b"x"), ("test.xlsx", b"invalid"),
        ("test.xlsx", excel([("=2+2", "Nguyễn Văn An", "an@demo.test", "BM-CNTT")]))]:
        with pytest.raises(HTTPException):
            parse_file(name, content)
    book = Workbook()
    book.create_sheet("extra")
    stream = BytesIO(); book.save(stream)
    with pytest.raises(HTTPException):
        parse_file("test.xlsx", stream.getvalue())


def test_preview_create_is_atomic_and_sends_no_mail(setup):
    client, _, admin, session, rows, headers, sent = setup
    data = excel(rows)
    before = session.scalar(select(func.count()).select_from(m.UserAccount))
    checked = client.post(BASE + "/import/preview", headers=headers, content=data)
    assert checked.status_code == 200, checked.text
    result = checked.json()
    assert result["can_import"] and result["valid_count"] == 3
    assert session.scalar(select(func.count()).select_from(m.UserAccount)) == before and not sent
    changed = client.post(BASE + "/import", headers={**headers, "X-Preview-SHA256": "bad"}, content=data)
    assert changed.status_code == 409
    created = client.post(BASE + "/import", headers={**headers, "X-Preview-SHA256": result["sha256"]}, content=data)
    assert created.status_code == 201, created.text
    assert created.json()["created_count"] == 3 and created.json()["invitations_sent"] == 0 and not sent
    ids = [UUID(value) for value in created.json()["user_ids"]]
    accounts = session.scalars(select(m.UserAccount).where(m.UserAccount.id.in_(ids))).all()
    assert len(accounts) == 3 and all(row.base_role == "LECTURER" and row.status == "DISABLED" and row.email_verified_at is None for row in accounts)
    assert session.scalar(select(func.count()).select_from(m.AuditEvent).where(m.AuditEvent.action == "LECTURER_IMPORTED", m.AuditEvent.resource_id.in_(ids))) == 3
    again = client.post(BASE + "/import", headers={**headers, "X-Preview-SHA256": result["sha256"]}, content=data)
    assert again.status_code == 409
    assert session.scalar(select(func.count()).select_from(m.UserAccount)) == before + 3


def test_preview_reports_all_duplicate_and_catalog_errors_no_silent_update(setup):
    client, _, _, session, rows, headers, sent = setup
    duplicate = [rows[0], (rows[0][0].lower(), "Tên khác", rows[0][2].upper(), "UNKNOWN"),
                 (rows[2][0], "", "bad-email", rows[2][3])]
    result = client.post(BASE + "/import/preview", headers=headers, content=excel(duplicate)).json()
    assert not result["can_import"] and all(row["errors"] for row in result["rows"])
    assert any("trùng trong tệp" in message for message in result["rows"][0]["errors"])
    assert any("bộ môn" in message for message in result["rows"][1]["errors"])
    assert len(result["rows"][2]["errors"]) >= 2 and not sent


def test_import_rolls_back_first_account_when_second_insert_fails(setup, monkeypatch):
    _, _, admin, session, rows, _, _ = setup
    data = excel(rows)
    parsed, digest, errors = parse_file("test.xlsx", data)
    original = session.flush

    def failing_flush(*args, **kwargs):
        if any(isinstance(row, m.UserAccount) and row.email == rows[1][2] for row in session.new):
            raise IntegrityError("synthetic concurrency collision", {}, Exception("duplicate"))
        return original(*args, **kwargs)

    monkeypatch.setattr(session, "flush", failing_flush)
    with pytest.raises(HTTPException) as failure:
        create_accounts(session, admin, parsed, digest, errors)
    assert failure.value.status_code == 409
    assert session.scalar(select(func.count()).select_from(m.UserAccount).where(m.UserAccount.email.in_([row[2] for row in rows]))) == 0


def test_only_admin_can_preview_create_list_download_or_send(setup):
    client, users, _, _, rows, headers, sent = setup
    data = excel(rows)
    for user in (users[0], users[3], users[4]):
        actor = {**headers, **hdr(user), "X-Preview-SHA256": hashlib.sha256(data).hexdigest()}
        assert client.get(BASE, headers=actor).status_code == 403
        assert client.get(BASE + "/import-template", headers=actor).status_code == 403
        assert client.post(BASE + "/import/preview", headers=actor, content=data).status_code == 403
        assert client.post(BASE + "/import", headers=actor, content=data).status_code == 403
        assert client.post(BASE + f"/{uuid4()}/activation-link", headers=actor).status_code == 403
    assert not sent


def test_send_per_account_cooldown_failure_persistence_and_activation_guard(setup, monkeypatch):
    for name in ("KLTN_SMTP_HOST", "KLTN_MAIL_FROM", "KLTN_SMTP_USER", "KLTN_SMTP_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    client, _, admin, session, rows, headers, sent = setup
    data = excel(rows)
    made = client.post(BASE + "/import", headers={**headers, "X-Preview-SHA256": hashlib.sha256(data).hexdigest()}, content=data)
    ids = made.json()["user_ids"]
    account = session.get(m.UserAccount, UUID(ids[0]))
    old_token = make_token(account, "activate")
    response = client.post(BASE + f"/{ids[0]}/activation-link", headers=hdr(admin))
    assert response.status_code == 200 and response.json()["sent"] and sent == [(rows[0][2], "activate")]
    session.refresh(account)
    assert token_account(old_token, "activate")[2] != account.row_version
    assert client.post(BASE + f"/{ids[0]}/activation-link", headers=hdr(admin)).status_code == 429
    def fail_mail(*_):
        raise RuntimeError("Synthetic SMTP failure - must not expose transport details")
    monkeypatch.setattr("backend.api.lecturer_import._mail_link", fail_mail)
    failed = client.post(BASE + f"/{ids[1]}/activation-link", headers=hdr(admin))
    assert failed.status_code == 200 and not failed.json()["sent"]
    directory = {row["user_id"]: row for row in client.get(BASE, headers=hdr(admin)).json()["items"]}
    assert directory[ids[0]]["mail_status"] == "SENT"
    assert directory[ids[0]]["delivery_mode"] == "development_outbox"
    assert directory[ids[1]]["mail_status"] == "FAILED"
    assert directory[ids[2]]["mail_status"] == "NOT_RECORDED"
    assert not directory[ids[0]]["can_send"]
    monkeypatch.setenv("KLTN_SMTP_HOST", "configured-later.test")
    monkeypatch.setenv("KLTN_MAIL_FROM", "system@configured-later.test")
    changed_config = client.get(BASE, headers=hdr(admin)).json()
    assert changed_config["delivery_mode"] == "smtp"
    assert next(row for row in changed_config["items"] if row["user_id"] == ids[0])["delivery_mode"] == "development_outbox"
    account.status = "ACTIVE"; account.email_verified_at = datetime.now(timezone.utc); session.commit()
    assert client.post(BASE + f"/{ids[0]}/activation-link", headers=hdr(admin)).status_code == 409
    locked = session.get(m.UserAccount, UUID(ids[2])); locked.status = "LOCKED"; session.commit()
    assert client.post(BASE + f"/{ids[2]}/activation-link", headers=hdr(admin)).status_code == 409


def test_download_template_parses_and_no_mail_when_delivery_not_configured(setup, monkeypatch):
    client, _, admin, _, rows, headers, sent = setup
    template = client.get(BASE + "/import-template", headers=hdr(admin))
    assert template.status_code == 200
    parsed, _, errors = parse_file("template.xlsx", template.content)
    assert len(parsed) == 3 and not any(errors.values())
    data = excel(rows)
    made = client.post(BASE + "/import", headers={**headers, "X-Preview-SHA256": hashlib.sha256(data).hexdigest()}, content=data)
    monkeypatch.setattr("backend.api.lecturer_import.mail_delivery_ready", lambda: False)
    assert client.post(BASE + f"/{made.json()['user_ids'][0]}/activation-link", headers=hdr(admin)).status_code == 503
    assert not sent


def test_existing_student_email_and_lecturer_code_cannot_be_reassigned(setup):
    client, users, admin, session, rows, headers, sent = setup
    from backend.services.passwords import unusable_password
    student = users[0]
    student.email = rows[0][2]; student.password_hash = unusable_password()
    profile = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == users[3].id))
    session.commit()
    data = excel([rows[0], (profile.lecturer_code.lower(), rows[1][1], rows[1][2], rows[1][3])])
    checked = client.post(BASE + "/import/preview", headers=headers, content=data).json()
    assert not checked["can_import"] and all(row["errors"] for row in checked["rows"])
    response = client.post(BASE + "/import", headers={**headers, "X-Preview-SHA256": checked["sha256"]}, content=data)
    assert response.status_code == 409
    session.refresh(student)
    assert student.base_role == "STUDENT" and not sent
