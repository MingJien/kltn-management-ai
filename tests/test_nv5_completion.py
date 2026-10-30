"""Post-registration edge cases on PostgreSQL; scanner verdicts are explicit fixture state."""
import json
from datetime import datetime, timedelta

from sqlalchemy import func, select

from test_core_workspace import workspace, open_milestone, version_headers, synthetic_pdf
from test_registration import hdr, scenario
from backend.db.models import entities as m
from backend.services.theses import now


def submit_file(client, path, user, milestone, summary="Synthetic report", content=None):
    return client.post(path+"/progress-submissions", headers=hdr(user),
        data={"report":json.dumps({"milestone_id":milestone["id"],"summary":summary,"reported_ratio":25})},
        files={"file":("evidence.pdf", synthetic_pdf() if content is None else content,"application/pdf")})


def test_late_and_closed_revision_report_include_file_atomically(workspace):
    client,users,_,_,session,path=workspace
    milestone=open_milestone(client,users,path)
    item=session.get(m.ProgressMilestone,milestone["id"])
    item.due_at=now()-timedelta(hours=1)
    session.commit()
    response=submit_file(client,path,users[0],milestone)
    assert response.status_code==201,response.text
    report=response.json()
    assert report["late"] and report["evidence_document_version_id"]
    assert report["evidence_scan_state"]=="QUARANTINED"
    revision=client.post(path+f"/progress-reports/{report['id']}/review",headers=version_headers(users[3],report),
        json={"decision":"REVISION_REQUIRED","comment":"Please revise"})
    assert revision.status_code==200,revision.text
    closed=client.post(path+f"/milestones/{item.id}/close",headers=version_headers(users[4],milestone),json={"reason":"Round closure"})
    assert closed.status_code==200,closed.text
    second=submit_file(client,path,users[1],milestone,"Revised after closure")
    assert second.status_code==201,second.text
    assert second.json()["version_no"]==2 and second.json()["evidence_document_version_id"]
    assert submit_file(client,path,users[1],milestone,"Not requested again").status_code==409
    assert len(client.get(path+"/progress-reports",headers=hdr(users[0])).json())==2


def test_invalid_file_does_not_create_report_or_advance_version(workspace):
    client,users,_,_,session,path=workspace
    milestone=open_milestone(client,users,path)
    assert submit_file(client,path,users[0],milestone,content=b"not a PDF").status_code==422
    assert client.get(path+"/progress-reports",headers=hdr(users[0])).json()==[]
    assert session.scalar(select(func.count()).select_from(m.DocumentVersion))==0
    assert submit_file(client,path,users[0],milestone).json()["version_no"]==1


def test_file_storage_failure_rolls_back_report_and_audit(workspace,monkeypatch):
    client,users,_,_,session,path=workspace
    milestone=open_milestone(client,users,path)
    from backend.services import documents
    def fail(*args,**kwargs):
        raise OSError("Synthetic storage failure")
    monkeypatch.setattr(documents,"persist_upload",fail)
    import pytest
    with pytest.raises(OSError,match="Synthetic storage failure"):
        submit_file(client,path,users[0],milestone)
    assert client.get(path+"/progress-reports",headers=hdr(users[0])).json()==[]
    assert not session.scalar(select(m.AuditEvent.id).where(m.AuditEvent.action=="PROGRESS_SUBMITTED"))
    assert not session.scalar(select(m.UserNotification.id).where(m.UserNotification.kind=="PROGRESS_SUBMITTED"))


def test_progress_evidence_is_private_even_through_document_routes(workspace):
    client,users,_,lecturers,session,path=workspace
    milestone=open_milestone(client,users,path)
    report=submit_file(client,path,users[0],milestone).json()
    version=session.get(m.DocumentVersion,report["evidence_document_version_id"])
    session.get(m.StoredFile,version.stored_file_id).scan_state="CLEAN";session.commit()
    download=path+f"/progress-reports/{report['id']}/evidence"
    for user in (users[2],users[5]):assert client.get(download,headers=hdr(user)).status_code==404
    assert client.get(download,headers=hdr(users[4])).status_code==403
    assert not any(row["action"].startswith("PROGRESS_") for row in client.get(path+"/audit",headers=hdr(users[4])).json())
    assert client.get(download,headers=hdr(users[3])).content==synthetic_pdf()
    assert client.get(path+f"/documents/{version.document_id}/versions/{version.id}/download",headers=hdr(users[4])).status_code==403
    assert all(doc["id"]!=str(version.document_id) for doc in client.get(path+"/documents",headers=hdr(users[4])).json())


