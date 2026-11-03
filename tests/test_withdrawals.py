"""Real PostgreSQL lifecycle, permissions, calendar boundary and immutable evidence."""
from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from docx import Document
from sqlalchemy import select
from test_core_workspace import workspace, synthetic_pdf, version_headers
from test_registration import hdr, scenario
from backend.db.models import entities as m
from backend.services import withdrawals as service
from backend.services.theses import now
from backend.services.registration import confirmed_student_ids
from test_nv6_evaluation import evaluation, complete_review, check, get as evaluation_get, assign, create as create_review


def setup(client, users, session, path, days=1):
    thesis = session.get(m.Thesis, UUID(path.split('/')[-1]))
    round_ = session.get(m.ThesisRound, thesis.round_id)
    response = client.put(f"/api/v1/withdrawal-rounds/{round_.id}/start", headers=version_headers(users[4], {"row_version":round_.row_version}),
        json={"starts_on":(now().astimezone(service.VN).date()-timedelta(days=days)).isoformat(),"reference":"Kế hoạch thử nghiệm tổng hợp"})
    assert response.status_code==200,response.text
    return thesis


def send(client,user,path):
    response=client.post(path+"/withdrawals",headers=hdr(user),json={"reason":"Xin thôi vì lý do cá nhân để học học phần thay thế","confirm_replacement":True})
    assert response.status_code==201,response.text
    return response.json()


def confirm(client,users,item):
    response=client.post(f"/api/v1/withdrawals/{item['id']}/advisor-decision",headers=version_headers(users[3],item),
        json={"decision":"CONFIRM","comment":"Xác nhận nội dung đơn xin thôi của sinh viên"})
    assert response.status_code==200,response.text
    return response.json()


def evidence(client,user,item,session):
    response=client.post(f"/api/v1/withdrawals/{item['id']}/signed-copy",headers={**version_headers(user,item),"X-File-Name":"don-co-xac-nhan.pdf"},content=synthetic_pdf())
    assert response.status_code==200,response.text
    item=response.json()
    # The fixture explicitly disables scanner; its quarantine must be enforced before a real verdict.
    assert item["scan_state"]=="QUARANTINED"
    request=session.get(m.ThesisWithdrawalRequest,UUID(item["id"]))
    file=session.get(m.StoredFile,request.evidence_file_id)
    file.scan_state="CLEAN"
    session.commit()
    return item


def outcome(client,user,item,kind="WITHDRAWN"):
    return client.post(f"/api/v1/withdrawals/{item['id']}/outcome",headers=version_headers(user,item),
        json={"outcome":kind,"confirm_evidence":True,"reference":"KHOA-TEST-2026/01","note":"Đã đối chiếu hồ sơ và kết quả giải quyết bên ngoài",
            "effective_on":now().astimezone(service.VN).date().isoformat()})


