from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from backend.api.dependencies import get_session
from backend.api.main import app
from backend.db.models import entities as m
from backend.db.validate_schema import load_env


@pytest.fixture
def scenario(monkeypatch):
    load_env()
    if not os.getenv("DATABASE_URL"):
        pytest.skip("Local PostgreSQL configuration unavailable")
    monkeypatch.setenv("KLTN_ENV", "test")
    monkeypatch.setenv("KLTN_DEV_AUTH", "true")
    engine = create_engine(os.environ["DATABASE_URL"])
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    now = datetime.now(timezone.utc)
    faculty = m.Faculty(id=uuid4(), code="T-"+uuid4().hex[:10], name="Synthetic faculty")
    department = m.Department(id=uuid4(), faculty_id=faculty.id, code="T-"+uuid4().hex[:10], name="Synthetic department")
    year = m.AcademicYear(id=uuid4(), code="T-"+uuid4().hex[:10], starts_on=date(2026, 9, 1), ends_on=date(2027, 8, 31), state="ACTIVE")
    round_ = m.ThesisRound(id=uuid4(), academic_year_id=year.id, code="TEST", round_type="MAIN",
                           opens_at=now-timedelta(days=1), closes_at=now+timedelta(days=7), state="OPEN")
    users = [m.UserAccount(id=uuid4(), external_subject="test-"+uuid4().hex, base_role="STUDENT" if i<3 else "LECTURER", status="ACTIVE") for i in range(6)]
    students = [m.StudentProfile(id=uuid4(), user_id=users[i].id, student_code="T-"+uuid4().hex[:10], department_id=department.id, display_name="Synthetic student") for i in range(3)]
    lecturers = [m.LecturerProfile(id=uuid4(), user_id=users[i+3].id, lecturer_code="T-"+uuid4().hex[:10], department_id=department.id, display_name="Synthetic lecturer") for i in range(3)]
    position = session.scalar(select(m.OrganizationalPosition).where(
        m.OrganizationalPosition.code == "DEPARTMENT_HEAD"
    ))
    if position is None:
        position = m.OrganizationalPosition(id=uuid4(), code="DEPARTMENT_HEAD", name="Department head")
    head_assignment = m.PositionAssignment(id=uuid4(), lecturer_id=lecturers[1].id, position_id=position.id,
                                           department_id=department.id, effective_from=now-timedelta(days=1), state="ACTIVE")
    topic = m.Topic(id=uuid4(), round_id=round_.id, department_id=department.id,
                    proposer_user_id=users[3].id, proposer_type="LECTURER",
                    code="TEST-"+uuid4().hex, current_title="Synthetic topic", max_students=3, state="APPROVED")
    session.add_all([faculty, year, *users])
    session.flush()
    session.add_all([department, round_, *students, *lecturers, position])
    session.flush()
    session.add_all([head_assignment, topic])
    session.flush()
    for student in students:
        session.add(m.EligibilitySnapshot(
            id=uuid4(), student_id=student.id, round_id=round_.id, version=1,
            passed_credit_ratio=0.8, gpa_4=3.0,
            evidence_ref="SYNTHETIC",
            captured_at=now, confirmed_by=users[4].id, confirmed_at=now, state="CONFIRMED",
        ))
    session.flush()

    def same_session():
        yield session
    app.dependency_overrides[get_session] = same_session
    try:
        yield TestClient(app), users, students, lecturers, topic, session
    finally:
        app.dependency_overrides.clear()
        session.close()
        outer.rollback()
        connection.close()
        engine.dispose()


def hdr(user):
    return {"X-Dev-User-Id": str(user.id)}


def test_registration_notice_is_private_and_read_per_account(scenario):
    client, users, _, _, topic, _ = scenario
    created = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),
                          json={"topic_id": str(topic.id)}).json()
    assert client.get("/api/v1/notifications", headers=hdr(users[3])).json()["unread_count"] == 0
    sent = client.post(f"/api/v1/topic-registrations/{created['id']}/submit",
                       headers={**hdr(users[0]), "If-Match": str(created["row_version"])})
    assert sent.status_code == 200, sent.text
    inbox = client.get("/api/v1/notifications", headers=hdr(users[3])).json()
    assert inbox["unread_count"] == 1
    notice = inbox["items"][0]
    assert topic.current_title in notice["message"]
    assert notice["url"] == f"/registrations?focus={created['id']}"
    path = f"/api/v1/notifications/{notice['id']}/read"
    assert client.post(path, headers=hdr(users[4])).status_code == 404
    assert client.post(path, headers=hdr(users[3])).status_code == 204
    assert client.post(path, headers=hdr(users[3])).status_code == 204
    seen = client.get("/api/v1/notifications", headers=hdr(users[3])).json()
    assert seen["unread_count"] == 0 and seen["items"][0]["read_at"]


def test_student_proposal_notice_moves_to_confirmed_lecturer(scenario):
    client, users, _, lecturers, topic, _ = scenario
    created = client.post("/api/v1/student-proposals", headers=hdr(users[0]), json={
        "round_id": str(topic.round_id), "title": "Student proposed research topic",
        "max_students": 1, "receiving_lecturer_id": str(lecturers[0].id),
    })
    assert created.status_code == 201, created.text
    reg = created.json()
    sent = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit",
                       headers={**hdr(users[0]), "If-Match": str(reg["row_version"])})
    assert sent.status_code == 200, sent.text
    suggested = client.get("/api/v1/topics?view=suggested", headers=hdr(users[3]))
    assert suggested.status_code == 200
    assert any(row["id"] == reg["topic_id"] for row in suggested.json())
    assert client.get(f"/api/v1/topics/{reg['topic_id']}", headers=hdr(users[3])).status_code == 200
    assert client.get(f"/api/v1/topics/{reg['topic_id']}", headers=hdr(users[5])).status_code == 404
    assert client.get("/api/v1/topics?view=suggested", headers=hdr(users[0])).status_code == 403
    first = client.get("/api/v1/notifications", headers=hdr(users[3])).json()
    assert first["unread_count"] == 1 and "chờ bộ môn duyệt" in first["items"][0]["message"]
    proposed = client.get(f"/api/v1/topics/{reg['topic_id']}", headers=hdr(users[4])).json()
    approved = client.post(f"/api/v1/topics/{reg['topic_id']}/department-decision",
        headers={**hdr(users[4]), "If-Match": str(proposed["row_version"])},
        json={"decision": "APPROVE", "receiving_lecturer_id": str(lecturers[2].id)})
    assert approved.status_code == 200, approved.text
    assert all(row["id"] != reg["topic_id"] for row in
        client.get("/api/v1/topics?view=suggested", headers=hdr(users[3])).json())
    assert any(row["id"] == reg["topic_id"] for row in
        client.get("/api/v1/topics?view=suggested", headers=hdr(users[5])).json())
    assert client.get("/api/v1/notifications", headers=hdr(users[3])).json()["items"] == []
    replacement = client.get("/api/v1/notifications", headers=hdr(users[5])).json()
    assert replacement["unread_count"] == 1
    assert "Mời bạn xét đăng ký" in replacement["items"][0]["message"]


