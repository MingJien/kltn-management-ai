"""Real PostgreSQL workflow; antivirus clearance is simulated for synthetic PDFs."""
from uuid import UUID, uuid4
from sqlalchemy import select
from test_nv6_evaluation import evaluation
from test_core_workspace import workspace, synthetic_pdf, version_headers
from test_registration import scenario, hdr
from backend.db.models import entities as m
from backend.services import publications


def proof(ctx):
    client, users, _, _, session, path = ctx
    doc = client.post(path+'/documents', headers=hdr(users[0]), json={
        'document_type':'SUPPORTING','title':'Synthetic research publication'}).json()
    uploaded = client.post(path+'/documents/'+doc['id']+'/versions', headers={**version_headers(users[0], doc),
        'X-File-Name':'publication.pdf','Content-Type':'application/octet-stream'}, content=synthetic_pdf())
    assert uploaded.status_code == 201, uploaded.text
    identifier = uploaded.json()['versions'][0]['id']
    version = session.get(m.DocumentVersion, UUID(identifier))
    session.get(m.StoredFile, version.stored_file_id).scan_state = 'CLEAN'
    session.commit()
    return identifier


def payload(ctx, evidence):
    return {'title':'Synthetic publication title','venue':'Synthetic journal', 'reference':'DOI: synthetic-123',
        'contribution':'Synthetic contributions of the participating student',
        'student_ids':[str(ctx[2][0].id)], 'evidence_version_id':evidence}


def test_two_stage_approval_is_scoped_versioned_and_not_document_receipt(evaluation):
    ctx, _ = evaluation
    client, users, students, _, session, path = ctx
    evidence = proof(ctx)
    endpoint = path+'/publication-claims'
    made = client.post(endpoint, headers=hdr(users[0]), json=payload(ctx,evidence))
    assert made.status_code == 201, made.text
    claim = made.json()
    decision = endpoint+'/'+claim['id']+'/decision'
    points = {str(students[0].id):'1'}
    def decide(user, outcome, version, amounts=None):
        return client.post(decision, headers={**hdr(users[user]),'If-Match':str(version)},
            json={'outcome':outcome,'reason':'Synthetic academic verification', 'points':amounts or {}})
    assert client.post(endpoint,headers=hdr(users[0]),json=payload(ctx,evidence)).status_code == 409
    assert decide(4,'APPROVE',1,points).status_code == 403
    assert decide(0,'CONFIRM',1).status_code == 403
    assert decide(5,'CONFIRM',1).status_code == 404
    confirmed = decide(3,'CONFIRM',1)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['state'] == 'ADVISOR_CONFIRMED'
    assert decide(3,'CONFIRM',1).status_code == 409
    assert decide(3,'APPROVE',2,points).status_code == 403
    assert decide(4,'APPROVE',2,{str(students[0].id):'1.01'}).status_code == 422
    assert decide(4,'APPROVE',2,{str(students[1].id):'1'}).status_code == 422
    approved = decide(4,'APPROVE',2,points)
    assert approved.status_code == 200, approved.text
    assert approved.json()['details']['points'] == points
    assert len(approved.json()['history']) == 3
    assert publications.approved_for(session, UUID(path.split('/')[-1]), students[0].id)['bonus'] == '1'
    assert publications.approved_for(session, UUID(path.split('/')[-1]), students[1].id)['bonus'] == '0'
    assert decide(4,'APPROVE',3,points).status_code == 403
    assert session.scalar(select(m.UserNotification.id).where(m.UserNotification.subject_type=='thesis',
        m.UserNotification.subject_id==UUID(path.split('/')[-1])))


def test_revision_keeps_history_and_requires_new_submission(evaluation):
    ctx,_=evaluation
    client,users,_,_,session,path=ctx
    evidence=proof(ctx)
    endpoint=path+'/publication-claims'
    claim=client.post(endpoint,headers=hdr(users[0]),json=payload(ctx,evidence)).json()
    res=client.post(endpoint+'/'+claim['id']+'/decision',headers={**hdr(users[3]),'If-Match':'1'},
        json={'outcome':'REVISION_REQUIRED','reason':'Please clarify the author contribution'})
    assert res.status_code==200,res.text
    assert len(res.json()['history'])==2
    made=client.post(endpoint,headers=hdr(users[0]),json=payload(ctx,evidence))
    assert made.status_code==201,made.text
    assert made.json()['id']!=claim['id']
    assert len(client.get(endpoint,headers=hdr(users[4])).json()['items'])==2
    version=session.get(m.DocumentVersion,UUID(evidence))
    session.get(m.StoredFile,version.stored_file_id).scan_state='INFECTED'
    session.commit()
    assert client.post(endpoint+'/'+made.json()['id']+'/decision',headers={**hdr(users[3]),'If-Match':'1'},
        json={'outcome':'CONFIRM','reason':'Synthetic confirm after file changed'}).status_code==422