def test_group_withdrawal_keeps_thesis_and_requires_new_proposal(workspace):
    client,users,students,_,session,path=workspace
    thesis=setup(client,users,session,path)
    proposal=m.Proposal(id=uuid4(),thesis_id=thesis.id,state="ADVISOR_CONFIRMED",current_version_no=1)
    session.add(proposal);session.commit()
    item=send(client,users[0],path)
    assert session.get(m.ThesisMember,session.scalar(select(m.ThesisMember.id).where(m.ThesisMember.student_id==students[0].id))).active
    assert client.get("/api/v1/withdrawals",headers=hdr(users[1])).json()["requests"]==[]
    assert client.get("/api/v1/withdrawals",headers=hdr(users[5])).json()["requests"]==[]
    assert client.post(f"/api/v1/withdrawals/{item['id']}/advisor-decision",headers=version_headers(users[4],item),json={"decision":"CONFIRM","comment":"Wrong actor"}).status_code==403
    exported=client.post(f"/api/v1/withdrawals/{item['id']}/print-copy",headers=hdr(users[0]))
    assert exported.status_code==200,exported.text
    doc=Document(BytesIO(exported.content))
    assert students[0].student_code in " ".join(p.text for p in doc.paragraphs)
    assert item["code"] in " ".join(p.text for p in doc.sections[0].footer.paragraphs)
    item=confirm(client,users,item)
    assert outcome(client,users[4],item).status_code==404 # no evidence, not an approval
    item=evidence(client,users[0],item,session)
    response=outcome(client,users[3],item)
    assert response.status_code==403
    response=outcome(client,users[4],item)
    assert response.status_code==200,response.text
    assert response.json()["state"]=="RECORDED"
    session.expire_all()
    left=session.scalar(select(m.ThesisMember).where(m.ThesisMember.student_id==students[0].id))
    remaining=session.scalar(select(m.ThesisMember).where(m.ThesisMember.student_id==students[1].id))
    assert not left.active and left.left_at and not left.is_coordinator
    assert remaining.active and remaining.is_coordinator
    assert session.get(m.Thesis,thesis.id).state=="ACTIVE"
    assert session.get(m.Proposal,proposal.id).state=="REVISION_REQUIRED"
    assert students[0].id not in confirmed_student_ids(session,thesis.round_id,[students[0].id])
    assert client.get(path,headers=hdr(users[0])).status_code==404
    assert client.get("/api/v1/withdrawals",headers=hdr(users[0])).json()["requests"][0]["state"]=="RECORDED"
    notices=client.get("/api/v1/notifications",headers=hdr(users[1])).json()["items"]
    assert any("đề cương mới" in n["message"] for n in notices)
    assert client.post(f"/api/v1/withdrawals/{item['id']}/print-copy",headers=hdr(users[1])).status_code==404
    assert outcome(client,users[4],response.json()).status_code==409


def test_cancel_return_and_deadline_are_not_course_withdrawal(workspace,monkeypatch):
    client,users,students,_,session,path=workspace
    thesis=setup(client,users,session,path)
    item=send(client,users[0],path)
    cancelled=client.post(f"/api/v1/withdrawals/{item['id']}/cancel",headers=version_headers(users[0],item))
    assert cancelled.status_code==200,cancelled.text
    assert students[0].id in confirmed_student_ids(session,thesis.round_id,[students[0].id])
    item=send(client,users[0],path)
    response=client.post(f"/api/v1/withdrawals/{item['id']}/advisor-decision",headers=version_headers(users[3],item),json={"decision":"RETURN","comment":"Đề nghị đối chiếu lại lý do"})
    assert response.status_code==200
    round_=session.get(m.ThesisRound,thesis.round_id)
    changed=client.put(f"/api/v1/withdrawal-rounds/{round_.id}/start",headers=version_headers(users[4],{"row_version":round_.row_version}),json={"starts_on":now().date().isoformat(),"reference":"Changed plan"})
    assert changed.status_code==409
    boundary=service.deadline(round_.execution_starts_on)
    monkeypatch.setattr(service,"now",lambda:boundary-timedelta(microseconds=1))
    timely=send(client,users[0],path)
    # Confirmation may happen later; the student's original timely filing is preserved.
    monkeypatch.setattr(service,"now",lambda:boundary+timedelta(days=2))
    assert confirm(client,users,timely)["state"]=="ADVISOR_CONFIRMED"
    late=client.post(path+"/withdrawals",headers=hdr(users[1]),json={"reason":"Xin thôi sau hạn theo tình huống kiểm thử","confirm_replacement":True})
    assert late.status_code==409
    assert students[1].id in confirmed_student_ids(session,thesis.round_id,[students[1].id])


