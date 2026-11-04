"""Integration coverage for the frozen defense exports and student access."""
from datetime import timedelta
from io import BytesIO
from uuid import uuid4

from docx import Document
from openpyxl import load_workbook

from backend.db.models import entities as m
from backend.services.theses import now
from test_core_workspace import workspace
from test_nv6_evaluation import check, complete_review, evaluation, get
from test_registration import hdr, scenario


def test_council_charts_marks_and_exports_use_one_frozen_record(evaluation):
    ctx,_ = evaluation
    client,users,students,lecturers,session,path = ctx
    thesis = get(ctx)
    account = m.UserAccount(id=uuid4(),external_subject="defense-"+uuid4().hex,base_role="LECTURER",status="ACTIVE")
    extra = m.LecturerProfile(id=uuid4(),user_id=account.id,department_id=lecturers[1].department_id,
        lecturer_code="D-"+uuid4().hex[:10],display_name="Synthetic council reviewer")
    session.add(account)
    session.flush()
    session.add(extra)
    session.commit()
    base = "/api/v1/defense"
    created = client.post(base+"/councils",headers=hdr(users[4]),json={"round_id":thesis["round_id"],
        "department_id":str(lecturers[1].department_id),"name":"Synthetic council","reference":"QD-DEFENSE-TEST",
        "members":[{"lecturer_id":str(person.id),"role":role} for person,role in
            [(lecturers[1],"CHAIR"),(lecturers[2],"SECRETARY"),(extra,"REVIEWER")]]})
    assert created.status_code==201,created.text
    council = created.json()["id"]
    body = {"council_id":council,"thesis_id":thesis["thesis_id"],"room":"Synthetic room",
        "starts_at":(now()-timedelta(hours=2)).isoformat(),"ends_at":(now()-timedelta(hours=1)).isoformat()}
    assert client.post(base+"/slots",headers=hdr(users[4]),json=body).status_code == 409
    for index in range(len(thesis["members"])):
        complete_review(ctx,member=index)
        response = check(ctx,member=index)
        assert response.status_code == 200,response.text
    response = client.post(base+"/slots",headers=hdr(users[4]),json=body)
    assert response.status_code==201,response.text
    slot = response.json()["id"]
    assert client.post(base+"/slots",headers=hdr(users[4]),json=body).status_code==409
    assert client.get(base,headers=hdr(users[2])).json()["slots"]==[]
    student_slots = client.get(base,headers=hdr(users[0])).json()["slots"]
    assert student_slots[0]["results"]=={} and len(student_slots[0]["roster"])==1
    first = student_slots[0]["roster"][0]["id"]
    second = client.get(base,headers=hdr(users[1])).json()["slots"][0]["roster"][0]["id"]
    endpoint = base+"/slots/"+slot

    def mutate(method,suffix,user,data,status=204):
        current = client.get(base,headers=hdr(users[4])).json()["slots"][0]["version"]
        res = client.request(method,endpoint+suffix,headers={**hdr(user),"If-Match":str(current)},json=data)
        assert res.status_code==status,res.text

    mutate("PUT","/attendance/"+first,users[5],{"status":"PRESENT"})
    mutate("PUT","/attendance/"+second,users[5],{"status":"ABSENT","reason":"Có báo vắng"})
    mutate("PUT","/bonus/"+first,users[4],{"points":"1","reference":"Synthetic research publication"})
    mutate("PUT","/minutes",users[5],{"discussion":"Synthetic discussion","conclusion":"Synthetic conclusion"})
    mutate("POST","/finalize",users[4],{},409)
    scores = ["1",".5",".5",".5",".5","1","1",".5",".5","1","2","1"]
    for account,person in [(users[4],lecturers[1]),(users[5],lecturers[2]),(account,extra)]:
        mutate("PUT","/marks",account,{"thesis_member_id":first,"lecturer_id":str(person.id),"scores":scores})
    mutate("POST","/finalize",users[4],{})
    mutate("PUT","/bonus/"+first,users[4],{"points":"0"},409)
    result = client.get(base,headers=hdr(users[0])).json()["slots"][0]["results"]
    assert result[first]["average"]=="10.00"
    absent = client.get(base,headers=hdr(users[1])).json()["slots"][0]["results"]
    assert absent[second]["average"] is None
    assert client.get(endpoint+"/forms/9",headers=hdr(users[0])).status_code==403
    minutes = client.get(endpoint+"/forms/9",headers=hdr(users[5]))
    assert minutes.status_code==200,minutes.text
    doc = Document(BytesIO(minutes.content))
    assert "Synthetic conclusion" in "\n".join(p.text for p in doc.paragraphs)
    form6 = client.get(endpoint+"/forms/6",headers=hdr(users[4]),params={
        "student_id":first,"lecturer_id":str(lecturers[1].id)})
    assert form6.status_code==200,form6.text
    sheet = load_workbook(BytesIO(form6.content)).active
    assert any(row[1]=="Tổng điểm" and row[3]==10 for row in sheet.values)
    assert client.get(base+"/councils/"+council+"/forms/11",headers=hdr(users[4])).status_code==409
    assert client.post(base+"/councils/"+council+"/close",headers=hdr(users[4])).status_code==204
    form10 = client.get(base+"/councils/"+council+"/forms/10",headers=hdr(users[4]))
    assert form10.status_code==200,form10.text
    assert any(row.cells[-1].text=="10.00" for row in Document(BytesIO(form10.content)).tables[1].rows)
    official = client.get(base+"/councils/"+council+"/forms/11",headers=hdr(users[4]))
    assert official.status_code==200,official.text
    rows = list(load_workbook(BytesIO(official.content),read_only=True).active.values)
    assert any(r[1]==students[0].student_code and r[5]==10 for r in rows)
    assert any(r[1]==students[1].student_code and r[5] is None and r[6]=="Vắng" for r in rows)