def test_special_eligibility_decision_requires_authorized_verifier_and_official_reference(scenario):
    client, users, students, _, topic, session = scenario
    session.add(m.EligibilitySnapshot(id=uuid4(), student_id=students[0].id,
        round_id=topic.round_id, version=2, passed_credit_ratio=0.6, gpa_4=2.0,
        evidence_ref="SYNTHETIC_SOURCE", captured_at=datetime.now(timezone.utc), state="SUBMITTED"))
    session.add(m.ResourceAssignment(id=uuid4(), user_id=users[4].id,
        round_id=topic.round_id, assignment_type="ELIGIBILITY_VERIFIER",
        effective_from=datetime.now(timezone.utc)-timedelta(days=1), state="ACTIVE"))
    session.flush()
    path = f"/api/v1/rounds/{topic.round_id}/roster/special-decision"
    data = {"student_id":str(students[0].id), "official_ref":"SYN-RECTOR-001",
        "reason":"Synthetic official exception to clause 2", "clause_1_verified":True}
    assert client.post(path, headers=hdr(users[0]), json=data).status_code == 403
    assert client.post(path, headers=hdr(users[4]), json={**data,"clause_1_verified":False}).status_code == 422
    result = client.post(path, headers=hdr(users[4]), json=data)
    assert result.status_code == 200, result.text
    latest = session.scalar(select(m.EligibilitySnapshot).where(
        m.EligibilitySnapshot.student_id == students[0].id,
        m.EligibilitySnapshot.round_id == topic.round_id).order_by(m.EligibilitySnapshot.version.desc()))
    assert latest.version == 3 and latest.state == "CONFIRMED"
    assert latest.confirmed_by == users[4].id and latest.evidence_ref == "SYN-RECTOR-001"
    assert session.scalar(select(m.AuditEvent.id).where(
        m.AuditEvent.action == "ELIGIBILITY_SPECIAL_DECISION_RECORDED",
        m.AuditEvent.resource_id == latest.id)) is not None


