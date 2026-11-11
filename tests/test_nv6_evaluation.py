"""Real PostgreSQL stories for NV6; file clearance is simulated only in this suite."""
from datetime import timedelta
import hashlib
import io
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from test_registration import hdr, scenario
from test_core_workspace import workspace, synthetic_pdf, version_headers
from backend.db.models import entities as m
from backend.services.evaluation import FORM_FIELDS
from backend.services.theses import now


@pytest.fixture
def evaluation(workspace):
    client, users, students, lecturers, session, path = workspace
    deadline = client.post(path+"/document-deadlines", headers=hdr(users[4]), json={
        "document_type":"REPORT", "due_at":(now()+timedelta(days=7)).isoformat(), "reason":"Synthetic faculty report deadline"})
    assert deadline.status_code == 200, deadline.text
    doc = client.post(path+"/documents", headers=hdr(users[0]), json={"document_type":"REPORT","title":"Synthetic thesis report"}).json()
    upload = client.post(path+f"/documents/{doc['id']}/versions", headers={**version_headers(users[0],doc),
        "X-File-Name":"report.pdf", "Content-Type":"application/octet-stream"}, content=synthetic_pdf())
    assert upload.status_code == 201, upload.text
    version = session.get(m.DocumentVersion, UUID(upload.json()["versions"][0]["id"]))
    session.get(m.StoredFile, version.stored_file_id).scan_state = "CLEAN"
    session.commit()
    return workspace, doc


def get(ctx, user=4):
    client, users, _, _, _, path = ctx
    result=client.get(path+"/evaluation",headers=hdr(users[user]))
    assert result.status_code==200,result.text
    return result.json()


def assign(ctx, user=5, expected=None):
    client,users,_,lecturers,_,path=ctx
    return client.post(path+"/evaluation/reviewers",headers=version_headers(users[4],{"row_version":expected or get(ctx)["row_version"]}),json={
        "lecturer_id":str(lecturers[user-3].id),"due_at":(now()+timedelta(days=4)).isoformat(),
        "source_reference":"QD-SYNTHETIC-01","reason":"Synthetic academic assignment"})


def create(ctx, member=0, user=3, kind="ADVISOR"):
    client,users,_,_,_,path=ctx
    data=get(ctx,user)
    return client.post(path+"/evaluation/reviews",headers=version_headers(users[user],data),json={
        "thesis_member_id":get(ctx)["members"][member]["id"],"report_version_id":data["report"]["id"],
        "kind":kind,"reason":"Synthetic review for this student and report"})


def complete_review(ctx, member=0, user=3, kind="ADVISOR", allow=True):
    client,users,_,_,session,path=ctx
    made=create(ctx,member,user,kind)
    assert made.status_code==201,made.text
    review=made.json();base=path+f"/evaluation/reviews/{review['id']}"
    data={"sections":{f["key"]:"Synthetic assessment: "+f["key"] for f in FORM_FIELDS[kind]},"source_reference":"SYNTHETIC-SIGNED-FORM"}
    if kind=="ADVISOR":data.update(thesis_completed=True,allow_defense=allow)
    saved=client.put(base,headers=version_headers(users[user],review),json=data)
    assert saved.status_code==200,saved.text
    review=saved.json()
    upload=client.post(base+"/signed-copy",headers={**version_headers(users[user],review),"X-File-Name":"signed.pdf","Content-Type":"application/octet-stream"},content=synthetic_pdf())
    assert upload.status_code==201,upload.text
    review=upload.json()
    assert review["signed_file"]["scan_state"]!="CLEAN"
    blocked=client.post(base+"/submit",headers=version_headers(users[user],review),json={"confirm_signed_copy":True})
    assert blocked.status_code==409,blocked.text
    item=session.get(m.ThesisReview,UUID(review["id"]))
    session.get(m.StoredFile,item.signed_file_id).scan_state="CLEAN";session.commit()
    sent=client.post(base+"/submit",headers=version_headers(users[user],review),json={"confirm_signed_copy":True})
    assert sent.status_code==200,sent.text
    return sent.json()


def check(ctx, member=0, discipline="CLEAR", data_override=None):
    client,users,_,_,_,path=ctx
    data=get(ctx);student=data["members"][member]
    return client.post(path+"/evaluation/eligibility",headers=version_headers(users[4],data),json={
        "thesis_member_id":student["id"],"report_version_id":data["report"]["id"],
        "advisor_review_id":student["eligibility"]["advisor_review_id"],"discipline_status":discipline,
        "source_reference":"SYNTHETIC-STUDENT-AFFAIRS-01","reason":"Verified against synthetic official source",**(data_override or {})})


