"""Exercise topic changes and extensions through authenticated API entry points."""
from datetime import timedelta
from uuid import UUID,uuid4

from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import membership_revision,thesis_changes as service
from backend.services.theses import now
from test_core_workspace import workspace,version_headers,synthetic_pdf
from test_registration import scenario,hdr
from test_withdrawals import setup


def listing(ctx,index=0):
    client,users,*_=ctx
    response=client.get("/api/v1/thesis-changes",headers=hdr(users[index]))
    assert response.status_code==200,response.text
    return response.json()


def submit(ctx,**overrides):
    client,users,_,_,session,path=ctx
    thesis=session.get(m.Thesis,UUID(path.split("/")[-1]))
    if not session.get(m.ThesisRound,thesis.round_id).execution_starts_on:
        setup(client,users,session,path)
    response=client.post(path+"/change-requests",headers=version_headers(users[0],{"row_version":thesis.row_version}),
        json={"kind":"ADJUSTMENT","proposed_title":"Synthetic revised thesis title","proposed_description":"Revised objectives and feasible scope for the group",
            "reason":"Synthetic academic reason for the topic change","confirm_consequences":True,**overrides})
    assert response.status_code==201,response.text
    return listing(ctx)["requests"][0]


def act(ctx,item,action,user,payload,status=200):
    client,users,*_=ctx
    response=client.post("/api/v1/thesis-changes/"+item["id"]+"/"+action,
        headers=version_headers(users[user],item),json=payload)
    assert response.status_code==status,response.text
    rows=listing(ctx,user)["requests"] if response.status_code==200 else []
    return next((row for row in rows if row["id"]==item["id"]),item)


def agree_group(ctx,item):
    return act(ctx,item,"consent",1,{"decision":"AGREE"})


def agree_advisor(ctx,item,index=3,role="CURRENT_ADVISOR"):
    return act(ctx,item,"advisor-review",index,{"role":role,"decision":"AGREE","reason":"Agreed synthetic academic scope"})


def approve(ctx,item):
    return act(ctx,item,"decision",4,{"decision":"APPROVE","reason":"Department reviewed scope and group agreement"})


def test_change_requires_group_advisor_and_head_and_invalidates_old_evidence(workspace):
    ctx=workspace
    client,users,students,lecturers,session,path=ctx
    item=submit(ctx)
    assert listing(ctx,2)=={"theses":[],"requests":[],"extension_requests":[]}
    act(ctx,item,"advisor-review",3,{"role":"CURRENT_ADVISOR","decision":"AGREE","reason":"Premature decision"},409)
    act(ctx,item,"decision",4,{"decision":"APPROVE","reason":"Missing agreements"},409)
    act(ctx,item,"decision",0,{"decision":"APPROVE","reason":"Student is not head"},403)
    item=agree_group(ctx,item)
    item=agree_advisor(ctx,item)
    assert item["state"]=="ADVISOR_REVIEWED"
    approved=approve(ctx,item)
    assert approved["state"]=="APPROVED"
    thesis=session.get(m.Thesis,UUID(path.split("/")[-1]))
    assert thesis.current_title=="Synthetic revised thesis title"
    reg=session.get(m.TopicRegistration,thesis.registration_id)
    assert session.get(m.Topic,reg.topic_id).current_title==thesis.current_title
    assert membership_revision.changed_at(session,thesis.id)
    assert {row["key"] for row in membership_revision.blockers(session,thesis,None)}=={"registration","plan","proposal","report"}
    act(ctx,item,"decision",4,{"decision":"APPROVE","reason":"Stale concurrent request"},409)
    history=client.get(path+"/evaluation",headers=hdr(users[4])).json()
    assert history["workflow_blockers"]
    assert client.get(f"/api/v1/topic-registrations/{reg.id}/forms",headers=hdr(users[0])).json()["can_submit"]
    notices=client.get("/api/v1/notifications",headers=hdr(users[1])).json()["items"]
    assert any("đổi đề tài" in notice["message"] for notice in notices)


def test_decline_cancel_duplicate_withdrawal_and_start_date_guards(workspace):
    ctx=workspace
    client,users,_,_,session,path=ctx
    item=submit(ctx)
    row=client.get(path,headers=hdr(users[0])).json()
    duplicate=client.post(path+"/change-requests",headers=version_headers(users[0],row),json={
        "kind":"ADJUSTMENT","proposed_title":"Another synthetic title","proposed_description":"Synthetic amended scope and objectives",
        "reason":"Another synthetic academic reason","confirm_consequences":True})
    assert duplicate.status_code==409
    assert client.post(path+"/withdrawals",headers=hdr(users[0]),json={"reason":"Want to withdraw from the thesis","confirm_replacement":True}).status_code==409
    declined=act(ctx,item,"consent",1,{"decision":"DECLINE"})
    assert declined["state"]=="REJECTED"
    before=client.get(path,headers=hdr(users[0])).json()["title"]
    new=submit(ctx)
    cancelled=act(ctx,new,"cancel",0,{})
    assert cancelled["state"]=="CANCELLED"
    assert client.get(path,headers=hdr(users[0])).json()["title"]==before