def test_topic_to_lecturer_acceptance(scenario):
    client, users, students, lecturers, _, session = scenario
    round_id = session.scalar(select(m.ThesisRound.id).where(m.ThesisRound.code == "TEST"))
    created = client.post("/api/v1/topics", headers=hdr(users[3]), json={
        "round_id": str(round_id), "title": "Synthetic new topic", "description": "Prototype flow", "max_students": 2,
    })
    assert created.status_code == 201, created.text
    topic = created.json()
    assert topic["state"] == "DRAFT"
    assert client.get("/api/v1/topics", headers=hdr(users[0])).json() == [
        row for row in client.get("/api/v1/topics", headers=hdr(users[0])).json()
        if row["id"] != topic["id"]
    ]
    assert client.post(f"/api/v1/topics/{topic['id']}/department-decision",
        headers={**hdr(users[4]), "If-Match": str(topic["row_version"])},
        json={"decision": "APPROVE"}).status_code == 409
    submitted = client.post(f"/api/v1/topics/{topic['id']}/submit",
        headers={**hdr(users[3]), "If-Match": str(topic["row_version"])}).json()
    assert submitted["state"] == "SUBMITTED"
    assert client.post(f"/api/v1/topics/{topic['id']}/department-decision",
        headers={**hdr(users[3]), "If-Match": str(submitted["row_version"])},
        json={"decision": "APPROVE"}).status_code == 403
    returned = client.post(f"/api/v1/topics/{topic['id']}/department-decision",
        headers={**hdr(users[4]), "If-Match": str(submitted["row_version"])},
        json={"decision": "RETURN", "reason": "Please clarify the scope"})
    assert returned.status_code == 200, returned.text
    assert returned.json()["decision_reason"] == "Please clarify the scope"
    revised = client.patch(f"/api/v1/topics/{topic['id']}",
        headers={**hdr(users[3]), "If-Match": str(returned.json()["row_version"])},
        json={"title": "Synthetic revised topic"})
    assert revised.status_code == 200, revised.text
    assert client.patch(f"/api/v1/topics/{topic['id']}",
        headers={**hdr(users[3]), "If-Match": str(returned.json()["row_version"])},
        json={"description": "Stale update"}).status_code == 409
    submitted = client.post(f"/api/v1/topics/{topic['id']}/submit",
        headers={**hdr(users[3]), "If-Match": str(revised.json()["row_version"])}).json()
    approved = client.post(f"/api/v1/topics/{topic['id']}/department-decision",
        headers={**hdr(users[4]), "If-Match": str(submitted["row_version"])},
        json={"decision": "APPROVE", "revised_title": "Synthetic approved topic"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "APPROVED"
    versions = session.scalars(select(m.TopicTitleVersion).where(m.TopicTitleVersion.topic_id == topic["id"])
                               .order_by(m.TopicTitleVersion.version_no)).all()
    assert [item.title for item in versions] == [
        "Synthetic new topic", "Synthetic revised topic", "Synthetic approved topic",
    ]
    reg = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={"topic_id": topic["id"]})
    assert reg.status_code == 201, reg.text
    joined = client.post("/api/v1/topic-registrations", headers=hdr(users[1]), json={"topic_id": topic["id"]})
    assert joined.status_code == 201 and joined.json()["id"] == reg.json()["id"]
    sent = client.post(f"/api/v1/topic-registrations/{reg.json()['id']}/submit", headers=hdr(users[0]))
    assert sent.status_code == 200, sent.text
    accepted = client.post(f"/api/v1/topic-registrations/{reg.json()['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(sent.json()["row_version"])},
        json={"decision": "ACCEPT"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["state"] == "FINALIZED"
    assert accepted.json()["thesis_id"]
    advisor = session.scalar(select(m.AdvisorAssignment).where(
        m.AdvisorAssignment.thesis_id == accepted.json()["thesis_id"]))
    assert advisor.lecturer_id == lecturers[0].id and advisor.assigned_by == users[3].id


def test_admin_can_create_and_control_round_without_new_schema(scenario):
    client, users, *_ = scenario
    users[5].base_role = "ADMIN"
    payload = {
        "academic_year_code": "2400-2401", "year_starts_on": "2400-09-01",
        "year_ends_on": "2401-08-31", "code": "TEST-ROUND",
        "round_type": "MAIN", "opens_at": "2400-09-20T08:00:00+07:00",
        "closes_at": "2400-10-20T17:00:00+07:00", "basis_ref": "SYNTHETIC PLAN",
    }
    assert client.post("/api/v1/admin/rounds", headers=hdr(users[3]), json=payload).status_code == 403
    created = client.post("/api/v1/admin/rounds", headers=hdr(users[5]), json=payload)
    assert created.status_code == 201, created.text
    round_id = created.json()["id"]
    assert created.json()["state"] == "DRAFT"
    assert client.post("/api/v1/admin/rounds", headers=hdr(users[5]), json=payload).status_code == 409
    edited = client.patch(f"/api/v1/admin/rounds/{round_id}/schedule",
        headers={**hdr(users[5]), "If-Match": "1"},
        json={"code": "TEST-ROUND-REVISED", "round_type": "MAIN",
              "opens_at": payload["opens_at"], "closes_at": "2400-10-25T17:00:00+07:00",
              "reason": "SYNTHETIC CORRECTION"})
    assert edited.status_code == 200, edited.text
    opened = client.patch(f"/api/v1/admin/rounds/{round_id}",
        headers={**hdr(users[5]), "If-Match": str(edited.json()["row_version"])},
        json={"state": "OPEN", "reason": "SYNTHETIC PLAN"})
    assert opened.status_code == 200, opened.text
    assert opened.json()["state"] == "OPEN"
    assert client.patch(f"/api/v1/admin/rounds/{round_id}/schedule",
        headers={**hdr(users[5]), "If-Match": str(opened.json()["row_version"])},
        json={"code": "NOT-ALLOWED", "round_type": "MAIN",
              "opens_at": payload["opens_at"], "closes_at": payload["closes_at"],
              "reason": "SYNTHETIC CORRECTION"}).status_code == 409
    assert client.patch(f"/api/v1/admin/rounds/{round_id}",
        headers={**hdr(users[5]), "If-Match": "1"},
        json={"state": "CLOSED", "reason": "SYNTHETIC CLOSE"}).status_code == 409
    closed = client.patch(f"/api/v1/admin/rounds/{round_id}",
        headers={**hdr(users[5]), "If-Match": str(opened.json()["row_version"])},
        json={"state": "CLOSED", "reason": "SYNTHETIC CLOSE"})
    assert closed.status_code == 200 and closed.json()["state"] == "CLOSED"


def test_admin_can_assign_round_progress_coordinator_to_lecturer(scenario):
    client, users, students, _, topic, _ = scenario
    admin = users[5]
    admin.base_role = "ADMIN"
    payload = {"round_id": str(topic.round_id), "user_id": str(users[4].id),
        "assignment_type": "KLTN_COORDINATOR", "basis_ref": "SYNTHETIC ROUND COORDINATION"}
    granted = client.post("/api/v1/admin/round-assignments", headers=hdr(admin), json=payload)
    assert granted.status_code == 201, granted.text
    assignments = client.get("/api/v1/admin/round-assignments", headers=hdr(admin)).json()
    assert any(row["id"] == granted.json()["assignment_id"] and
        row["assignment_type"] == "KLTN_COORDINATOR" for row in assignments)
    mine = client.get("/api/v1/me/round-assignments", headers=hdr(users[4])).json()
    assert any(row["assignment_type"] == "KLTN_COORDINATOR" and
        row["round_id"] == str(topic.round_id) for row in mine)
    invalid = client.post("/api/v1/admin/round-assignments", headers=hdr(admin), json={**payload,
        "user_id": str(users[0].id)})
    assert invalid.status_code == 422
    revoked = client.post(f"/api/v1/admin/round-assignments/{granted.json()['assignment_id']}/revoke",
        headers=hdr(admin), json={"reason": "Synthetic test completed"})
    assert revoked.status_code == 204


def test_lecturer_cannot_accept_after_eligibility_is_revoked(scenario):
    client, users, students, _, topic, session = scenario
    registered = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),
        json={"topic_id": str(topic.id)})
    assert registered.status_code == 201, registered.text
    submitted = client.post(f"/api/v1/topic-registrations/{registered.json()['id']}/submit",
        headers=hdr(users[0]))
    assert submitted.status_code == 200, submitted.text
    session.add(m.EligibilitySnapshot(id=uuid4(), student_id=students[0].id,
        round_id=topic.round_id, version=2, captured_at=datetime.now(timezone.utc),
        confirmed_by=users[4].id, confirmed_at=datetime.now(timezone.utc),
        evidence_ref="SYNTHETIC REVOKE", state="REJECTED"))
    session.flush()
    blocked = client.post(f"/api/v1/topic-registrations/{registered.json()['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(submitted.json()["row_version"])}, json={"decision": "ACCEPT"})
    assert blocked.status_code == 409
    assert session.scalar(select(m.Thesis.id).where(m.Thesis.registration_id == registered.json()["id"])) is None
    assert session.get(m.TopicRegistration, registered.json()["id"]).state == "SUBMITTED"


def test_acceptance_rolls_back_thesis_if_primary_advisor_insert_fails(scenario):
    from backend.api.schemas import LecturerDecision
    from backend.services.registration import lecturer_decision

    _, users, students, _, topic, session = scenario
    registered = session.scalar(select(m.TopicRegistration).where(m.TopicRegistration.topic_id == topic.id))
    if registered is None:
        created = session  # Keep setup inside the test transaction.
        from backend.api.schemas import RegistrationCreate
        from backend.services.registration import create_registration, submit_registration
        response = create_registration(created, users[0], RegistrationCreate(
            topic_id=topic.id, member_student_ids=[students[0].id], confirm_creator=True))
        submitted = submit_registration(created, users[0], response.id)
        registration_id, version = response.id, submitted.row_version
    else:
        registration_id, version = registered.id, registered.row_version
    if session.get(m.TopicRegistration, registration_id).state != "SUBMITTED":
        from backend.services.registration import submit_registration
        submitted = submit_registration(session, users[0], registration_id)
        version = submitted.row_version

    def fail_primary_advisor_flush(target_session, _flush_context, _instances):
        if any(isinstance(item, m.AdvisorAssignment) for item in target_session.new):
            raise RuntimeError("Injected primary advisor insert failure")

    event.listen(session, "before_flush", fail_primary_advisor_flush)
    try:
        with pytest.raises(RuntimeError, match="Injected primary advisor insert failure"):
            lecturer_decision(session, users[3], registration_id,
                LecturerDecision(decision="ACCEPT"), version)
    finally:
        event.remove(session, "before_flush", fail_primary_advisor_flush)
    assert session.scalar(select(m.Thesis.id).where(m.Thesis.registration_id == registration_id)) is None
    assert session.get(m.TopicRegistration, registration_id).state == "SUBMITTED"
    assert session.get(m.Topic, topic.id).state == "APPROVED"


def test_email_login_and_session_access(scenario, monkeypatch):
    from backend.services.passwords import hash_password

    client, users, *_ , session = scenario
    user = users[0]
    user.email = "student@demo.kltn.invalid"
    user.password_hash = hash_password("correct-demo-password")
    user.email_verified_at = datetime.now(timezone.utc)
    session.flush()
    monkeypatch.setenv("KLTN_DEV_AUTH", "false")
    wrong = client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "incorrect-password",
    })
    assert wrong.status_code == 401
    signed_in = client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "correct-demo-password",
    })
    assert signed_in.status_code == 204, signed_in.text
    context = client.get("/api/v1/me/context").json()
    assert context["user_id"] == str(user.id)
    token = context["csrf_token"]
    assert token
    trusted_origin = {"Origin": "http://localhost:5173"}
    assert client.post("/api/v1/topic-registrations", json={"topic_id": str(scenario[4].id)},
        headers=trusted_origin).status_code == 403
    assert client.post("/api/v1/topic-registrations", json={"topic_id": str(scenario[4].id)},
        headers={**trusted_origin, "X-CSRF-Token": "wrong"}).status_code == 403
    created = client.post("/api/v1/topic-registrations", json={"topic_id": str(scenario[4].id)},
        headers={**trusted_origin, "X-CSRF-Token": token})
    assert created.status_code == 201, created.text
    assert client.post("/api/v1/auth/logout", headers=trusted_origin).status_code == 403
    assert client.post("/api/v1/auth/logout",
        headers={**trusted_origin, "X-CSRF-Token": token}).status_code == 204
    assert client.get("/api/v1/me/context").status_code == 401