def test_discipline_can_be_recorded_while_changed_membership_needs_review(evaluation, monkeypatch):
    from backend.services import membership_revision

    ctx, _ = evaluation
    client, users, _, _, _, path = ctx
    monkeypatch.setattr(membership_revision, "changed_at", lambda session, thesis_id: now())
    before = get(ctx)
    assert before["workflow_blockers"]
    assert create(ctx).status_code == 409

    recorded = check(ctx)
    assert recorded.status_code == 200, recorded.text
    result = recorded.json()
    eligibility = result["members"][0]["eligibility"]
    assert eligibility["discipline_status"] == "CLEAR"
    assert next(item for item in eligibility["conditions"] if item["key"] == "discipline")["met"]
    assert eligibility["state"] != "ELIGIBLE"
    assert result["state"] != "READY_FOR_DEFENSE"
    assert client.post(path + "/evaluation/eligibility", headers=version_headers(users[3], result), json={
        "thesis_member_id": result["members"][0]["id"], "report_version_id": result["report"]["id"],
        "advisor_review_id": None, "discipline_status": "CLEAR", "source_reference": "SYNTHETIC",
        "reason": "No department authority",
    }).status_code == 403


def test_supporting_upload_remains_open_after_eligibility_is_finalized(evaluation):
    ctx, _ = evaluation
    client, users, _, _, session, path = ctx
    for member in range(len(get(ctx)["members"])):
        complete_review(ctx, member=member)
        assert check(ctx, member=member).status_code == 200
    assert get(ctx)["state"] == "READY_FOR_DEFENSE"
    workspace = client.get(path, headers=hdr(users[0])).json()
    assert "document:supporting_submit" in workspace["actions"]
    assert "document:submit" not in workspace["actions"]
    made = client.post(path+"/documents", headers=hdr(users[0]), json={
        "document_type":"SUPPORTING", "title":"Minh chứng công bố khoa học"})
    assert made.status_code == 201, made.text
    document = made.json()
    uploaded = client.post(path+f"/documents/{document['id']}/versions", headers={
        **version_headers(users[0], document), "X-File-Name":"supporting.pdf", "Content-Type":"application/octet-stream"},
        content=synthetic_pdf())
    assert uploaded.status_code == 201, uploaded.text
    version = session.get(m.DocumentVersion, UUID(uploaded.json()["versions"][0]["id"]))
    session.get(m.StoredFile, version.stored_file_id).scan_state = "CLEAN"
    session.commit()
    downloaded = client.get(path+f"/documents/{document['id']}/versions/{version.id}/download", headers=hdr(users[0]))
    assert downloaded.status_code == 200
    assert "Minh-chung-cong-bo-khoa-hoc-" in downloaded.headers["Content-Disposition"]
    assert "-v1.pdf" in downloaded.headers["Content-Disposition"]
    assert downloaded.content == synthetic_pdf()
    assert client.post(path+"/documents", headers=hdr(users[0]), json={
        "document_type":"REPORT", "title":"Wrong stage report"}).status_code == 409


def test_assignment_authority_conflict_concurrency_and_revoked_access(evaluation):
    ctx,_=evaluation;client,users,_,lecturers,session,path=ctx
    initial=get(ctx)
    assert client.get(path+"/evaluation",headers=hdr(users[5])).status_code==404
    body={"lecturer_id":str(lecturers[2].id),"due_at":(now()+timedelta(days=4)).isoformat(),"reason":"Scoped assignment","source_reference":"QD-SYN"}
    assert client.post(path+"/evaluation/reviewers",headers=version_headers(users[3],get(ctx,3)),json=body).status_code==403
    assert assign(ctx,3).status_code==422  # no self-supervision/review conflict
    made=assign(ctx);assert made.status_code==201,made.text
    assert assign(ctx,expected=initial["row_version"]).status_code==409
    assert assign(ctx).status_code==409
    reviewer=get(ctx,5)
    assert "evaluation:reviewer" in reviewer["actions"]
    assert client.get(path+"/documents",headers=hdr(users[5])).status_code==403
    assert client.get(path+"/progress-reports",headers=hdr(users[5])).status_code==403
    assert client.get(path+f"/evaluation/reports/{reviewer['report']['id']}",headers=hdr(users[5])).status_code==200
    notices=client.get("/api/v1/notifications",headers=hdr(users[5])).json()["items"]
    assert any(n["url"].startswith("/evaluation/") for n in notices)
    assignment=made.json()["assignments"][0]
    revoked=client.post(path+f"/evaluation/reviewers/{assignment['id']}/revoke",headers=version_headers(users[4],get(ctx)),json={"reason":"Replace reviewer with documented cause"})
    assert revoked.status_code==200,revoked.text
    assert client.get(path+"/evaluation",headers=hdr(users[5])).status_code==404
    assert client.get(path+f"/evaluation/reports/{reviewer['report']['id']}",headers=hdr(users[5])).status_code==404
    inbox=client.get("/api/v1/notifications",headers=hdr(users[5])).json()["items"]
    assert not any(n["url"].startswith("/evaluation/") for n in inbox)
    assert any("thu hồi phân công" in n["message"] for n in inbox)


