"""Integration stories on PostgreSQL: rights, lifecycle, immutable history and file rollback."""
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_registration import hdr, scenario
from backend.db.models import entities as m
from backend.services.passwords import hash_password
from backend.services.theses import now


@pytest.fixture
def workspace(scenario, monkeypatch, tmp_path):
    client, users, students, lecturers, topic, session = scenario
    monkeypatch.setenv("KLTN_DOCUMENT_DIR", str(tmp_path / "documents"))
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(topic.id), "member_student_ids": [str(students[0].id), str(students[1].id)], "confirm_creator": True})
    assert made.status_code == 201, made.text
    reg = made.json()
    assert client.post(f"/api/v1/topic-registrations/{reg['id']}/member-response", headers=hdr(users[1]),
        json={"consent_status": "ACCEPTED"}).status_code == 200
    submitted = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0])).json()
    accepted = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(submitted['row_version'])}, json={"decision": "ACCEPT"}).json()
    finalized = client.post(f"/api/v1/topic-registrations/{reg['id']}/department-finalization",
        headers={**hdr(users[4]), "If-Match": str(accepted['row_version'])})
    assert finalized.status_code == 200, finalized.text
    thesis_id = finalized.json()["thesis_id"]
    session.add(m.ResourceAssignment(id=uuid4(), assignment_type="KLTN_COORDINATOR", user_id=users[4].id,
        round_id=topic.round_id, effective_from=now()-timedelta(days=1), state="ACTIVE"))
    session.commit()
    return client, users, students, lecturers, session, f"/api/v1/theses/{thesis_id}"


def version_headers(user, row):
    return {**hdr(user), "If-Match": str(row["row_version"])}


