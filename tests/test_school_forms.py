"""PostgreSQL integration for round-scoped, versioned institutional files."""
from datetime import timedelta
from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import select
from openpyxl import Workbook

from backend.db.models import entities as m
from backend.services.theses import now
from test_registration import hdr,scenario
from test_core_workspace import workspace,synthetic_pdf,version_headers


@pytest.fixture
def forms(workspace):
    client,users,students,lecturers,session,thesis_path=workspace
    thesis=session.get(m.Thesis,thesis_path.split("/")[-1])
    session.add(m.ResourceAssignment(id=uuid4(),assignment_type="FORM_MANAGER",user_id=users[4].id,
        round_id=thesis.round_id,effective_from=now()-timedelta(minutes=1),state="ACTIVE"));session.commit()
    return client,users,students,lecturers,session,thesis.round_id


def create(forms,**overrides):
    client,users,_,_,_,round_id=forms
    response=client.post("/api/v1/school-forms",headers=hdr(users[4]),json={"round_id":str(round_id),
        "code":"mau-02","title":"Kế hoạch thực hiện","document_kind":"FORM","audience":"STUDENT_AND_LECTURER","reason":"Synthetic official source",**overrides})
    assert response.status_code==201,response.text
    return response.json()


def upload(forms,item,name="template.pdf",content=None,clean=True):
    client,users,_,_,session,_=forms
    response=client.post(f"/api/v1/school-forms/{item['id']}/versions",data={"source_reference":"SYNTHETIC official source","reason":"Khoa cập nhật nội dung mẫu"},
        headers=version_headers(users[4],item),files={"file":(name,content or synthetic_pdf(),"application/octet-stream")})
    assert response.status_code==201,response.text
    result=response.json()
    version=session.get(m.OfficialFormVersion,result["versions"][0]["id"])
    if clean:session.get(m.StoredFile,version.stored_file_id).scan_state="CLEAN";session.commit()
    return result


def publish(forms,item,expected=None):
    client,users,_,_,_,_=forms;version=item["versions"][0]
    return client.post(f"/api/v1/school-forms/{item['id']}/versions/{version['id']}/publish",
        headers={**hdr(users[4]),"If-Match":str(expected or version["row_version"])},json={"reason":"Khoa phát hành phiên bản đúng"})


def test_explicit_form_assignment_not_implied_by_admin_coordinator_or_head(forms):
    client,users,_,_,session,round_id=forms
    payload=dict(round_id=str(round_id),code="sample",title="Tài liệu Khoa",document_kind="FORM",audience="LECTURER",reason="Synthetic official source")
    assert client.post("/api/v1/school-forms",headers=hdr(users[3]),json=payload).status_code==403
    assert client.post("/api/v1/school-forms",headers=hdr(users[0]),json=payload).status_code==403
    # Technical ADMIN does not implicitly publish academic forms.
    users[5].base_role="ADMIN";session.commit()
    assert client.post("/api/v1/school-forms",headers=hdr(users[5]),json=payload).status_code==403
    assert client.post("/api/v1/school-forms",headers=hdr(users[4]),json=payload).status_code==201


def test_draft_not_visible_publish_versions_legacy_download_and_withdraw(forms):
    client,users,_,_,_,round_id=forms
    item=upload(forms,create(forms));base=f"/api/v1/school-forms/{item['id']}";v1=item["versions"][0]
    assert client.get("/api/v1/school-forms",params={"round_id":str(round_id)},headers=hdr(users[0])).json()==[]
    assert client.get(base+f"/versions/{v1['id']}/download",headers=hdr(users[0])).status_code==404
    first=publish(forms,item);assert first.status_code==200,first.text;item=first.json()
    assert client.get(base+f"/versions/{v1['id']}/download",headers=hdr(users[0])).content==synthetic_pdf()
    assert client.get("/api/v1/form-templates/plan",params={"round_id":str(round_id)},headers=hdr(users[0])).content==synthetic_pdf()
    item=upload(forms,item,name="updated.pdf",content=synthetic_pdf()+b"\n% revision 2")
    assert publish(forms,item,expected=99).status_code==409
    second=publish(forms,item);assert second.status_code==200,second.text;item=second.json()
    assert [row["state"] for row in item["versions"]]==["PUBLISHED","SUPERSEDED"]
    assert client.get(base+f"/versions/{v1['id']}/download",headers=hdr(users[0])).content==synthetic_pdf()
    v2=item["versions"][0]
    withdrawn=client.post(base+f"/versions/{v2['id']}/withdraw",headers=version_headers(users[4],v2),json={"reason":"Khoa thu hồi bản sai"})
    assert withdrawn.status_code==200,withdrawn.text
    assert client.get("/api/v1/form-templates/plan",params={"round_id":str(round_id)},headers=hdr(users[0])).status_code==409
    assert client.get(base+f"/versions/{v2['id']}/download",headers=hdr(users[0])).status_code==404


