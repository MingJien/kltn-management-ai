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

from backend.db.models import entities as m
from backend.services.theses import now
from backend.services.defense import thesis_state_allows_schedule, validate_extension_window
from test_core_workspace import workspace, synthetic_pdf, version_headers
from test_nv6_evaluation import check, complete_review, evaluation, get
from test_registration import hdr, scenario


def test_council_charts_marks_and_exports_use_one_frozen_record(evaluation):
    ctx,_ = evaluation
    client,users,students,lecturers,session,path = ctx
    thesis = get(ctx)
    proof=client.post(path+'/documents',headers=hdr(users[0]),json={'document_type':'SUPPORTING','title':'Synthetic research publication evidence'})
    assert proof.status_code==201,proof.text
    proof=proof.json()
    uploaded=client.post(path+'/documents/'+proof['id']+'/versions',headers={**version_headers(users[0],proof),
        'X-File-Name':'research-evidence.pdf','Content-Type':'application/octet-stream'},content=synthetic_pdf())
    assert uploaded.status_code==201,uploaded.text
    evidence_version=uploaded.json()['versions'][0]['id']
    evidence=session.get(m.DocumentVersion,UUID(evidence_version))
    session.get(m.StoredFile,evidence.stored_file_id).scan_state='CLEAN'
    session.commit()
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
    assert len(student_slots[0]["roster"])==1
    own_id=student_slots[0]["roster"][0]["id"]
    assert set(student_slots[0]["results"]) <= {own_id}
    assert all(row.get("average") is None and not row.get("scores") for row in student_slots[0]["results"].values())
    first = student_slots[0]["roster"][0]["id"]
    second = client.get(base,headers=hdr(users[1])).json()["slots"][0]["roster"][0]["id"]
    record=client.get(base,headers=hdr(users[4])).json()["councils"][0]
    edited={"round_id":record["round_id"],"department_id":record["department_id"],"name":"Synthetic council revised","reference":"QD-REVISED",
        "members":[{"lecturer_id":p["id"],"role":p["role"]} for p in record["members"]]}
    response=client.put(base+"/councils/"+council,headers={**hdr(users[4]),"If-Match":record["signature"]},json=edited)
    assert response.status_code==200,response.text
    assert client.put(base+"/councils/"+council,headers={**hdr(users[4]),"If-Match":record["signature"]},json=edited).status_code==409
    endpoint = base+"/slots/"+slot

    def mutate(method,suffix,user,data,status=204):
        current = next(s["version"] for s in client.get(base,headers=hdr(users[4])).json()["slots"] if s["id"]==slot)
        res = client.request(method,endpoint+suffix,headers={**hdr(user),"If-Match":str(current)},json=data)
        assert res.status_code==status,res.text

    mutate("POST","/finalize",users[4],{},409)
    mutate("PUT","/council-attendance",users[5],{
        "present_ids":[str(lecturers[1].id),str(extra.id),str(extras[0][1].id)],
        "reason":"Secretary missing from meeting"},422)
    present=[str(person.id) for person in [lecturers[1],lecturers[2],extra,extras[0][1]]]
    mutate("PUT","/council-attendance",users[5],{"present_ids":present,"reason":"Four members present, member absent"})
    updated=client.get(base,headers=hdr(users[4])).json()["councils"][0]
    assert client.put(base+"/councils/"+council,headers={**hdr(users[4]),"If-Match":updated["signature"]},json=edited).status_code==409
    mutate("PUT","/attendance/"+first,users[5],{"status":"PRESENT"})
    mutate("PUT","/attendance/"+second,users[5],{"status":"ABSENT","reason":"Có báo vắng"})
    mutate("PUT","/bonus/"+first,users[4],{"points":"1","reference":"Synthetic research publication"},422)
    mutate("PUT","/bonus/"+first,users[4],{"points":"1","reference":"Synthetic research publication","evidence_version_id":evidence_version})
    mutate("PUT","/minutes",users[5],{"discussion":"Synthetic discussion","conclusion":"Synthetic conclusion"})
    mutate("POST","/finalize",users[4],{},409)
    blank = client.get(endpoint+"/forms/6",headers=hdr(users[5]),params={"student_id":first,"lecturer_id":str(lecturers[1].id),"blank":True})
    assert blank.status_code==200,blank.text
    blank_rows=list(load_workbook(BytesIO(blank.content),read_only=True).active.values)
    assert any(r[0]=="1.1" and r[3] is None for r in blank_rows)
    assert client.get(endpoint+"/forms/6",headers=hdr(users[5])).status_code==409
    assert client.get(endpoint+"/report",headers=hdr(users[2])).status_code==404
    assert client.get(endpoint+"/report",headers=hdr(account)).status_code==200
    shared=client.get(base,headers=hdr(users[4])).json()["slots"][0]
    scores = ["1",".5",".5",".5",".5","1","1",".5",".5","1","2","1"]
    for account,person in [(users[4],lecturers[1]),(users[5],lecturers[2]),(account,extra),extras[0]]:
        res=client.put(endpoint+"/marks",headers={**hdr(account),"If-Match":str(shared["version"])},json={
            "thesis_member_id":first,"lecturer_id":str(person.id),"scores":scores,"ballot_revision":0,"context_token":shared["context_token"]})
        assert res.status_code==204,res.text
    stale=client.put(endpoint+"/marks",headers={**hdr(users[4]),"If-Match":str(shared["version"])},json={
        "thesis_member_id":first,"lecturer_id":str(lecturers[1].id),"scores":scores,"ballot_revision":0,"context_token":shared["context_token"]})
    assert stale.status_code==409
    mutate("POST","/marks/"+first+"/"+str(lecturers[1].id)+"/void",users[5],{"reason":"Wrong paper was entered"})
    mutate("PUT","/marks",users[4],{"thesis_member_id":first,"lecturer_id":str(lecturers[1].id),"scores":scores})
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
    original=slot
    decision_path=endpoint+"/absence/"+second
    decision={"outcome":"NOT_PASSED","reference":"QD-ABSENCE-01","reason":"Faculty confirmed absence after reviewing the case","revision":0}
    assert client.post(decision_path,headers=hdr(users[0]),json=decision).status_code==403
    assert client.post(decision_path,headers=hdr(users[4]),json=decision).status_code==204
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
    mutate("PUT","/minutes",users[5],{"discussion":"Supplementary defense discussion","conclusion":"Student assessed separately"})
    for user,person in [(users[4],lecturers[1]),(users[5],lecturers[2]),extras[0]]:
        mutate("PUT","/marks",user,{"thesis_member_id":second,"lecturer_id":str(person.id),"scores":scores})
    mutate("PUT","/marks",users[5],{"thesis_member_id":second,"lecturer_id":str(extra.id),"scores":scores,"paper_entry_reason":"Entered from paper ballot"})
    mutate("POST","/finalize",users[5],{})
    slots_after=client.get(base,headers=hdr(users[4])).json()["slots"]
    old=next(s for s in slots_after if s["id"]==original)
    new=next(s for s in slots_after if s["id"]==slot)
    assert old["results"][first]["average"]=="10.0" and old["results"][second]["average"] is None
    assert new["results"][second]["average"]=="10.0" and first not in new["results"]



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