def test_local_demo_login_uses_only_seeded_identity_and_real_session(scenario, monkeypatch):
    from backend.api import auth

    client, users, *_ = scenario
    user = users[0]
    monkeypatch.setattr(auth, "_demo_user", lambda _session, key: user if key == "sv1" else None)
    monkeypatch.setenv("KLTN_ENV", "development")
    monkeypatch.setenv("KLTN_DEMO_MODE", "true")
    monkeypatch.setenv("KLTN_DEV_AUTH", "false")
    origin = {"Origin": "http://127.0.0.1:5173"}

    with TestClient(app, client=("127.0.0.1", 53001)) as local:
        accounts = local.get("/api/v1/auth/demo-accounts", headers=origin)
        assert accounts.status_code == 200
        assert [item["key"] for item in accounts.json()] == ["sv1"]
        assert local.post("/api/v1/auth/demo-login", json={"key": "admin"}, headers=origin).status_code == 422
        assert local.post("/api/v1/auth/demo-login", json={"key": "sv1"},
            headers={"Origin": "https://untrusted.example"}).status_code == 403
        signed_in = local.post("/api/v1/auth/demo-login", json={"key": "sv1"}, headers=origin)
        assert signed_in.status_code == 204
        context = local.get("/api/v1/me/context", headers=origin).json()
        assert context["user_id"] == str(user.id)
        assert context["base_role"] == "STUDENT" and context["csrf_token"]
        assert local.post("/api/v1/auth/logout", headers={**origin,
            "X-CSRF-Token": context["csrf_token"]}).status_code == 204
        assert local.get("/api/v1/me/context", headers=origin).status_code == 401
        monkeypatch.setenv("KLTN_ENV", "production")
        assert local.get("/api/v1/auth/demo-accounts", headers=origin).status_code == 404

    monkeypatch.setenv("KLTN_ENV", "development")
    with TestClient(app, client=("192.0.2.15", 53002)) as remote:
        assert remote.get("/api/v1/auth/demo-accounts", headers=origin).status_code == 404
    monkeypatch.setenv("KLTN_DEMO_MODE", "false")
    assert client.get("/api/v1/auth/demo-accounts", headers=origin).status_code == 404


def test_registration_vertical_slice(scenario):
    client, users, students, lecturers, topic, session = scenario
    reg = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={"topic_id":str(topic.id)}).json()
    assert reg["state"] == "DRAFT" and reg["members"][0]["consent_status"] == "ACCEPTED"
    assert client.get("/api/v1/topic-registrations", headers=hdr(users[3])).json() == []
    assert client.get(f"/api/v1/topic-registrations/{reg['id']}", headers=hdr(users[3])).status_code == 404
    for user in users[1:3]:
        joined = client.post("/api/v1/topic-registrations", headers=hdr(user), json={"topic_id":str(topic.id)})
        assert joined.status_code == 201 and joined.json()["id"] == reg["id"]
    group = client.get(f"/api/v1/topic-registrations/{reg['id']}", headers=hdr(users[0])).json()
    assert len(group["members"]) == 3 and all(m["consent_status"] == "ACCEPTED" for m in group["members"])
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[1])).status_code == 403
    assert client.post("/api/v1/topic-registrations", headers=hdr(users[3]), json={"topic_id":str(topic.id)}).status_code == 403
    submitted = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0])).json()
    outsider = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[5]),"If-Match":str(submitted["row_version"])},json={"decision":"ACCEPT"})
    assert outsider.status_code == 403
    accepted = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]),"If-Match":str(submitted["row_version"])},json={"decision":"ACCEPT"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["state"] == "FINALIZED"
    thesis_id = accepted.json()["thesis_id"]
    assert thesis_id
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/department-finalization",
        headers={**hdr(users[4]),"If-Match":str(accepted.json()["row_version"])}).status_code == 404
    assert len(session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis_id)).all()) == 3
    advisor = session.scalar(select(m.AdvisorAssignment).where(m.AdvisorAssignment.thesis_id == thesis_id))
    assert advisor.lecturer_id == lecturers[0].id
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]),"If-Match":str(accepted.json()["row_version"])},
        json={"decision":"ACCEPT"}).status_code == 409


def test_dev_identity_fail_closed(scenario, monkeypatch):
    client, users, *_ = scenario
    monkeypatch.setenv("KLTN_ENV", "production")
    assert client.get("/api/v1/me/context", headers=hdr(users[0])).status_code == 401


def test_rejection_releases_students_for_new_registration(scenario):
    client, users, students, _, topic, session = scenario
    members = [str(students[0].id)]
    created = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(topic.id), "member_student_ids": members,
    })
    assert created.status_code == 201, created.text
    reg = created.json()
    submitted = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0]))
    assert submitted.status_code == 200
    rejected = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(submitted.json()["row_version"])},
        json={"decision": "REJECT", "reason": "Synthetic rejection"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["state"] == "LECTURER_REJECTED"
    assert rejected.json()["member_student_ids"] == members
    second = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(topic.id), "member_student_ids": members,
    })
    assert second.status_code == 201, second.text