def test_unscanned_files_cannot_be_published(forms):
    client,users,_,_,_,_=forms
    item=upload(forms,create(forms),clean=False)
    assert publish(forms,item).status_code==409
    version=item["versions"][0]
    assert client.get(f"/api/v1/school-forms/{item['id']}/versions/{version['id']}/download",headers=hdr(users[4])).status_code==409


def test_student_cannot_download_lecturer_forms_even_direct_link(forms):
    client,users,_,_,_,_=forms
    item=upload(forms,create(forms,code="mau-06",audience="LECTURER"))
    published=publish(forms,item);assert published.status_code==200
    item=published.json()
    path=f"/api/v1/school-forms/{item['id']}/versions/{item['versions'][0]['id']}/download"
    assert client.get(path,headers=hdr(users[0])).status_code==404
    assert client.get(path,headers=hdr(users[3])).status_code==200
    bad=client.patch(f"/api/v1/school-forms/{item['id']}",headers=version_headers(users[4],item),
        json={"title":"Mẫu đánh giá","audience":"STUDENT_AND_LECTURER","state":"ACTIVE","reason":"Cannot expose this protected form"})
    assert bad.status_code==422


def test_filled_list_is_round_scoped_and_excel_is_previewed_without_import(forms):
    client,users,students,_,session,round_id=forms
    workbook=Workbook();sheet=workbook.active;sheet.title="Danh sách";sheet.append(["MSSV","Họ tên"]);sheet.append(["000123","Sinh viên giả lập"])
    blob=BytesIO();workbook.save(blob)
    item=upload(forms,create(forms,code="ds-sv-chot",title="Mẫu 4 đã chốt",document_kind="PUBLICATION"),name="danh-sach.xlsx",content=blob.getvalue())
    assert publish(forms,item).status_code==200
    path=f"/api/v1/school-forms/{item['id']}/versions/{item['versions'][0]['id']}"
    preview=client.get(path+"/spreadsheet",headers=hdr(users[0]));assert preview.status_code==200,preview.text
    assert preview.json()["sheets"][0]["rows"][1][0]=="000123"
    # Revoke a non-member's eligibility: a PUBLICATION must no longer be visible.
    eligibility=session.scalar(select(m.EligibilitySnapshot).where(m.EligibilitySnapshot.round_id==round_id,m.EligibilitySnapshot.student_id==students[2].id))
    session.add(m.EligibilitySnapshot(id=uuid4(),student_id=students[2].id,round_id=round_id,version=eligibility.version+1,evidence_ref="SYNTHETIC revocation",captured_at=now(),confirmed_by=users[4].id,confirmed_at=now(),state="REJECTED"));session.commit()
    assert client.get(path+"/download",headers=hdr(users[2])).status_code==404
    assert client.get(path+"/spreadsheet",headers=hdr(users[2])).status_code==404


def test_form_manager_can_trace_shared_catalog_audit_but_not_other_rounds(forms):
    from backend.services.theses import audit
    client,users,_,_,session,_=forms
    item=create(forms)
    # Another staff member may have performed a past action on the same catalog.
    audit(session,users[3],"OFFICIAL_FORM_METADATA_UPDATED","official_form",item["id"],"Khoa ghi nhận điều chỉnh biểu mẫu")
    session.commit()
    response=client.get("/api/v1/activity",headers=hdr(users[4]),params={"resource_type":"official_form","resource_id":item["id"]})
    assert response.status_code==200,response.text
    assert any(row["action"]=="OFFICIAL_FORM_METADATA_UPDATED" and row["resource_label"]==item["title"] for row in response.json()["items"])
    response=client.get("/api/v1/activity",headers=hdr(users[0]),params={"resource_type":"official_form","resource_id":item["id"]})
    assert response.status_code==200 and response.json()["total"]==0


def test_form_management_can_be_assigned_after_registration_round_closes(forms):
    client,users,_,_,session,round_id=forms
    session.get(m.ThesisRound,round_id).state="CLOSED"
    users[5].base_role="ADMIN"
    session.commit()
    payload={"round_id":str(round_id),"user_id":str(users[3].id),"assignment_type":"FORM_MANAGER","basis_ref":"Khoa giao cập nhật mẫu sau khi đóng đăng ký"}
    response=client.post("/api/v1/admin/round-assignments",headers=hdr(users[5]),json=payload)
    assert response.status_code==201,response.text
    payload["assignment_type"]="ELIGIBILITY_IMPORTER"
    assert client.post("/api/v1/admin/round-assignments",headers=hdr(users[5]),json=payload).status_code==422