def test_changed_membership_requires_fresh_request(workspace):
    ctx=workspace
    _,_,students,_,session,path=ctx
    item=submit(ctx)
    member=session.scalar(select(m.ThesisMember).where(m.ThesisMember.student_id==students[1].id))
    member.active=False
    session.commit()
    act(ctx,item,"consent",1,{"decision":"AGREE"},409)
    act(ctx,item,"cancel",0,{})


def test_replacement_requires_new_advisor_and_updates_registration_atomically(workspace):
    ctx=workspace
    client,users,_,lecturers,session,path=ctx
    thesis=session.get(m.Thesis,UUID(path.split("/")[-1]))
    original_title=thesis.current_title
    before=now()
    topic=m.Topic(id=uuid4(),round_id=thesis.round_id,department_id=thesis.department_id,
        code="CHANGE-"+uuid4().hex[:10],current_title="New synthetic approved topic",
        description="A different published topic for this group",max_students=2,state="APPROVED",
        proposer_type="LECTURER",proposer_user_id=users[5].id,receiving_lecturer_id=lecturers[2].id)
    session.add(topic);session.commit()
    item=submit(ctx,kind="REPLACEMENT",target_topic_id=str(topic.id),proposed_title="",proposed_description="")
    item=agree_group(ctx,item)
    item=agree_advisor(ctx,item)
    assert not item["ready"]
    item=agree_advisor(ctx,item,index=5,role="NEW_ADVISOR")
    approved=approve(ctx,item)
    assert approved["state"]=="APPROVED"
    session.expire_all()
    thesis=session.get(m.Thesis,thesis.id)
    assert thesis.topic_id==topic.id
    assert session.get(m.TopicRegistration,thesis.registration_id).topic_id==topic.id
    assert client.get(path,headers=hdr(users[3])).status_code==404
    assert client.get(path,headers=hdr(users[5])).status_code==200
    assert service.historical_identity(session,thesis,before)["title"]==original_title
    assignments=session.scalars(select(m.AdvisorAssignment).where(m.AdvisorAssignment.thesis_id==thesis.id)).all()
    assert {row.state for row in assignments}=={"ACTIVE","ENDED"}


def test_change_deadline_is_inclusive_and_no_new_request_after_boundary(workspace,monkeypatch):
    client,users,_,_,session,path=workspace
    thesis=setup(client,users,session,path)
    round_=session.get(m.ThesisRound,thesis.round_id)
    monkeypatch.setattr(service,"now",lambda:service.deadline(round_.execution_starts_on))
    result=client.post(path+"/change-requests",headers=version_headers(users[0],{"row_version":thesis.row_version}),json={
        "kind":"ADJUSTMENT","proposed_title":"Late synthetic changed topic","proposed_description":"A sufficiently detailed academic scope",
        "reason":"Synthetic late request test","confirm_consequences":True})
    assert result.status_code==409


def test_legacy_extension_endpoint_cannot_bypass_student_request(workspace):
    client,users,_,_,session,path=workspace
    thesis=session.get(m.Thesis,UUID(path.split("/")[-1]))
    response=client.post(path+"/extension",headers=version_headers(users[4],{"row_version":thesis.row_version}),json={
        "decision_on":now().date().isoformat(),"until_at":(now()+timedelta(days=30)).isoformat(),
        "reference":"SYN-OLD-API","reason":"Synthetic external recording","confirm_decision":True})
    assert response.status_code==409 and "SV gửi yêu cầu" in response.json()["detail"]


def test_approval_failure_rolls_back_title_forms_and_request(workspace,monkeypatch):
    from fastapi import HTTPException
    ctx=workspace
    client,users,_,_,session,path=ctx
    before=client.get(path,headers=hdr(users[0])).json()["title"]
    item=agree_advisor(ctx,agree_group(ctx,submit(ctx)))
    original=service.audit
    def fail_after_changes(session,user,event,*args,**kwargs):
        if event=="THESIS_CHANGE_APPROVED":
            raise HTTPException(409,"Synthetic failure after mutation")
        return original(session,user,event,*args,**kwargs)
    monkeypatch.setattr(service,"audit",fail_after_changes)
    act(ctx,item,"decision",4,{"decision":"APPROVE","reason":"Synthetic failed transaction"},409)
    session.expire_all()
    assert client.get(path,headers=hdr(users[0])).json()["title"]==before
    assert listing(ctx)["requests"][0]["state"]=="ADVISOR_REVIEWED"
    assert membership_revision.changed_at(session,UUID(path.split("/")[-1])) is None