def test_document_deadline_history_and_late_snapshot_are_scoped(workspace):
    client,users,_,_,session,path=workspace
    deadline=session.scalar(select(m.DocumentDeadline).where(m.DocumentDeadline.document_type=="PLAN"))
    deadline.due_at=now()-timedelta(days=1)
    session.commit()
    doc=client.post(path+"/documents",headers=hdr(users[0]),json={"title":"Plan","document_type":"PLAN"}).json()
    uploaded=client.post(path+f"/documents/{doc['id']}/versions",headers={**version_headers(users[0],doc),"X-File-Name":"plan.pdf","Content-Type":"application/octet-stream"},content=synthetic_pdf())
    assert uploaded.status_code==201,uploaded.text
    assert uploaded.json()["versions"][0]["late"]
    original=deadline.due_at
    assert client.post(path+"/document-deadlines",headers=version_headers(users[3],{"row_version":deadline.row_version}),json={"document_type":"PLAN","due_at":(now()+timedelta(days=2)).isoformat(),"reason":"Faculty extends all theses"}).status_code==403
    extended=client.post(path+"/document-deadlines",headers=version_headers(users[4],{"row_version":deadline.row_version}),json={"document_type":"PLAN","due_at":(now()+timedelta(days=2)).isoformat(),"reason":"Faculty extends all theses"})
    assert extended.status_code==200,extended.text
    history=client.get(path+"/document-deadline-history",headers=hdr(users[0]))
    assert history.status_code==200
    assert history.json()[0]["action"]=="DOCUMENT_DEADLINE_EXTENDED"
    assert "Faculty extends all theses" in history.json()[0]["reason"]
    assert client.get(path+"/document-deadline-history",headers=hdr(users[2])).status_code==404
    saved=client.get(path+"/documents",headers=hdr(users[0])).json()[0]["versions"][0]
    assert saved["late"] and datetime.fromisoformat(saved["due_at_at_submission"].replace("Z","+00:00"))==original


def test_plan_requires_printable_file_without_creating_partial_version(workspace):
    client,users,_,_,session,path=workspace
    doc=client.post(path+"/documents",headers=hdr(users[0]),json={"title":"Official plan","document_type":"PLAN"}).json()
    response=client.post(path+f"/documents/{doc['id']}/versions",headers={**version_headers(users[0],doc),
        "X-File-Name":"plan.txt","Content-Type":"application/octet-stream"},content=b"A plan without the official page layout")
    assert response.status_code==422
    assert "PDF" in response.json()["detail"] and "DOCX" in response.json()["detail"]
    current=client.get(path+"/documents",headers=hdr(users[0])).json()[0]
    assert current["versions"]==[] and current["row_version"]==doc["row_version"]
    accepted=client.post(path+f"/documents/{doc['id']}/versions",headers={**version_headers(users[0],doc),
        "X-File-Name":"plan.pdf","Content-Type":"application/octet-stream"},content=synthetic_pdf())
    assert accepted.status_code==201 and accepted.json()["versions"][0]["version_no"]==1


def test_archived_round_cannot_change_or_close_document_deadlines(workspace):
    client,users,_,_,session,path=workspace
    milestone=open_milestone(client,users,path)
    thesis=session.get(m.Thesis,path.rsplit("/",1)[-1])
    round_=session.get(m.ThesisRound,thesis.round_id)
    deadline=session.scalar(select(m.DocumentDeadline).where(m.DocumentDeadline.round_id==thesis.round_id,
        m.DocumentDeadline.document_type=="PLAN"))
    headers=version_headers(users[4],{"row_version":deadline.row_version})
    round_.state="ARCHIVED";session.commit()
    change=client.post(path+"/document-deadlines",headers=headers,json={"document_type":"PLAN",
        "due_at":(now()+timedelta(days=100)).isoformat(),"reason":"Attempt to change an archived round"})
    assert change.status_code==409
    assert client.post(path+"/document-deadlines/PLAN/close",headers=headers,
        json={"reason":"Attempt to close archived round"}).status_code==409
    assert client.post(path+f"/milestones/{milestone['id']}/close",headers=version_headers(users[4],milestone),
        json={"reason":"Attempt to close archived milestone"}).status_code==409
