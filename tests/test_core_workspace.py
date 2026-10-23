"""Integration stories on PostgreSQL: rights, lifecycle, immutable history and file rollback."""
from datetime import timedelta
from io import BytesIO
from uuid import uuid4

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy import func, select

from test_registration import hdr, scenario
from backend.db.models import entities as m
from backend.services.passwords import hash_password
from backend.services.theses import now


@pytest.fixture
def workspace(scenario, monkeypatch, tmp_path):
    client, users, students, lecturers, topic, session = scenario
    monkeypatch.setenv("KLTN_DOCUMENT_DIR", str(tmp_path / "documents"))
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(topic.id), "member_student_ids": [str(students[0].id)], "confirm_creator": True})
    assert made.status_code == 201, made.text
    reg = made.json()
    joined = client.post("/api/v1/topic-registrations", headers=hdr(users[1]), json={
        "topic_id": str(topic.id), "member_student_ids": [str(students[1].id)], "confirm_creator": True})
    assert joined.status_code == 201, joined.text
    submitted = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit", headers=hdr(users[0])).json()
    accepted = client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",
        headers={**hdr(users[3]), "If-Match": str(submitted['row_version'])}, json={"decision": "ACCEPT"}).json()
    assert accepted["state"] == "FINALIZED" and accepted["thesis_id"]
    thesis_id = accepted["thesis_id"]
    session.add(m.ResourceAssignment(id=uuid4(), assignment_type="KLTN_COORDINATOR", user_id=users[4].id,
        round_id=topic.round_id, effective_from=now()-timedelta(days=1), state="ACTIVE"))
    for doc_type in ("PROPOSAL", "PLAN", "SUPPORTING"):
        session.add(m.DocumentDeadline(id=uuid4(), round_id=topic.round_id,
            document_type=doc_type, due_at=now()+timedelta(days=30),
            state="OPEN", set_by=users[4].id, reason="Initial deadline"))
    session.commit()
    return client, users, students, lecturers, session, f"/api/v1/theses/{thesis_id}"


def version_headers(user, row):
    return {**hdr(user), "If-Match": str(row["row_version"])}


