from datetime import timedelta

from sqlalchemy import select

from test_core_workspace import workspace, open_milestone, version_headers
from test_registration import scenario, hdr
from backend.db.models import entities as m
from backend.services.theses import now


def test_coordinator_reopens_latest_milestone_without_rewriting_old_lateness(workspace):
    client,users,_,_,_,path=workspace
    milestone=open_milestone(client,users,path,due_at=(now()-timedelta(hours=1)).isoformat())
    report=client.post(path+"/progress-reports",headers=hdr(users[0]),json={"milestone_id":milestone["id"],"summary":"Late initial report","reported_ratio":25}).json()
    assert report["late"]
    closed=client.post(path+f"/milestones/{milestone['id']}/close",headers=version_headers(users[4],milestone),json={"reason":"Faculty closes submissions"}).json()
    body={"due_at":(now()+timedelta(days=10)).isoformat(),"reason":"Faculty reopens the entire round"}
    endpoint=path+f"/milestones/{milestone['id']}/extend"
    assert client.post(endpoint,headers=version_headers(users[3],closed),json=body).status_code==403
    reopened=client.post(endpoint,headers=version_headers(users[4],closed),json=body)
    assert reopened.status_code==200 and reopened.json()["state"]=="OPEN"
    assert client.post(endpoint,headers=version_headers(users[4],closed),json=body).status_code==409
    assert client.get(path+"/progress-reports",headers=hdr(users[0])).json()[0]["due_at_at_submission"]==report["due_at_at_submission"]
    history=client.get(path+"/milestone-history",headers=hdr(users[0])).json()
    assert history[0]["action"]=="MILESTONE_REOPENED" and body["reason"] in history[0]["reason"]
    closed_again=client.post(path+f"/milestones/{milestone['id']}/close",headers=version_headers(users[4],reopened.json()),json={"reason":"Issue a newer milestone version"}).json()
    open_milestone(client,users,path)
    assert client.post(endpoint,headers=version_headers(users[4],closed_again),json={**body,"due_at":(now()+timedelta(days=20)).isoformat()}).status_code==409


def test_coordinator_reopens_document_deadline_and_records_history(workspace):
    client,users,_,_,session,path=workspace
    deadline=session.scalar(select(m.DocumentDeadline).where(m.DocumentDeadline.document_type=="PLAN"))
    closed=client.post(path+"/document-deadlines/PLAN/close",headers=version_headers(users[4],{"row_version":deadline.row_version}),json={"reason":"End first intake"}).json()
    body={"document_type":"PLAN","due_at":(now()+timedelta(days=100)).isoformat(),"reason":"Faculty opens a supplementary intake"}
    assert client.post(path+"/document-deadlines",headers=version_headers(users[3],closed),json=body).status_code==403
    reopened=client.post(path+"/document-deadlines",headers=version_headers(users[4],closed),json=body)
    assert reopened.status_code==200 and reopened.json()["state"]=="OPEN"
    history=client.get(path+"/document-deadline-history",headers=hdr(users[0])).json()
    assert history[0]["action"]=="DOCUMENT_DEADLINE_REOPENED" and body["reason"] in history[0]["reason"]