def test_external_refusal_keeps_student_and_quarantine_blocks_recording(workspace):
    client,users,students,_,session,path=workspace
    setup(client,users,session,path)
    item=confirm(client,users,send(client,users[0],path))
    uploaded=client.post(f"/api/v1/withdrawals/{item['id']}/signed-copy",headers={**version_headers(users[0],item),"X-File-Name":"don.pdf"},content=synthetic_pdf())
    assert uploaded.status_code==200,uploaded.text
    item=uploaded.json()
    assert outcome(client,users[4],item).status_code==409
    assert client.get(f"/api/v1/withdrawals/{item['id']}/signed-copy",headers=hdr(users[0])).status_code==409
    row=session.get(m.ThesisWithdrawalRequest,UUID(item["id"]))
    session.get(m.StoredFile,row.evidence_file_id).scan_state="CLEAN";session.commit()
    response=outcome(client,users[4],item,"NOT_GRANTED")
    assert response.status_code==200,response.text
    assert students[0].id in confirmed_student_ids(session,session.get(m.Thesis,row.thesis_id).round_id,[students[0].id])
    assert client.get(path,headers=hdr(users[0])).status_code==200


def test_last_member_withdrawal_closes_thesis_and_advisor_history_remains_readable(workspace):
    client,users,students,_,session,path=workspace
    thesis=setup(client,users,session,path)
    assert assign(workspace).status_code == 201
    # Simulate a one-student thesis without creating or touching any production records.
    member=session.scalar(select(m.ThesisMember).where(m.ThesisMember.student_id==students[1].id))
    member.active=False;session.commit()
    item=evidence(client,users[0],confirm(client,users,send(client,users[0],path)),session)
    response=outcome(client,users[4],item)
    assert response.status_code==200,response.text
    session.expire_all()
    assert session.get(m.Thesis,thesis.id).state=="WITHDRAWN"
    assert session.get(m.TopicRegistration,thesis.registration_id).state=="CANCELLED"
    assert not session.scalar(select(m.ReviewerAssignment.id).where(m.ReviewerAssignment.thesis_id == thesis.id,
        m.ReviewerAssignment.state == "ACTIVE"))
    assert client.get(path+"/evaluation", headers=hdr(users[5])).status_code == 404
    assert client.get("/api/v1/withdrawals",headers=hdr(users[3])).json()["requests"][0]["state"]=="RECORDED"


def test_remaining_student_resubmits_proposal_without_reusing_old_approval(workspace):
    client,users,students,_,session,path=workspace
    thesis=setup(client,users,session,path)
    def submit(user,row):
        response=client.post(path+"/proposal/versions",headers={**version_headers(user,row),"X-File-Name":"de-cuong.pdf"},content=synthetic_pdf())
        assert response.status_code==201,response.text
        row=response.json()
        version=session.get(m.ProposalVersion,UUID(row["versions"][0]["id"]))
        session.get(m.StoredFile,version.stored_file_id).scan_state="CLEAN";session.commit()
        return row
    def approve(row):
        response=client.post(path+"/proposal/reviews",headers=version_headers(users[3],row),json={"decision":"CONFIRM","comment":"Đề cương phù hợp thành viên và nội dung hiện tại"})
        assert response.status_code==200,response.text
        response=client.post(path+"/proposal/department-finalization",headers=version_headers(users[4],response.json()),json={"reason":"Bộ môn đối chiếu đề cương theo thành viên hiện tại"})
        assert response.status_code==200,response.text
        return response.json()
    first=approve(submit(users[0],{"row_version":0}))
    assert first["department_confirmed"]
    item=evidence(client,users[0],confirm(client,users,send(client,users[0],path)),session)
    assert outcome(client,users[4],item).status_code==200
    proposal=client.get(path+"/proposal",headers=hdr(users[1])).json()
    assert proposal["state"]=="REVISION_REQUIRED" and not proposal["department_confirmed"]
    assert client.post(path+"/proposal/reviews", headers=version_headers(users[3],proposal),
        json={"decision":"CONFIRM", "comment":"Không được tái sử dụng bản cũ cho nhóm mới"}).status_code == 409
    assert client.post(path+"/proposal/department-finalization", headers=version_headers(users[4],proposal),
        json={"reason":"Không được chốt lại bản cũ chưa cập nhật"}).status_code == 409
    assert session.scalar(select(m.SignatureConfirmation.id).where(m.SignatureConfirmation.proposal_version_no==1))
    second=submit(users[1],proposal)
    assert second["current_version_no"]==2 and len(second["versions"])==2 and not second["department_confirmed"]
    final=approve(second)
    assert final["department_confirmed"] and final["current_version_no"]==2
    # Cancellation recorded in one round also excludes this student in a later round.
    round_=session.get(m.ThesisRound,thesis.round_id)
    new_round=m.ThesisRound(id=uuid4(),academic_year_id=round_.academic_year_id,code="LATER-TEST",round_type="SUPPLEMENTARY",
        opens_at=now()-timedelta(days=1),closes_at=now()+timedelta(days=3),state="OPEN")
    session.add(new_round);session.flush()
    session.add(m.EligibilitySnapshot(id=uuid4(),student_id=students[0].id,round_id=new_round.id,version=1,
        passed_credit_ratio=0.8,gpa_4=3.0,evidence_ref="TEST",captured_at=now(),confirmed_by=users[4].id,confirmed_at=now(),state="CONFIRMED"))
    session.commit()
    assert students[0].id not in confirmed_student_ids(session,new_round.id,[students[0].id])


