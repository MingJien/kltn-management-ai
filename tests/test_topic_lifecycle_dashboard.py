from uuid import uuid4
from sqlalchemy import func, select
from backend.db.models import entities as m
from test_registration import scenario, hdr

def test_archiving_scoped_reversible_and_preserves_existing_state(scenario):
    client, users, students, lecturers, topic, session = scenario
    session.commit()
    path=f"/api/v1/topics/{topic.id}"
    headers=lambda user,version:{**hdr(user),"If-Match":str(version)}
    assert client.post(path+"/archive",headers=headers(users[3],topic.row_version),json={"reason":"Không tiếp tục tuyển mới"}).status_code==403
    response=client.post(path+"/archive",headers=headers(users[4],topic.row_version),json={"reason":"Không tiếp tục tuyển mới"})
    assert response.status_code==204,response.text
    session.refresh(topic)
    assert topic.state=="APPROVED" and topic.archived_at and topic.archived_by==users[4].id
    assert all(item["id"]!=str(topic.id) for item in client.get("/api/v1/topics",headers=hdr(users[0])).json())
    assert any(item["id"]==str(topic.id) for item in client.get("/api/v1/topics?view=archived",headers=hdr(users[4])).json())
    assert client.post("/api/v1/topic-registrations",headers=hdr(users[0]),json={"topic_id":str(topic.id)}).status_code==409
    assert client.get(path,headers=hdr(users[0])).status_code==200
    assert client.post(path+"/restore",headers=headers(users[4],topic.row_version),json={"reason":"Mở lại theo kế hoạch"}).status_code==204
    session.refresh(topic)
    assert topic.archived_at is None and topic.state=="APPROVED"

def test_only_owner_can_delete_unlinked_draft_and_issued_code_not_reused(scenario):
    client,users,students,lecturers,topic,session=scenario
    payload={"round_id":str(topic.round_id),"title":"Đề tài nháp kiểm thử vòng đời","max_students":1}
    made=client.post("/api/v1/topics",headers=hdr(users[3]),json=payload)
    assert made.status_code==201,made.text
    draft=made.json();path=f"/api/v1/topics/{draft['id']}/delete-draft"
    headers=lambda user:{**hdr(user),"If-Match":str(draft["row_version"])}
    assert client.post(path,headers=headers(users[4]),json={"reason":"Xóa nháp của người khác"}).status_code==403
    deleted=client.post(path,headers=headers(users[3]),json={"reason":"Nháp tạo nhầm chưa gửi"})
    assert deleted.status_code==204,deleted.text
    from uuid import UUID
    assert session.get(m.Topic,UUID(draft["id"])) is None
    assert session.scalar(select(func.count()).select_from(m.TopicTitleVersion).where(m.TopicTitleVersion.topic_id==UUID(draft["id"])))==0
    assert session.scalar(select(m.AuditEvent.id).where(m.AuditEvent.action=="TOPIC_DELETED",m.AuditEvent.resource_id==UUID(draft["id"])))
    next_topic=client.post("/api/v1/topics",headers=hdr(users[3]),json=payload)
    assert next_topic.status_code==201 and next_topic.json()["code"]!=draft["code"]

def test_dashboard_admin_only_and_aggregate_counts(scenario):
    client,users,students,lecturers,topic,session=scenario
    admin=m.UserAccount(id=uuid4(),external_subject=uuid4().hex,base_role="ADMIN",status="ACTIVE")
    session.add(admin);session.flush()
    assert client.get("/api/v1/admin/dashboard",headers=hdr(users[4])).status_code==403
    response=client.get("/api/v1/admin/dashboard",headers=hdr(admin))
    assert response.status_code==200,response.text
    data=response.json()
    assert data["accounts"]["STUDENT"]>=3 and data["accounts"]["LECTURER"]>=3
    assert data["topics"]["APPROVED"]>=1
    assert "generated_at" in data and "email" not in data and "items" not in data


from test_core_workspace import workspace

def test_archiving_linked_topic_keeps_thesis_members_and_private_access(workspace):
    client, users, students, lecturers, session, path = workspace
    from uuid import UUID
    thesis=session.get(m.Thesis,UUID(path.rsplit("/",1)[1]));topic=session.get(m.Topic,thesis.topic_id)
    old_state=topic.state
    members=session.scalar(select(func.count()).select_from(m.ThesisMember).where(m.ThesisMember.thesis_id==thesis.id))
    headers={**hdr(users[4]),"If-Match":str(topic.row_version)}
    response=client.post(f"/api/v1/topics/{topic.id}/archive",headers=headers,json={"reason":"Không nhận đăng ký mới, giữ khóa luận đang làm"})
    assert response.status_code==204,response.text
    session.refresh(topic)
    assert topic.state==old_state
    assert client.get(path,headers=hdr(users[0])).status_code==200
    assert client.get(path,headers=hdr(users[3])).status_code==200
    assert client.get(path,headers=hdr(users[2])).status_code==404
    assert session.scalar(select(func.count()).select_from(m.ThesisMember).where(m.ThesisMember.thesis_id==thesis.id))==members
    assert session.scalar(select(m.UserNotification.id).where(m.UserNotification.recipient_user_id==users[0].id,m.UserNotification.subject_id==topic.id))