def test_student_withdraws_submitted_registration_and_can_choose_another_topic(scenario):
    client, users, students, _, topic, session = scenario
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),
        json={"topic_id": str(topic.id)}).json()
    sent = client.post(f"/api/v1/topic-registrations/{made['id']}/submit", headers=hdr(users[0])).json()
    withdrawn = client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[0]))
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["state"] == "CANCELLED"
    assert withdrawn.json()["members"][0]["active"] is False
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[0])).status_code == 409
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(sent["row_version"])},
        json={"decision": "ACCEPT"}).status_code == 409
    other = m.Topic(id=uuid4(), round_id=topic.round_id, department_id=topic.department_id,
        proposer_user_id=users[3].id, proposer_type="LECTURER", code="TEST-"+uuid4().hex,
        current_title="Other synthetic topic", max_students=1, state="APPROVED")
    session.add(other)
    session.flush()
    second = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),
        json={"topic_id": str(other.id)})
    assert second.status_code == 201, second.text
    assert session.scalar(select(m.AuditEvent.id).where(
        m.AuditEvent.resource_id == made["id"],
        m.AuditEvent.action == "REGISTRATION_MEMBER_WITHDREW")) is not None


def test_group_member_withdraws_without_cancelling_other_students(scenario):
    client, users, students, _, topic, session = scenario
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),
        json={"topic_id": str(topic.id)}).json()
    client.post("/api/v1/topic-registrations", headers=hdr(users[1]),
        json={"topic_id": str(topic.id)})
    sent = client.post(f"/api/v1/topic-registrations/{made['id']}/submit", headers=hdr(users[0])).json()
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[2])).status_code == 404
    withdrawn = client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[0]))
    assert withdrawn.status_code == 200, withdrawn.text
    row = withdrawn.json()
    assert row["state"] == "SUBMITTED" and row["row_version"] > sent["row_version"]
    member_states = {member["student_id"]: (member["active"], member["is_coordinator"])
                     for member in row["members"]}
    assert member_states == {str(students[0].id): (False, False),
                             str(students[1].id): (True, True)}
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(sent["row_version"])},
        json={"decision": "ACCEPT"}).status_code == 409
    accepted = client.post(f"/api/v1/topic-registrations/{made['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(row["row_version"])},
        json={"decision": "ACCEPT"})
    assert accepted.status_code == 200, accepted.text
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[1])).status_code == 409


def test_withdrawn_student_can_rejoin_same_pending_group(scenario):
    client, users, students, _, topic, _ = scenario
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),
        json={"topic_id": str(topic.id)}).json()
    client.post("/api/v1/topic-registrations", headers=hdr(users[1]),
        json={"topic_id": str(topic.id)})
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[1])).status_code == 200
    rejoined = client.post("/api/v1/topic-registrations", headers=hdr(users[1]),
        json={"topic_id": str(topic.id)})
    assert rejoined.status_code == 201, rejoined.text
    assert rejoined.json()["id"] == made["id"]
    assert len([member for member in rejoined.json()["members"] if member["active"]]) == 2


def test_accepted_registration_is_final_and_rejects_new_group_members(scenario):
    client, users, students, _, topic, session = scenario
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),
        json={"topic_id": str(topic.id)}).json()
    sent = client.post(f"/api/v1/topic-registrations/{made['id']}/submit", headers=hdr(users[0])).json()
    accepted = client.post(f"/api/v1/topic-registrations/{made['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(sent["row_version"])},
        json={"decision": "ACCEPT"})
    assert accepted.status_code == 200, accepted.text
    joined = client.post("/api/v1/topic-registrations", headers=hdr(users[1]),
        json={"topic_id": str(topic.id)})
    assert joined.status_code == 409, joined.text
    assert session.scalar(select(m.ThesisMember.id).where(
        m.ThesisMember.thesis_id == accepted.json()["thesis_id"],
        m.ThesisMember.student_id == students[1].id)) is None
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[0])).status_code == 409
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[1])).status_code == 409


def test_withdrawing_only_student_removes_student_proposal_from_review(scenario):
    client, users, _, lecturers, topic, _ = scenario
    made = client.post("/api/v1/student-proposals", headers=hdr(users[0]), json={
        "round_id": str(topic.round_id), "title": "Synthetic proposal withdrawn before review",
        "max_students": 1, "receiving_lecturer_id": str(lecturers[0].id),
    }).json()
    sent = client.post(f"/api/v1/topic-registrations/{made['id']}/submit", headers=hdr(users[0]))
    assert sent.status_code == 200 and sent.json()["topic_state"] == "SUBMITTED"
    withdrawn = client.post(f"/api/v1/topic-registrations/{made['id']}/withdraw", headers=hdr(users[0]))
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["state"] == "CANCELLED" and withdrawn.json()["topic_state"] == "DRAFT"


def test_no_invitations_or_registration_on_another_students_behalf(scenario):
    client, users, students, _, topic, session = scenario
    before = session.scalar(select(m.TopicRegistration.id).where(m.TopicRegistration.topic_id == topic.id))
    assert before is None
    invalid = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),json={
        "topic_id":str(topic.id),"member_student_ids":[str(students[1].id)]})
    assert invalid.status_code == 422
    invalid = client.post("/api/v1/topic-registrations", headers=hdr(users[0]),json={
        "topic_id":str(topic.id),"member_student_ids":[str(s.id) for s in students[:2]]})
    assert invalid.status_code == 422
    assert session.scalar(select(m.RegistrationMember.id).where(m.RegistrationMember.student_id == students[1].id)) is None
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[1]),json={"topic_id":str(topic.id)})
    assert made.status_code == 201
    reg = made.json()
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/member-response",
        headers=hdr(users[1]),json={"consent_status":"DECLINED"}).status_code == 422
    cancelled = client.post(f"/api/v1/topic-registrations/{reg['id']}/cancel", headers=hdr(users[1]))
    assert cancelled.status_code == 200 and all(not m["active"] for m in cancelled.json()["members"])
    assert client.post("/api/v1/topic-registrations", headers=hdr(users[1]),json={"topic_id":str(topic.id)}).status_code == 201


def test_health_and_openapi(scenario):
    client, *_ = scenario
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}
    spec = client.get("/openapi.json").json()
    assert "/api/v1/topic-registrations" in spec["paths"]
    assert "/api/v1/ai/chat" in spec["paths"]