def test_two_reviewers_and_invalid_deadlines(evaluation):
    ctx,_=evaluation;client,users,_,lecturers,session,path=ctx
    assert assign(ctx).status_code==201
    assert assign(ctx,4).status_code==201
    # Repeated or conflicting assignments cannot use an extra slot.
    assert assign(ctx,3).status_code==422
    user=m.UserAccount(id=uuid4(),external_subject="synthetic-"+uuid4().hex,base_role="LECTURER",status="ACTIVE")
    lecturer=m.LecturerProfile(id=uuid4(),user_id=user.id,department_id=lecturers[0].department_id,
        lecturer_code="SYN-"+uuid4().hex[:16],display_name="Synthetic fourth lecturer")
    session.add(user);session.flush();session.add(lecturer);session.commit()
    body={"lecturer_id":str(lecturer.id),"due_at":(now()+timedelta(days=3)).isoformat(),"reason":"Third distinct reviewer is not allowed","source_reference":"SYN"}
    assert client.post(path+"/evaluation/reviewers",headers=version_headers(users[4],get(ctx)),json=body).status_code==409
    body={"lecturer_id":str(lecturers[2].id),"due_at":"2026-01-01T00:00:00","reason":"No timezone in date","source_reference":"SYN"}
    assert client.post(path+"/evaluation/reviewers",headers=version_headers(users[4],get(ctx)),json=body).status_code==422


def test_private_draft_fields_and_optimistic_edit(evaluation):
    ctx,_=evaluation;client,users,_,_,_,path=ctx
    assert assign(ctx).status_code==201
    review=create(ctx).json();base=path+f"/evaluation/reviews/{review['id']}"
    assert get(ctx,0)["reviews"]==[] and get(ctx,4)["reviews"]==[] and get(ctx,5)["reviews"]==[]
    assert create(ctx).status_code==409
    assert client.put(base,headers=version_headers(users[5],review),json={"sections":{}}).status_code==403
    assert client.put(base,headers=version_headers(users[3],review),json={"sections":{"invented":"Not in form"}}).status_code==422
    saved=client.put(base,headers=version_headers(users[3],review),json={"sections":{"attitude":"  Saved private draft  "}})
    assert saved.status_code==200,saved.text
    assert saved.json()["sections"]["attitude"]=="Saved private draft"
    assert client.put(base,headers=version_headers(users[3],review),json={"sections":{}}).status_code==409
    assert client.post(base+"/submit",headers=version_headers(users[3],saved.json()),json={"confirm_signed_copy":True}).status_code==422


def test_signed_submitted_review_is_immutable_and_student_specific(evaluation):
    ctx,_=evaluation;client,users,_,_,_,path=ctx
    sent=complete_review(ctx)
    data=get(ctx);member_id=sent["thesis_member_id"]
    student_id=next(i for i in (0,1) if get(ctx,i)["members"][0]["id"]==member_id)
    other=1-student_id
    assert any(r["id"]==sent["id"] for r in get(ctx,student_id)["reviews"])
    assert get(ctx,other)["reviews"]==[]
    base=path+f"/evaluation/reviews/{sent['id']}"
    assert client.put(base,headers=version_headers(users[3],sent),json={"sections":{}}).status_code==409
    assert client.get(base+"/signed-copy",headers=hdr(users[other])).status_code==404
    assert client.get(base+"/signed-copy",headers=hdr(users[student_id])).content==synthetic_pdf()
    assert create(ctx).status_code==201
    assert len(get(ctx,student_id)["reviews"])==1  # new draft remains private


