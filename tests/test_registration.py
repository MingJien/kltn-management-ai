from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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
                    current_title="Synthetic topic", max_students=3, state="APPROVED")
    session.add_all([faculty, year, *users])
    session.flush()
    session.add_all([department, round_, *students, *lecturers, position])
    session.flush()
    session.add_all([head_assignment, topic])
    session.flush()
    for student in students:
        session.add(m.EligibilitySnapshot(
            id=uuid4(), student_id=student.id, round_id=round_.id, version=1,
            passed_credit_ratio=0.8, gpa_4=3.0, discipline_status="CLEAR",
            criminal_case_status="CLEAR", evidence_ref="SYNTHETIC",
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


def test_registration_vertical_slice(scenario):
    client, users, students, lecturers, topic, session = scenario
    payload = {"topic_id": str(topic.id), "member_student_ids": [str(s.id) for s in students]}
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json=payload)
    assert made.status_code == 201, made.text
    reg = made.json()
    assert reg["state"] == "DRAFT"
    assert len(reg["member_student_ids"]) == 3
    assert {member["consent_status"] for member in reg["members"]} == {"PENDING"}
    assert client.get("/api/v1/topic-registrations", headers=hdr(users[3])).json() == []
    assert client.get(f"/api/v1/topic-registrations/{reg['id']}", headers=hdr(users[3])).status_code == 404
    premature = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0]))
    assert premature.status_code == 409
    wrong_member = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/member-response",
        headers=hdr(users[3]), json={"consent_status": "ACCEPTED"},
    )
    assert wrong_member.status_code == 403
    again = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json=payload)
    assert again.status_code == 409
    outsider = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[5]), "If-Match": str(reg["row_version"])},
        json={"decision": "ACCEPT"},
    )
    assert outsider.status_code == 403
    lecturer_cannot_add = client.post("/api/v1/topic-registrations", headers=hdr(users[3]), json=payload)
    assert lecturer_cannot_add.status_code == 403
    first_response = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/member-response",
        headers=hdr(users[0]),
        json={"consent_status": "ACCEPTED", "student_id": str(students[1].id)},
    )
    assert first_response.status_code == 200, first_response.text
    first_member = next(member for member in first_response.json()["members"] if member["student_id"] == str(students[0].id))
    assert first_member["consent_status"] == "ACCEPTED"
    assert first_member["active"]
    repeat_response = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/member-response",
        headers=hdr(users[0]), json={"consent_status": "DECLINED"},
    )
    assert repeat_response.status_code == 409
    for index in range(1, 3):
        accepted_member = client.post(
            f"/api/v1/topic-registrations/{reg['id']}/member-response",
            headers=hdr(users[index]), json={"consent_status": "ACCEPTED"},
        )
        assert accepted_member.status_code == 200, accepted_member.text
    non_coordinator_submit = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[1]))
    assert non_coordinator_submit.status_code == 403
    submitted = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0]))
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["state"] == "SUBMITTED"
    late_response = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/member-response",
        headers=hdr(users[0]), json={"consent_status": "DECLINED"},
    )
    assert late_response.status_code == 409
    accepted = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(submitted.json()["row_version"])},
        json={"decision": "ACCEPT"},
    )
    assert accepted.status_code == 200, accepted.text
    wrong_head = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/department-finalization",
        headers={**hdr(users[5]), "If-Match": str(accepted.json()["row_version"])},
    )
    assert wrong_head.status_code == 403
    finalized = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/department-finalization",
        headers={**hdr(users[4]), "If-Match": str(accepted.json()["row_version"])},
    )
    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["state"] == "FINALIZED"
    thesis_id = finalized.json()["thesis_id"]
    assert thesis_id is not None
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.registration_id == reg["id"]))
    assert str(thesis.id) == thesis_id
    assert len(session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id)).all()) == 3
    advisor = session.scalar(select(m.AdvisorAssignment).where(m.AdvisorAssignment.thesis_id == thesis.id))
    assert advisor.lecturer_id == lecturers[0].id
    hidden = client.get(f"/api/v1/topic-registrations/{reg['id']}", headers=hdr(users[2]))
    assert hidden.status_code == 200
    unrelated = client.get(f"/api/v1/topic-registrations/{reg['id']}", headers=hdr(users[5]))
    assert unrelated.status_code == 404
    repeat = client.post(
        f"/api/v1/topic-registrations/{reg['id']}/department-finalization",
        headers={**hdr(users[4]), "If-Match": str(accepted.json()["row_version"])},
    )
    assert repeat.status_code == 200
    assert repeat.json()["thesis_id"] == thesis_id


def test_dev_identity_fail_closed(scenario, monkeypatch):
    client, users, *_ = scenario
    monkeypatch.setenv("KLTN_ENV", "production")
    assert client.get("/api/v1/me/context", headers=hdr(users[0])).status_code == 503


def test_rejection_releases_students_for_new_registration(scenario):
    client, users, students, _, topic, session = scenario
    members = [str(students[0].id)]
    created = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(topic.id), "member_student_ids": members,
    })
    assert created.status_code == 201, created.text
    reg = created.json()
    confirmed = client.post(f"/api/v1/topic-registrations/{reg['id']}/member-response", headers=hdr(users[0]), json={"consent_status": "ACCEPTED"})
    assert confirmed.status_code == 200
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


def test_draft_decline_must_be_cancelled_before_reforming(scenario):
    client, users, students, *_ = scenario
    members = [str(student.id) for student in students[:2]]
    created = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(scenario[4].id), "member_student_ids": members,
    })
    assert created.status_code == 201, created.text
    reg = created.json()
    declined = client.post(f"/api/v1/topic-registrations/{reg['id']}/member-response", headers=hdr(users[1]), json={"consent_status": "DECLINED"})
    assert declined.status_code == 200
    denied_submit = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0]))
    assert denied_submit.status_code == 409
    cancelled = client.post(f"/api/v1/topic-registrations/{reg['id']}/cancel", headers=hdr(users[0]))
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["state"] == "CANCELLED"
    assert all(not member["active"] for member in cancelled.json()["members"])
    retry = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(scenario[4].id), "member_student_ids": [str(students[0].id)],
    })
    assert retry.status_code == 201, retry.text


def test_health_and_openapi(scenario):
    client, *_ = scenario
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}
    spec = client.get("/openapi.json").json()
    assert "/api/v1/topic-registrations" in spec["paths"]
    assert "/api/v1/ai/chat" in spec["paths"]