def test_student_proposal_review_and_receiving_lecturer(scenario):
    client, users, students, lecturers, topic, session = scenario
    made = client.post("/api/v1/student-proposals", headers=hdr(users[0]),json={
        "round_id":str(topic.round_id),"title":"Student suggested application","max_students":2,
        "receiving_lecturer_id":str(lecturers[0].id)})
    assert made.status_code == 201, made.text
    reg = made.json()
    assert len(reg["members"]) == 1 and reg["members"][0]["consent_status"] == "ACCEPTED"
    assert client.post("/api/v1/topic-registrations",headers=hdr(users[1]),json={"topic_id":reg["topic_id"]}).status_code in (403,409)
    sent = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0])).json()
    assert sent["topic_state"] == "SUBMITTED"
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]),"If-Match":str(sent["row_version"])},json={"decision":"ACCEPT"}).status_code == 409
    proposed = client.get(f"/api/v1/topics/{reg['topic_id']}", headers=hdr(users[4])).json()
    assert client.get(f"/api/v1/topics/{reg['topic_id']}",headers=hdr(users[2])).status_code == 404
    approved = client.post(f"/api/v1/topics/{reg['topic_id']}/department-decision",
        headers={**hdr(users[4]),"If-Match":str(proposed["row_version"])},
        json={"decision":"APPROVE","revised_title":"Student topic approved by department","receiving_lecturer_id":str(lecturers[2].id)})
    assert approved.status_code == 200, approved.text
    joined = client.post("/api/v1/topic-registrations",headers=hdr(users[1]),json={"topic_id":reg["topic_id"]})
    assert joined.status_code == 201 and joined.json()["id"] == reg["id"]
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]),"If-Match":str(joined.json()["row_version"])},json={"decision":"ACCEPT"}).status_code == 403
    received = client.get(f"/api/v1/topic-registrations/{reg['id']}",headers=hdr(users[5])).json()
    assert received["receiving_lecturer_user_id"] == str(users[5].id)
    rejected = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[5]),"If-Match":str(received["row_version"])},json={"decision":"REJECT","reason":"Outside current capacity"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["state"] == "LECTURER_REJECTED"


def test_student_proposal_return_edit_resubmit(scenario):
    client, users, students, lecturers, topic, _ = scenario
    made = client.post("/api/v1/student-proposals", headers=hdr(users[0]), json={
        "round_id": str(topic.round_id), "title":"Student proposal to clarify", "max_students":1,
        "member_student_ids":[str(students[0].id)],"receiving_lecturer_id":str(lecturers[0].id),"confirm_creator":True}).json()
    assert client.post(f"/api/v1/topic-registrations/{made['id']}/submit",headers=hdr(users[0])).status_code == 200
    detail=client.get(f"/api/v1/topics/{made['topic_id']}",headers=hdr(users[4])).json()
    returned=client.post(f"/api/v1/topics/{detail['id']}/department-decision",headers={**hdr(users[4]),"If-Match":str(detail['row_version'])},json={"decision":"RETURN","reason":"Clarify objectives"})
    assert returned.status_code == 200
    revised=client.patch(f"/api/v1/topics/{detail['id']}",headers={**hdr(users[0]),"If-Match":str(returned.json()['row_version'])},json={"title":"Student proposal with precise scope"})
    assert revised.status_code == 200, revised.text
    sent=client.post(f"/api/v1/topic-registrations/{made['id']}/submit",headers=hdr(users[0]))
    assert sent.status_code == 200 and sent.json()['topic_state'] == 'SUBMITTED'


def test_requirements_capacity_and_year_codes(scenario):
    client, users, students, _, topic, session = scenario
    body={"round_id":str(topic.round_id),"title":"Individual Python application","max_students":1,
        "requirements":[{"requirement_type":"PREFERRED_GPA","preferred_gpa":3.2,"value_text":"Transcript optional"},{"requirement_type":"SKILL","value_text":"Python"}]}
    created=client.post('/api/v1/topics',headers=hdr(users[3]),json=body)
    assert created.status_code == 201, created.text
    row=created.json()
    assert row['code'].startswith('DT-2026-2027-') and row['round_label']=='Năm học 2026-2027'
    second=client.post('/api/v1/topics',headers=hdr(users[3]),json=body).json()
    assert row['code'] != second['code']
    updated=client.patch('/api/v1/topics/'+row['id'],headers={**hdr(users[3]),'If-Match':str(row['row_version'])},
        json={'requirements':[{'requirement_type':'SKILL','value_text':'PostgreSQL'}]})
    assert updated.status_code == 200, updated.text
    audit=session.scalar(select(m.AuditEvent).where(m.AuditEvent.resource_id==row['id'],m.AuditEvent.action=='TOPIC_UPDATED'))
    assert audit.before_hash != audit.after_hash  # Requirements alone must change the audit fingerprint.
    model=session.get(m.Topic,row['id']); model.state='APPROVED'; session.commit()
    assert client.post('/api/v1/topic-registrations',headers=hdr(users[0]),json={"topic_id":row['id'],"member_student_ids":[str(s.id) for s in students[:2]]}).status_code == 422
    # Preferred GPA is not a second automatic eligibility gate.
    registered=client.post('/api/v1/topic-registrations',headers=hdr(users[0]),json={"topic_id":row['id'],"member_student_ids":[str(students[0].id)],"confirm_creator":True})
    assert registered.status_code == 201, registered.text
    bad={**body,"requirements":[{"requirement_type":"PREFERRED_GPA","preferred_gpa":4.1}]}
    assert client.post('/api/v1/topics',headers=hdr(users[3]),json=bad).status_code == 422


def test_private_member_evidence_and_submission_lock(scenario, monkeypatch, tmp_path):
    client, users, students, _, topic, session=scenario
    monkeypatch.setenv('KLTN_EVIDENCE_DIR',str(tmp_path))
    reg=client.post('/api/v1/topic-registrations',headers=hdr(users[0]),json={"topic_id":str(topic.id)}).json()
    assert client.post('/api/v1/topic-registrations',headers=hdr(users[1]),json={"topic_id":str(topic.id)}).status_code == 201
    url=f"/api/v1/topic-registrations/{reg['id']}/evidence"
    payload=b'%PDF-1.7\nSynthetic demonstration, no PII\n%%EOF'
    upload=client.post(url,headers={**hdr(users[0]),"X-File-Name":"proof.pdf","Content-Type":"application/octet-stream"},content=payload)
    assert upload.status_code == 200,upload.text
    member=session.scalar(select(m.RegistrationMember).where(m.RegistrationMember.registration_id==reg['id'],m.RegistrationMember.student_id==students[0].id))
    first_file_id=member.evidence_file_id
    assert session.get(m.StoredFile, first_file_id).scan_state == 'QUARANTINED'
    assert client.post(url,headers={**hdr(users[2]),"X-File-Name":"proof.pdf"},content=payload).status_code == 404
    assert client.post(url,headers={**hdr(users[0]),"X-File-Name":"proof.pdf"},content=b'not a PDF').status_code == 422
    assert client.post(url,headers={**hdr(users[0]),"X-File-Name":"proof.pdf"},content=b'%PDF-'+b'x'*(5*1024*1024)).status_code == 413
    download=f"/api/v1/topic-registrations/{reg['id']}/members/{students[0].id}/evidence"
    assert client.get(download,headers=hdr(users[2])).status_code == 404
    assert client.get(download,headers=hdr(users[3])).status_code == 404
    # Quarantined evidence is neither downloadable nor usable as proof.
    assert client.get(download,headers=hdr(users[1])).status_code == 409
    # Replacing evidence keeps the previous stored file and records the old link in the audit trail.
    replacement=b'%PDF-1.7\nReplacement proof\n%%EOF'
    replaced=client.post(url,headers={**hdr(users[0]),"X-File-Name":"proof-v2.pdf","Content-Type":"application/octet-stream"},content=replacement)
    assert replaced.status_code == 200, replaced.text
    session.refresh(member)
    assert member.evidence_file_id and member.evidence_file_id != first_file_id
    assert session.get(m.StoredFile, first_file_id) is not None
    audit=session.scalar(select(m.AuditEvent).where(m.AuditEvent.action=='REGISTRATION_EVIDENCE_REPLACED',
        m.AuditEvent.resource_id==reg['id']))
    assert audit is not None and f'previous_stored_file={first_file_id}' in audit.reason
    current=session.get(m.StoredFile, member.evidence_file_id)
    current.scan_state='CLEAN'  # test double for a real scanner; production never assigns CLEAN itself
    session.commit()
    assert client.get(download,headers=hdr(users[1])).content == replacement
    client.post(f"/api/v1/topic-registrations/{reg['id']}/submit",headers=hdr(users[0]))
    assert client.get(download,headers=hdr(users[3])).content == replacement
    assert client.get(download,headers=hdr(users[5])).status_code == 404
    assert client.post(url,headers={**hdr(users[0]),"X-File-Name":"proof.pdf"},content=payload).status_code == 409
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/withdraw", headers=hdr(users[1])).status_code == 200
    assert client.get(download, headers=hdr(users[1])).status_code == 404


def test_latest_eligibility_result_supersedes_old_confirmation(scenario):
    client,users,students,_,topic,session=scenario
    now=datetime.now(timezone.utc)
    session.add(m.EligibilitySnapshot(id=uuid4(),student_id=students[0].id,round_id=topic.round_id,version=2,
        evidence_ref='SYNTHETIC',captured_at=now,confirmed_by=users[4].id,confirmed_at=now,state='REJECTED'))
    session.flush()
    listed=client.get(f'/api/v1/eligible-students?round_id={topic.round_id}',headers=hdr(users[0])).json()
    assert str(students[0].id) not in [row['id'] for row in listed]
    assert client.post('/api/v1/topic-registrations',headers=hdr(users[0]),json={"topic_id":str(topic.id),"member_student_ids":[str(students[0].id)]}).status_code == 409


def test_cancelled_unsent_draft_stays_private(scenario):
    client, users, students, _, topic, _ = scenario
    reg=client.post('/api/v1/topic-registrations',headers=hdr(users[0]),json={"topic_id":str(topic.id),"member_student_ids":[str(students[0].id)]}).json()
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/cancel",headers=hdr(users[0])).status_code == 200
    assert client.get(f"/api/v1/topic-registrations/{reg['id']}",headers=hdr(users[3])).status_code == 404
    assert client.get('/api/v1/topic-registrations',headers=hdr(users[3])).json() == []


def test_round_number_display_and_student_proposal_atomicity(scenario):
    client, users, students, lecturers, topic, session = scenario
    base = session.get(m.ThesisRound, topic.round_id)
    now = datetime.now(timezone.utc)
    session.add(m.ThesisRound(id=uuid4(),academic_year_id=base.academic_year_id,code='TEST-2',round_type='SUPPLEMENTARY',
        opens_at=now-timedelta(hours=1),closes_at=now+timedelta(days=10),state='OPEN'))
    session.commit()
    rows=client.get('/api/v1/rounds/open',headers=hdr(users[3])).json()
    assert {r['label'] for r in rows if r['academic_year']=='2026-2027'} >= {
        'Năm học 2026-2027 · Đợt 1 · Đợt chính',
        'Năm học 2026-2027 · Đợt 2 · Đợt bổ sung',
    }
    rejected=client.post('/api/v1/student-proposals',headers=hdr(users[0]),json={"round_id":str(topic.round_id),"title":"Must not leave an orphan proposal",
        "max_students":1,"member_student_ids":[str(s.id) for s in students[:2]],"receiving_lecturer_id":str(lecturers[0].id)})
    assert rejected.status_code == 422
    assert session.scalar(select(m.Topic.id).where(m.Topic.current_title=='Must not leave an orphan proposal')) is None


def test_capacity_closes_before_lecturer_acceptance(scenario):
    client, users, _, _, topic, session = scenario
    topic.max_students = 2
    session.commit()
    first = client.post('/api/v1/topic-registrations', headers=hdr(users[0]), json={'topic_id':str(topic.id)}).json()
    assert first['expected_member_count'] == 2
    detail = client.get(f'/api/v1/topics/{topic.id}', headers=hdr(users[1])).json()
    assert detail['remaining_slots'] == 1 and detail['available']
    second = client.post('/api/v1/topic-registrations', headers=hdr(users[1]), json={'topic_id':str(topic.id)})
    assert second.status_code == 201 and second.json()['id'] == first['id']
    detail = client.get(f'/api/v1/topics/{topic.id}', headers=hdr(users[2])).json()
    assert detail['remaining_slots'] == 0 and not detail['available']
    assert client.post('/api/v1/topic-registrations', headers=hdr(users[2]), json={'topic_id':str(topic.id)}).status_code == 409
    assert len(session.scalars(select(m.TopicRegistration).where(m.TopicRegistration.topic_id == topic.id)).all()) == 1


def test_lecturer_acceptance_locks_the_current_group(scenario):
    client, users, students, _, topic, session = scenario
    topic.max_students = 2
    session.commit()
    reg = client.post('/api/v1/topic-registrations', headers=hdr(users[0]), json={'topic_id':str(topic.id)}).json()
    sent = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0])).json()
    accepted = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]),'If-Match':str(sent['row_version'])}, json={'decision':'ACCEPT'})
    assert accepted.status_code == 200 and accepted.json()['state'] == 'FINALIZED'
    assert len(accepted.json()['members']) == 1
    thesis_id = accepted.json()['thesis_id']
    assert session.scalar(select(m.ThesisMember.id).where(m.ThesisMember.thesis_id == thesis_id,
        m.ThesisMember.student_id == students[0].id)) is not None
    joined = client.post('/api/v1/topic-registrations', headers=hdr(users[1]), json={'topic_id':str(topic.id)})
    assert joined.status_code == 409
    assert session.scalar(select(m.ThesisMember.id).where(m.ThesisMember.thesis_id == thesis_id,
        m.ThesisMember.student_id == students[1].id)) is None


