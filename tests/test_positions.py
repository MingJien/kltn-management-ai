"""Real PostgreSQL tests for organizational appointment lifecycle and permissions."""
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select

from backend.db.models import entities as m
from backend.services.lecturer_profiles import can_review
from backend.services.theses import now
from test_lecturer_profiles import profiles
from test_registration import hdr, scenario


def existing(ctx):
    _, _, lecturers, session, _ = ctx
    return session.scalar(select(m.PositionAssignment).where(m.PositionAssignment.lecturer_id == lecturers[1].id))


def payload(ctx, **extra):
    _, _, lecturers, _, _ = ctx
    return dict(lecturer_id=str(lecturers[0].id), basis_ref="QĐ TEST bổ nhiệm",
        reason="Ghi nhận quyết định bổ nhiệm dữ liệu giả", **extra)


def context(ctx, index):
    client, users, _, _, _ = ctx
    return client.get("/api/v1/me/context", headers=hdr(users[index])).json()


def test_admin_listing_and_direct_endpoint_protection(profiles):
    client, users, lecturers, session, admin = profiles
    base="/api/v1/admin/positions"
    assert client.get(base+"/catalog",headers=hdr(users[4])).status_code==403
    assert client.get(base,headers=hdr(users[0])).status_code==403
    assert client.post(base,headers=hdr(users[4]),json=payload(profiles,department_id=str(lecturers[0].department_id))).status_code==403
    row=existing(profiles)
    for action in ("replace","revoke"):
        assert client.post(base+f"/{row.id}/{action}",headers={**hdr(users[4]),"If-Match":str(row.row_version)},json=payload(profiles) if action=="replace" else {"basis_ref":"QĐ TEST","reason":"Không có quyền ghi nhận"}).status_code==403
    assert client.get(base,headers=hdr(admin)).status_code==200
    assert client.get(base+"/catalog",headers=hdr(admin)).json()["lecturers"]
    assert client.get(base+"/available",headers=hdr(users[4])).status_code==403
    available=client.get(base+"/available",headers=hdr(admin))
    assert available.status_code==200
    assert any(item["id"]==str(row.id) for item in available.json())


