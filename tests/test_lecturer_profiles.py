"""Profile publication, privacy, independent authority and safe images on PostgreSQL."""
from datetime import timedelta
from io import BytesIO
from uuid import UUID,uuid4

import pytest
from PIL import Image
from sqlalchemy import func,select

from test_registration import scenario,hdr
from backend.db.models import entities as m
from backend.services.theses import now


@pytest.fixture
def profiles(scenario,monkeypatch,tmp_path):
    from backend.services import file_scanner
    monkeypatch.setenv("KLTN_DOCUMENT_DIR",str(tmp_path/"avatars"))
    monkeypatch.setattr(file_scanner,"executable",lambda:None)
    monkeypatch.setattr(file_scanner,"clamdscan_executable",lambda:None)
    client,users,students,lecturers,topic,session=scenario
    admin=m.UserAccount(id=uuid4(),external_subject="syn-admin-"+uuid4().hex,base_role="ADMIN",status="ACTIVE")
    session.add(admin);session.commit()
    return client,users,lecturers,session,admin


def headers(user,version):return {**hdr(user),"If-Match":str(version)}


def own(ctx,index=3):
    client,users,_,_,_=ctx
    result=client.get("/api/v1/account/lecturer-profile",headers=hdr(users[index]));assert result.status_code==200,result.text
    return result.json()


def draft(ctx,index=3):
    client,users,_,_,_=ctx;version=own(ctx,index)["profile"]["row_version"]
    result=client.post("/api/v1/account/lecturer-profile/changes",headers=headers(users[index],version))
    assert result.status_code==201,result.text
    return result.json()


def save(ctx,request,index=3,**changes):
    client,users,_,_,_=ctx
    data={**request["proposed_data"],"display_name":"Giảng viên hồ sơ mẫu","academic_degree":"MASTER",
        "contact_email":"contact@example.test","contact_phone":"0901234567","show_phone":False,
        "biography":"Thông tin chuyên môn giả để kiểm thử","specializations":["Công nghệ phần mềm"],**changes}
    result=client.put(f"/api/v1/lecturer-profile-changes/{request['id']}",headers=headers(users[index],request["row_version"]),json=data)
    assert result.status_code==200,result.text
    return result.json()


def submit(ctx,request,index=3):
    client,users,_,_,_=ctx
    result=client.post(f"/api/v1/lecturer-profile-changes/{request['id']}/submit",headers=headers(users[index],request["row_version"]),json={"note":"Đề nghị đối chiếu hồ sơ chuyên môn mẫu"})
    assert result.status_code==200,result.text
    return result.json()


def decide(ctx,request,decision="APPROVE",index=4):
    client,users,_,_,_=ctx
    return client.post(f"/api/v1/lecturer-profile-changes/{request['id']}/decision",headers=headers(users[index],request["row_version"]),
        json={"decision":decision,"reason":"Đã đối chiếu theo nguồn hồ sơ giả kiểm thử","confirm_verified":True})


def image():
    out=BytesIO();Image.new("RGB",(800,600),(50,120,90)).save(out,format="JPEG",comment=b"SYNTHETIC METADATA")
    return out.getvalue()


