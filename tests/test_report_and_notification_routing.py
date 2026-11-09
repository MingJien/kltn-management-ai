"""Report-book deadline and per-person notification routing on PostgreSQL."""
from datetime import timedelta
from uuid import uuid4

from test_core_workspace import workspace, open_milestone, synthetic_pdf, version_headers
from test_registration import hdr, scenario
from test_registration_forms import forms, upload as upload_registration_form
from backend.db.models import entities as m
from backend.services.theses import now


def notices(client, user, limit=100):
    response = client.get(f"/api/v1/notifications?limit={limit}", headers=hdr(user))
    assert response.status_code == 200, response.text
    return response.json()["items"]


def messages(client, user):
    return [item["message"] for item in notices(client, user)]


def test_round_deadline_is_public_but_report_submission_is_private(workspace):
    client, users, _, _, _, path = workspace
    requested = client.post(path + "/document-deadlines", headers=hdr(users[4]), json={
        "document_type": "REPORT",
        "due_at": (now() + timedelta(days=5)).isoformat(),
        "reason": "Hạn nộp cuốn báo cáo trước hội đồng",
    })
    assert requested.status_code == 200, requested.text

    for user in users:
        announcements = [item for item in notices(client, user)
                         if "đã thiết lập hạn nộp Cuốn báo cáo KLTN" in item["message"]]
        assert len(announcements) == 1
        assert announcements[0]["url"] == "/documents"

    doc = client.post(path + "/documents", headers=hdr(users[0]),
        json={"title": "Cuốn báo cáo KLTN", "document_type": "REPORT"}).json()
    uploaded = client.post(path + f"/documents/{doc['id']}/versions", headers={
        **version_headers(users[0], doc), "X-File-Name": "bao-cao.pdf",
        "Content-Type": "application/octet-stream"}, content=synthetic_pdf())
    assert uploaded.status_code == 201, uploaded.text

    advisor = notices(client, users[3])
    assert any(item["message"].startswith("Synthetic student đã nộp Cuốn báo cáo KLTN")
               and item["url"].endswith("?section=submissions&kind=REPORT") for item in advisor)
    # The thesis advisor alone receives the submission; other students/lecturers do not.
    assert not any("đã nộp Cuốn báo cáo KLTN" in item["message"] for item in notices(client, users[2]))
    assert not any("đã nộp Cuốn báo cáo KLTN" in item["message"] for item in notices(client, users[5]))


def test_progress_submission_notice_is_private_to_the_thesis_advisor(workspace):
    client, users, _, _, _, path = workspace
    milestone = open_milestone(client, users, path)
    made = client.post(path + "/progress-reports", headers=hdr(users[0]), json={
        "milestone_id": milestone["id"], "summary": "Báo cáo tuần", "reported_ratio": 35})
    assert made.status_code == 201, made.text

    assert any(item["message"].startswith("Synthetic student đã nộp báo cáo tiến độ")
               for item in notices(client, users[3]))
    assert not any("đã nộp báo cáo tiến độ" in item["message"] for item in notices(client, users[4]))
    assert not any("đã nộp báo cáo tiến độ" in item["message"] for item in notices(client, users[5]))
    assert not any("đã nộp báo cáo tiến độ" in item["message"] for item in notices(client, users[2]))


def test_proposal_upload_notifies_only_the_advisor(workspace, monkeypatch, tmp_path):
    client, users, _, _, _, path = workspace
    monkeypatch.setenv("KLTN_PROPOSAL_DIR", str(tmp_path / "proposals"))
    uploaded = client.post(path + "/proposal/versions", headers={
        **hdr(users[0]), "If-Match": "0", "X-File-Name": "proposal.pdf",
        "Content-Type": "application/octet-stream"}, content=b"%PDF-1.4\nsynthetic proposal")
    assert uploaded.status_code == 201, uploaded.text

    advisor = [item for item in notices(client, users[3]) if "đề cương" in item["message"]]
    assert advisor and advisor[0]["url"].endswith("?section=proposal")
    # Other students, another lecturer and the department head are not addressed.
    for outsider in (users[2], users[4], users[5]):
        assert not any("đề cương" in text for text in messages(client, outsider))


