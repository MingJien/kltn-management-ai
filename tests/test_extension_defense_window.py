"""Regression tests against isolated PostgreSQL: calendar, schedule, expiry, audit."""
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from backend.db.models import entities as m
from backend.services import thesis_extensions as service
from backend.services.extension_policy import maximum_until
from backend.services.theses import now
from test_registration import scenario, hdr
from test_core_workspace import workspace, version_headers
from test_nv6_evaluation import evaluation, complete_review, check, get


def approve_extension(ctx):
    client, users, _, _, session, path = ctx
    thesis = session.get(m.Thesis, UUID(path.split('/')[-1]))
    deadline = session.scalar(select(m.DocumentDeadline).where(m.DocumentDeadline.round_id == thesis.round_id,
        m.DocumentDeadline.document_type == 'REPORT'))
    start = deadline.due_at
    until = start + timedelta(days=40)
    result = client.post(path+'/extension-requests', headers=version_headers(users[0],{'row_version':thesis.row_version}), json={
        'until_at':until.isoformat(),'reason':'Synthetic request for a later faculty defense session','confirm_consequences':True})
    assert result.status_code == 201, result.text
    item = result.json()
    for action, who, body in [('consent',1,{'decision':'AGREE'}),
        ('advisor-review',3,{'decision':'AGREE','reason':'Feasible academic extension'}),
        ('decision',4,{'decision':'APPROVE','reason':'Official academic extension decision checked',
         'extension_starts_at':start.isoformat(),'until_at':until.isoformat(),
         'decision_on':now().date().isoformat(),'reference':'SYN-EXT-ACADEMIC-01','confirm_decision':True})]:
        response=client.post('/api/v1/thesis-extension-requests/'+item['id']+'/'+action,
            headers=version_headers(users[who],item),json=body)
        assert response.status_code == 200, response.text
        item=response.json()
    session.expire_all()
    return session.get(m.ThesisExtensionRequest, UUID(item['id'])), start, until


def create_council(ctx):
    client,users,_,lecturers,session,path=ctx
    thesis=session.get(m.Thesis,UUID(path.split('/')[-1]))
    people=[]
    for n in range(5):
        user=m.UserAccount(id=uuid4(),external_subject='ext-council-'+uuid4().hex,base_role='LECTURER',status='ACTIVE')
        session.add(user);session.flush()
        lecturer=m.LecturerProfile(id=uuid4(),user_id=user.id,department_id=thesis.department_id,
            lecturer_code='EXT-'+uuid4().hex[:12],display_name=f'Synthetic extension committee {n}')
        session.add(lecturer);session.flush();people.append(lecturer)
    session.commit()
    result=client.post('/api/v1/defense/councils',headers=hdr(users[4]),json={
        'round_id':str(thesis.round_id),'department_id':str(thesis.department_id),
        'name':'Synthetic extension council','reference':'SYN-QD-COUNCIL',
        'members':[{'lecturer_id':str(p.id),'role':role} for p,role in zip(people,
            ['CHAIR','SECRETARY','REVIEWER','REVIEWER','MEMBER'])]})
    assert result.status_code==201,result.text
    return result.json()['id']


@pytest.mark.parametrize('year,month,day,expected',[(2027,5,1,(2027,10,1)),
    (2027,9,30,(2028,2,29)),(2026,9,30,(2027,2,28)),(2027,12,31,(2028,5,31))])
def test_five_calendar_months_clamps_month_end_and_handles_leap_year(year,month,day,expected):
    start=datetime(year,month,day,8,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
    cap=maximum_until(start)
    assert (cap.year,cap.month,cap.day)==expected and cap.hour==8


def test_schedule_extended_thesis_reschedule_and_delayed_results(evaluation,monkeypatch):
    ctx,_=evaluation
    client,users,_,_,session,path=ctx
    for n in range(2):
        complete_review(ctx,member=n)
        assert check(ctx,member=n).status_code==200
    current=get(ctx)
    locked_doc=client.post(path+'/documents',headers=hdr(users[0]),json={'document_type':'REPORT','title':'Must remain locked'})
    assert locked_doc.status_code==409,locked_doc.text
    options=client.get('/api/v1/thesis-changes',headers=hdr(users[0])).json()
    assert next(t for t in options['theses'] if t['id']==current['thesis_id'])['can_request_extension']
    request,start,until=approve_extension(ctx)
    council=create_council(ctx)
    listing=client.get('/api/v1/defense',headers=hdr(users[4]))
    assert listing.status_code==200,listing.text
    listed=next(t for t in listing.json()['eligible'] if t['id']==str(request.thesis_id))
    assert listed['extension_until_at']
    data={'confirmed_no_conflict':True,'thesis_id':str(request.thesis_id),'council_id':council,'room':'Synthetic extension room',
        'starts_at':(start+timedelta(days=1)).isoformat(),'ends_at':(start+timedelta(days=1,hours=1)).isoformat()}
    wrong={**data,'starts_at':(until+timedelta(days=1)).isoformat(),'ends_at':(until+timedelta(days=1,hours=1)).isoformat()}
    failed=client.post('/api/v1/defense/slots',headers=hdr(users[4]),json=wrong)
    assert failed.status_code==409,failed.text
    assert not session.scalar(select(m.DefenseSlot.id).where(m.DefenseSlot.thesis_id==request.thesis_id))
    made=client.post('/api/v1/defense/slots',headers=hdr(users[4]),json=data)
    assert made.status_code==201,made.text
    slot=session.get(m.DefenseSlot,UUID(made.json()['id']))
    rejected=client.put('/api/v1/defense/slots/'+str(slot.id),headers=version_headers(users[4],{'row_version':slot.row_version}),json=wrong)
    assert rejected.status_code==409,rejected.text
    session.refresh(slot)
    assert slot.starts_at==start+timedelta(days=1)
    approval=(request.decided_at,request.decision_reason,request.decided_by)
    monkeypatch.setattr(service.c,'now',lambda: until+timedelta(days=1))
    service.process_expired(session)
    session.flush()
    assert request.state=='APPROVED'
    assert not service.expire_without_council(session,request)
    result=service.output(session,users[4],request)
    assert result['defense']['status']=='PENDING_RESULT'
    assert request.state=='APPROVED' and (request.decided_at,request.decision_reason,request.decided_by)==approval
    session.refresh(session.get(m.Thesis,request.thesis_id))
    assert session.get(m.Thesis,request.thesis_id).state=='EXTENDED'
    # Cancellation of an unheld schedule exposes the no-council outcome after the deadline.
    session.delete(slot);session.commit()
    service.process_expired(session)
    session.commit()
    session.refresh(request)
    assert request.state=='EXPIRED'
    assert service.output(session,users[4],request)['defense']['status']=='NOT_PASSED'
    assert (request.decided_at,request.decision_reason,request.decided_by)==approval
    assert not service.expire_without_council(session,request)