def test_three_school_conditions_per_student_without_reviewer_gate_and_reopening(evaluation):
    ctx,_=evaluation;client,users,_,_,_,path=ctx
    assert check(ctx).json()["members"][0]["eligibility"]["state"]=="BLOCKED"
    for index in range(len(get(ctx)["members"])):
        complete_review(ctx,index)
        result=check(ctx,index)
        assert result.status_code==200,result.text
    ready=get(ctx)
    assert ready["state"]=="READY_FOR_DEFENSE"
    assert all(member["eligibility"]["state"]=="ELIGIBLE" for member in ready["members"])
    assert ready["assignments"]==[]  # no invented fourth school condition
    assert create(ctx).status_code==409
    # PB may still complete the independent review after school eligibility is confirmed.
    assert assign(ctx).status_code==201
    assert complete_review(ctx,user=5,kind="REVIEWER")["state"]=="SUBMITTED"
    reopened=client.post(path+"/evaluation/reopen",headers=version_headers(users[4],get(ctx)),json={"reason":"Reopen for corrected report and written consent"})
    assert reopened.status_code==200,reopened.text
    assert reopened.json()["state"]=="IN_PROGRESS"
    assert all(member["eligibility"]["state"]=="BLOCKED" for member in reopened.json()["members"])
    assert create(ctx).status_code==201
    assert len(get(ctx)["eligibility_history"])>=4


@pytest.mark.parametrize("discipline",["WARNING_OR_HIGHER","UNKNOWN"])
def test_discipline_condition_cannot_be_overridden(evaluation,discipline):
    ctx,_=evaluation
    complete_review(ctx)
    checked=check(ctx,discipline=discipline)
    assert checked.status_code==200,checked.text
    assert checked.json()["members"][0]["eligibility"]["state"]=="BLOCKED"
    assert checked.json()["state"]!="READY_FOR_DEFENSE"


def test_advisor_refusal_is_not_consent(evaluation):
    ctx,_=evaluation
    complete_review(ctx,allow=False)
    checked=check(ctx)
    assert checked.status_code==200,checked.text
    assert not checked.json()["members"][0]["eligibility"]["conditions"][2]["met"]


def test_new_report_invalidates_review_and_eligibility_without_overwriting_history(evaluation):
    ctx,doc=evaluation;client,users,_,_,session,path=ctx
    sent=complete_review(ctx)
    checked=check(ctx).json()
    current=client.get(path+"/documents",headers=hdr(users[0])).json()[0]
    uploaded=client.post(path+f"/documents/{doc['id']}/versions",headers={**version_headers(users[0],current),
        "X-File-Name":"report-v2.pdf","Content-Type":"application/octet-stream"},content=synthetic_pdf())
    assert uploaded.status_code==201,uploaded.text
    data=get(ctx)
    assert data["members"][0]["eligibility"]["state"]=="STALE"
    assert data["members"][0]["eligibility"]["advisor_review_id"] is None
    assert sent["id"] in {r["id"] for r in data["reviews"]}
    assert check(ctx,data_override={"report_version_id":checked["report"]["id"],"advisor_review_id":sent["id"]}).status_code==409


def test_editing_contents_detaches_previous_signed_copy(evaluation):
    ctx,_=evaluation;client,users,_,_,session,path=ctx
    draft=create(ctx).json();base=path+f"/evaluation/reviews/{draft['id']}"
    uploaded=client.post(base+"/signed-copy",headers={**version_headers(users[3],draft),"X-File-Name":"signed.pdf","Content-Type":"application/octet-stream"},content=synthetic_pdf()).json()
    assert uploaded["signed_file"]
    saved=client.put(base,headers=version_headers(users[3],uploaded),json={"sections":{"attitude":"Changed after signing"}})
    assert saved.status_code==200,saved.text
    assert saved.json()["signed_file"] is None


def test_reviewer_revocation_preserves_submitted_history_and_reassignment_creates_new_identity(evaluation):
    ctx,_=evaluation;client,users,_,_,_,path=ctx
    assert assign(ctx).status_code==201
    sent=complete_review(ctx,user=5,kind="REVIEWER")
    data=get(ctx);assignment=data["assignments"][0]
    assert client.post(path+f"/evaluation/reviewers/{assignment['id']}/revoke",headers=version_headers(users[4],data),json={"reason":"Replace with documented academic cause"}).status_code==200
    assert sent["id"] in {r["id"] for r in get(ctx)["reviews"]}
    assert assign(ctx).status_code==201
    assert create(ctx,user=5,kind="REVIEWER").status_code==201