def test_assigned_reviewers_receive_a_private_assignment_notice(workspace, monkeypatch, tmp_path):
    client, users, _, lecturers, _, path = workspace
    monkeypatch.setenv("KLTN_PROPOSAL_DIR", str(tmp_path / "proposals"))
    uploaded = client.post(path + "/proposal/versions", headers={
        **hdr(users[0]), "If-Match": "0", "X-File-Name": "proposal.pdf",
        "Content-Type": "application/octet-stream"}, content=b"%PDF-1.4\nsynthetic proposal")
    assert uploaded.status_code == 201, uploaded.text
    proposal = uploaded.json()

    assigned = client.post(path + "/proposal/reviewers",
        headers=version_headers(users[4], proposal),
        json={"lecturer_id": str(lecturers[2].id), "reason": "Góp ý đề cương theo phân công"})
    assert assigned.status_code == 200, assigned.text
    assert any("góp ý đề cương" in text and "Góp ý đề cương theo phân công" in text
               for text in messages(client, users[5]))
    assert not any("góp ý đề cương" in text for text in messages(client, users[2]))

    thesis = client.get(path, headers=hdr(users[4])).json()
    made = client.post(path + "/progress-reviewers",
        headers=version_headers(users[4], thesis),
        json={"lecturer_id": str(lecturers[2].id), "reason": "Góp ý chéo tiến độ"})
    assert made.status_code == 403, made.text
    assert not any("góp ý chéo tiến độ" in text for text in messages(client, users[5]))
    assert not any("góp ý chéo tiến độ" in text for text in messages(client, users[0]))


def test_registration_form_upload_notifies_receiving_lecturer_and_department_head(forms):
    client, users, _, _, _, reg, path = forms
    submitted = client.post(f"/api/v1/topic-registrations/{reg['id']}/submit",
                            headers=hdr(users[0]))
    assert submitted.status_code == 200, submitted.text
    made = upload_registration_form(client, users[0], path)
    assert made.status_code == 201, made.text

    assert any("đơn Mẫu 1a" in text for text in messages(client, users[3]))
    assert any("đơn Mẫu 1a" in text for text in messages(client, users[4]))
    # Unrelated students and lecturers get no copy of the private registration file.
    assert not any("đơn Mẫu 1a" in text for text in messages(client, users[1]))
    assert not any("đơn Mẫu 1a" in text for text in messages(client, users[5]))


def test_dean_confirmation_notifies_students_advisor_and_department_head(workspace, monkeypatch, tmp_path):
    client, users, _, lecturers, session, path = workspace
    monkeypatch.setenv("KLTN_PROPOSAL_DIR", str(tmp_path / "proposals"))
    uploaded = client.post(path + "/proposal/versions", headers={
        **hdr(users[0]), "If-Match": "0", "X-File-Name": "proposal.pdf",
        "Content-Type": "application/octet-stream"}, content=b"%PDF-1.4\nsynthetic proposal")
    assert uploaded.status_code == 201, uploaded.text
    row = uploaded.json()
    stored = session.get(m.StoredFile, session.get(m.ProposalVersion, row["versions"][0]["id"]).stored_file_id)
    stored.scan_state = "CLEAN"
    session.commit()

    confirmed = client.post(path + "/proposal/reviews", headers=version_headers(users[3], row),
        json={"decision": "CONFIRM", "comment": "Đề cương đạt"})
    assert confirmed.status_code == 200, confirmed.text
    finalized = client.post(path + "/proposal/department-finalization",
        headers=version_headers(users[4], confirmed.json()), json={"reason": "Bộ môn chốt"})
    assert finalized.status_code == 200, finalized.text

    faculty_id = session.get(m.Department, lecturers[2].department_id).faculty_id
    position = m.OrganizationalPosition(id=uuid4(), code="FACULTY_DEAN", name="Synthetic dean")
    session.add(position)
    session.flush()
    session.add(m.PositionAssignment(id=uuid4(), lecturer_id=lecturers[2].id,
        position_id=position.id, faculty_id=faculty_id,
        effective_from=now() - timedelta(days=1), state="ACTIVE"))
    session.commit()
    signed = client.post(path + "/proposal/dean-signed-copy",
        headers=version_headers(users[5], finalized.json()), json={"official_ref": "SYN-REF-001"})
    assert signed.status_code == 200, signed.text

    for recipient in (users[0], users[1], users[3], users[4]):
        assert any("Trưởng khoa đã ghi nhận bản đề cương" in text for text in messages(client, recipient))
    assert not any("Trưởng khoa đã ghi nhận bản đề cương" in text for text in messages(client, users[2]))