def test_draft_is_private_and_one_open_request_per_lecturer(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx
    d=draft(ctx);assert own(ctx)["profile"]["avatar_url"] is None
    assert client.post("/api/v1/account/lecturer-profile/changes",headers=headers(users[3],1)).status_code==409
    path=f"/api/v1/lecturer-profile-changes/{d['id']}"
    for user in (users[0],users[4],users[5],admin):assert client.get(path,headers=hdr(user)).status_code==404
    assert client.get("/api/v1/account/lecturer-profile",headers=hdr(users[0])).status_code==403
    saved=save(ctx,d)
    assert client.get(f"/api/v1/lecturer-profiles/{lecturers[0].id}",headers=hdr(users[0])).json()["display_name"]==lecturers[0].display_name
    assert own(ctx)["active_request"]["proposed_data"]["display_name"]==saved["proposed_data"]["display_name"]


def test_approval_is_atomic_publishes_only_reviewed_data_and_notifies(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx
    original=lecturers[0].display_name
    sent=submit(ctx,save(ctx,draft(ctx)))
    assert lecturers[0].display_name==original
    inbox=client.get("/api/v1/notifications",headers=hdr(users[4])).json()["items"]
    assert any("gửi cập nhật hồ sơ" in row["message"] for row in inbox)
    assert client.get("/api/v1/lecturer-profile-reviews",headers=hdr(users[4])).json()["total"]==1
    result=decide(ctx,sent);assert result.status_code==200,result.text
    visible=client.get(f"/api/v1/lecturer-profiles/{lecturers[0].id}",headers=hdr(users[0])).json()
    assert visible["display_name"]=="Giảng viên hồ sơ mẫu" and visible["verified_at"]
    assert visible["data"]["academic_degree"]=="MASTER"
    assert visible["data"]["contact_phone"] is None and visible["account_email"] is None
    assert own(ctx)["profile"]["data"]["contact_phone"]=="0901234567"
    inbox=client.get("/api/v1/notifications",headers=hdr(users[3])).json()["items"]
    assert any("đã được duyệt" in row["message"] for row in inbox)
    assert decide(ctx,sent).status_code==409
    assert client.put(f"/api/v1/lecturer-profile-changes/{sent['id']}",headers=headers(users[3],result.json()["row_version"]),json=sent["proposed_data"]).status_code==409
    assert own(ctx)["history"][0]["state"]=="APPROVED"


def test_return_and_withdraw_preserve_previous_publication_and_history(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx
    sent=submit(ctx,save(ctx,draft(ctx)));returned=decide(ctx,sent,"RETURN")
    assert returned.status_code==200,returned.text
    d=draft(ctx);assert d["version_no"]==2 and d["proposed_data"]==sent["proposed_data"]
    assert own(ctx)["profile"]["display_name"]!="Giảng viên hồ sơ mẫu"
    response=client.post(f"/api/v1/lecturer-profile-changes/{d['id']}/withdraw",headers=headers(users[3],d["row_version"]),json={"reason":"Bổ sung thông tin rồi gửi bản khác"})
    assert response.status_code==200 and response.json()["state"]=="WITHDRAWN"
    assert len(own(ctx)["history"])==2


def test_scope_self_approval_and_expired_head_are_rejected(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx
    sent=submit(ctx,save(ctx,draft(ctx)))
    assert decide(ctx,sent,index=3).status_code==403
    assert decide(ctx,sent,index=5).status_code==404
    assert client.get("/api/v1/lecturer-profile-reviews",headers=hdr(admin)).status_code==403
    assignment=session.scalar(select(m.PositionAssignment).where(m.PositionAssignment.lecturer_id==lecturers[1].id))
    assignment.effective_to=now()-timedelta(minutes=1);session.commit()
    assert decide(ctx,sent).status_code==404
    assert not any("gửi cập nhật hồ sơ" in row["message"] for row in client.get("/api/v1/notifications",headers=hdr(users[4])).json()["items"])


def test_head_profile_requires_an_independent_faculty_dean(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx
    sent=submit(ctx,save(ctx,draft(ctx,4),index=4),index=4)
    assert decide(ctx,sent,index=4).status_code==403
    faculty=session.get(m.Department,lecturers[1].department_id).faculty_id
    position=m.OrganizationalPosition(id=uuid4(),code="FACULTY_DEAN",name="Trưởng khoa mẫu")
    session.add(position);session.flush()
    session.add(m.PositionAssignment(id=uuid4(),lecturer_id=lecturers[2].id,position_id=position.id,faculty_id=faculty,effective_from=now()-timedelta(days=1),state="ACTIVE"));session.commit()
    approved=decide(ctx,sent,index=5);assert approved.status_code==200,approved.text


def test_stale_draft_and_stale_base_cannot_overwrite_identity_correction(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx
    d=draft(ctx);saved=save(ctx,d)
    assert client.put(f"/api/v1/lecturer-profile-changes/{d['id']}",headers=headers(users[3],d["row_version"]),json=d["proposed_data"]).status_code==409
    sent=submit(ctx,saved)
    correction={"display_name":"Tên định danh đã đối chiếu","lecturer_code":lecturers[0].lecturer_code,"department_id":str(lecturers[0].department_id),"reason":"Sửa theo danh sách nhân sự chính thức","source_reference":"SYN-OFFICIAL-01"}
    result=client.put(f"/api/v1/lecturer-directory/{lecturers[0].id}/identity",headers=headers(admin,lecturers[0].row_version),json=correction)
    assert result.status_code==200,result.text
    assert decide(ctx,sent).status_code==409
    assert decide(ctx,sent,"RETURN").status_code==200
    new=draft(ctx);assert new["proposed_data"]["display_name"]==correction["display_name"]


def test_approval_requires_explicit_verification_and_active_target(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx
    sent=submit(ctx,save(ctx,draft(ctx)))
    path=f"/api/v1/lecturer-profile-changes/{sent['id']}/decision"
    assert client.post(path,headers=headers(users[4],sent["row_version"]),json={"decision":"APPROVE","reason":"Lý do kiểm thử xác nhận"}).status_code==422
    users[3].status="LOCKED";session.commit()
    assert decide(ctx,sent).status_code==409
    assert decide(ctx,sent,"RETURN").status_code==200


def test_avatar_is_normalized_quarantined_private_and_published_only_after_approval(profiles):
    ctx=profiles;client,users,lecturers,session,admin=ctx
    d=save(ctx,draft(ctx));path=f"/api/v1/lecturer-profile-changes/{d['id']}"
    uploaded=client.post(path+"/avatar",headers={**headers(users[3],d["row_version"]),"Content-Type":"application/octet-stream"},content=image())
    assert uploaded.status_code==201,uploaded.text
    d=uploaded.json();assert d["avatar_scan_state"]=="QUARANTINED"
    assert client.get(path+"/avatar",headers=hdr(users[3])).status_code==409
    assert client.get(path+"/avatar",headers=hdr(users[4])).status_code==404
    assert client.post(path+"/submit",headers=headers(users[3],d["row_version"]),json={"note":"Đề nghị duyệt ảnh kiểm thử"}).status_code==409
    stored=session.get(m.StoredFile,session.get(m.LecturerProfileChange,UUID(d["id"])).avatar_file_id)
    stored.scan_state="CLEAN";session.commit()
    returned=client.get(path+"/avatar",headers=hdr(users[3]));assert returned.status_code==200
    decoded=Image.open(BytesIO(returned.content));assert decoded.size==(512,512) and decoded.format=="PNG" and "exif" not in decoded.info
    sent=submit(ctx,d);assert client.get(path+"/avatar",headers=hdr(users[4])).status_code==200
    assert decide(ctx,sent).status_code==200
    assert client.get(f"/api/v1/lecturer-profiles/{lecturers[0].id}/avatar",headers=hdr(users[0])).status_code==200
    d=draft(ctx);removed=client.delete(f"/api/v1/lecturer-profile-changes/{d['id']}/avatar",headers=headers(users[3],d["row_version"]))
    assert removed.status_code==200 and removed.json()["avatar_url"] is None
    assert own(ctx)["profile"]["avatar_url"]
    assert decide(ctx,submit(ctx,removed.json())).status_code==200
    assert own(ctx)["profile"]["avatar_url"] is None


@pytest.mark.parametrize("content",[b"not an image",b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',b"x"*(5*1024*1024+1)],ids=["invalid","svg","oversized"])
def test_unsafe_avatar_and_oversized_upload_leave_no_stored_file(profiles,content):
    ctx=profiles;client,users,_,session,_=ctx;d=draft(ctx)
    before=session.scalar(select(func.count()).select_from(m.StoredFile))
    result=client.post(f"/api/v1/lecturer-profile-changes/{d['id']}/avatar",headers=headers(users[3],d["row_version"]),content=content)
    assert result.status_code in (413,422)
    assert session.scalar(select(func.count()).select_from(m.StoredFile))==before


@pytest.mark.parametrize("changes",[{"website":"javascript:alert(1)"},{"contact_phone":"not-a-phone"},{"academic_degree":"FAKE"},{"specializations":["x"]*13},{"biography":"a\x00b"},{"department_id":str(uuid4())}])
def test_profile_fields_reject_invalid_or_privilege_changing_data(profiles,changes):
    ctx=profiles;client,users,_,_,_=ctx;d=draft(ctx)
    result=client.put(f"/api/v1/lecturer-profile-changes/{d['id']}",headers=headers(users[3],d["row_version"]),json={**d["proposed_data"],**changes})
    assert result.status_code==422,result.text


def test_directory_search_pagination_and_private_account_email(profiles):
    client,users,lecturers,session,admin=profiles
    lecturers[0].display_name="Nguyễn Đăng Mẫu";users[3].email="private@example.test";users[3].password_hash="synthetic-hash";session.commit()
    results=client.get("/api/v1/lecturer-directory?q=nguyen%20dang",headers=hdr(users[0])).json()
    assert results["total"]==1 and results["items"][0]["account_email"] is None
    assert client.get("/api/v1/lecturer-directory?q=private@example.test",headers=hdr(users[0])).json()["total"]==0
    assert client.get("/api/v1/lecturer-directory?q=private@example.test",headers=hdr(admin)).json()["total"]==1
    paged=client.get("/api/v1/lecturer-directory?limit=1&offset=1",headers=hdr(users[0])).json()
    assert len(paged["items"])==1 and paged["total"]==3
    users[3].status="DISABLED";session.commit()
    assert client.get(f"/api/v1/lecturer-profiles/{lecturers[0].id}",headers=hdr(users[0])).status_code==404
    assert client.get(f"/api/v1/lecturer-profiles/{lecturers[0].id}",headers=hdr(admin)).status_code==200