def test_immediate_replacement_transfers_scoped_rights_and_preserves_history(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx;old=existing(ctx)
    old_id=old.id;old_version=old.row_version
    response=client.post(f"/api/v1/admin/positions/{old.id}/replace",headers={**hdr(admin),"If-Match":str(old_version)},json=payload(ctx))
    assert response.status_code==201,response.text
    new=response.json()
    assert new["status"]=="EFFECTIVE" and new["basis_ref"]=="QĐ TEST bổ nhiệm"
    assert "topic:department_decide" not in context(ctx,4)["actions"]
    assert "lecturer:profile_review" in context(ctx,3)["actions"]
    assert "topic:department_decide" in context(ctx,3)["actions"]
    assert "lecturer:profile_review" not in client.get("/api/v1/me/context",headers=hdr(admin)).json()["actions"]
    assert can_review(session,users[3],lecturers[0])
    assert can_review(session,users[3],lecturers[1])
    session.expire_all()
    assert session.get(m.PositionAssignment,old_id).state=="REVOKED"
    history=client.get("/api/v1/admin/positions",headers=hdr(admin)).json()["items"]
    assert any(row["id"]==str(old_id) for row in history) and any(row["id"]==new["id"] for row in history)
    assert next(row for row in history if row["id"]==str(old_id))["basis_ref"] is None
    assert client.post(f"/api/v1/admin/positions/{old_id}/revoke",headers={**hdr(admin),"If-Match":str(old_version)},json={"basis_ref":"QĐ TEST","reason":"Bản đã cũ không được ghi đè"}).status_code==409
    notices=client.get("/api/v1/notifications",headers=hdr(users[3])).json()["items"]
    assert any("bổ nhiệm Trưởng bộ môn" in row["message"] for row in notices)
    activity=client.get("/api/v1/activity",headers=hdr(users[3]),params={"resource_type":"position_assignment","resource_id":new["id"]}).json()
    assert any(row["action"]=="POSITION_ASSIGNED" for row in activity["items"])
    revoked=client.post(f"/api/v1/admin/positions/{new['id']}/revoke",headers={**hdr(admin),"If-Match":str(new["row_version"])},json={"basis_ref":"QĐ TEST thu hồi","reason":"Kết thúc phân công dữ liệu giả"})
    assert revoked.status_code==200,revoked.text
    assert "topic:department_decide" not in context(ctx,3)["actions"]


def test_overlap_invalid_dates_and_wrong_candidates_do_not_modify_head(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx;row=existing(ctx);version=row.row_version
    base="/api/v1/admin/positions"
    assert client.post(base,headers=hdr(admin),json=payload(ctx,department_id=str(row.department_id))).status_code==409
    assert client.post(base,headers=hdr(admin),json=payload(ctx,department_id=str(row.department_id),effective_from=(now()-timedelta(days=1)).isoformat())).status_code==422
    assert client.post(base,headers=hdr(admin),json=payload(ctx,department_id=str(row.department_id),effective_from="2030-01-01T08:00")).status_code==422
    assert client.post(base,headers=hdr(admin),json=payload(ctx,department_id=str(row.department_id),effective_to=(now()-timedelta(days=1)).isoformat())).status_code==422
    users[3].status="LOCKED";session.commit()
    assert client.post(base+f"/{row.id}/replace",headers={**hdr(admin),"If-Match":str(version)},json=payload(ctx)).status_code==422
    users[3].status="ACTIVE";session.commit()
    other=m.Department(id=uuid4(),faculty_id=session.get(m.Department,row.department_id).faculty_id,code="TEST-"+uuid4().hex[:10],name="Bộ môn khác")
    session.add(other);session.commit()
    assert client.post(base,headers=hdr(admin),json=payload(ctx,department_id=str(other.id))).status_code==422
    session.expire_all();assert session.get(m.PositionAssignment,row.id).row_version==version
    assert "topic:department_decide" in context(ctx,4)["actions"]


def test_future_replacement_and_cancel_do_not_grant_early(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx;old=existing(ctx)
    start=now()+timedelta(days=1);end=start+timedelta(days=90)
    response=client.post(f"/api/v1/admin/positions/{old.id}/replace",headers={**hdr(admin),"If-Match":str(old.row_version)},json=payload(ctx,effective_from=start.isoformat(),effective_to=end.isoformat()))
    assert response.status_code==201,response.text
    new=response.json();assert new["status"]=="SCHEDULED"
    assert "topic:department_decide" in context(ctx,4)["actions"]
    assert "topic:department_decide" not in context(ctx,3)["actions"]
    session.expire_all();assert session.get(m.PositionAssignment,old.id).effective_to==start
    cancel=client.post(f"/api/v1/admin/positions/{new['id']}/revoke",headers={**hdr(admin),"If-Match":str(new["row_version"])},json={"basis_ref":"QĐ TEST hủy","reason":"Hủy quyết định chưa có hiệu lực"})
    assert cancel.status_code==200,cancel.text
    assert cancel.json()["state"]=="REVOKED"
    assert "topic:department_decide" not in context(ctx,3)["actions"]
    assert "topic:department_decide" in context(ctx,4)["actions"]


def test_conflicting_replacement_rolls_back_old_appointment(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx;old=existing(ctx)
    # Simulate legacy inconsistent source records; a failed replacement must undo its first update.
    other=m.PositionAssignment(id=uuid4(),lecturer_id=lecturers[2].id,position_id=old.position_id,department_id=old.department_id,effective_from=now()+timedelta(days=2),state="ACTIVE")
    session.add(other);session.commit();version=old.row_version
    before=session.scalar(select(func.count()).select_from(m.PositionAssignment))
    response=client.post(f"/api/v1/admin/positions/{old.id}/replace",headers={**hdr(admin),"If-Match":str(version)},json=payload(ctx))
    assert response.status_code==409,response.text
    session.expire_all();old=session.get(m.PositionAssignment,old.id)
    assert old.state=="ACTIVE" and old.effective_to is None and old.row_version==version
    assert session.scalar(select(func.count()).select_from(m.PositionAssignment))==before


def test_expired_appointment_does_not_block_reappointment(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx;old=existing(ctx)
    old.effective_from=now()-timedelta(days=3);old.effective_to=now()-timedelta(days=1);session.commit()
    response=client.post("/api/v1/admin/positions",headers=hdr(admin),json=payload(ctx,department_id=str(old.department_id)))
    assert response.status_code==201,response.text
    session.expire_all();assert session.get(m.PositionAssignment,old.id).state=="EXPIRED"
