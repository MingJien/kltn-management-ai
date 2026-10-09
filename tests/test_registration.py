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
    assert accepted.json()["state"] == "LECTURER_ACCEPTED"


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
    wrong = client.post(f"/api/v1/topic-registrations/{reg['id']}/department-finalization",
        headers={**hdr(users[5]),"If-Match":str(accepted.json()["row_version"])})
    assert wrong.status_code == 403
    finalized = client.post(f"/api/v1/topic-registrations/{reg['id']}/department-finalization",
        headers={**hdr(users[4]),"If-Match":str(accepted.json()["row_version"])})
    assert finalized.status_code == 200, finalized.text
    thesis_id = finalized.json()["thesis_id"]
    assert finalized.json()["state"] == "FINALIZED" and thesis_id
    assert len(session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis_id)).all()) == 3
    advisor = session.scalar(select(m.AdvisorAssignment).where(m.AdvisorAssignment.thesis_id == thesis_id))
    assert advisor.lecturer_id == lecturers[0].id
    repeat = client.post(f"/api/v1/topic-registrations/{reg['id']}/department-finalization",
        headers={**hdr(users[4]),"If-Match":str(accepted.json()["row_version"])})
    assert repeat.status_code == 200 and repeat.json()["thesis_id"] == thesis_id


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
    assert all(not m["active"] for m in rejected.json()["members"])


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
    assert client.post(url,headers={**hdr(users[2]),"X-File-Name":"proof.pdf"},content=payload).status_code == 404
    assert client.post(url,headers={**hdr(users[0]),"X-File-Name":"proof.pdf"},content=b'not a PDF').status_code == 422
    assert client.post(url,headers={**hdr(users[0]),"X-File-Name":"proof.pdf"},content=b'%PDF-'+b'x'*(5*1024*1024)).status_code == 413
    download=f"/api/v1/topic-registrations/{reg['id']}/members/{students[0].id}/evidence"
    assert client.get(download,headers=hdr(users[2])).status_code == 404
    assert client.get(download,headers=hdr(users[3])).status_code == 404
    assert client.get(download,headers=hdr(users[1])).content == payload
    client.post(f"/api/v1/topic-registrations/{reg['id']}/submit",headers=hdr(users[0]))
    assert client.get(download,headers=hdr(users[3])).content == payload
    assert client.get(download,headers=hdr(users[5])).status_code == 404
    assert client.post(url,headers={**hdr(users[0]),"X-File-Name":"proof.pdf"},content=payload).status_code == 409
    assert session.get(m.StoredFile, session.scalar(select(m.RegistrationMember).where(m.RegistrationMember.registration_id==reg['id'],m.RegistrationMember.student_id==students[0].id)).evidence_file_id).scan_state == 'QUARANTINED'


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
    assert {r['label'] for r in rows if r['academic_year']=='2026-2027'} >= {'Năm học 2026-2027 (đợt 1)','Năm học 2026-2027 (đợt 2)'}
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


def test_partial_group_acceptance_and_later_join_requires_new_decision(scenario):
    client, users, _, _, topic, session = scenario
    topic.max_students = 2
    session.commit()
    reg = client.post('/api/v1/topic-registrations', headers=hdr(users[0]), json={'topic_id':str(topic.id)}).json()
    sent = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0])).json()
    accepted = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]),'If-Match':str(sent['row_version'])}, json={'decision':'ACCEPT'})
    assert accepted.status_code == 200 and len(accepted.json()['members']) == 1
    joined = client.post('/api/v1/topic-registrations', headers=hdr(users[1]), json={'topic_id':str(topic.id)})
    assert joined.status_code == 201, joined.text
    updated = joined.json()
    assert updated['id'] == reg['id'] and updated['state'] == 'SUBMITTED'
    assert updated['lecturer_decided_at'] is None
    assert next(m for m in updated['members'] if not m['is_coordinator'])['can_upload_evidence']
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]),'If-Match':str(accepted.json()['row_version'])}, json={'decision':'ACCEPT'}).status_code == 409
    again = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]),'If-Match':str(updated['row_version'])}, json={'decision':'ACCEPT'})
    assert again.status_code == 200
    events = session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_id == reg['id'],m.AuditEvent.action == 'REGISTRATION_MEMBER_JOINED')).all()
    assert len(events) == 1 and 'LECTURER_ACCEPTED' in events[0].reason


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