def test_notification_receipt_and_student_personal_privacy(evaluation):
    ctx,_=evaluation;client,users,_,_,_,path=ctx
    sent=complete_review(ctx)
    check(ctx,discipline="WARNING_OR_HIGHER")
    data=get(ctx)
    member=next(m for m in data["members"] if m["id"]==sent["thesis_member_id"])
    own=next(index for index in (0,1) if get(ctx,index)["members"][0]["id"]==member["id"])
    other=1-own
    assert get(ctx,other)["eligibility_history"]==[]
    inbox=client.get("/api/v1/notifications?limit=100",headers=hdr(users[own])).json()["items"]
    assert any(n["url"].startswith("/evaluation/") for n in inbox)
    outsiders=client.get("/api/v1/notifications?limit=100",headers=hdr(users[2])).json()["items"]
    assert not any(n["url"].startswith("/evaluation/") for n in outsiders)
    assert client.get(path+"/evaluation",headers=hdr(users[2])).status_code==404
    activity=client.get("/api/v1/activity?q=SYNTHETIC-STUDENT-AFFAIRS",headers=hdr(users[other])).json()
    assert not any(item["action"]=="DEFENSE_ELIGIBILITY_CHECKED" for item in activity["items"])


def test_reviewer_deadline_extension_has_authority_concurrency_and_notification(evaluation):
    ctx,_=evaluation;client,users,_,_,session,path=ctx
    assert assign(ctx).status_code==201
    data=get(ctx);assignment=data["assignments"][0]
    endpoint=path+f"/evaluation/reviewers/{assignment['id']}/deadline"
    body={"due_at":(now()+timedelta(days=8)).isoformat(),"reason":"Faculty grants additional time","source_reference":"SYNTHETIC-EXTENSION"}
    assert client.post(endpoint,headers=version_headers(users[5],get(ctx,5)),json=body).status_code==403
    made=client.post(endpoint,headers=version_headers(users[4],data),json=body)
    assert made.status_code==200,made.text
    assert client.post(endpoint,headers=version_headers(users[4],data),json=body).status_code==409
    assert client.post(endpoint,headers=version_headers(users[4],get(ctx)),json=body).status_code==422
    assert session.scalar(select(m.AuditEvent.id).where(m.AuditEvent.action=="THESIS_REVIEW_DEADLINE_EXTENDED"))
    inbox=client.get("/api/v1/notifications",headers=hdr(users[5])).json()["items"]
    assert any("gia hạn gửi nhận xét" in item["message"] for item in inbox)


def test_faculty_wide_reviewer_accepts_other_department_but_rejects_locked_account(evaluation):
    ctx,_=evaluation;client,users,_,lecturers,session,path=ctx
    original=session.get(m.Department,lecturers[2].department_id)
    other=m.Department(id=uuid4(),faculty_id=original.faculty_id,code="SYN-"+uuid4().hex[:12],name="Synthetic other department")
    session.add(other);session.flush();lecturers[2].department_id=other.id;session.commit()
    assigned=assign(ctx)
    assert assigned.status_code==201,assigned.text
    # End the first assignment before testing a locked candidate.
    row=session.scalar(select(m.ReviewerAssignment).where(m.ReviewerAssignment.lecturer_id==lecturers[2].id,m.ReviewerAssignment.state=="ACTIVE"))
    row.state="REVOKED"
    lecturers[2].department_id=original.id;users[5].status="LOCKED";session.commit()
    assert assign(ctx).status_code==422