def test_open_round_announces_to_active_accounts_without_theses(scenario):
    client, users, _, _, topic, session = scenario
    admin = users[5]
    admin.base_role = "ADMIN"
    existing = session.get(m.ThesisRound, topic.round_id)
    year = session.get(m.AcademicYear, existing.academic_year_id)
    round_ = m.ThesisRound(id=uuid4(), academic_year_id=year.id, code="SYN-NOTICE",
        round_type="MAIN", opens_at=now(), closes_at=now()+timedelta(days=5), state="DRAFT")
    session.add(round_)
    session.commit()

    response = client.patch(f"/api/v1/admin/rounds/{round_.id}",
        headers={**hdr(admin), "If-Match": str(round_.row_version)},
        json={"state":"OPEN", "reason":"Synthetic announcement"})
    assert response.status_code == 200, response.text
    for user in users:
        assert sum("Khoa đã mở đợt đăng ký KLTN SYN-NOTICE" in text
                   for text in messages(client, user)) == 1

def test_registration_round_extension_checks_authority_audit_and_announces(scenario):
    from sqlalchemy import select
    client, users, _, _, topic, session = scenario
    admin = users[5]
    admin.base_role = "ADMIN"
    existing = session.get(m.ThesisRound, topic.round_id)
    year = session.get(m.AcademicYear, existing.academic_year_id)
    year.state = "ACTIVE"
    round_ = m.ThesisRound(id=uuid4(), academic_year_id=year.id, code="SYN-EXTEND",
        round_type="MAIN", opens_at=now()-timedelta(days=7),
        closes_at=now()-timedelta(days=2), state="OPEN")
    session.add(round_)
    session.commit()
    old_end, version = round_.closes_at, round_.row_version
    path = f"/api/v1/admin/rounds/{round_.id}/extend"
    data = {"closes_at":(now()+timedelta(days=2)).isoformat(),
            "basis_ref":"QĐ DEMO 01", "reason":"Gia hạn theo kế hoạch Khoa"}
    assert client.post(path, headers={**hdr(users[4]),"If-Match":str(version)}, json=data).status_code == 403
    bad = {**data,"closes_at":old_end.isoformat()}
    assert client.post(path, headers={**hdr(admin),"If-Match":str(version)}, json=bad).status_code == 422
    response = client.post(path, headers={**hdr(admin),"If-Match":str(version)}, json=data)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "OPEN"
    assert client.post(path, headers={**hdr(admin),"If-Match":str(version)}, json=data).status_code == 409
    event = session.scalar(select(m.AuditEvent).where(
        m.AuditEvent.action=="ROUND_REGISTRATION_EXTENDED", m.AuditEvent.resource_id==round_.id))
    assert event and event.source_reference=="QĐ DEMO 01" and old_end.isoformat() in event.reason
    for user in users:
        assert sum("gia hạn đăng ký KLTN đợt SYN-EXTEND" in text for text in messages(client, user)) == 1
    round_.state = "CLOSED"
    session.commit()
    response = client.post(path, headers={**hdr(admin),"If-Match":str(round_.row_version)},
        json={**data,"closes_at":(now()+timedelta(days=3)).isoformat()})
    assert response.status_code == 409


def test_admin_reopens_closed_registration_round_only_with_explicit_confirmation(scenario):
    client,users,_,_,topic,session=scenario
    admin=users[5]
    admin.base_role="ADMIN"
    round_=session.get(m.ThesisRound,topic.round_id)
    round_.state="CLOSED"
    session.commit()
    payload={"closes_at":(now()+timedelta(days=12)).isoformat(),"basis_ref":"QD-SYN-REOPEN",
        "reason":"Supplementary registration intake","reopen_closed":True}
    response=client.post(f"/api/v1/admin/rounds/{round_.id}/extend",
        headers=version_headers(admin,{"row_version":round_.row_version}),json=payload)
    assert response.status_code==200,response.text
    assert response.json()["state"]=="OPEN"
    history=client.get(f"/api/v1/admin/rounds/{round_.id}/history",headers=hdr(admin)).json()
    assert history[0]["action"]=="ROUND_REGISTRATION_REOPENED"
    assert history[0]["reference"]=="QD-SYN-REOPEN"
    assert client.get(f"/api/v1/admin/rounds/{round_.id}/history",headers=hdr(users[0])).status_code==403
