"""Integration coverage for the frozen defense exports and student access."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from io import BytesIO
from uuid import uuid4

from docx import Document
from openpyxl import load_workbook
import pytest
from fastapi import HTTPException

from backend.db.models import entities as m
from backend.services.theses import now
from backend.services.defense import thesis_state_allows_schedule, validate_extension_window
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
    extras=[]
    for index in range(2):
        account2=m.UserAccount(id=uuid4(),external_subject="council-"+uuid4().hex,base_role="LECTURER",status="ACTIVE")
        person=m.LecturerProfile(id=uuid4(),user_id=account2.id,department_id=lecturers[1].department_id,
            lecturer_code="C-"+uuid4().hex[:10],display_name=f"Synthetic council extra {index}")
        session.add(account2);session.flush();session.add(person);session.flush()
        extras.append((account2,person))
    session.commit()
    base = "/api/v1/defense"
    created = client.post(base+"/councils",headers=hdr(users[4]),json={"round_id":thesis["round_id"],
        "department_id":str(lecturers[1].department_id),"name":"Synthetic council","reference":"QD-DEFENSE-TEST",
        "members":[{"lecturer_id":str(person.id),"role":role} for person,role in
            [(lecturers[1],"CHAIR"),(lecturers[2],"SECRETARY"),(extra,"REVIEWER"),(extras[0][1],"REVIEWER"),(extras[1][1],"MEMBER")]]})
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

    mutate("POST","/finalize",users[4],{},409)
    mutate("PUT","/council-attendance",users[5],{
        "present_ids":[str(lecturers[1].id),str(extra.id),str(extras[0][1].id)],
        "reason":"Secretary missing from meeting"},422)
    present=[str(person.id) for person in [lecturers[1],lecturers[2],extra,extras[0][1]]]
    mutate("PUT","/council-attendance",users[5],{"present_ids":present,"reason":"Four members present, member absent"})
    mutate("PUT","/attendance/"+first,users[5],{"status":"PRESENT"})
    mutate("PUT","/attendance/"+second,users[5],{"status":"ABSENT","reason":"Có báo vắng"})
    mutate("PUT","/bonus/"+first,users[4],{"points":"1","reference":"Synthetic research publication"})
    mutate("PUT","/minutes",users[5],{"discussion":"Synthetic discussion","conclusion":"Synthetic conclusion"})
    mutate("POST","/finalize",users[4],{},409)
    scores = ["1",".5",".5",".5",".5","1","1",".5",".5","1","2","1"]
    for account,person in [(users[4],lecturers[1]),(users[5],lecturers[2]),(account,extra),extras[0]]:
        mutate("PUT","/marks",account,{"thesis_member_id":first,"lecturer_id":str(person.id),"scores":scores})
    mutate("PUT","/marks",extras[1][0],{"thesis_member_id":first,"lecturer_id":str(extras[1][1].id),
        "scores":scores},409)
    mutate("POST","/finalize",users[4],{})
    mutate("PUT","/bonus/"+first,users[4],{"points":"0"},409)
    mutate("POST","/reopen-unsigned",users[4],{"reason":"Correct unsigned meeting conclusion","confirm_unsigned":True})
    mutate("PUT","/minutes",users[5],{"discussion":"Synthetic discussion","conclusion":"Synthetic conclusion corrected"})
    mutate("POST","/finalize",users[4],{})
    result = client.get(base,headers=hdr(users[0])).json()["slots"][0]["results"]
    assert result[first]["average"]=="10.0"
    absent = client.get(base,headers=hdr(users[1])).json()["slots"][0]["results"]
    assert absent[second]["average"] is None
    assert client.get(endpoint+"/forms/9",headers=hdr(users[0])).status_code==403
    minutes = client.get(endpoint+"/forms/9",headers=hdr(users[5]))
    assert minutes.status_code==200,minutes.text
    doc = Document(BytesIO(minutes.content))
    assert "Synthetic conclusion corrected" in "\n".join(p.text for p in doc.paragraphs)
    form6 = client.get(endpoint+"/forms/6",headers=hdr(users[4]),params={
        "student_id":first,"lecturer_id":str(lecturers[1].id)})
    assert form6.status_code==200,form6.text
    sheet = load_workbook(BytesIO(form6.content)).active
    assert any(row[1]=="Tổng điểm" and row[3]==10 for row in sheet.values)
    assert client.get(base+"/councils/"+council+"/forms/11",headers=hdr(users[4])).status_code==409
    assert client.post(base+"/councils/"+council+"/close",headers=hdr(users[4])).status_code==204
    form10 = client.get(base+"/councils/"+council+"/forms/10",headers=hdr(users[4]))
    assert form10.status_code==200,form10.text
    assert any(row.cells[-1].text=="10.0" for row in Document(BytesIO(form10.content)).tables[1].rows)
    official = client.get(base+"/councils/"+council+"/forms/11",headers=hdr(users[4]))
    assert official.status_code==200,official.text
    rows = list(load_workbook(BytesIO(official.content),read_only=True).active.values)
    assert any(r[1]==students[0].student_code and r[5]==10 for r in rows)
    assert any(r[1]==students[1].student_code and r[5] is None and r[6]=="Vắng" for r in rows)


def test_only_ready_or_officially_extended_thesis_can_be_scheduled():
    assert thesis_state_allows_schedule(SimpleNamespace(state="READY_FOR_DEFENSE"), None)
    assert thesis_state_allows_schedule(SimpleNamespace(state="EXTENDED"), object())
    assert not thesis_state_allows_schedule(SimpleNamespace(state="EXTENDED"), None)
    assert not thesis_state_allows_schedule(SimpleNamespace(state="IN_PROGRESS"), object())


def test_extended_thesis_must_defend_in_last_extension_month():
    vn=ZoneInfo("Asia/Ho_Chi_Minh")
    extension=SimpleNamespace(until_at=datetime(2027,9,30,23,59,59,tzinfo=vn))
    request=SimpleNamespace(extension_starts_at=datetime(2027,5,1,0,0,tzinfo=vn))
    validate_extension_window(extension,request,datetime(2027,9,12,9,0,tzinfo=vn),datetime(2027,9,12,11,0,tzinfo=vn))
    with pytest.raises(HTTPException) as err:
        validate_extension_window(extension,request,datetime(2027,8,30,9,0,tzinfo=vn),datetime(2027,8,30,11,0,tzinfo=vn))
    assert "tháng 09/2027" in err.value.detail
    with pytest.raises(HTTPException) as err:
        validate_extension_window(extension,request,datetime(2027,9,30,22,0,tzinfo=vn),datetime(2027,10,1,0,30,tzinfo=vn))
    assert "vượt hạn gia hạn" in err.value.detail


def test_each_ballot_rounds_before_final_average():
    from decimal import Decimal
    from types import SimpleNamespace
    from backend.services.defense import total,results
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