def test_advisor_consent_history_and_resource_isolation(workspace):
    client, users, students, lecturers, session, path = workspace
    initial = client.get(path, headers=hdr(users[4])).json()
    assert initial["advisor_name"] == lecturers[0].display_name
    assert client.get(path, headers=hdr(users[2])).status_code == 404
    assert client.get(path, headers=hdr(users[5])).status_code == 404
    assert client.get("/api/v1/theses", headers=hdr(users[2])).json() == []
    assert client.post(path+"/advisor-nomination", headers=version_headers(users[0], initial), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Change supervision"}).status_code == 403
    nominated = client.post(path+"/advisor-nomination", headers=version_headers(users[4], initial), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Change supervision"})
    assert nominated.status_code == 200, nominated.text
    nomination = nominated.json()
    assert nomination["advisor_lecturer_id"] == str(lecturers[0].id)
    assert client.get(path+"/documents", headers=hdr(users[5])).status_code == 403
    assert client.get(path+"/progress-reports", headers=hdr(users[5])).status_code == 403
    assert client.post(path+"/advisor-response", headers=version_headers(users[5], initial), json={
        "decision": "ACCEPT", "reason": "Agree to supervise"}).status_code == 409
    result = client.post(path+"/advisor-response", headers=version_headers(users[5], nomination), json={
        "decision": "ACCEPT", "reason": "Agree to supervise"})
    assert result.status_code == 200, result.text
    assert result.json()["advisor_lecturer_id"] == str(lecturers[2].id)
    assert [item['state'] for item in result.json()['advisor_history']] == ["ACTIVE", "ENDED"]
    assert client.get(path, headers=hdr(users[3])).status_code == 404
    assert client.get(path+"/documents", headers=hdr(users[5])).status_code == 200
    assert client.get(path+"/audit", headers=hdr(users[4])).json()[0]["action"] == "ADVISOR_ACCEPT"
    assert client.get(path+"/audit", headers=hdr(users[0])).status_code == 403


def test_decline_keeps_current_advisor_and_ends_nominee_rights(workspace):
    client, users, _, lecturers, _, path = workspace
    original = client.get(path, headers=hdr(users[4])).json()
    pending = client.post(path+"/advisor-nomination", headers=version_headers(users[4], original), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Department proposal"}).json()
    response = client.post(path+"/advisor-response", headers=version_headers(users[5], pending), json={
        "decision": "DECLINE", "reason": "Schedule unavailable"})
    assert response.status_code == 200, response.text
    assert response.json()["advisor_lecturer_id"] == original["advisor_lecturer_id"]
    assert response.json()["pending_advisor"] is None
    assert client.get(path, headers=hdr(users[5])).status_code == 404


def open_milestone(client, users, path, **extra):
    response = client.post(path+"/milestones", headers=hdr(users[4]), json={
        "code": "INTERNAL_1", "title": "Review implementation plan", "due_at": (now()+timedelta(days=5)).isoformat(),
        "expected_ratio": 30, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_progress_revision_cross_comment_and_closed_milestone(workspace):
    client, users, _, lecturers, session, path = workspace
    milestone = open_milestone(client, users, path)
    assert client.post(path+"/milestones", headers=hdr(users[3]), json={"code": "NEW", "title": "New",
        "due_at": now().isoformat()}).status_code == 403
    payload = {"milestone_id": milestone["id"], "summary": "Initial results and remaining work", "reported_ratio": 25}
    assert client.post(path+"/progress-reports", headers=hdr(users[0]), json={**payload, "reported_ratio": 101}).status_code == 422
    report = client.post(path+"/progress-reports", headers=hdr(users[0]), json=payload)
    assert report.status_code == 201, report.text
    first = report.json()
    assert client.post(path+"/progress-reports", headers=hdr(users[1]), json=payload).status_code == 409
    thesis = client.get(path, headers=hdr(users[4])).json()
    assert client.post(path+"/progress-reviewers", headers=version_headers(users[4], thesis), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Internal peer comments"}).status_code == 204
    assert client.get(path+"/documents", headers=hdr(users[5])).status_code == 403
    assert client.post(path+f"/progress-reports/{first['id']}/review", headers=version_headers(users[5], first), json={
        "decision": "CONFIRM", "comment": "Peer cannot confirm"}).status_code == 403
    commented = client.post(path+f"/progress-reports/{first['id']}/review", headers=version_headers(users[5], first), json={
        "decision": "COMMENT_ONLY", "comment": "Consider extra validation"})
    assert commented.status_code == 200, commented.text
    assert commented.json()["state"] == "SUBMITTED"
    returned = client.post(path+f"/progress-reports/{first['id']}/review", headers=version_headers(users[3], commented.json()), json={
        "decision": "REVISION_REQUIRED", "comment": "Add measurements"})
    assert returned.status_code == 200, returned.text
    second = client.post(path+"/progress-reports", headers=hdr(users[1]), json={**payload, "summary": "Revised with measurements"})
    assert second.status_code == 201, second.text
    assert second.json()["version_no"] == 2
    confirmed = client.post(path+f"/progress-reports/{second.json()['id']}/review", headers=version_headers(users[3], second.json()), json={
        "decision": "CONFIRM", "comment": "Measurements verified"})
    assert confirmed.status_code == 200, confirmed.text
    assert client.post(path+"/progress-reports", headers=hdr(users[0]), json=payload).status_code == 409
    history = client.get(path+"/progress-reports", headers=hdr(users[0])).json()
    assert {row["summary"] for row in history} == {payload["summary"], "Revised with measurements"}
    closed = client.post(path+f"/milestones/{milestone['id']}/close", headers=version_headers(users[4], milestone), json={"reason": "Checkpoint complete"})
    assert closed.status_code == 200, closed.text
    new_milestone = open_milestone(client, users, path)
    assert new_milestone["version_no"] == 2
    assert client.post(path+"/progress-reports", headers=hdr(users[0]), json=payload).status_code == 409


def test_late_submission_marked_not_faked_as_on_time(workspace):
    client, users, *_ , path = workspace
    milestone = open_milestone(client, users, path, due_at=(now()-timedelta(days=1)).isoformat())
    report = client.post(path+"/progress-reports", headers=hdr(users[0]), json={
        "milestone_id": milestone["id"], "summary": "Late submission", "reported_ratio": 50})
    assert report.status_code == 201, report.text
    assert report.json()["late"] is True


def upload(client, user, path, doc, content=b"Synthetic report", name="report.txt"):
    return client.post(path+f"/documents/{doc['id']}/versions", headers={**version_headers(user, doc),
        "Content-Type": "application/octet-stream", "X-File-Name": name}, content=content)


def test_document_versions_review_download_and_corruption_detection(workspace, monkeypatch):
    client, users, _, _, session, path = workspace
    doc = client.post(path+"/documents", headers=hdr(users[0]), json={"title": "Results", "document_type": "REPORT"}).json()
    first = upload(client, users[0], path, doc)
    assert first.status_code == 201, first.text
    doc1 = first.json()
    v1 = doc1["versions"][0]
    assert v1["scan_state"] == "QUARANTINED"
    assert upload(client, users[1], path, doc).status_code == 409
    response = client.post(path+f"/documents/{doc['id']}/versions/{v1['id']}/review", headers=version_headers(users[3], v1),
        json={"decision": "REVISION_REQUIRED", "comment": "Add the experiment"})
    assert response.status_code == 200, response.text
    second = upload(client, users[1], path, response.json(), b"Synthetic revised report")
    assert second.status_code == 201, second.text
    assert [v['version_no'] for v in second.json()['versions']] == [2, 1]
    download = path+f"/documents/{doc['id']}/versions/{v1['id']}/download"
    assert client.get(download, headers=hdr(users[2])).status_code == 404
    downloaded = client.get(download, headers=hdr(users[3]))
    assert downloaded.content == b"Synthetic report"
    assert "attachment" in downloaded.headers["content-disposition"]
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert client.post(path+f"/documents/{doc['id']}/versions/{v1['id']}/review", headers=version_headers(users[3], v1),
        json={"decision": "ACCEPT", "comment": "Cannot accept an old version"}).status_code == 409
    from backend.services.documents import storage_root
    file_id = session.get(m.DocumentVersion, v1["id"]).stored_file_id
    key = session.get(m.StoredFile, file_id).storage_key.removeprefix("documents/")
    (storage_root()/key).write_bytes(b"Altered bytes")
    assert client.get(download, headers=hdr(users[0])).status_code == 409


def test_upload_validation_and_database_failure_remove_written_file(workspace, monkeypatch):
    client, users, _, _, session, path = workspace
    doc = client.post(path+"/documents", headers=hdr(users[0]), json={"title": "Results", "document_type": "REPORT"}).json()
    from backend.services import documents
    assert upload(client, users[0], path, doc, b"not a pdf", "report.pdf").status_code == 422
    assert upload(client, users[0], path, doc, b"", "report.txt").status_code == 422
    assert upload(client, users[0], path, doc, b"x"*(documents.MAX_BYTES+1)).status_code == 413
    original_commit = session.commit
    def fail_commit():
        raise RuntimeError("Synthetic database commit failure")
    monkeypatch.setattr(session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="Synthetic database"):
        upload(client, users[0], path, doc)
    monkeypatch.setattr(session, "commit", original_commit)
    assert list(documents.storage_root().glob("*")) == []
    assert client.get(path+"/documents", headers=hdr(users[0])).json()[0]["versions"] == []


def test_proposal_file_does_not_bypass_academic_approval(workspace):
    client, users, *_ , path = workspace
    doc = client.post(path+"/documents", headers=hdr(users[0]), json={"title": "Proposal", "document_type": "PROPOSAL"}).json()
    uploaded = upload(client, users[0], path, doc).json()
    version = uploaded["versions"][0]
    response = client.post(path+f"/documents/{doc['id']}/versions/{version['id']}/review", headers=version_headers(users[3], version),
        json={"decision": "ACCEPT", "comment": "Should need proposal workflow"})
    assert response.status_code == 409
    assert client.get(path, headers=hdr(users[0])).json()["state"] == "ACTIVE"


def test_individual_work_version_and_frozen_thesis(workspace):
    client, users, students, _, session, path = workspace
    payload = {"student_id": str(students[1].id), "work_description": "Implement data validation", "expected_output": "Validation module and test results"}
    assignment = client.post(path+"/work-assignments", headers=hdr(users[0]), json=payload)
    assert assignment.status_code == 201, assignment.text
    item = assignment.json()
    approved = client.post(path+f"/work-assignments/{item['id']}/review", headers=version_headers(users[3], item),
        json={"decision": "APPROVE", "comment": "Clear individual contribution"})
    assert approved.status_code == 200, approved.text
    assert client.post(path+"/work-assignments", headers=hdr(users[1]), json={**payload, "student_id": str(students[0].id)}).status_code == 403
    thesis = session.get(m.Thesis, path.split("/")[-1])
    thesis.state = "WITHDRAWN"
    session.flush()
    session.commit()  # Persist the freeze before the rejected request rolls back its own transaction.
    assert client.post(path+"/work-assignments", headers=hdr(users[0]), json=payload).status_code == 409
    assert client.get(path+"/work-assignments", headers=hdr(users[0])).json()[0]["state"] == "APPROVED"
    assert "work:submit" not in client.get(path, headers=hdr(users[0])).json()["actions"]


def test_cross_department_and_expired_assignments_do_not_grant_access(workspace):
    client, users, students, lecturers, session, path = workspace
    original = client.get(path, headers=hdr(users[4])).json()
    other = m.Department(id=uuid4(), faculty_id=session.get(m.Department, students[0].department_id).faculty_id,
        code="OTHER-"+uuid4().hex[:8], name="Other synthetic department")
    session.add(other)
    session.flush()
    lecturers[2].department_id = other.id
    session.commit()
    assert client.post(path+"/advisor-nomination", headers=version_headers(users[4], original), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Wrong department"}).status_code == 422
    assert client.post(path+"/progress-reviewers", headers=version_headers(users[4], original), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Wrong department"}).status_code == 422
    head = session.scalar(select(m.PositionAssignment).where(m.PositionAssignment.lecturer_id == lecturers[1].id))
    head.effective_to = now()-timedelta(hours=1)
    session.commit()
    # Coordinator assignment still allows metadata access, never substitutes for an expired head position.
    assert "advisor:nominate" not in client.get(path, headers=hdr(users[4])).json()["actions"]
    assert client.post(path+"/advisor-nomination", headers=version_headers(users[4], original), json={
        "lecturer_id": str(lecturers[0].id), "reason": "Expired position"}).status_code == 403


def test_cross_reviewer_revocation_takes_effect_immediately(workspace):
    client, users, _, lecturers, _, path = workspace
    original = client.get(path, headers=hdr(users[4])).json()
    assert client.post(path+"/progress-reviewers", headers=version_headers(users[4], original), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Peer checkpoint review"}).status_code == 204
    assigned = client.get(path, headers=hdr(users[4])).json()
    assert assigned["cross_reviewers"][0]["lecturer_id"] == str(lecturers[2].id)
    assert client.get(path+"/progress-reports", headers=hdr(users[5])).status_code == 200
    assert client.post(path+f"/progress-reviewers/{lecturers[2].id}/revoke", headers=version_headers(users[4], assigned), json={
        "reason": "Checkpoint finished"}).status_code == 204
    assert client.get(path, headers=hdr(users[5])).status_code == 404
    assert client.get(path+"/progress-reports", headers=hdr(users[5])).status_code == 404


def test_status_and_password_changes_revoke_all_previous_sessions(workspace):
    from fastapi.testclient import TestClient
    from backend.api.main import app
    client, users, _, _, session, _ = workspace
    admin = m.UserAccount(id=uuid4(), external_subject="admin-session-"+uuid4().hex, base_role="ADMIN", status="ACTIVE")
    student = users[0]
    student.email = "session-student@preview.invalid"
    student.password_hash = hash_password("synthetic-session-password")
    student.email_verified_at = now()
    session.add(admin)
    session.commit()
    first, second = TestClient(app), TestClient(app)
    login = {"email": student.email, "password": "synthetic-session-password"}
    assert first.post("/api/v1/auth/login", json=login).status_code == 204
    assert second.post("/api/v1/auth/login", json=login).status_code == 204
    csrf = first.get("/api/v1/me/context").json()["csrf_token"]
    assert first.post("/api/v1/account/password-change", headers={"X-CSRF-Token": csrf}, json={
        "current_password": login["password"], "new_password": "replacement-session-password"}).status_code == 204
    assert second.get("/api/v1/me/context").status_code == 401
    login["password"] = "replacement-session-password"
    assert second.post("/api/v1/auth/login", json=login).status_code == 204
    assert client.post(f"/api/v1/admin/users/{student.id}/lock", headers=hdr(admin), json={
        "locked": True, "reason": "Review account temporarily"}).status_code == 204
    assert second.get("/api/v1/me/context").status_code == 401


def test_progress_evidence_cannot_reference_another_thesis_document(workspace):
    client, users, _, _, session, path = workspace
    milestone = open_milestone(client, users, path)
    assert client.post(path+"/progress-reports", headers=hdr(users[0]), json={
        "milestone_id": milestone["id"], "summary": "No forged evidence", "reported_ratio": 30,
        "document_version_id": str(uuid4())}).status_code == 422


@pytest.mark.parametrize("change", ["STUDENT_LOCKED", "ADVISOR_LOCKED", "ELIGIBILITY_REJECTED"])
def test_department_rechecks_accounts_and_eligibility_at_finalization(scenario, change):
    client, users, students, lecturers, topic, session = scenario
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(topic.id), "member_student_ids": [str(students[0].id)], "confirm_creator": True}).json()
    path = "/api/v1/topic-registrations/"+made["id"]
    sent = client.post(path+"/submit", headers=hdr(users[0])).json()
    accepted = client.post(path+"/lecturer-decision", headers=version_headers(users[3], sent), json={"decision": "ACCEPT"}).json()
    if change == "ELIGIBILITY_REJECTED":
        session.add(m.EligibilitySnapshot(id=uuid4(), student_id=students[0].id, round_id=topic.round_id, version=2,
            evidence_ref="Synthetic replacement decision", captured_at=now(), confirmed_by=users[4].id, confirmed_at=now(), state="REJECTED"))
    else:
        users[0 if change == "STUDENT_LOCKED" else 3].status = "LOCKED"
    session.commit()
    blocked = client.post(path+"/department-finalization", headers=version_headers(users[4], accepted))
    assert blocked.status_code == 409, blocked.text
    assert session.scalar(select(m.Thesis.id).where(m.Thesis.registration_id == made["id"])) is None
    assert session.get(m.TopicRegistration, made["id"]).state == "LECTURER_ACCEPTED"