def synthetic_pdf():
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def test_lecturer_acceptance_sets_official_advisor_and_removes_nomination(workspace):
    client, users, students, lecturers, session, path = workspace
    initial = client.get(path, headers=hdr(users[4])).json()
    assert initial["advisor_name"] == lecturers[0].display_name
    assert [item["state"] for item in initial["advisor_history"]] == ["ACTIVE"]
    assert initial["pending_advisor"] is None
    assert "advisor:nominate" not in initial["actions"]
    assert client.get(path, headers=hdr(users[2])).status_code == 404
    assert client.get(path, headers=hdr(users[5])).status_code == 404
    assert client.get("/api/v1/theses", headers=hdr(users[2])).json() == []
    assert client.post(path+"/advisor-nomination", headers=version_headers(users[4], initial), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Change supervision"}).status_code == 404
    assert client.post(path+"/advisor-response", headers=version_headers(users[5], initial), json={
        "decision": "ACCEPT", "reason": "Agree to supervise"}).status_code == 404
    assert client.get(path+"/documents", headers=hdr(users[3])).status_code == 200
    assert client.get(path+"/progress-reports", headers=hdr(users[3])).status_code == 200
    audit = client.get(path+"/audit", headers=hdr(users[4])).json()
    assert any(event["action"] == "THESIS_CREATED_FROM_REGISTRATION_ACCEPTANCE" for event in audit)
    assert client.get(path+"/audit", headers=hdr(users[0])).status_code == 403


def test_official_advisor_cannot_be_replaced_after_acceptance(workspace):
    client, users, _, lecturers, _, path = workspace
    original = client.get(path, headers=hdr(users[4])).json()
    assert original["advisor_lecturer_id"] == str(lecturers[0].id)
    assert client.post(path+"/advisor-nomination", headers=version_headers(users[4], original), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Department proposal"}).status_code == 404
    refreshed = client.get(path, headers=hdr(users[4])).json()
    assert refreshed["advisor_lecturer_id"] == original["advisor_lecturer_id"]
    assert len(refreshed["advisor_history"]) == 1
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


def test_round_extension_keeps_old_late_mark_and_applies_new_deadline(workspace):
    client, users, _, _, session, path = workspace
    milestone = open_milestone(client, users, path, due_at=(now()-timedelta(days=1)).isoformat())
    payload = {"milestone_id": milestone["id"], "summary": "Late before extension", "reported_ratio": 30}
    first = client.post(path+"/progress-reports", headers=hdr(users[0]), json=payload)
    assert first.status_code == 201 and first.json()["late"] is True, first.text
    extension_path = path+f"/milestones/{milestone['id']}/extend"
    due = (now()+timedelta(days=2)).isoformat()
    body = {"due_at": due, "reason": "Faculty approved extension for this round"}
    assert client.post(extension_path, headers=version_headers(users[0], milestone), json=body).status_code == 403
    assert client.post(extension_path, headers=version_headers(users[4], milestone),
        json={**body, "reason": " "}).status_code == 422
    changed = client.post(extension_path, headers=version_headers(users[4], milestone), json=body)
    assert changed.status_code == 200, changed.text
    assert client.post(extension_path, headers=version_headers(users[4], milestone), json=body).status_code == 409
    history = client.get(path+"/progress-reports", headers=hdr(users[0])).json()
    assert history[0]["late"] is True
    assert history[0]["due_at_at_submission"] == first.json()["due_at_at_submission"]
    review = client.post(path+f"/progress-reports/{first.json()['id']}/review",
        headers=version_headers(users[3], first.json()),
        json={"decision": "REVISION_REQUIRED", "comment": "Revise the report"})
    assert review.status_code == 200, review.text
    second = client.post(path+"/progress-reports", headers=hdr(users[0]),
        json={**payload, "summary": "Revised after extension"})
    assert second.status_code == 201 and second.json()["late"] is False, second.text
    assert session.scalar(select(m.AuditEvent.id).where(m.AuditEvent.action == "MILESTONE_EXTENDED"))
    audit = client.get(path+"/audit", headers=hdr(users[4])).json()
    assert any(event["action"] == "MILESTONE_EXTENDED" for event in audit)
    assert any("Faculty approved extension" in (event["reason"] or "") for event in audit)
    # Every member can read why the round deadline moved, without seeing the full audit feed.
    history = client.get(path+"/milestone-history", headers=hdr(users[0]))
    assert history.status_code == 200, history.text
    assert any(event["action"] == "MILESTONE_EXTENDED" for event in history.json())


def upload(client, user, path, doc, content=b"Synthetic report", name="report.txt"):
    return client.post(path+f"/documents/{doc['id']}/versions", headers={**version_headers(user, doc),
        "Content-Type": "application/octet-stream", "X-File-Name": name}, content=content)


def test_progress_report_cannot_be_created_as_standalone_document(workspace):
    client, users, _, _, _, path = workspace
    response = client.post(path+"/documents", headers=hdr(users[0]),
        json={"title": "Progress report outside milestone", "document_type": "REPORT"})
    assert response.status_code == 409
    assert "Tiến độ" in response.json()["detail"]
    assert client.get(path+"/documents", headers=hdr(users[0])).json() == []


def test_document_versions_review_download_and_corruption_detection(workspace, monkeypatch):
    monkeypatch.setattr("backend.services.documents.file_scanner.scan", lambda file, path: file.scan_state)
    client, users, _, _, session, path = workspace
    doc = client.post(path+"/documents", headers=hdr(users[0]), json={"title": "Results", "document_type": "SUPPORTING"}).json()
    first = upload(client, users[0], path, doc)
    assert first.status_code == 201, first.text
    doc1 = first.json()
    v1 = doc1["versions"][0]
    assert v1["scan_state"] == "QUARANTINED"
    assert upload(client, users[1], path, doc).status_code == 409
    download = path+f"/documents/{doc['id']}/versions/{v1['id']}/download"
    assert client.get(download, headers=hdr(users[2])).status_code == 404
    # Unscanned uploads must not be downloaded or accepted.
    assert client.get(download, headers=hdr(users[3])).status_code == 409
    assert client.post(path+f"/documents/{doc['id']}/versions/{v1['id']}/review", headers=version_headers(users[3], v1),
        json={"decision": "ACCEPT", "comment": "Cannot accept unscanned file"}).status_code == 409
    # Simulate a real scanner clearing the file; production never assigns CLEAN by itself.
    stored = session.get(m.StoredFile, session.get(m.DocumentVersion, v1["id"]).stored_file_id)
    stored.scan_state = "CLEAN"
    session.commit()
    response = client.post(path+f"/documents/{doc['id']}/versions/{v1['id']}/review", headers=version_headers(users[3], v1),
        json={"decision": "REVISION_REQUIRED", "comment": "Add the experiment"})
    assert response.status_code == 200, response.text
    second = upload(client, users[1], path, response.json(), b"Synthetic revised report")
    assert second.status_code == 201, second.text
    assert [v['version_no'] for v in second.json()['versions']] == [2, 1]
    downloaded = client.get(download, headers=hdr(users[3]))
    assert downloaded.content == b"Synthetic report"
    assert "attachment" in downloaded.headers["content-disposition"]
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert client.post(path+f"/documents/{doc['id']}/versions/{v1['id']}/review", headers=version_headers(users[3], v1),
        json={"decision": "ACCEPT", "comment": "Cannot accept an old version"}).status_code == 409
    from backend.services.documents import storage_root
    key = stored.storage_key.removeprefix("documents/")
    (storage_root()/key).write_bytes(b"Altered bytes")
    assert client.get(download, headers=hdr(users[0])).status_code == 409


def test_student_withdraws_mistaken_document_without_erasing_versions(workspace):
    client, users, _, _, session, path = workspace
    created = client.post(path+"/documents", headers=hdr(users[0]),
        json={"title": "Wrong report", "document_type": "SUPPORTING"}).json()
    uploaded = upload(client, users[0], path, created, b"Wrong attachment", "wrong.txt")
    assert uploaded.status_code == 201, uploaded.text
    doc = uploaded.json()
    withdraw = path+f"/documents/{doc['id']}/withdraw"
    assert client.post(withdraw, headers=version_headers(users[3], doc),
        json={"reason": "Wrong attachment"}).status_code == 403
    assert client.post(withdraw, headers=version_headers(users[0], doc), json={"reason": "x"}).status_code == 422
    assert client.post(withdraw, headers=version_headers(users[0], doc),
        json={"reason": "Uploaded the wrong faculty form"}).status_code == 204
    assert client.get(path+"/documents", headers=hdr(users[0])).json() == []
    assert session.get(m.Document, doc["id"]).state == "REVOKED"
    version = session.get(m.DocumentVersion, doc["versions"][0]["id"])
    assert version and session.get(m.StoredFile, version.stored_file_id)
    assert session.scalar(select(m.AuditEvent.id).where(m.AuditEvent.action == "DOCUMENT_WITHDRAWN"))


def test_advisor_can_request_reupload_before_scan_but_cannot_accept(workspace, monkeypatch):
    monkeypatch.setattr("backend.services.documents.file_scanner.scan", lambda file, path: file.scan_state)
    client, users, _, _, _, path = workspace
    created = client.post(path+"/documents", headers=hdr(users[0]),
        json={"title": "Report for advisor", "document_type": "SUPPORTING"}).json()
    uploaded = upload(client, users[0], path, created, b"Synthetic content", "report.txt")
    doc = uploaded.json()
    version = doc["versions"][0]
    review = path+f"/documents/{doc['id']}/versions/{version['id']}/review"
    assert client.post(review, headers=version_headers(users[3], version),
        json={"decision": "ACCEPT", "comment": "Cannot accept without scan"}).status_code == 409
    returned = client.post(review, headers=version_headers(users[3], version),
        json={"decision": "REVISION_REQUIRED", "comment": "Wrong form; submit a new report"})
    assert returned.status_code == 200, returned.text
    assert returned.json()["versions"][0]["state"] == "REVISION_REQUESTED"
    assert client.post(path+f"/documents/{doc['id']}/withdraw", headers=version_headers(users[0], returned.json()),
        json={"reason": "Cannot erase advisor review"}).status_code == 409
    revised = upload(client, users[0], path, returned.json(), b"Revised content", "report-revised.txt")
    assert revised.status_code == 201, revised.text
    assert [row["version_no"] for row in revised.json()["versions"]] == [2, 1]


def test_approved_document_print_copy_has_footer_and_preserves_source(workspace):
    client, users, _, _, session, path = workspace
    created = client.post(path+"/documents", headers=hdr(users[0]),
        json={"title": "Kế hoạch thực hiện", "document_type": "PLAN"})
    assert created.status_code == 201, created.text
    doc = created.json()
    source_pdf = synthetic_pdf()
    uploaded = upload(client, users[0], path, doc, source_pdf, "ke-hoach.pdf")
    assert uploaded.status_code == 201, uploaded.text
    version = uploaded.json()["versions"][0]
    print_path = path+f"/documents/{doc['id']}/versions/{version['id']}/print-copy"
    assert client.post(print_path, headers=hdr(users[0])).status_code == 409
    stored = session.get(m.StoredFile, session.get(m.DocumentVersion, version["id"]).stored_file_id)
    stored.scan_state = "CLEAN"
    session.commit()
    reviewed = client.post(path+f"/documents/{doc['id']}/versions/{version['id']}/review",
        headers=version_headers(users[3], version),
        json={"decision": "ACCEPT", "comment": "The plan is complete"})
    assert reviewed.status_code == 200, reviewed.text
    exported = client.post(print_path, headers=hdr(users[0]))
    assert exported.status_code == 200, exported.text
    code = exported.headers["x-document-code"]
    assert code.startswith("KH-")
    assert exported.headers["x-exported-at"]
    assert len(exported.headers["x-print-sha256"]) == 64
    footer = PdfReader(BytesIO(exported.content)).pages[0].extract_text()
    assert code in footer and ("5173" in footer) and ("Ma:" in footer or "ma so" in footer)
    event = session.scalar(select(m.AuditEvent).where(m.AuditEvent.action == "DOCUMENT_PRINT_COPY_EXPORTED"))
    assert event and event.after_hash == exported.headers["x-print-sha256"]
    original = client.get(path+f"/documents/{doc['id']}/versions/{version['id']}/download", headers=hdr(users[0]))
    assert original.content == source_pdf


def test_upload_validation_and_database_failure_remove_written_file(workspace, monkeypatch):
    client, users, _, _, session, path = workspace
    doc = client.post(path+"/documents", headers=hdr(users[0]), json={"title": "Results", "document_type": "SUPPORTING"}).json()
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


def test_upload_storage_failure_leaves_no_metadata_or_file(workspace, monkeypatch, tmp_path):
    client, users, _, _, session, path = workspace
    from backend.services import documents
    doc = client.post(path+"/documents", headers=hdr(users[0]),
        json={"title": "Results", "document_type": "SUPPORTING"}).json()
    stored_before = session.scalar(select(func.count(m.StoredFile.id)))
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(documents, "storage_root", lambda: blocked)
    with pytest.raises(OSError):
        upload(client, users[0], path, doc)
    assert client.get(path+"/documents", headers=hdr(users[0])).json()[0]["versions"] == []
    assert session.scalar(select(func.count(m.StoredFile.id))) == stored_before


def test_upload_delete_failure_does_not_hide_original_error(workspace, monkeypatch, tmp_path):
    from pathlib import Path

    client, users, _, _, session, path = workspace
    from backend.services import documents
    root = tmp_path / "documents"
    monkeypatch.setenv("KLTN_DOCUMENT_DIR", str(root))
    doc = client.post(path+"/documents", headers=hdr(users[0]),
        json={"title": "Results", "document_type": "SUPPORTING"}).json()
    original_commit = session.commit
    original_unlink = Path.unlink

    def fail_unlink(self, *args, **kwargs):
        if str(self).startswith(str(root)):
            raise OSError("Synthetic delete failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("Synthetic commit failure")))
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with pytest.raises(RuntimeError, match="Synthetic commit failure"):
        upload(client, users[0], path, doc)
    monkeypatch.setattr(session, "commit", original_commit)
    assert client.get(path+"/documents", headers=hdr(users[0])).json()[0]["versions"] == []
    leftovers = list(root.glob("*"))
    assert len(leftovers) == 1  # kept for tools/check_file_integrity to report, not silently lost
    original_unlink(leftovers[0])


def test_proposal_versions_scoped_review_and_paper_reference(workspace, monkeypatch, tmp_path):
    client, users, _, lecturers, session, path = workspace
    monkeypatch.setenv("KLTN_PROPOSAL_DIR", str(tmp_path / "proposals"))
    assert client.post(path+"/documents", headers=hdr(users[0]),
        json={"title": "Proposal", "document_type": "PROPOSAL"}).status_code == 409
    first = client.post(path+"/proposal/versions", headers={**hdr(users[0]), "If-Match": "0",
        "X-File-Name": "proposal.pdf", "Content-Type": "application/octet-stream"}, content=b"%PDF-1.4\nsynthetic proposal")
    assert first.status_code == 201, first.text
    row = first.json()
    assert row["state"] == "SUBMITTED" and row["current_version_no"] == 1
    stored = session.get(m.StoredFile, session.get(m.ProposalVersion, row["versions"][0]["id"]).stored_file_id)
    stored.scan_state = "CLEAN"  # test double for a real scanner; production keeps files quarantined
    session.commit()
    assert client.get(path+"/proposal", headers=hdr(users[2])).status_code == 404
    assert client.post(path+"/proposal/reviews", headers=version_headers(users[5], row),
        json={"decision": "CONFIRM", "comment": "Unauthorized"}).status_code == 404
    assigned = client.post(path+"/proposal/reviewers", headers=version_headers(users[4], row),
        json={"lecturer_id": str(lecturers[2].id), "reason": "Góp ý theo phân công"})
    assert assigned.status_code == 200, assigned.text
    row = assigned.json()
    assert client.post(path+"/proposal/reviews", headers=version_headers(users[5], row),
        json={"decision": "CONFIRM", "comment": "Cannot confirm"}).status_code == 403
    comment = client.post(path+"/proposal/reviews", headers=version_headers(users[5], row),
        json={"decision": "COMMENT", "comment": "Add evaluation data"})
    assert comment.status_code == 200, comment.text
    row = comment.json()
    revision = client.post(path+"/proposal/reviews", headers=version_headers(users[3], row),
        json={"decision": "REVISION_REQUIRED", "comment": "Add scope and data"})
    assert revision.status_code == 200, revision.text
    row = revision.json()
    assert row["state"] == "REVISION_REQUIRED"
    second = client.post(path+"/proposal/versions", headers={**version_headers(users[1], row),
        "X-File-Name": "proposal-v2.pdf", "Content-Type": "application/octet-stream"},
        content=b"%PDF-1.4\nrevised synthetic proposal")
    assert second.status_code == 201, second.text
    row = second.json()
    assert [v["version_no"] for v in row["versions"]] == [2, 1]
    v2_file = session.get(m.StoredFile, session.get(m.ProposalVersion, row["versions"][0]["id"]).stored_file_id)
    v2_file.scan_state = "CLEAN"
    session.commit()
    old = row["versions"][1]
    download = client.get(path+f"/proposal/versions/{old['id']}/download", headers=hdr(users[0]))
    assert download.status_code == 200 and download.content == b"%PDF-1.4\nsynthetic proposal"
    confirmed = client.post(path+"/proposal/reviews", headers=version_headers(users[3], row),
        json={"decision": "CONFIRM", "comment": "Version 2 acceptable"})
    assert confirmed.status_code == 200, confirmed.text
    row = confirmed.json()
    assert client.post(path+"/proposal/department-finalization", headers=version_headers(users[0], row),
        json={"reason": "Cannot finalize"}).status_code == 403
    finalized = client.post(path+"/proposal/department-finalization", headers=version_headers(users[4], row),
        json={"reason": "Confirmed against paper workflow"})
    assert finalized.status_code == 200, finalized.text
    row = finalized.json()
    assert row["department_confirmed"] is True
    assert client.post(path+"/proposal/dean-signed-copy", headers=version_headers(users[4], row),
        json={"official_ref": "SYN-REF-001"}).status_code == 403
    faculty_id = session.get(m.Department, lecturers[2].department_id).faculty_id
    position = m.OrganizationalPosition(id=uuid4(), code="FACULTY_DEAN", name="Synthetic dean")
    session.add(position)
    session.flush()
    session.add(m.PositionAssignment(id=uuid4(), lecturer_id=lecturers[2].id,
        position_id=position.id, faculty_id=faculty_id, effective_from=now()-timedelta(days=1), state="ACTIVE"))
    session.flush()
    signed = client.post(path+"/proposal/dean-signed-copy", headers=version_headers(users[5], row),
        json={"official_ref": "SYN-REF-001"})
    assert signed.status_code == 200, signed.text
    assert signed.json()["dean_confirmed"] is True
    assert client.post(path+"/proposal/versions", headers={**version_headers(users[0], signed.json()),
        "X-File-Name": "new.pdf"}, content=b"%PDF-1.4\nnew").status_code == 409
    assert client.get(path, headers=hdr(users[0])).json()["state"] == "ACTIVE"


def test_finalized_proposal_print_copy_has_footer_and_preserves_source(workspace, monkeypatch, tmp_path):
    client, users, _, _, session, path = workspace
    monkeypatch.setenv("KLTN_PROPOSAL_DIR", str(tmp_path / "proposals"))
    source_pdf = synthetic_pdf()
    uploaded = client.post(path+"/proposal/versions", headers={**hdr(users[0]), "If-Match": "0",
        "X-File-Name": "proposal.pdf", "Content-Type": "application/octet-stream"},
        content=source_pdf)
    assert uploaded.status_code == 201, uploaded.text
    proposal = uploaded.json()
    version_id = proposal["versions"][0]["id"]
    print_path = path+f"/proposal/versions/{version_id}/print-copy"
    assert client.post(print_path, headers=hdr(users[0])).status_code == 409
    stored = session.get(m.StoredFile, session.get(m.ProposalVersion, version_id).stored_file_id)
    stored.scan_state = "CLEAN"
    session.commit()
    confirmed = client.post(path+"/proposal/reviews", headers=version_headers(users[3], proposal),
        json={"decision": "CONFIRM", "comment": "Ready for department"})
    assert confirmed.status_code == 200, confirmed.text
    finalized = client.post(path+"/proposal/department-finalization",
        headers=version_headers(users[4], confirmed.json()), json={"reason": "Approved version"})
    assert finalized.status_code == 200, finalized.text
    exported = client.post(print_path, headers=hdr(users[0]))
    assert exported.status_code == 200, exported.text
    code = exported.headers["x-document-code"]
    assert code.startswith("DC-")
    assert exported.headers["x-exported-at"]
    assert len(exported.headers["x-print-sha256"]) == 64
    footer = PdfReader(BytesIO(exported.content)).pages[0].extract_text()
    assert code in footer and ("5173" in footer) and ("Ma:" in footer or "ma so" in footer)
    event = session.scalar(select(m.AuditEvent).where(m.AuditEvent.action == "PROPOSAL_PRINT_COPY_EXPORTED"))
    assert event and event.after_hash == exported.headers["x-print-sha256"]
    original = client.get(path+f"/proposal/versions/{version_id}/download", headers=hdr(users[0]))
    assert original.content == source_pdf


def test_proposal_upload_commit_failure_removes_file_and_version(workspace, monkeypatch, tmp_path):
    client, users, _, _, session, path = workspace
    root = tmp_path / "proposals"
    monkeypatch.setenv("KLTN_PROPOSAL_DIR", str(root))
    original_commit = session.commit
    monkeypatch.setattr(session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("Synthetic commit failure")))
    with pytest.raises(RuntimeError, match="Synthetic commit failure"):
        client.post(path+"/proposal/versions", headers={**hdr(users[0]), "If-Match":"0",
            "X-File-Name":"draft.pdf", "Content-Type":"application/octet-stream"},
            content=b"%PDF-1.4\nsynthetic rollback")
    monkeypatch.setattr(session, "commit", original_commit)
    assert list(root.glob("*")) == []
    assert client.get(path+"/proposal", headers=hdr(users[0])).json()["versions"] == []


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
        "lecturer_id": str(lecturers[2].id), "reason": "Wrong department"}).status_code == 404
    assert client.post(path+"/progress-reviewers", headers=version_headers(users[4], original), json={
        "lecturer_id": str(lecturers[2].id), "reason": "Wrong department"}).status_code == 422
    head = session.scalar(select(m.PositionAssignment).where(m.PositionAssignment.lecturer_id == lecturers[1].id))
    head.effective_to = now()-timedelta(hours=1)
    session.commit()
    # Coordinator assignment still allows metadata access, never substitutes for an expired head position.
    assert "advisor:nominate" not in client.get(path, headers=hdr(users[4])).json()["actions"]
    assert client.post(path+"/advisor-nomination", headers=version_headers(users[4], original), json={
        "lecturer_id": str(lecturers[0].id), "reason": "Expired position"}).status_code == 404
    assert client.post(path+"/progress-reviewers", headers=version_headers(users[4], original), json={
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
def test_lecturer_acceptance_rechecks_accounts_and_eligibility(scenario, change):
    client, users, students, lecturers, topic, session = scenario
    made = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={
        "topic_id": str(topic.id), "member_student_ids": [str(students[0].id)], "confirm_creator": True}).json()
    path = "/api/v1/topic-registrations/"+made["id"]
    sent = client.post(path+"/submit", headers=hdr(users[0])).json()
    if change == "ELIGIBILITY_REJECTED":
        session.add(m.EligibilitySnapshot(id=uuid4(), student_id=students[0].id, round_id=topic.round_id, version=2,
            evidence_ref="Synthetic replacement decision", captured_at=now(), confirmed_by=users[4].id, confirmed_at=now(), state="REJECTED"))
    else:
        users[0 if change == "STUDENT_LOCKED" else 3].status = "LOCKED"
    session.commit()
    blocked = client.post(path+"/lecturer-decision", headers=version_headers(users[3], sent), json={"decision": "ACCEPT"})
    assert blocked.status_code in {401, 409}, blocked.text
    assert session.scalar(select(m.Thesis.id).where(m.Thesis.registration_id == made["id"])) is None
    assert session.get(m.TopicRegistration, made["id"]).state == "SUBMITTED"
