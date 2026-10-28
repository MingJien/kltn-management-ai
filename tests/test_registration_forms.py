from datetime import timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from test_registration import scenario, hdr
from test_core_workspace import synthetic_pdf
from backend.db.models import entities as m
from backend.services import file_scanner
from backend.services.theses import now


@pytest.fixture
def forms(scenario, monkeypatch, tmp_path):
    client, users, students, lecturers, topic, session = scenario
    monkeypatch.setenv("KLTN_DOCUMENT_DIR", str(tmp_path))
    monkeypatch.setattr(file_scanner,"executable",lambda:None)
    monkeypatch.setattr(file_scanner,"clamdscan_executable",lambda:None)
    reg=client.post("/api/v1/topic-registrations",headers=hdr(users[0]),json={"topic_id":str(topic.id)}).json()
    yield client,users,students,topic,session,reg,f"/api/v1/topic-registrations/{reg['id']}/forms"


def upload(client,user,path,code="1A",version=None,content=None,name="application.pdf"):
    current=client.get(path,headers=hdr(user)).json()
    return client.post(path,headers={**hdr(user),"If-Match":str(current["registration_version"] if version is None else version),
        "X-Form-Code":code,"X-File-Name":name,"Content-Type":"application/octet-stream"},
        content=synthetic_pdf() if content is None else content)


def clean(session,row):
    item=session.get(m.RegistrationFormVersion,row["id"])
    session.get(m.StoredFile,item.stored_file_id).scan_state="CLEAN"
    session.commit()


def test_receipt_preserves_versions_and_does_not_approve_registration(forms):
    client,users,_,_,session,reg,path=forms
    initial=client.get(path,headers=hdr(users[0])).json()
    assert initial["form_code"]=="1A" and initial["can_submit"]
    assert client.get(path,headers=hdr(users[1])).status_code==404
    assert client.get(path,headers=hdr(users[3])).status_code==404  # Not submitted to lecturer yet.
    response=upload(client,users[0],path)
    assert response.status_code==201,response.text
    first=response.json()["versions"][0]
    download=path+f"/{first['id']}/download"
    printing=path+f"/{first['id']}/print-copy"
    assert client.get(download,headers=hdr(users[0])).status_code==409
    assert client.post(printing,headers=hdr(users[0])).status_code==409
    clean(session,first)
    exported=client.post(printing,headers=hdr(users[0]))
    assert exported.status_code==200,exported.text
    text=PdfReader(BytesIO(exported.content)).pages[0].extract_text()
    assert "Ban nop, chua xac nhan Khoa duyet" in text
    assert exported.headers["x-document-code"].startswith("DK1A-")
    assert client.get(download,headers=hdr(users[0])).content==synthetic_pdf()
    assert session.get(m.TopicRegistration,reg["id"]).state=="DRAFT"
    stale=upload(client,users[0],path,version=initial["registration_version"])
    assert stale.status_code==409
    second=upload(client,users[0],path).json()
    assert [v["version_no"] for v in second["versions"]]==[2,1]
    assert client.post(printing,headers=hdr(users[0])).status_code==409
    assert client.get(download,headers=hdr(users[0])).content==synthetic_pdf()


def test_group_change_invalidates_old_solo_form_and_requires_group_template(forms):
    client,users,_,topic,session,reg,path=forms
    first=upload(client,users[0],path).json()["versions"][0];clean(session,first)
    joined=client.post("/api/v1/topic-registrations",headers=hdr(users[1]),json={"topic_id":str(topic.id)})
    assert joined.status_code==201,joined.text
    data=client.get(path,headers=hdr(users[0])).json()
    assert data["form_code"]=="1B" and not data["versions"][0]["current"]
    assert client.post(path+f"/{first['id']}/print-copy",headers=hdr(users[0])).status_code==409
    assert upload(client,users[0],path,"1A").status_code==409
    second=upload(client,users[1],path,"1B")
    assert second.status_code==201,second.text
    assert second.json()["versions"][0]["form_code"]=="1B"
    assert client.get(path+f"/{uuid4()}/download",headers=hdr(users[0])).status_code==404


def test_acceptance_locks_upload_but_keeps_receipt_available(forms):
    client,users,_,_,session,reg,path=forms
    first=upload(client,users[0],path).json()["versions"][0];clean(session,first)
    current=client.post(f"/api/v1/topic-registrations/{reg['id']}/submit",headers=hdr(users[0])).json()
    accepted=client.post(f"/api/v1/topic-registrations/{reg['id']}/lecturer-decision",headers={**hdr(users[3]),"If-Match":str(current["row_version"])},
        json={"decision":"ACCEPT"})
    assert accepted.status_code==200,accepted.text
    assert not client.get(path,headers=hdr(users[0])).json()["can_submit"]
    assert upload(client,users[0],path).status_code==409
    assert client.get(path,headers=hdr(users[3])).status_code==200
    assert client.post(path+f"/{first['id']}/print-copy",headers=hdr(users[0])).status_code==200


def test_invalid_types_and_deadline_cannot_create_a_form_version(forms):
    client,users,_,topic,session,_,path=forms
    assert upload(client,users[0],path,content=b"not a form",name="application.txt").status_code==422
    assert upload(client,users[0],path,content=b"%PDF-"+b"x"*(20*1024*1024)).status_code==413
    assert client.get(path,headers=hdr(users[0])).json()["versions"]==[]
    round_=session.get(m.ThesisRound,topic.round_id);round_.closes_at=now()-timedelta(hours=1);session.commit()
    assert upload(client,users[0],path).status_code==409
    users[2].base_role="ADMIN";session.commit()
    assert client.get(path,headers=hdr(users[2])).status_code==404


def test_upload_failure_rolls_back_form_and_cleans_file(forms,monkeypatch):
    client,users,_,_,session,_,path=forms
    from backend.services import registration_forms
    root=registration_forms.documents.storage_root()
    original=file_scanner.scan
    def broken(*args):raise RuntimeError("synthetic scanner failure")
    monkeypatch.setattr(file_scanner,"scan",broken)
    with pytest.raises(RuntimeError,match="synthetic scanner failure"):
        upload(client,users[0],path)
    assert not list(root.glob("*"))
    assert client.get(path,headers=hdr(users[0])).json()["versions"]==[]
    monkeypatch.setattr(file_scanner,"scan",original)
    assert upload(client,users[0],path).json()["versions"][0]["version_no"]==1
