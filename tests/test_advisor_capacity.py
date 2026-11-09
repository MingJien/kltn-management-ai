"""Enforce the supervision limit across rounds on real PostgreSQL."""
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from backend.db.models import entities as m
from backend.services.advisor_capacity import CAPACITY_MESSAGE
from backend.services.theses import now
from test_registration import scenario, hdr
from test_core_workspace import workspace, version_headers
from test_thesis_changes import submit, agree_group, agree_advisor


def test_capacity_includes_extended_old_round_and_rechecks_acceptance(scenario):
    client, users, students, lecturers, topic, session = scenario
    current = session.get(m.ThesisRound, topic.round_id)
    old = m.ThesisRound(id=uuid4(), academic_year_id=current.academic_year_id, code="OLD-"+uuid4().hex[:8],
        round_type="SUPPLEMENTARY", opens_at=now()-timedelta(days=60), closes_at=now()-timedelta(days=30), state="CLOSED")
    session.add(old); session.flush()
    theses = []
    for index in range(3):
        round_id = old.id if index == 0 else current.id
        extra_topic = m.Topic(id=uuid4(), round_id=round_id, department_id=topic.department_id,
            code="CAP-"+uuid4().hex[:12], current_title="Synthetic supervised topic", max_students=2,
            state="LOCKED", proposer_type="LECTURER", proposer_user_id=users[3].id)
        session.add(extra_topic); session.flush()
        reg = m.TopicRegistration(id=uuid4(), round_id=round_id, topic_id=extra_topic.id,
            created_by=students[2].id, expected_member_count=2, state="FINALIZED")
        session.add(reg); session.flush()
        thesis = m.Thesis(id=uuid4(), round_id=round_id, topic_id=extra_topic.id, registration_id=reg.id,
            department_id=topic.department_id, current_title=extra_topic.current_title, state="EXTENDED" if index == 0 else "ACTIVE")
        session.add(thesis); session.flush()
        session.add(m.AdvisorAssignment(id=uuid4(), thesis_id=thesis.id, lecturer_id=lecturers[0].id,
            assigned_by=users[3].id, effective_from=now()-timedelta(days=1), state="ACTIVE"))
        theses.append(thesis)
    session.commit()
    proposal = client.post("/api/v1/student-proposals", headers=hdr(users[0]), json={
        "round_id":str(current.id), "title":"Synthetic proposed topic", "max_students":1,
        "receiving_lecturer_id":str(lecturers[0].id)})
    assert proposal.status_code == 409 and proposal.json()["detail"] == CAPACITY_MESSAGE
    rejected = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={"topic_id":str(topic.id)})
    assert rejected.status_code == 409 and rejected.json()["detail"] == CAPACITY_MESSAGE
    theses[2].state="COMPLETED"; session.commit()
    reg = client.post("/api/v1/topic-registrations", headers=hdr(users[0]), json={"topic_id":str(topic.id)})
    assert reg.status_code == 201, reg.text
    reg=reg.json()
    submitted=client.post(f"/api/v1/topic-registrations/{reg['id']}/submit",
        headers={**hdr(users[0]),"If-Match":str(reg["row_version"])})
    assert submitted.status_code == 200, submitted.text
    theses[2].state="ACTIVE"; session.commit()
    endpoint=f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision"
    headers={**hdr(users[3]),"If-Match":str(submitted.json()["row_version"])}
    result=client.post(endpoint,headers=headers,json={"decision":"ACCEPT"})
    assert result.status_code == 409 and result.json()["detail"] == CAPACITY_MESSAGE
    assert not session.scalar(select(m.Thesis.id).where(m.Thesis.registration_id == reg["id"]))
    theses[2].state="COMPLETED"; session.commit()
    accepted=client.post(endpoint,headers=headers,json={"decision":"ACCEPT"})
    assert accepted.status_code == 200 and accepted.json()["thesis_id"], accepted.text


def test_topic_replacement_rechecks_new_advisor_before_head_decision(workspace):
    client, users, students, lecturers, session, path = workspace
    from uuid import UUID
    thesis=session.get(m.Thesis,UUID(path.split("/")[-1]))
    previous_topic=thesis.topic_id
    target=m.Topic(id=uuid4(),round_id=thesis.round_id,department_id=thesis.department_id,
        code="CAP-"+uuid4().hex[:12],current_title="Synthetic replacement topic",
        description="A different published topic for the whole group",max_students=2,state="APPROVED",
        proposer_type="LECTURER",proposer_user_id=users[5].id,receiving_lecturer_id=lecturers[2].id)
    session.add(target); session.commit()
    item=submit(workspace,kind="REPLACEMENT",target_topic_id=str(target.id),proposed_title="",proposed_description="")
    item=agree_advisor(workspace,agree_group(workspace,item))
    item=agree_advisor(workspace,item,index=5,role="NEW_ADVISOR")
    for _ in range(3):
        topic=m.Topic(id=uuid4(),round_id=thesis.round_id,department_id=thesis.department_id,
            code="CAP-"+uuid4().hex[:12],current_title="Another synthetic topic",max_students=1,
            state="LOCKED",proposer_type="LECTURER",proposer_user_id=users[5].id)
        session.add(topic); session.flush()
        reg=m.TopicRegistration(id=uuid4(),round_id=thesis.round_id,topic_id=topic.id,created_by=students[2].id,
            expected_member_count=1,state="FINALIZED")
        session.add(reg); session.flush()
        other=m.Thesis(id=uuid4(),round_id=thesis.round_id,topic_id=topic.id,registration_id=reg.id,
            department_id=thesis.department_id,current_title=topic.current_title,state="ACTIVE")
        session.add(other); session.flush()
        session.add(m.AdvisorAssignment(id=uuid4(),thesis_id=other.id,lecturer_id=lecturers[2].id,
            assigned_by=users[5].id,effective_from=now()-timedelta(days=1),state="ACTIVE"))
    session.commit()
    response=client.post("/api/v1/thesis-changes/"+item["id"]+"/decision",
        headers=version_headers(users[4],item),json={"decision":"APPROVE","reason":"Synthetic review after capacity change"})
    assert response.status_code == 409 and response.json()["detail"] == CAPACITY_MESSAGE
    session.expire_all()
    assert session.get(m.Thesis,thesis.id).topic_id == previous_topic
    assert session.get(m.ThesisChangeRequest,UUID(item["id"])).state == "ADVISOR_REVIEWED"