@pytest.mark.parametrize("kind,user",[("ADVISOR",3),("REVIEWER",5)])
def test_export_fills_official_form_preserves_reference_and_requires_saved_complete_draft(evaluation,kind,user):
    from backend.services import form_templates
    meta=next(meta for meta in form_templates.OFFICIAL_FORMS if meta["id"]==("mau-07" if kind=="ADVISOR" else "mau-08"))
    source=form_templates.OFFICIAL_DIR/meta["filename"]
    if not source.is_file():pytest.skip("Faculty's retained official review template is not provisioned")
    original=source.read_bytes()
    ctx,_=evaluation;client,users,_,_,_,path=ctx
    if kind=="REVIEWER":assert assign(ctx).status_code==201
    review=create(ctx,user=user,kind=kind).json();base=path+f"/evaluation/reviews/{review['id']}"
    assert client.post(base+"/print-copy",headers=version_headers(users[user],review)).status_code==422
    payload={"sections":{field["key"]:"SYNTHETIC EXPORT TEXT "+field["key"] for field in FORM_FIELDS[kind]}}
    if kind=="ADVISOR":payload.update(thesis_completed=True,allow_defense=True)
    saved=client.put(base,headers=version_headers(users[user],review),json=payload).json()
    result=client.post(base+"/print-copy",headers=version_headers(users[user],saved))
    assert result.status_code==200,result.text
    assert result.headers["X-Print-SHA256"]==hashlib.sha256(result.content).hexdigest()
    if kind == "ADVISOR":
        document = __import__("docx").Document(io.BytesIO(result.content))
        heading = next(p for p in document.paragraphs if p.text.strip().startswith("1. Về tinh thần"))
        assert any(run.italic and "Về tinh thần" in run.text for run in heading.runs)
        assert any("SYNTHETIC EXPORT TEXT attitude" in p.text for p in document.paragraphs)
    with zipfile.ZipFile(io.BytesIO(original)) as before,zipfile.ZipFile(io.BytesIO(result.content)) as after:
        editable={"word/document.xml","word/_rels/document.xml.rels","[Content_Types].xml"}
        assert all(before.read(name)==after.read(name) for name in before.namelist() if name not in editable)
        xml=after.read("word/document.xml").decode()
        assert "SYNTHETIC EXPORT TEXT" in xml
        assert "Synthetic student" in xml
        assert "Bản để ký" in after.read("word/footerNv6Review.xml").decode()
    assert source.read_bytes()==original
    assert client.post(base+"/print-copy",headers=version_headers(users[0],saved)).status_code in (403,404)
    assert client.post(base+"/print-copy",headers=version_headers(users[user],review)).status_code==409

def test_submit_without_scan_then_scoped_paper_receipt(evaluation):
    ctx,_=evaluation;client,users,_,_,session,path=ctx
    review=create(ctx).json();base=path+f"/evaluation/reviews/{review['id']}"
    payload={"sections":{f["key"]:"Complete authenticated review "+f["key"] for f in FORM_FIELDS["ADVISOR"]},"thesis_completed":True,"allow_defense":True}
    saved=client.put(base,headers=version_headers(users[3],review),json=payload).json()
    assert client.post(base+"/submit",headers=version_headers(users[3],saved),json={}).status_code==422
    sent=client.post(base+"/submit",headers=version_headers(users[3],saved),json={"confirm_content":True})
    assert sent.status_code==200,sent.text
    sent=sent.json();assert sent["signed_file"] is None
    eligibility=get(ctx)["members"][0]["eligibility"]
    assert next(c for c in eligibility["conditions"] if c["key"]=="completion")["met"]
    assert not next(c for c in eligibility["conditions"] if c["key"]=="consent")["met"]
    export=client.post(base+"/print-copy",headers=version_headers(users[3],sent))
    assert export.status_code==200,export.text
    code=export.headers["X-Document-Code"]
    receipt={"reference":"PAPER-REGISTER-2026-01","export_code":code,"confirm_paper":True}
    assert client.post(base+"/paper-receipt",headers=version_headers(users[5],sent),json=receipt).status_code in (403,404)
    session.add(m.ResourceAssignment(id=uuid4(),user_id=users[5].id,round_id=session.get(m.Thesis,UUID(path.split("/")[-1])).round_id,
        assignment_type="REVIEW_RECORDS_MANAGER",state="ACTIVE",effective_from=now()))
    session.commit()
    assert "evaluation:record" in get(ctx,5)["actions"]
    bad=client.post(base+"/paper-receipt",headers=version_headers(users[5],sent),json={**receipt,"export_code":"OTHER-EXPORT-CODE"})
    assert bad.status_code==422
    received=client.post(base+"/paper-receipt",headers=version_headers(users[5],sent),json=receipt)
    assert received.status_code==200,received.text
    item=next(r for r in received.json()["reviews"] if r["id"]==sent["id"])
    assert item["paper_receipt"]["reference"]==receipt["reference"]
    assert client.post(base+"/paper-receipt",headers=version_headers(users[5],item),json=receipt).status_code==409
    assert next(c for c in get(ctx)["members"][0]["eligibility"]["conditions"] if c["key"]=="consent")["met"]