def test_record_rollback_restores_group_and_request_on_failure(workspace,monkeypatch):
    from fastapi import HTTPException
    client,users,students,_,session,path=workspace
    thesis=setup(client,users,session,path)
    item=evidence(client,users[0],confirm(client,users,send(client,users[0],path)),session)
    original=service.audit
    def fail_after_membership_update(session,user,action,*args,**kwargs):
        if action=="WITHDRAWAL_RECORDED":
            raise HTTPException(409,"Synthetic failure after member update")
        return original(session,user,action,*args,**kwargs)
    monkeypatch.setattr(service,"audit",fail_after_membership_update)
    assert outcome(client,users[4],item).status_code==409
    session.expire_all()
    assert session.get(m.ThesisWithdrawalRequest,UUID(item["id"])).state=="ADVISOR_CONFIRMED"
    members=session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id==thesis.id,m.ThesisMember.active.is_(True))).all()
    assert len(members)==2 and any(x.student_id==students[0].id and x.is_coordinator for x in members)
    assert students[0].id in confirmed_student_ids(session,thesis.round_id,[students[0].id])


def test_membership_change_blocks_old_report_reviews_and_checks_until_reapproval(evaluation):
    ctx, doc = evaluation
    client, users, students, _, session, path = ctx
    setup(client, users, session, path)
    member_index = next(i for i, member in enumerate(evaluation_get(ctx)["members"])
        if member["student_id"] == str(students[1].id))
    assert assign(ctx).status_code == 201
    old_review = complete_review(ctx, member=member_index)
    assert check(ctx, member=member_index).status_code == 200
    draft = create_review(ctx, member=member_index, user=5, kind="REVIEWER").json()
    current_doc = client.get(path+"/documents", headers=hdr(users[3])).json()[0]
    old_version = current_doc["versions"][0]
    response = client.post(path+f"/documents/{doc['id']}/versions/{old_version['id']}/review",
        headers=version_headers(users[3], old_version), json={"decision":"ACCEPT", "comment":"Báo cáo của nhóm ban đầu đã được tiếp nhận"})
    assert response.status_code == 200, response.text
    deadline = session.scalar(select(m.DocumentDeadline).where(m.DocumentDeadline.document_type == "REPORT"))
    deadline.state = "CLOSED"; session.commit()
    item = evidence(client, users[0], confirm(client, users, send(client, users[0], path)), session)
    assert outcome(client, users[4], item).status_code == 200
    data = evaluation_get(ctx)
    assert {b["key"] for b in data["workflow_blockers"]} == {"proposal", "report"}
    assert data["members"][0]["eligibility"]["state"] == "STALE"
    assert not next(r for r in evaluation_get(ctx, 5)["reviews"] if r["id"] == draft["id"])["can_edit"]
    assert client.get(path+"/evaluation", headers=hdr(users[0])).status_code == 404
    for kind, user in [("ADVISOR", 3), ("REVIEWER", 5)]:
        assert create_review(ctx, user=user, kind=kind).status_code == 409
    assert check(ctx).status_code == 409
    # The report's automatic revision request permits one correction after close.
    current_doc = client.get(path+"/documents", headers=hdr(users[1])).json()[0]
    assert current_doc["versions"][0]["state"] == "REVISION_REQUESTED"
    response = client.post(path+f"/documents/{doc['id']}/versions",
        headers={**version_headers(users[1], current_doc), "X-File-Name":"bao-cao-nhom-moi.pdf"}, content=synthetic_pdf())
    assert response.status_code == 201, response.text
    version = session.get(m.DocumentVersion, UUID(response.json()["versions"][0]["id"]))
    session.get(m.StoredFile, version.stored_file_id).scan_state = "CLEAN"; session.commit()
    assert [b["key"] for b in evaluation_get(ctx)["workflow_blockers"]] == ["proposal"]
    assert check(ctx).status_code == 409
    # An approved proposal for the remaining member releases the workflow.
    response = client.post(path+"/proposal/versions", headers={**version_headers(users[1], {"row_version":0}),
        "X-File-Name":"de-cuong-nhom-moi.pdf"}, content=synthetic_pdf())
    assert response.status_code == 201, response.text
    proposal = response.json()
    pv = session.get(m.ProposalVersion, UUID(proposal["versions"][0]["id"]))
    session.get(m.StoredFile, pv.stored_file_id).scan_state = "CLEAN"; session.commit()
    response = client.post(path+"/proposal/reviews", headers=version_headers(users[3], proposal),
        json={"decision":"CONFIRM", "comment":"Phạm vi phù hợp thành viên còn lại"})
    assert response.status_code == 200, response.text
    assert evaluation_get(ctx)["workflow_blockers"] # advisor confirmation alone is insufficient
    response = client.post(path+"/proposal/department-finalization", headers=version_headers(users[4], response.json()),
        json={"reason":"Bộ môn chốt đề cương theo nhóm mới"})
    assert response.status_code == 200, response.text
    assert evaluation_get(ctx)["workflow_blockers"] == []
    assert evaluation_get(ctx)["members"][0]["eligibility"]["state"] == "STALE"
    complete_review(ctx)
    final = check(ctx)
    assert final.status_code == 200 and final.json()["state"] == "READY_FOR_DEFENSE"
    assert len(final.json()["eligibility_history"]) == 2
    assert any(r["id"] == old_review["id"] for r in final.json()["reviews"])


@pytest.mark.parametrize("confirmation", [None, False])
def test_external_outcome_requires_explicit_evidence_confirmation(workspace, confirmation):
    client, users, _, _, session, path = workspace
    setup(client, users, session, path)
    item = evidence(client, users[0], confirm(client, users, send(client, users[0], path)), session)
    payload = {"outcome":"WITHDRAWN", "reference":"KHOA-TEST", "note":"Đã đối chiếu hồ sơ thử nghiệm",
        "effective_on":now().astimezone(service.VN).date().isoformat()}
    if confirmation is not None:
        payload["confirm_evidence"] = confirmation
    response = client.post(f"/api/v1/withdrawals/{item['id']}/outcome", headers=version_headers(users[4], item), json=payload)
    assert response.status_code == 422
    assert session.get(m.ThesisWithdrawalRequest, UUID(item["id"])).state == "ADVISOR_CONFIRMED"