def test_late_join_is_blocked_after_deadline(scenario):
    client, users, _, _, topic, session = scenario
    client.post('/api/v1/topic-registrations', headers=hdr(users[0]), json={'topic_id':str(topic.id)})
    round_ = session.get(m.ThesisRound, topic.round_id)
    round_.closes_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.commit()
    assert client.post('/api/v1/topic-registrations', headers=hdr(users[1]), json={'topic_id':str(topic.id)}).status_code == 409
    assert not client.get(f'/api/v1/topics/{topic.id}',headers=hdr(users[1])).json()['available']


@pytest.mark.parametrize('stage', ['submit','accept'])
def test_inactive_member_cannot_be_submitted_or_accepted(scenario, stage):
    client, users, _, _, topic, session = scenario
    reg = client.post('/api/v1/topic-registrations', headers=hdr(users[0]), json={'topic_id':str(topic.id)}).json()
    client.post('/api/v1/topic-registrations', headers=hdr(users[1]), json={'topic_id':str(topic.id)})
    if stage == 'accept':
        reg = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit",headers=hdr(users[0])).json()
    users[1].status = 'LOCKED'
    session.commit()
    if stage == 'submit':
        result = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit",headers=hdr(users[0]))
    else:
        result = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
            headers={**hdr(users[3]),'If-Match':str(reg['row_version'])},json={'decision':'ACCEPT'})
    assert result.status_code == 409, result.text