def test_changed_review_cannot_receive_paper_for_old_export(evaluation):
    ctx,_=evaluation;client,users,_,_,_,path=ctx
    r=create(ctx).json();base=path+f"/evaluation/reviews/{r['id']}"
    payload={"sections":{f["key"]:"Original text "+f["key"] for f in FORM_FIELDS["ADVISOR"]},"thesis_completed":True,"allow_defense":True}
    r=client.put(base,headers=version_headers(users[3],r),json=payload).json()
    export=client.post(base+"/print-copy",headers=version_headers(users[3],r))
    assert export.status_code==200,export.text
    payload["sections"]["attitude"]="Corrected content after first print"
    r=client.put(base,headers=version_headers(users[3],r),json=payload).json()
    r=client.post(base+"/submit",headers=version_headers(users[3],r),json={"confirm_content":True}).json()
    result=client.post(base+"/paper-receipt",headers=version_headers(users[4],r),json={
        "reference":"PAPER-OLD-CONTENT","export_code":export.headers["X-Document-Code"],"confirm_paper":True})
    assert result.status_code==422


def test_review_author_can_confirm_signed_export_without_upload(evaluation):
    ctx,_=evaluation;client,users,_,_,_,path=ctx
    review=create(ctx).json();base=path+f"/evaluation/reviews/{review['id']}"
    payload={"sections":{field["key"]:"Synthetic signed review "+field["key"] for field in FORM_FIELDS["ADVISOR"]},
        "thesis_completed":True,"allow_defense":True}
    review=client.put(base,headers=version_headers(users[3],review),json=payload).json()
    review=client.post(base+"/submit",headers=version_headers(users[3],review),json={"confirm_content":True}).json()
    exported=client.post(base+"/print-copy",headers=version_headers(users[3],review))
    assert exported.status_code==200
    receipt={"reference":"SYNTHETIC SIGNED PAPER","export_code":exported.headers["X-Document-Code"],"confirm_paper":True}
    assert client.post(base+"/paper-receipt",headers=version_headers(users[5],review),json=receipt).status_code in (403,404)
    response=client.post(base+"/paper-receipt",headers=version_headers(users[3],review),json=receipt)
    assert response.status_code==200,response.text
    assert next(c for c in get(ctx)["members"][0]["eligibility"]["conditions"] if c["key"]=="consent")["met"]

@pytest.mark.parametrize("source_code,target_code", [("BM-CNTT","BM-KHMT"), ("BM-KHMT","BM-CNTT")])
def test_computing_departments_can_assign_cross_reviewer(evaluation, source_code, target_code):
    ctx,_=evaluation
    client,users,_,lecturers,session,path=ctx
    source=session.get(m.Department,lecturers[0].department_id)
    source.code=source_code
    other=m.Department(id=uuid4(),faculty_id=source.faculty_id,code=target_code,name="Synthetic computing department")
    session.add(other);session.flush()
    lecturers[2].department_id=other.id;session.commit()
    assert str(lecturers[2].id) in {candidate["id"] for candidate in get(ctx)["candidates"]}
    result=assign(ctx)
    assert result.status_code==201,result.text
    assert "evaluation:reviewer" in get(ctx,5)["actions"]


def test_cross_reviewer_rejects_other_faculty_and_accepts_same_faculty(evaluation):
    ctx,_=evaluation
    _,_,_,lecturers,session,_=ctx
    source=session.get(m.Department,lecturers[0].department_id)
    source.code="BM-CNTT"
    another=m.Faculty(id=uuid4(),code="T-"+uuid4().hex[:10],name="Synthetic other faculty")
    session.add(another);session.flush()
    outside=m.Department(id=uuid4(),faculty_id=another.id,code="BM-KHMT",name="Other faculty computing")
    engineering=m.Department(id=uuid4(),faculty_id=source.faculty_id,code="BM-KT",name="Synthetic engineering")
    session.add_all([outside,engineering]);session.flush()
    for department in [outside,engineering]:
        lecturers[2].department_id=department.id;session.commit()
        candidates={candidate["id"] for candidate in get(ctx)["candidates"]}
        if department.id==outside.id:
            assert str(lecturers[2].id) not in candidates
            assert assign(ctx).status_code==422
        else:
            assert str(lecturers[2].id) in candidates
            assert assign(ctx).status_code==201
