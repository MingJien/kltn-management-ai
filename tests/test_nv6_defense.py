"""Integration coverage for the frozen defense exports and student access."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from io import BytesIO
from uuid import UUID, uuid4

from docx import Document
from openpyxl import load_workbook
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services.theses import now
from backend.services.defense import thesis_state_allows_schedule, validate_extension_window
from test_core_workspace import workspace, synthetic_pdf, version_headers
from test_nv6_evaluation import check, complete_review, evaluation, get
from test_registration import hdr, scenario


def test_report_cache_refresh_expiration_and_scope(workspace, monkeypatch):
    from backend.services import nv6_reporting

    client, users, students, lecturers, session, path = workspace
    thesis = session.get(m.Thesis, UUID(path.rsplit("/", 1)[-1]))
    endpoint = f"/api/v1/nv6-reports/{thesis.round_id}"
    headers = hdr(users[4])
    elapsed = 100.0
    monkeypatch.setattr(nv6_reporting, "monotonic", lambda: elapsed)

    first = client.get(endpoint, headers=headers)
    assert first.status_code == 200, first.text
    assert len(first.json()["rows"]) == 2
    thesis.current_title = "Synthetic renamed thesis"
    session.commit()
    assert client.get(endpoint, headers=headers).json() == first.json()
    assert client.get(endpoint, headers=hdr(users[0])).status_code == 404

    refreshed = client.get(endpoint, headers=headers, params={"refresh": True}).json()
    assert all(row["title"] == "Synthetic renamed thesis" for row in refreshed["rows"])
    thesis.current_title = "Synthetic latest thesis title"
    session.commit()
    elapsed += 899
    assert client.get(endpoint, headers=headers).json() == refreshed
    elapsed += 1
    expired = client.get(endpoint, headers=headers).json()
    assert expired["rows"][0]["title"] == "Synthetic latest thesis title"

    coordinator = session.scalar(select(m.ResourceAssignment).where(
        m.ResourceAssignment.user_id == users[4].id,
        m.ResourceAssignment.assignment_type == "KLTN_COORDINATOR"))
    head = session.scalar(select(m.PositionAssignment).where(m.PositionAssignment.lecturer_id == lecturers[1].id))
    coordinator.state = head.state = "REVOKED"
    session.commit()
    assert client.get(endpoint, headers=headers).status_code == 404
    assert client.get(endpoint, headers=headers, params={"refresh": True, "department_id": students[0].department_id}).status_code == 404


def test_academic_profile_before_schedule_uses_scope_and_revision(evaluation):
    ctx, _ = evaluation
    client, users, students, lecturers, session, _ = ctx
    thesis = get(ctx)
    member = thesis["members"][0]["id"]
    endpoint = f"/api/v1/nv6-reports/{thesis['round_id']}/students/{member}"
    student = students[0]
    major = m.DepartmentMajor(department_id=student.department_id, code="SYN-CNTT", name="Công nghệ thông tin", active=True)
    session.add(major)
    session.commit()
    assert client.get(endpoint, headers=hdr(users[0])).status_code == 404
    profile = client.get(endpoint, headers=hdr(users[4]))
    assert profile.status_code == 200, profile.text
    summary_endpoint = f"/api/v1/nv6-reports/{thesis['round_id']}"
    for params in ({}, {"department_id": str(student.department_id)}):
        before = client.get(summary_endpoint, headers=hdr(users[4]), params=params)
        assert before.status_code == 200
        assert next(row for row in before.json()["rows"] if row["id"] == member)["class_name"] != "ĐHCNTT22A"
    data = {"class_name":"  ĐHCNTT22A ", "major_code":"SYN-CNTT", "training_cohort":"2022–2026",
            "birth_date":"2004-03-15", "source_reference":"Danh sách học vụ kiểm thử", "reason":"Đối chiếu thông tin học vụ"}
    headers = {**hdr(users[4]), "If-Match":profile.json()["revision"]}
    assert client.put(endpoint, headers=headers, json={**data,"major_code":"UNKNOWN"}).status_code == 422
    updated = client.put(endpoint, headers=headers, json=data)
    assert updated.status_code == 204, updated.text
    assert client.put(endpoint, headers=headers, json=data).status_code == 409
    for params in ({}, {"department_id": str(student.department_id)}):
        report = client.get(summary_endpoint, headers=hdr(users[4]), params=params).json()
        row = next(row for row in report["rows"] if row["id"] == member)
        assert row["class_name"] == "ĐHCNTT22A" and row["issues"] == []


def test_demo_council_accepts_head_and_newly_activated_guest(evaluation):
    from backend.services.account_tokens import make_token
    from backend.services.passwords import unusable_password

    ctx, _ = evaluation
    client, users, _, lecturers, session, _ = ctx
    thesis = get(ctx)
    round_ = session.get(m.ThesisRound, UUID(thesis["round_id"]))
    department = session.get(m.Department, lecturers[1].department_id)
    round_.code, department.code = "SYN-DEMO", "SYN-DEMO-DEP"
    faculty = m.Faculty(id=uuid4(), code="KHOA-CNKT", name="Synthetic faculty of technology")
    unit = m.Department(id=uuid4(), faculty_id=faculty.id, code="BM-CNTT", name="Công nghệ thông tin")
    session.add(faculty)
    session.flush()
    session.add(unit)
    session.flush()
    guests = []
    for index in range(3):
        account = m.UserAccount(id=uuid4(), email=f"synthetic-{uuid4().hex}@example.invalid",
            password_hash=unusable_password(), base_role="LECTURER", status="DISABLED" if index == 0 else "ACTIVE",
            email_verified_at=None if index == 0 else now())
        person = m.LecturerProfile(id=uuid4(), user_id=account.id, department_id=unit.id,
            lecturer_code="GV-" + uuid4().hex[:8], display_name="Synthetic guest lecturer")
        session.add(account)
        session.flush()
        session.add(person)
        guests.append((account, person))
    session.commit()
    base = "/api/v1/defense"

    def candidate_ids():
        response = client.get(base, headers=hdr(users[4]))
        assert response.status_code == 200, response.text
        return {item["id"] for item in response.json()["candidates"]}

    catalog = client.get(base, headers=hdr(users[4])).json()["scope_catalog"]
    assert {row["department_code"] for row in catalog if row["round_code"] == "SYN-DEMO"} >= {"BM-CNTT", "SYN-DEMO-DEP"}
    assert all(row["can_manage"] for row in catalog if row["round_code"] == "SYN-DEMO")

    account, invited = guests[0]
    assert str(lecturers[1].id) in candidate_ids()
    assert str(invited.id) not in candidate_ids()
    activated = client.post("/api/v1/account/activate", json={
        "token": make_token(account, "activate"), "password": "Synthetic-Demo-Password-42"})
    assert activated.status_code == 204, activated.text
    assert str(invited.id) in candidate_ids()

    members = [lecturers[1], lecturers[2], *[person for _, person in guests]]
    payload = {"round_id": str(round_.id), "department_id": str(department.id), "name": "Synthetic demo council",
        "reference": "QD-SYNTHETIC", "thesis_ids": [thesis["thesis_id"]], "confirmed_no_conflict": True,
        "members": [{"lecturer_id": str(person.id), "role": role} for person, role in zip(
            members, ["CHAIR", "SECRETARY", "REVIEWER", "REVIEWER", "MEMBER"])]}
    created = client.post(base + "/councils", headers=hdr(users[4]), json=payload)
    assert created.status_code == 201, created.text
    saved = session.get(m.DefenseCouncil, UUID(created.json()["id"]))
    assert all("invitation_reference" not in member for member in saved.members)


def test_council_charts_marks_and_exports_use_one_frozen_record(evaluation, monkeypatch):
    ctx,_ = evaluation
    client,users,students,lecturers,session,path = ctx
    major_code="EXPORT-MAJOR"
    for dept in {student.department_id for student in students}:
        session.add(m.DepartmentMajor(id=uuid4(),department_id=dept,code=major_code,name="Công nghệ thông tin"))
    session.flush()
    for student in students:
        student.class_name="ĐHCNTT22A"
        student.major_code=major_code
        student.birth_date=datetime(2004,3,15).date()
        student.training_cohort="2022–2026"
    session.commit()
    thesis = get(ctx)
    proof=client.post(path+'/documents',headers=hdr(users[0]),json={'document_type':'SUPPORTING','title':'Synthetic research publication evidence'})
    register = f"/api/v1/defense/round-register/{thesis['round_id']}"
    assert proof.status_code==201,proof.text
    proof=proof.json()
    uploaded=client.post(path+'/documents/'+proof['id']+'/versions',headers={**version_headers(users[0],proof),
        'X-File-Name':'research-evidence.pdf','Content-Type':'application/octet-stream'},content=synthetic_pdf())
    assert uploaded.status_code==201,uploaded.text
    evidence_version=uploaded.json()['versions'][0]['id']
    evidence=session.get(m.DocumentVersion,UUID(evidence_version))
    session.get(m.StoredFile,evidence.stored_file_id).scan_state='CLEAN'
    session.commit()
    claim_endpoint = path+'/publication-claims'
    claim = client.post(claim_endpoint, headers=hdr(users[0]), json={
        'title':'Synthetic publication title','venue':'Synthetic journal','reference':'DOI synthetic publication',
        'contribution':'Synthetic individual contribution to the thesis research',
        'student_ids':[str(students[0].id)],'evidence_version_id':evidence_version})
    assert claim.status_code==201,claim.text
    claim_endpoint += '/'+claim.json()['id']+'/decision'
    confirmed=client.post(claim_endpoint,headers={**hdr(users[3]),'If-Match':'1'},json={
        'outcome':'CONFIRM','reason':'GVHD confirmed contribution'})
    assert confirmed.status_code==200,confirmed.text
    account = m.UserAccount(id=uuid4(),external_subject="defense-"+uuid4().hex,base_role="LECTURER",status="ACTIVE")
    extra = m.LecturerProfile(id=uuid4(),user_id=account.id,department_id=lecturers[1].department_id,
        lecturer_code="D-"+uuid4().hex[:10],display_name="Synthetic council reviewer")
    session.add(account)
    session.flush()
    session.add(extra)
    session.commit()
    visiting_faculty = m.Faculty(id=uuid4(), code="VF-"+uuid4().hex[:10], name="Synthetic visiting faculty")
    visiting_department = m.Department(id=uuid4(), faculty_id=visiting_faculty.id,
        code="VD-"+uuid4().hex[:10], name="Synthetic visiting department")
    session.add(visiting_faculty)
    session.flush()
    session.add(visiting_department)
    session.flush()
    extras=[]
    for index in range(2):
        account2=m.UserAccount(id=uuid4(),external_subject="council-"+uuid4().hex,base_role="LECTURER",status="ACTIVE")
        person=m.LecturerProfile(id=uuid4(),user_id=account2.id,
            department_id=visiting_department.id if index==1 else lecturers[1].department_id,
            lecturer_code="C-"+uuid4().hex[:10],display_name=f"Synthetic council extra {index}")
        session.add(account2);session.flush();session.add(person);session.flush()
        extras.append((account2,person))
    session.commit()
    base = "/api/v1/defense"
    council_input = {"round_id":thesis["round_id"],
        "department_id":str(lecturers[1].department_id),"name":"Synthetic council","reference":"QD-DEFENSE-TEST",
        "thesis_ids":[thesis["thesis_id"]],"confirmed_no_conflict":True,
        "members":[{"lecturer_id":str(person.id),"role":role} for person,role in
            [(lecturers[1],"CHAIR"),(lecturers[2],"SECRETARY"),(extra,"REVIEWER"),(extras[0][1],"REVIEWER"),(extras[1][1],"MEMBER")]]}
    conflicted = {**council_input, "members": [*council_input["members"][:-1],
        {"lecturer_id":str(lecturers[0].id),"role":"MEMBER"}]}
    conflict_response = client.post(base+"/councils",headers=hdr(users[4]),json=conflicted)
    assert conflict_response.status_code==409 and "GVHD" in conflict_response.json()["detail"]
    unconfirmed = client.post(base+"/councils",headers=hdr(users[4]),json=council_input)
    assert unconfirmed.status_code==422 and "ngoài Khoa" in unconfirmed.json()["detail"]
    created = client.post(base+"/councils",headers=hdr(users[4]),json={**council_input,"confirmed_guests":True})
    assert created.status_code==201,created.text
    council = created.json()["id"]
    assert session.get(m.DefenseCouncil,UUID(council)).members[-1]["invitation_reference"]==council_input["reference"]
    body = {"confirmed_no_conflict":True,"council_id":council,"thesis_id":thesis["thesis_id"],"room":"Synthetic room",
        "starts_at":(now()-timedelta(hours=2)).isoformat(),"ends_at":(now()-timedelta(hours=1)).isoformat()}
    assert client.post(base+"/slots",headers=hdr(users[4]),json=body).status_code == 409
    for index in range(len(thesis["members"])):
        complete_review(ctx,member=index)
        response = check(ctx,member=index)
        assert response.status_code == 200,response.text
    unscheduled=client.get(register,headers=hdr(users[4])).json()
    assert len(unscheduled['unscheduled'])==2 and unscheduled['scheduled_count']==0
    response = client.post(base+"/slots",headers=hdr(users[4]),json=body)
    assert response.status_code==201,response.text
    slot = response.json()["id"]
    assert client.get(base,headers=hdr(users[0])).json()['slots'][0]['results'][
        client.get(base,headers=hdr(users[0])).json()['slots'][0]['roster'][0]['id']]['attendance'].get('bonus','0')=='0'
    approved=client.post(claim_endpoint,headers={**hdr(users[4]),'If-Match':'2'},json={
        'outcome':'APPROVE','reason':'TBM confirmed research publication','points':{str(students[0].id):'1'}})
    assert approved.status_code==200,approved.text
    assert client.get(base,headers=hdr(users[0])).json()['slots'][0]['results'][
        client.get(base,headers=hdr(users[0])).json()['slots'][0]['roster'][0]['id']]['attendance']['bonus']=='1'
    assert client.post(base+"/slots",headers=hdr(users[4]),json=body).status_code==409
    assert client.get(base,headers=hdr(users[2])).json()["slots"]==[]
    student_slots = client.get(base,headers=hdr(users[0])).json()["slots"]
    assert len(student_slots[0]["roster"])==1
    own_id=student_slots[0]["roster"][0]["id"]
    assert set(student_slots[0]["results"]) <= {own_id}
    assert all(row.get("average") is None and not row.get("scores") for row in student_slots[0]["results"].values())
    first = student_slots[0]["roster"][0]["id"]
    second = client.get(base,headers=hdr(users[1])).json()["slots"][0]["roster"][0]["id"]
    record=client.get(base,headers=hdr(users[4])).json()["councils"][0]
    edited={"round_id":record["round_id"],"department_id":record["department_id"],"name":"Synthetic council revised","reference":"QD-REVISED",
        "confirmed_guests":True,
        "members":[{"lecturer_id":p["id"],"role":p["role"]} for p in record["members"]]}
    response=client.put(base+"/councils/"+council,headers={**hdr(users[4]),"If-Match":record["signature"]},json=edited)
    assert response.status_code==200,response.text
    assert client.put(base+"/councils/"+council,headers={**hdr(users[4]),"If-Match":record["signature"]},json=edited).status_code==409
    endpoint = base+"/slots/"+slot

    def mutate(method,suffix,user,data,status=204):
        current = next(s["version"] for s in client.get(base,headers=hdr(users[4])).json()["slots"] if s["id"]==slot)
        res = client.request(method,endpoint+suffix,headers={**hdr(user),"If-Match":str(current)},json=data)
        assert res.status_code==status,res.text

    current_slot = lambda: next(s for s in client.get(base, headers=hdr(users[4])).json()["slots"] if s["id"] == slot)
    old = current_slot()
    new_time = {**body, "starts_at": (now()+timedelta(days=1)).isoformat(),
        "ends_at": (now()+timedelta(days=1, hours=1)).isoformat(), "room": "New synthetic room"}
    mutate("PUT", "", users[4], new_time, 200)
    assert current_slot()["room"] == "New synthetic room"
    assert client.put(endpoint, headers={**hdr(users[4]),"If-Match":str(old["version"])}, json=body).status_code == 409
    for recipient in (users[0], users[1], users[3], users[5]):
        inbox = client.get("/api/v1/notifications", headers=hdr(recipient)).json()["items"]
        assert any("New synthetic room" in n["message"] for n in inbox)
    mutate("PUT", "", users[4], body, 200)

    alternative = m.Topic(id=uuid4(), round_id=UUID(thesis["round_id"]), department_id=lecturers[1].department_id,
        proposer_user_id=users[3].id, proposer_type="LECTURER", code="ALT-"+uuid4().hex,
        current_title="Synthetic replacement thesis", max_students=1, state="APPROVED")
    session.add(alternative)
    session.commit()
    registration = client.post("/api/v1/topic-registrations", headers=hdr(users[2]), json={
        "topic_id":str(alternative.id),"member_student_ids":[str(students[2].id)],"confirm_creator":True})
    assert registration.status_code==201,registration.text
    reg_url="/api/v1/topic-registrations/"+registration.json()["id"]
    submitted=client.post(reg_url+"/submit",headers=hdr(users[2]))
    assert submitted.status_code==200,submitted.text
    accepted=client.post(reg_url+"/lecturer-decision",headers=version_headers(users[3],submitted.json()),json={"decision":"ACCEPT"})
    assert accepted.status_code==200,accepted.text
    replacement_id=accepted.json()["thesis_id"]
    replacement_path="/api/v1/theses/"+replacement_id
    replacement_ctx=(*ctx[:-1],replacement_path)
    change={**new_time,"thesis_id":replacement_id}
    mutate("PUT","",users[4],change,409)
    report_doc=client.post(replacement_path+"/documents",headers=hdr(users[2]),
        json={"document_type":"REPORT","title":"Replacement thesis report"})
    assert report_doc.status_code==201,report_doc.text
    upload=client.post(replacement_path+"/documents/"+report_doc.json()["id"]+"/versions",
        headers={**version_headers(users[2],report_doc.json()),"X-File-Name":"replacement.pdf","Content-Type":"application/octet-stream"},
        content=synthetic_pdf())
    assert upload.status_code==201,upload.text
    version=session.get(m.DocumentVersion,UUID(upload.json()["versions"][0]["id"]))
    session.get(m.StoredFile,version.stored_file_id).scan_state="CLEAN"
    session.commit()
    complete_review(replacement_ctx)
    checked=check(replacement_ctx)
    assert checked.status_code==200,checked.text
    mutate("PUT","",users[4],change,200)
    assert current_slot()["thesis_id"]==replacement_id
    assert current_slot()["report_filename"]=="replacement.pdf"
    assert client.get(base,headers=hdr(users[0])).json()["slots"]==[]
    assert client.get(base,headers=hdr(users[2])).json()["slots"][0]["thesis_id"]==replacement_id
    inbox=client.get("/api/v1/notifications",headers=hdr(users[0])).json()["items"]
    assert any("không còn được xếp" in notice["message"] for notice in inbox)
    mutate("PUT","",users[4],body,200)
    assert current_slot()["results"][first]["attendance"]["bonus"]=="1"

    mutate("POST","/finalize",users[4],{},409)
    mutate("PUT","/council-attendance",users[5],{
        "present_ids":[str(lecturers[1].id),str(extra.id),str(extras[0][1].id)],
        "reason":"Secretary missing from meeting"},422)
    present=[str(person.id) for person in [lecturers[1],lecturers[2],extra,extras[0][1]]]
    mutate("PUT","/council-attendance",users[5],{"present_ids":present,"reason":"Four members present, member absent"})
    updated=client.get(base,headers=hdr(users[4])).json()["councils"][0]
    assert client.put(base+"/councils/"+council,headers={**hdr(users[4]),"If-Match":updated["signature"]},json=edited).status_code==409
    mutate("PUT", "", users[4], new_time, 409)
    mutate("PUT","/attendance/"+first,users[5],{"status":"PRESENT"})
    mutate("PUT","/attendance/"+second,users[5],{"status":"ABSENT","reason":"Có báo vắng"})
    mutate("PUT","/bonus/"+first,users[4],{"points":"1","reference":"Synthetic research publication"},422)
    mutate("PUT","/bonus/"+first,users[4],{"points":"1","reference":"Synthetic research publication","evidence_version_id":evidence_version})
    meeting={"discussion":"Synthetic discussion","conclusion":"Synthetic conclusion","objectives":"Mục tiêu kiểm thử","functions":"Chức năng kiểm thử","achievements":"Kết quả kiểm thử","recommendations":"Kiến nghị kiểm thử","classifications":{first:"Xuất sắc"}}
    mutate("PUT","/minutes",users[5],meeting)
    mutate("POST","/finalize",users[4],{},409)
    blank = client.get(endpoint+"/forms/6",headers=hdr(users[5]),params={"student_id":first,"lecturer_id":str(lecturers[1].id),"blank":True})
    assert blank.status_code==200,blank.text
    blank_sheet=load_workbook(BytesIO(blank.content)).active
    assert str(blank_sheet["A14"].value)=="1.1" and blank_sheet["F14"].value is None
    assert blank_sheet["F28"].value==1
    assert client.get(endpoint+"/forms/6",headers=hdr(users[5])).status_code==404
    assert client.get(endpoint+"/report",headers=hdr(users[2])).status_code==404
    assert client.get(endpoint+"/report",headers=hdr(account)).status_code==200
    shared=client.get(base,headers=hdr(users[4])).json()["slots"][0]
    scores = ["1",".5",".5",".5",".5","1","1",".5",".5","1","2","1"]
    for account,person in [(users[4],lecturers[1]),(users[5],lecturers[2]),(account,extra),extras[0]]:
        res=client.put(endpoint+"/marks",headers={**hdr(account),"If-Match":str(shared["version"])},json={
            "thesis_member_id":first,"lecturer_id":str(person.id),"scores":scores,"ballot_revision":0,"context_token":shared["context_token"]})
        assert res.status_code==204,res.text
    claims_workspace=client.get(path+'/publication-claims',headers=hdr(users[4])).json()
    assert not claims_workspace['can_approve'] and not claims_workspace['can_review']
    assert client.post(claim_endpoint,headers={**hdr(users[4]),'If-Match':'3'},json={
        'outcome':'APPROVE','reason':'Attempt to change bonus after marking','points':{str(students[0].id):'0'}}).status_code==409
    students[0].class_name="ĐHCNTT22C"
    session.commit()
    pending_form=client.get(endpoint+"/forms/6",headers=hdr(users[4]),params={"student_id":first,"lecturer_id":str(lecturers[1].id)})
    assert pending_form.status_code==200,pending_form.text
    pending_sheet=load_workbook(BytesIO(pending_form.content)).active
    assert pending_sheet["F28"].value==1 and pending_sheet["F29"].value==10
    assert "ĐHCNTT22C" in pending_sheet["A7"].value
    assert "CHƯA CHỐT" in pending_sheet.oddFooter.left.text
    stale=client.put(endpoint+"/marks",headers={**hdr(users[4]),"If-Match":str(shared["version"])},json={
        "thesis_member_id":first,"lecturer_id":str(lecturers[1].id),"scores":scores,"ballot_revision":0,"context_token":shared["context_token"]})
    assert stale.status_code==409
    mutate("POST","/marks/"+first+"/"+str(lecturers[1].id)+"/void",users[5],{"reason":"Wrong paper was entered"})
    mutate("PUT","/marks",users[4],{"thesis_member_id":first,"lecturer_id":str(lecturers[1].id),"scores":scores})
    mutate("PUT","/marks",extras[1][0],{"thesis_member_id":first,"lecturer_id":str(extras[1][1].id),
        "scores":scores},409)
    mutate("PUT","/minutes",users[5],{**meeting,"recommendations":"","classifications":{first:"Chờ xác nhận"}})
    mutate("POST","/finalize",users[4],{},409)
    meeting["oral_comments"] = {first:{str(extra.id):"Ý kiến từ phản biện tại cuộc họp"}}
    mutate("PUT","/minutes",users[5],meeting)
    mutate("POST","/finalize",users[4],{})
    mutate("PUT","/bonus/"+first,users[4],{"points":"0"},409)
    mutate("POST","/reopen-unsigned",users[4],{"reason":"Correct unsigned meeting conclusion","confirm_unsigned":True})
    mutate("PUT","/minutes",users[5],{**meeting,"conclusion":"Synthetic conclusion corrected"})
    mutate("POST","/finalize",users[4],{})
    result = client.get(base,headers=hdr(users[0])).json()["slots"][0]["results"]
    assert result[first]["average"]=="10.0"
    absent = client.get(base,headers=hdr(users[1])).json()["slots"][0]["results"]
    assert absent[second]["average"] is None
    assert client.get(endpoint+"/forms/9",headers=hdr(users[0])).status_code==403
    for layout in ({"line_spacing":1.2}, {"paragraph_space":0}, {"break_recommendations":True}):
        assert client.get(endpoint+"/forms/9",headers=hdr(users[4]),params=layout).status_code==403
        assert client.get(endpoint+"/forms/9",headers=hdr(users[5]),params=layout).status_code==200
    minutes = client.get(endpoint+"/forms/9",headers=hdr(users[5]))
    assert minutes.status_code==200,minutes.text
    doc = Document(BytesIO(minutes.content))
    assert "Synthetic conclusion corrected" in "\n".join(p.text for p in doc.paragraphs)
    assert "Mục tiêu kiểm thử" in "\n".join(p.text for p in doc.paragraphs)
    assert "Ý kiến từ phản biện tại cuộc họp" in "\n".join(p.text for p in doc.paragraphs)
    def issue(url,user):
        separator='&' if '?' in url else '?'
        preview=client.get(url+separator+'preview_revision=true',headers=hdr(user))
        assert preview.status_code==200,preview.text
        return client.post(url+separator+'expected_revision='+preview.json()['revision'],headers=hdr(user))
    legacy = session.get(m.DefenseSlot, UUID(slot))
    complete_roster = legacy.roster
    legacy.roster = [{**row, "class_name": ""} if row["id"] == first else row for row in complete_roster]
    session.commit()
    shown = client.get(endpoint+"/forms/9?preview_revision=true", headers=hdr(users[5])).json()["revision"]
    previous_class = students[0].class_name
    students[0].class_name = "ĐHCNTT22-XAC-MINH"
    session.commit()
    assert client.post(endpoint+"/forms/9?expected_revision="+shown, headers=hdr(users[5])).status_code == 409
    legacy.roster = complete_roster
    students[0].class_name = previous_class
    session.commit()
    issued_minutes=issue(endpoint+"/forms/9",users[5])
    assert issued_minutes.status_code==200,issued_minutes.text
    waiting=client.get('/api/v1/thesis-archive',headers=hdr(users[0])).json()[0]
    assert waiting['blockers'] and len(waiting['snapshot']['students'])==2
    assert waiting['snapshot']['advisor'] and not waiting['can_submit']
    minutes_record=client.get(endpoint+"/prints",headers=hdr(users[5])).json()[0]
    replacement=issue(endpoint+'/forms/9',users[5])
    assert replacement.status_code==200,replacement.text
    history=client.get(endpoint+'/prints',headers=hdr(users[5])).json()
    latest=history[0]
    previous=next(r for r in history if r['id']==minutes_record['id'])
    assert latest['current'] and not previous['current'] and previous['superseded_by']==latest['code']
    assert latest['print_number']==2
    import re
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    printed_footer = Document(BytesIO(replacement.content)).sections[0].footer.paragraphs[0]
    assert printed_footer.alignment == WD_ALIGN_PARAGRAPH.LEFT
    assert printed_footer.text.startswith("Xuất tại: http")
    assert re.search(rf"Mã số: {latest['code']} · v2 · \d{{2}}:\d{{2}} \d{{2}}/\d{{2}}/\d{{4}}$", printed_footer.text)
    lookup=client.get(base+'/print-lookup/'+minutes_record['code'],headers=hdr(users[5]))
    assert lookup.status_code==200 and not lookup.json()['current']
    assert client.get(base+'/print-lookup/'+minutes_record['code'],headers=hdr(users[0])).status_code in (403,404)
    assert client.post(base+'/prints/'+latest['id']+'/withdraw',headers=hdr(users[5]),json={'reason':'Withdraw duplicate test print'}).status_code==204
    assert not client.get(base+'/print-lookup/'+latest['code'],headers=hdr(users[5])).json()['current']
    assert client.get(base+"/prints/"+minutes_record["id"],headers=hdr(users[0])).status_code==404
    layout_fields=client.get(endpoint+"/forms/9?layout_fields=true",headers=hdr(users[5]))
    assert {r["key"] for r in layout_fields.json()["fields"]}=={"objectives","functions","achievements","discussion","conclusion","recommendations","reviewer_comments","member_comments"}
    styled=client.get(endpoint+"/forms/9",headers=hdr(users[5]),params={"line_breaks":'{"conclusion":[9]}',"narrative_italic":"true"})
    assert styled.status_code==200,styled.text
    assert any(p.text=="Synthetic\n conclusion corrected" for p in Document(BytesIO(styled.content)).paragraphs)
    for broken in ['{"average":[0]}','{"conclusion":"changed"}','{"conclusion":[99999]}','{"conclusion":[true]}']:
        assert client.get(endpoint+"/forms/9",headers=hdr(users[5]),params={"line_breaks":broken}).status_code==422

    form6 = client.get(endpoint+"/forms/6",headers=hdr(users[4]),params={
        "student_id":first,"lecturer_id":str(lecturers[1].id)})
    assert form6.status_code==200,form6.text
    sheet = load_workbook(BytesIO(form6.content)).active
    assert sheet["F29"].value==10 and sheet["F28"].value==1
    assert client.get(register+"/forms/11",headers=hdr(users[4])).status_code==409
    assert client.post(base+"/councils/"+council+"/close",headers=hdr(users[4])).status_code==204
    assert client.get(register+"/forms/10",headers=hdr(users[4])).status_code==409
    assert client.get(register,headers=hdr(users[5])).status_code==404
    decision_path=endpoint+"/absence/"+second
    decision={"outcome":"NOT_PASSED","reference":"QD-ABSENCE-01","reason":"Faculty confirmed absence after reviewing the case","revision":0}
    assert client.post(decision_path,headers=hdr(users[0]),json=decision).status_code==403
    assert client.post(decision_path,headers=hdr(users[4]),json=decision).status_code==204
    # The replacement thesis shown during rescheduling remains eligible but
    # unscheduled until its own eligibility is independently reassessed.
    incomplete_register = client.get(register, headers=hdr(users[4])).json()
    assert [row["code"] for row in incomplete_register["unscheduled"]]==[students[2].student_code]
    assert any("chưa được xếp lịch" in issue for issue in incomplete_register["issues"])
    for form_path in ("/forms/10", "/forms/11?course_code=ALT_11"):
        blocked = client.get(register+form_path, headers=hdr(users[4]))
        assert blocked.status_code == 409
        assert "chưa được xếp lịch" in blocked.json()["detail"]
    assert check(replacement_ctx, discipline="WARNING_OR_HIGHER").status_code==200
    form10 = issue(register+"/forms/10",users[4])
    assert form10.status_code==200,form10.text
    assert any(row.cells[-1].text=="10.0" for row in Document(BytesIO(form10.content)).tables[1].rows)
    assert client.get(register+"/forms/11",headers=hdr(users[4])).status_code==422
    official = client.get(register+"/forms/11?course_code=IT2026",headers=hdr(users[4]))
    assert official.status_code==200,official.text
    rows = list(load_workbook(BytesIO(official.content),read_only=True).active.values)
    assert any(r[1]==students[0].student_code and r[5]==10 for r in rows)
    assert rows[4][1] == "Học phần: [IT2026] - Khóa luận tốt nghiệp"
    assert any(r[1]==students[1].student_code and r[5] is None and r[6].startswith("Không đạt do vắng") for r in rows)
    print_record=client.get(register+"/prints",headers=hdr(users[4])).json()[0]
    # An authorized metadata correction remains possible after locking, with an
    # auditable new export revision and the exact same frozen academic result.
    import copy
    record=session.get(m.DefenseSlot,UUID(slot))
    snapshot=copy.deepcopy(record.minutes["results_snapshot"])
    old_marks=copy.deepcopy(record.marks)
    academic={"class_name":"ĐHCNTT22B","major_code":major_code,"birth_date":"2004-03-15",
        "training_cohort":"2022–2026","source_reference":"DS-TEST-2026","reason":"Correct class from verified student record"}
    cached_report = f"/api/v1/nv6-reports/{thesis['round_id']}"
    before_correction = client.get(cached_report,headers=hdr(users[4])).json()
    assert next(row for row in before_correction["rows"] if row["id"]==first)["class_name"] != "ĐHCNTT22B"
    mutate("PUT","/academic-profile/"+first,users[5],academic,403)
    mutate("PUT","/academic-profile/"+first,users[4],{**academic,"major_code":"UNRELATED"},422)
    mutate("PUT","/academic-profile/"+first,users[4],{**academic,"birth_date":"2099-01-01"},422)
    mutate("PUT","/academic-profile/"+first,users[4],{**academic,"scores":[0]*12},422)
    mutate("PUT","/academic-profile/"+first,users[4],academic)
    updated_report = client.get(cached_report,headers=hdr(users[4])).json()
    assert next(row for row in updated_report["rows"] if row["id"]==first)["class_name"] == "ĐHCNTT22B"
    session.refresh(record)
    assert record.minutes["results_snapshot"]==snapshot and record.marks==old_marks
    corrected=client.get(register+"/forms/10",headers=hdr(users[4]))
    assert "ĐHCNTT22B" in "\n".join(c.text for r in Document(BytesIO(corrected.content)).tables[1].rows for c in r.cells)
    assert client.get(endpoint+"/forms/9?font_size=5",headers=hdr(users[5])).status_code==422
    assert client.get(base+"/prints/"+print_record["id"],headers=hdr(users[4])).content==form10.content
    assert client.get(base+"/prints/"+minutes_record["id"],headers=hdr(users[5])).content==issued_minutes.content
    sheet_preview=client.get(register+"/forms/11?preview_sheet=true&course_code=IN4299N",headers=hdr(users[4]))
    assert sheet_preview.status_code==200 and sheet_preview.json()["sheets"]
    member_view=client.get(base,headers=hdr(extras[1][0])).json()["slots"][0]
    assert all("birth_date" not in r for r in member_view["roster"])
    original=slot
    decision.update(outcome="SUPPLEMENTARY",revision=1)
    assert client.post(decision_path,headers=hdr(users[4]),json=decision).status_code==204
    assert client.post(decision_path,headers=hdr(users[4]),json=decision).status_code==409
    edited.update(name="Synthetic supplementary council")
    fresh_council=client.post(base+"/councils",headers=hdr(users[4]),json=edited)
    assert fresh_council.status_code==201,fresh_council.text
    extra_body={**body,"council_id":fresh_council.json()["id"],"prior_slot_id":original,"thesis_member_ids":[first],
        "starts_at":(now()-timedelta(minutes=30)).isoformat(),"ends_at":(now()-timedelta(minutes=5)).isoformat()}
    assert client.post(base+"/slots",headers=hdr(users[4]),json=extra_body).status_code==409
    extra_body["thesis_member_ids"]=[second]
    supplementary=client.post(base+"/slots",headers=hdr(users[4]),json=extra_body)
    assert supplementary.status_code==201,supplementary.text
    slot=supplementary.json()["id"];endpoint=base+"/slots/"+slot
    found=next(s for s in client.get(base,headers=hdr(users[5])).json()["slots"] if s["id"]==slot)
    assert [r["id"] for r in found["roster"]]==[second]
    assert client.post(decision_path,headers=hdr(users[4]),json={**decision,"revision":2}).status_code==409
    mutate("PUT","/council-attendance",users[5],{"present_ids":present,"reason":"Four members present for supplementary defense"})
    mutate("PUT","/attendance/"+second,users[5],{"status":"PRESENT"})
    mutate("PUT","/minutes",users[5],{**meeting,"discussion":"Supplementary defense discussion","conclusion":"Student assessed separately",
        "recommendations":"","no_recommendations":True,"classifications":{second:"Xuất sắc"},"oral_comments":{}})
    for user,person in [(users[4],lecturers[1]),(users[5],lecturers[2]),extras[0]]:
        mutate("PUT","/marks",user,{"thesis_member_id":second,"lecturer_id":str(person.id),"scores":scores})
    mutate("PUT","/marks",users[5],{"thesis_member_id":second,"lecturer_id":str(extra.id),"scores":scores,"paper_entry_reason":"Entered from paper ballot"})
    mutate("POST","/finalize",users[5],{})
    slots_after=client.get(base,headers=hdr(users[4])).json()["slots"]
    old=next(s for s in slots_after if s["id"]==original)
    new=next(s for s in slots_after if s["id"]==slot)
    assert old["results"][first]["average"]=="10.0" and old["results"][second]["average"] is None
    assert new["results"][second]["average"]=="10.0" and first not in new["results"]
    assert client.post(base+"/councils/"+fresh_council.json()["id"]+"/close",headers=hdr(users[4])).status_code==204
    final_form=issue(register+"/forms/11?course_code=ALT_11",users[4])
    assert final_form.status_code==200,final_form.text
    workbook=load_workbook(BytesIO(final_form.content)).active
    assert workbook["B5"].value=="Học phần: [ALT_11] - Khóa luận tốt nghiệp"
    assert workbook["A7"].value=="[ASCIMP]"
    populated=[(workbook.cell(index,2).value,workbook.cell(index,6).value) for index in range(11,18) if workbook.cell(index,2).value]
    assert sorted(populated)==sorted([(students[0].student_code,10),(students[1].student_code,10)])
    report_path="/api/v1/nv6-reports/"+thesis["round_id"]
    report=client.get(report_path,headers=hdr(users[4]))
    assert report.status_code==200,report.text
    assert report.json()["results"]["GRADED"]==2 and report.json()["councils"]==2
    assert sum(report.json()["results"].values())==report.json()["students"]
    assert report.json()["archives"]=={"NOT_SUBMITTED":1}
    assert client.get(report_path,headers=hdr(users[0])).status_code==404

    from backend.services import file_scanner
    monkeypatch.setattr(file_scanner,"require_available",lambda: None)

    def scan_demo(file,path):
        file.scan_state="CLEAN"
        return "CLEAN"

    monkeypatch.setattr(file_scanner,"scan",scan_demo)
    archive="/api/v1/thesis-archive"
    upload_headers={**hdr(users[0]),"X-File-Name":"synthetic-final.pdf","Content-Type":"application/octet-stream"}
    assert client.get(archive,headers=hdr(users[0])).json()[0]["can_submit"]
    submission_path=archive+"/theses/"+thesis["thesis_id"]
    thesis_path = "/api/v1/theses/" + thesis["thesis_id"]
    assert "archive:view" in client.get(thesis_path, headers=hdr(users[0])).json()["actions"]
    work_url = "/repository?mode=work&focus="+thesis["thesis_id"]
    def archive_notices():
        # The fixture keeps every savepoint in one outer transaction. DB timestamps can tie.
        return client.get("/api/v1/notifications", headers=hdr(users[0]), params={"limit":100}).json()["items"]
    assert any("Nhóm có thể nộp bản hoàn thiện" in n["message"] and n["url"]==work_url for n in archive_notices())
    work = client.get(archive+"/search", headers=hdr(users[0]), params={"mode":"work","state":"EMPTY"}).json()
    assert {s["code"] for s in work["items"][0]["snapshot"]["students"]} == {s.student_code for s in students[:2]}
    from test_participation_revocation import verifier
    verifier(session, users[4], UUID(thesis["round_id"]))
    roster_path = f"/api/v1/rounds/{thesis['round_id']}/roster"
    payload = {"student_id": str(students[0].id), "reason": "Kiểm thử thu hồi trong đợt", "basis_ref": "E2E-123"}
    assert client.post(roster_path+"/revoke", headers=hdr(users[4]), json=payload).status_code == 200
    blocked = client.get(submission_path, headers=hdr(users[0])).json()
    assert blocked["submission_suspended"] and not blocked["can_submit"]
    assert client.get(submission_path, headers=hdr(users[1])).json()["can_submit"]
    assert client.post(submission_path, headers=upload_headers, content=synthetic_pdf()).status_code == 403
    assert client.post(roster_path+"/restore", headers=hdr(users[4]), json=payload).status_code == 200
    assert client.get(submission_path, headers=hdr(users[0])).json()["can_submit"]
    sent=client.post(submission_path,headers=upload_headers,content=synthetic_pdf())
    assert sent.status_code==201,sent.text
    assert client.post(submission_path,headers=upload_headers,content=synthetic_pdf()).status_code==409
    first_archive=archive+"/versions/"+sent.json()["id"]
    assert client.get(first_archive+"/file",headers=hdr(users[2])).status_code==404
    original_student = next(row for row in sent.json()["snapshot"]["students"] if row["slot_id"]==slot)
    mutate("PUT","/academic-profile/"+second,users[4],{**academic,"class_name":"ĐHCNTT22D"})
    stale = client.get(submission_path,headers=hdr(users[4])).json()
    assert stale["can_decide"] and not stale["can_approve"]
    assert any(original_student["code"] in block["message"] and "lớp" in block["message"]
               and block["url"]==f"/defense?slot={slot}&tab=results" for block in stale["blockers"])
    assert client.post(first_archive+"/decision", headers={**hdr(users[4]),"If-Match":"1"},
                       json={"decision":"ACCEPTED","reason":"Thử duyệt sau đính chính"}).status_code==409
    returned=client.post(first_archive+"/decision",headers={**hdr(users[4]),"If-Match":"1"},json={"decision":"RETURNED","reason":"Bổ sung kết luận theo biên bản"})
    assert returned.status_code==204,returned.text
    assert client.post(submission_path,headers={**upload_headers,"If-Match":"0"},content=synthetic_pdf()).status_code==409
    resubmitted=client.post(submission_path,headers=upload_headers,content=synthetic_pdf())
    assert resubmitted.status_code==201,resubmitted.text
    assert client.post(first_archive+"/decision",headers={**hdr(users[4]),"If-Match":"2"},
                       json={"decision":"ACCEPTED","reason":"Thử duyệt bản cũ"}).status_code==409
    assert not client.get(submission_path,headers=hdr(users[0])).json()["can_approve"]
    latest_archive=archive+"/versions/"+resubmitted.json()["id"]
    accepted=client.post(latest_archive+"/decision",headers={**hdr(users[4]),"If-Match":"1"},json={"decision":"ACCEPTED","reason":"Đã đối chiếu bản hoàn thiện"})
    assert accepted.status_code==204,accepted.text
    assert client.get(thesis_path, headers=hdr(users[0])).json()["state"] == "COMPLETED"
    assert client.get(report_path,headers=hdr(users[4])).json()["archives"]=={"ACCEPTED":1}
    assert client.get(report_path,headers=hdr(users[4]),params={"refresh": True}).json()["archives"]=={"ACCEPTED":1}
    assert any("Đã đưa khóa luận vào kho nội bộ" in n["message"] and n["url"]=="/repository?focus="+thesis["thesis_id"]
               for n in archive_notices())
    assert client.get(latest_archive+"/file",headers=hdr(users[1])).status_code==200
    assert client.get(submission_path,headers=hdr(users[2])).status_code==404
    catalog=client.get(archive+"/search",headers=hdr(users[0]),params={"q":students[0].student_code})
    assert catalog.status_code==200,catalog.text
    assert catalog.json()["total"]==1 and catalog.json()["items"][0]["state"]=="ACCEPTED"
    frozen = catalog.json()["items"][0]["snapshot"]
    assert frozen["topic_code"] and frozen["department_code"]
    assert {s["student_id"] for s in frozen["students"]} == {str(s.id) for s in students[:2]}
    thesis_row = session.get(m.Thesis, UUID(thesis["thesis_id"]))
    old_title = thesis_row.current_title
    thesis_row.current_title = "Tiêu đề thay đổi sau khi duyệt"
    session.commit()
    assert client.get(archive+"/search",headers=hdr(users[4]),params={"q":"tieu de thay doi"}).json()["total"]==0
    thesis_row.current_title = old_title
    session.commit()
    assert client.get(archive+"/search",headers=hdr(users[2])).json()["total"]==0
    reopen_data={"reason":"Phát hiện lưu nhầm tài liệu, yêu cầu bản thay thế"}
    assert client.post(latest_archive+"/reopen",headers={**hdr(users[0]),"If-Match":"2"},json=reopen_data).status_code==404
    assert client.post(latest_archive+"/reopen",headers={**hdr(users[4]),"If-Match":"1"},json=reopen_data).status_code==409
    assert client.post(latest_archive+"/reopen",headers={**hdr(users[4]),"If-Match":"2"},json=reopen_data).status_code==204
    assert client.get(thesis_path, headers=hdr(users[0])).json()["state"] == "DEFENDED"
    assert client.get(archive+"/search",headers=hdr(users[0])).json()["total"]==0
    detail=client.get(submission_path,headers=hdr(users[0])).json()
    def saved_class(version):
        return next(row["class_name"] for row in version["snapshot"]["students"]
                    if row["student_id"]==original_student["student_id"])
    assert [saved_class(version) for version in detail["versions"]] == ["ĐHCNTT22D",original_student["class_name"]]
    assert detail["can_submit"] and detail["versions"][0]["state"]=="REOPENED"
    assert detail["versions"][0]["decision_note"]=="Đã đối chiếu bản hoàn thiện"
    assert detail["versions"][0]["reopened"]["reason"]==reopen_data["reason"]
    assert client.get(report_path,headers=hdr(users[4]),params={"refresh": True}).json()["archives"]=={"REOPENED":1}
    assert client.get(latest_archive+"/file",headers=hdr(users[1])).content==synthetic_pdf()
    assert client.get(archive,headers=hdr(users[2])).json()==[]
    assert any("đã thu hồi bản lưu" in n["message"] and n["url"]==work_url for n in archive_notices())

    # Closed records need an independently approved correction; never unlock.
    correction_path=endpoint+'/corrections'
    closed_slot=next(s for s in client.get(base,headers=hdr(users[4])).json()['slots'] if s['id']==slot)
    assert client.get(correction_path,headers=hdr(users[1])).status_code==403
    proposal={'kind':'BALLOT','student_id':second,'lecturer_id':str(lecturers[1].id),
        'scores':['0']*12,'note':'Đính chính theo phiếu gốc đã đối chiếu',
        'reason':'Nhập nhầm các điểm tiêu chí trên phiếu','reference':'QD-DINH-CHINH-2026'}
    request_headers={**hdr(users[5]),'If-Match':str(closed_slot['version'])}
    assert client.post(correction_path,headers=request_headers,json=proposal).status_code==204
    pending=client.get(correction_path,headers=hdr(users[4])).json()['items'][0]
    assert client.post(correction_path,headers=request_headers,json=proposal).status_code==409
    waiting_again = client.get(submission_path, headers=hdr(users[0])).json()
    assert not waiting_again["can_submit"]
    assert any("đính chính" in row["message"] for row in waiting_again["blockers"])
    assert client.post(submission_path,headers=upload_headers,content=synthetic_pdf()).status_code==409
    assert issue(register+'/forms/11?course_code=ALT_11',users[4]).status_code==409
    decision_url=base+'/corrections/'+pending['id']+'/decision'
    approve={'decision':'APPROVED','reason':'Đã đối chiếu phiếu và quyết định của Khoa'}
    assert client.post(decision_url,headers={**hdr(users[5]),'If-Match':'1'},json=approve).status_code==403
    approved=client.post(decision_url,headers={**hdr(users[4]),'If-Match':'1'},json=approve)
    assert approved.status_code==204,approved.text
    assert client.post(decision_url,headers={**hdr(users[4]),'If-Match':'1'},json=approve).status_code==409
    revised=next(s for s in client.get(base,headers=hdr(users[4])).json()['slots'] if s['id']==slot)
    assert revised['finalized_at'] and revised['council']['closed_at'] and revised['results'][second]['average']!='10.0'
    assert client.get(base+'/prints/'+minutes_record['id'],headers=hdr(users[5])).content==issued_minutes.content
    assert any(not item['current'] for item in client.get(register+'/prints',headers=hdr(users[4])).json())
    fresh=client.get(register+'/forms/11?course_code=ALT_11&preview_revision=true',headers=hdr(users[4])).json()['revision']
    assert client.post(register+'/forms/11?course_code=ALT_11',headers=hdr(users[4])).status_code==409
    assert client.post(register+'/forms/11?course_code=ALT_11&font_size=14&expected_revision='+fresh,headers=hdr(users[4])).status_code==409
    # Fill missing historical minutes without changing the already locked score.
    session.expire_all()
    row=session.get(m.DefenseSlot,UUID(slot)); old_minutes=dict(row.minutes)
    row.minutes={**row.minutes,'classifications':{}};row.row_version+=1;session.commit()
    version=row.row_version
    restored={k:v for k,v in old_minutes.items() if k in {'discussion','conclusion','objectives','functions','achievements','recommendations','no_recommendations','classifications','oral_comments'}}
    missing=client.get(correction_path,headers=hdr(users[5])).json()
    assert any('xếp loại' in s for s in missing['missing'])
    requested=client.post(correction_path,headers={**hdr(users[5]),'If-Match':str(version)},json={
        'kind':'MINUTES','minutes':restored,'reason':'Bổ sung xếp loại theo biên bản gốc','reference':'BB-HOI-DONG-2026'})
    assert requested.status_code==204,requested.text
    row_id=client.get(correction_path,headers=hdr(users[4])).json()['items'][0]['id']
    result=client.post(base+'/corrections/'+row_id+'/decision',headers={**hdr(users[4]),'If-Match':'1'},json=approve)
    assert result.status_code==204,result.text
    final=next(s for s in client.get(base,headers=hdr(users[4])).json()['slots'] if s['id']==slot)
    assert final['results'][second]['average']==revised['results'][second]['average']
    assert not client.get(correction_path,headers=hdr(users[4])).json()['missing']
    stale=client.post(correction_path,headers={**hdr(users[5]),'If-Match':str(final['version'])},json={
        'kind':'MINUTES','minutes':restored,'reason':'Đề nghị kiểm tra lại nội dung đã ghi','reference':'BB-DOI-CHIEU-2026'})
    assert stale.status_code==204,stale.text
    pending_id=client.get(correction_path,headers=hdr(users[4])).json()['items'][0]['id']
    session.expire_all();record=session.get(m.DefenseSlot,UUID(slot));record.row_version+=1;session.commit()
    path_decision=base+'/corrections/'+pending_id+'/decision'
    stale_approval=client.post(path_decision,headers={**hdr(users[4]),'If-Match':'1'},json=approve)
    assert stale_approval.status_code==409 and 'Nguồn đã đổi' in stale_approval.json()['detail']
    assert client.post(path_decision,headers={**hdr(users[4]),'If-Match':'1'},json={**approve,'decision':'REJECTED'}).status_code==204



def test_only_ready_or_officially_extended_thesis_can_be_scheduled():
    assert thesis_state_allows_schedule(SimpleNamespace(state="READY_FOR_DEFENSE"), None)
    assert thesis_state_allows_schedule(SimpleNamespace(state="EXTENDED"), object())
    assert not thesis_state_allows_schedule(SimpleNamespace(state="EXTENDED"), None)
    assert not thesis_state_allows_schedule(SimpleNamespace(state="IN_PROGRESS"), object())


def test_extended_thesis_can_defend_in_any_faculty_session_within_window():
    vn=ZoneInfo("Asia/Ho_Chi_Minh")
    extension=SimpleNamespace(until_at=datetime(2027,9,30,23,59,59,tzinfo=vn))
    request=SimpleNamespace(extension_starts_at=datetime(2027,5,1,0,0,tzinfo=vn))
    validate_extension_window(extension,request,datetime(2027,9,12,9,0,tzinfo=vn),datetime(2027,9,12,11,0,tzinfo=vn))
    validate_extension_window(extension,request,datetime(2027,8,30,9,0,tzinfo=vn),datetime(2027,8,30,11,0,tzinfo=vn))
    with pytest.raises(HTTPException) as err:
        validate_extension_window(extension,request,datetime(2027,4,30,9,0,tzinfo=vn),datetime(2027,4,30,11,0,tzinfo=vn))
    assert "chưa nằm trong" in err.value.detail
    with pytest.raises(HTTPException) as err:
        validate_extension_window(extension,request,datetime(2027,9,30,22,0,tzinfo=vn),datetime(2027,10,1,0,30,tzinfo=vn))
    assert "vượt hạn gia hạn" in err.value.detail


def test_each_ballot_rounds_before_final_average():
    from decimal import Decimal
    from types import SimpleNamespace
    from backend.services.defense import total,results
    assert total({"scores":["3.85"]},{"bonus":"0"})==Decimal("3.9")
    assert total({"scores":["7.24"]},{"bonus":"0"})==Decimal("7.2")
    assert total({"scores":["7.25"]},{"bonus":"0"})==Decimal("7.3")
    assert total({"scores":["9.8"]},{"bonus":"1"})==Decimal("10.0")
    slot=SimpleNamespace(finalized_at=None,minutes={},roster=[{"id":"sv"}],
        attendance={"sv":{"status":"PRESENT"},"_council":{"present_ids":["a","b","c"]}},
        marks={"sv":{"a":{"scores":["7.24"]},"b":{"scores":["7.25"]},"c":{"scores":["7.25"]}}})
    council=SimpleNamespace(members=[{"id":x} for x in ["a","b","c","d","e"]])
    assert results(slot,council)["sv"]["average"]=="7.3"
    slot.finalized_at=True
    assert results(slot,council)["sv"]["average"]=="7.25"


def test_correcting_one_student_preserves_other_historical_precision():
    from backend.services.defense_corrections import recalculated_results
    frozen={'a':{'average':'7.25','scores':['7.24','7.25','7.25']},'b':{'average':'8.0'}}
    slot=SimpleNamespace(finalized_at=True,minutes={'results_snapshot':frozen},roster=[{'id':'a'},{'id':'b'}],
        attendance={'a':{'status':'PRESENT'},'b':{'status':'PRESENT'},'_council':{'present_ids':['x','y','z']}},
        marks={s:{p:{'scores':['0']} for p in ['x','y','z']} for s in ['a','b']})
    council=SimpleNamespace(members=[{'id':p} for p in ['x','y','z']])
    changed=recalculated_results(slot,council,'b')
    assert changed['a']==frozen['a'] and changed['a']['average']=='7.25'
    assert changed['b']['average']=='0.0' and slot.finalized_at is True
    assert frozen['b']['average']=='8.0'