def test_wrong_profile_role_has_no_actions(scenario):
    client, users, _, _, topic, session = scenario
    users[0].base_role = 'LECTURER'
    session.commit()
    assert client.get('/api/v1/me/context',headers=hdr(users[0])).json()['actions'] == []
    assert client.post('/api/v1/topic-registrations',headers=hdr(users[0]),json={'topic_id':str(topic.id)}).status_code == 403


def test_topic_list_pagination_and_bounded_query_count(scenario):
    from sqlalchemy import event
    client, users, _, _, topic, session = scenario
    for index in range(25):
        session.add(m.Topic(id=uuid4(),round_id=topic.round_id,department_id=topic.department_id,
            proposer_user_id=users[3].id,proposer_type='LECTURER',code='PAGED-'+uuid4().hex,
            current_title=f'Pagination topic {index:02d}',max_students=2,state='APPROVED'))
    session.commit()
    queries = []
    def track(*args): queries.append(args[2])
    event.listen(session.bind, 'before_cursor_execute',track)
    try:
        first = client.get('/api/v1/topics?limit=20&search=Pagination',headers=hdr(users[0])).json()
    finally:
        event.remove(session.bind,'before_cursor_execute',track)
    second = client.get('/api/v1/topics?limit=20&offset=20&search=Pagination',headers=hdr(users[0])).json()
    assert len(first) == 20 and len(second) == 5
    assert not {t['id'] for t in first} & {t['id'] for t in second}
    assert len([q for q in queries if q.lstrip().startswith('SELECT')]) <= 14
    assert client.get('/api/v1/topics?search=%25',headers=hdr(users[0])).json() == []


def test_student_proposal_rolls_back_if_student_already_registered(scenario):
    client,users,_,lecturers,topic,session = scenario
    client.post('/api/v1/topic-registrations',headers=hdr(users[0]),json={'topic_id':str(topic.id)})
    result = client.post('/api/v1/student-proposals',headers=hdr(users[0]),json={
        'round_id':str(topic.round_id),'title':'Orphan topic must not survive',
        'max_students':1,'receiving_lecturer_id':str(lecturers[0].id)})
    assert result.status_code == 409
    assert session.scalar(select(m.Topic.id).where(m.Topic.current_title == 'Orphan topic must not survive')) is None



@pytest.mark.parametrize('stage', ['create', 'edit'])
def test_student_cannot_forge_lecturer_requirements(scenario, stage):
    client, users, _, lecturers, topic, session = scenario
    payload = {'round_id':str(topic.round_id),'title':'Personal proposed topic',
               'max_students':2,'receiving_lecturer_id':str(lecturers[0].id)}
    requirement = {'requirement_type':'PREFERRED_GPA','value_text':'GPA preferred by lecturer','preferred_gpa':3.0}
    if stage == 'create':
        result = client.post('/api/v1/student-proposals',headers=hdr(users[0]),
                             json={**payload,'requirements':[requirement]})
    else:
        created = client.post('/api/v1/student-proposals',headers=hdr(users[0]),json=payload).json()
        result = client.patch(f"/api/v1/topics/{created['topic_id']}",
            headers={**hdr(users[0]),'If-Match':'1'},json={'requirements':[requirement]})
    assert result.status_code == 422
    assert 'not student-editable' in result.json()['detail']
    assert not session.scalars(select(m.TopicRequirement).join(m.Topic).where(m.Topic.proposer_user_id == users[0].id)).all()


def test_lecturer_cannot_submit_topic_after_round_closes(scenario):
    client, users, _, _, topic, session = scenario
    created = client.post('/api/v1/topics',headers=hdr(users[3]),
        json={'round_id':str(topic.round_id),'title':'Topic prepared before deadline','max_students':2}).json()
    session.get(m.ThesisRound,topic.round_id).closes_at = datetime.now(timezone.utc)-timedelta(seconds=1)
    session.commit()
    result = client.post(f"/api/v1/topics/{created['id']}/submit",
        headers={**hdr(users[3]),'If-Match':str(created['row_version'])})
    assert result.status_code == 409
    assert session.get(m.Topic,created['id']).state == 'DRAFT'


def test_private_api_cache_and_legacy_student_directory(scenario):
    client, users, students, _, topic, _ = scenario
    response = client.get('/api/v1/topics',headers=hdr(users[0]))
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    legacy = client.get(f'/api/v1/eligible-students?round_id={topic.round_id}',headers=hdr(users[0]))
    assert [row['id'] for row in legacy.json()] == [str(students[0].id)]
    assert client.get('/api/v1/me/eligibility?round_id='+str(topic.round_id),headers=hdr(users[0])).json()['eligible']
