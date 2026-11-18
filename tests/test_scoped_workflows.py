from datetime import timedelta
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select
from backend.db.models import entities as m
from backend.services import thesis_changes as changes
from backend.services.theses import now
from test_registration import scenario,hdr
from test_core_workspace import workspace,version_headers,synthetic_pdf
from test_thesis_changes import submit,agree_group,agree_advisor,approve

def extension_request(ctx):
    client,users,_,_,session,path=ctx
    thesis=session.get(m.Thesis,UUID(path.split('/')[-1]))
    baseline=m.DocumentDeadline(round_id=thesis.round_id,document_type='REPORT',due_at=now()+timedelta(days=5),
        state='CLOSED',set_by=users[4].id,reason='Synthetic official completion schedule')
    session.add(baseline);session.commit()
    response=client.post(path+'/extension-requests',headers=version_headers(users[0],{'row_version':thesis.row_version}),
        json={'reason':'Synthetic reason to complete the academic work','confirm_consequences':True})
    assert response.status_code==201,response.text
    return response.json(),baseline

def extension_action(ctx,item,action,user,data,status=200):
    client,users,*_=ctx
    response=client.post('/api/v1/thesis-extension-requests/'+item['id']+'/'+action,
        headers=version_headers(users[user],item),json=data)
    assert response.status_code==status,response.text
    return response.json() if status==200 else item

def test_group_extension_requires_each_member_advisor_and_head(workspace):
    client,users,_,_,session,path=workspace
    item,baseline=extension_request(workspace)
    extension_action(workspace,item,'advisor-review',3,{'decision':'AGREE','reason':'Premature review'},409)
    extension_action(workspace,item,'consent',2,{'decision':'AGREE'},404)
    extension_action(workspace,item,'decision',4,{'decision':'APPROVE','reason':'Must wait for the group'},409)
    item=extension_action(workspace,item,'consent',1,{'decision':'AGREE'})
    assert item['all_agreed']
    item=extension_action(workspace,item,'advisor-review',3,{'decision':'AGREE','reason':'Academic work can be completed'})
    data={'decision':'APPROVE','reason':'External decision has been checked','decision_on':now().date().isoformat(),
        'extension_starts_at':baseline.due_at.isoformat(),'until_at':(now()+timedelta(days=30)).isoformat(),
        'reference':'SYN-QD-EXT-01','confirm_decision':True}
    extension_action(workspace,item,'decision',0,data,403)
    extension_action(workspace,item,'decision',4,{**data,'until_at':(now()+timedelta(days=200)).isoformat()},422)
    item=extension_action(workspace,item,'decision',4,data)
    assert item['state']=='APPROVED'
    thesis=session.get(m.Thesis,UUID(path.split('/')[-1]));session.refresh(thesis)
    assert thesis.state=='EXTENDED'
    session.refresh(baseline)
    assert baseline.state=='CLOSED'
    extension_action(workspace,item,'decision',4,data,409)
    assert client.get('/api/v1/thesis-changes',headers=hdr(users[2])).json()['extension_requests']==[]

def test_declined_or_expired_extension_does_not_cancel_participation(workspace,monkeypatch):
    client,users,_,_,session,path=workspace
    item,_=extension_request(workspace)
    item=extension_action(workspace,item,'consent',1,{'decision':'DECLINE'})
    assert item['state']=='REJECTED'
    thesis=session.get(m.Thesis,UUID(path.split('/')[-1]));session.refresh(thesis)
    assert thesis.state=='ACTIVE'
    assert len(session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id==thesis.id,m.ThesisMember.active.is_(True))).all())==2
    baseline=session.scalar(select(m.DocumentDeadline).where(m.DocumentDeadline.round_id==thesis.round_id,m.DocumentDeadline.document_type=='REPORT'))
    response=client.post(path+'/extension-requests',headers=version_headers(users[0],{'row_version':thesis.row_version}),json={
        'until_at':(now()+timedelta(days=35)).isoformat(),'reason':'A new synthetic request after group discussion','confirm_consequences':True})
    assert response.status_code==201,response.text
    item=response.json();due=now()+timedelta(days=1)
    item=extension_action(workspace,item,'consent-deadline',4,{'due_at':due.isoformat(),'reason':'Synthetic consent cutoff'})
    monkeypatch.setattr(changes,'now',lambda:due+timedelta(seconds=1))
    rows=client.get('/api/v1/thesis-changes',headers=hdr(users[0])).json()['extension_requests']
    assert next(row for row in rows if row['id']==item['id'])['state']=='EXPIRED'
    session.refresh(thesis);assert thesis.state=='ACTIVE'
    assert not session.scalar(select(m.ThesisExtension.id).where(m.ThesisExtension.thesis_id==thesis.id))

def split(ctx,finalize=True):
    client,users,_,lecturers,session,path=ctx
    original=session.get(m.Thesis,UUID(path.split('/')[-1]))
    topic=m.Topic(id=uuid4(),round_id=original.round_id,department_id=original.department_id,code='SPLIT-'+uuid4().hex[:10],
        current_title='Synthetic individual replacement topic',description='An independent topic with one student',max_students=1,
        state='APPROVED',proposer_type='LECTURER',proposer_user_id=users[5].id,receiving_lecturer_id=lecturers[2].id)
    session.add(topic);session.commit()
    item=submit(ctx,scope='INDIVIDUAL',kind='REPLACEMENT',target_topic_id=str(topic.id),proposed_title='',proposed_description='')
    assert item['scope']=='INDIVIDUAL'
    assert not ctx[0].get('/api/v1/thesis-changes',headers=hdr(ctx[1][1])).json()['requests'][0]['can_consent']
    item=agree_advisor(ctx,item)
    item=agree_advisor(ctx,item,index=5,role='NEW_ADVISOR')
    if finalize:item=approve(ctx,item)
    return original,item

def test_individual_split_is_atomic_and_preserves_remaining_group(workspace):
    client,users,students,lecturers,session,path=workspace
    old_title=client.get(path,headers=hdr(users[0])).json()['title']
    old,item=split(workspace)
    assert item['scope']=='INDIVIDUAL' and item['result_thesis_id']
    new=session.get(m.Thesis,UUID(item['result_thesis_id']));session.refresh(old)
    assert old.current_title==old_title and old.id!=new.id
    old_members=session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id==old.id,m.ThesisMember.active.is_(True))).all()
    assert len(old_members)==1 and old_members[0].student_id==students[1].id and old_members[0].is_coordinator
    for thesis,user in [(old,users[1]),(new,users[0])]:
        forms=client.get('/api/v1/topic-registrations/'+str(thesis.registration_id)+'/forms',headers=hdr(user))
        assert forms.status_code==200,forms.text
        assert forms.json()['can_submit'] and forms.json()['form_code']=='1A'
    assert client.get(path,headers=hdr(users[0])).status_code==404
    assert client.get('/api/v1/theses/'+str(new.id),headers=hdr(users[1])).status_code==404
    assert client.get('/api/v1/theses/'+str(new.id),headers=hdr(users[0])).status_code==200
    assert not session.scalar(select(m.ThesisWithdrawalRequest.id).where(m.ThesisWithdrawalRequest.student_id==students[0].id))

def test_advisor_milestones_are_private_and_same_code_can_repeat_per_thesis(workspace):
    client,users,_,_,session,path=workspace
    old,item=split(workspace);new_path='/api/v1/theses/'+item['result_thesis_id']
    body={'scope':'THESIS','code':'WEEK_1','title':'Private weekly work','due_at':(now()+timedelta(days=7)).isoformat()}
    first=client.post(path+'/milestones',headers=hdr(users[3]),json=body)
    assert first.status_code==201,first.text
    second=client.post(new_path+'/milestones',headers=hdr(users[5]),json=body)
    assert second.status_code==201,second.text
    assert client.get(path+'/milestones',headers=hdr(users[4])).json()==[]
    assert client.post(path+'/milestones/'+first.json()['id']+'/close',headers=version_headers(users[4],first.json()),json={'reason':'Coordinator cannot change private work'}).status_code==403
    bad=client.post(new_path+'/progress-reports',headers=hdr(users[0]),json={'milestone_id':first.json()['id'],'summary':'Wrong thesis private milestone','reported_ratio':20})
    assert bad.status_code==409
    good=client.post(new_path+'/progress-reports',headers=hdr(users[0]),json={'milestone_id':second.json()['id'],'summary':'Results for the correct thesis','reported_ratio':20})
    assert good.status_code==201,good.text

def test_faculty_wide_receiver_does_not_expand_head_authority(scenario):
    client,users,students,lecturers,topic,session=scenario
    original_dept=session.get(m.Department,topic.department_id)
    other=m.Department(id=uuid4(),faculty_id=original_dept.faculty_id,code='SYN-OTHER-'+uuid4().hex[:5],name='Other academic department')
    session.add(other);session.flush()
    lecturers[2].department_id=other.id
    lecturers[2].profile_data={'specializations':['Computer vision'],'research_interests':[]}
    lecturers[2].profile_verified_at=now();lecturers[2].profile_verified_by=users[4].id
    topic.current_title='Computer vision for thesis reporting';session.commit()
    choices=client.get('/api/v1/lecturers?topic_id='+str(topic.id),headers=hdr(users[0]))
    assert choices.status_code==200,choices.text
    candidate=next(row for row in choices.json() if row['id']==str(lecturers[2].id))
    assert candidate['department_name']==other.name and candidate['recommended']
    draft_choices=client.get('/api/v1/lecturers',params={'query_text':'Computer vision academic project'},headers=hdr(users[0])).json()
    assert next(row for row in draft_choices if row['id']==str(lecturers[2].id))['recommended']
    lecturers[2].profile_verified_at=None;session.commit()
    draft_choices=client.get('/api/v1/lecturers',params={'query_text':'Computer vision academic project'},headers=hdr(users[0])).json()
    assert not next(row for row in draft_choices if row['id']==str(lecturers[2].id))['recommended']
    lecturers[2].profile_verified_at=now();session.commit()
    made=client.post('/api/v1/student-proposals',headers=hdr(users[0]),json={'round_id':str(topic.round_id),
        'title':'Computer vision student proposal','description':'Synthetic faculty-wide supervision topic',
        'max_students':1,'receiving_lecturer_id':str(lecturers[2].id)})
    assert made.status_code==201,made.text
    reg=made.json()
    submitted=client.post('/api/v1/topic-registrations/'+reg['id']+'/submit',headers=version_headers(users[0],reg))
    assert submitted.status_code==200,submitted.text
    proposal=client.get('/api/v1/topics/'+reg['topic_id'],headers=hdr(users[4])).json()
    decision=client.post('/api/v1/topics/'+reg['topic_id']+'/department-decision',headers=version_headers(users[4],proposal),json={
        'decision':'APPROVE','receiving_lecturer_id':str(lecturers[2].id)})
    assert decision.status_code==200,decision.text
    reg=client.get('/api/v1/topic-registrations/'+reg['id'],headers=hdr(users[5])).json()
    accepted=client.post('/api/v1/topic-registrations/'+reg['id']+'/lecturer-decision',headers=version_headers(users[5],reg),json={'decision':'ACCEPT'})
    assert accepted.status_code==200,accepted.text


def test_split_rolls_back_all_membership_and_registration_changes(workspace,monkeypatch):
    from fastapi import HTTPException
    client,users,students,_,session,path=workspace
    old,item=split(workspace,finalize=False)
    def fail_after_creation(*args):raise HTTPException(409,'Synthetic failure after creating replacement records')
    monkeypatch.setattr(changes,'reset_evidence',fail_after_creation)
    result=client.post('/api/v1/thesis-changes/'+item['id']+'/decision',headers=version_headers(users[4],item),
        json={'decision':'APPROVE','reason':'Approved independent scope for synthetic group'})
    assert result.status_code==409,result.text
    session.expire_all()
    members=session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id==old.id,m.ThesisMember.active.is_(True))).all()
    assert len(members)==2 and next(row for row in members if row.student_id==students[0].id).is_coordinator
    assert len(session.scalars(select(m.ThesisMember).where(m.ThesisMember.student_id==students[0].id,m.ThesisMember.active.is_(True))).all())==1
    request=session.get(m.ThesisChangeRequest,UUID(item['id']))
    assert request.state=='ADVISOR_REVIEWED' and 'result_thesis_id' not in request.snapshot


def test_extension_opens_only_own_report_submission_not_official_round(workspace):
    client,users,_,_,session,path=workspace
    item,baseline=extension_request(workspace)
    item=extension_action(workspace,item,'consent',1,{'decision':'AGREE'})
    item=extension_action(workspace,item,'advisor-review',3,{'decision':'AGREE','reason':'The work can be completed after extension'})
    until=now()+timedelta(days=30)
    extension_action(workspace,item,'decision',4,{'decision':'APPROVE','reason':'Synthetic external decision has been checked',
        'decision_on':now().date().isoformat(),'extension_starts_at':baseline.due_at.isoformat(),
        'until_at':until.isoformat(),'reference':'SYN-EXTENSION-REPORT-01','confirm_decision':True})
    doc=client.post(path+'/documents',headers=hdr(users[0]),json={'document_type':'REPORT','title':'Extended academic report'})
    assert doc.status_code==201,doc.text
    uploaded=client.post(path+'/documents/'+doc.json()['id']+'/versions',headers={**version_headers(users[0],doc.json()),
        'X-File-Name':'synthetic-report.pdf','Content-Type':'application/octet-stream'},content=synthetic_pdf())
    assert uploaded.status_code==201,uploaded.text
    version=session.get(m.DocumentVersion,UUID(uploaded.json()['versions'][0]['id']))
    assert abs((version.due_at_at_submission-until).total_seconds())<1
    session.refresh(baseline)
    assert baseline.state=='CLOSED' and baseline.due_at<until


def test_confirmed_extension_window_allows_decision_and_records_outcome(workspace,monkeypatch):
    from backend.services import thesis_extensions
    client,users,_,_,session,path=workspace
    item,baseline=extension_request(workspace)
    item=extension_action(workspace,item,'consent',1,{'decision':'AGREE'})
    item=extension_action(workspace,item,'advisor-review',3,{'decision':'AGREE','reason':'Feasible academic work after an extension'})
    listing=client.get('/api/v1/thesis-changes',headers=hdr(users[4])).json()
    assert listing['extension_requests'][0]['all_agreed']
    start=baseline.due_at
    cap=thesis_extensions.c.add_months(start,5)
    extension_action(workspace,item,'decision',4,{'decision':'APPROVE','reason':'Khoa đã đối chiếu thời hạn gia hạn',
        'decision_on':now().date().isoformat(),'extension_starts_at':start.isoformat(),
        'until_at':(cap-timedelta(seconds=1)).isoformat(),'reference':'SYN-EXTENSION-DECISION','confirm_decision':True})
    request=session.get(m.ThesisExtensionRequest,UUID(item['id']))
    thesis=session.get(m.Thesis,UUID(path.split('/')[-1]))
    extension=session.get(m.ThesisExtension,request.extension_id)
    assert request.state=='APPROVED' and thesis.state=='EXTENDED'
    assert extension.until_at<cap
    monkeypatch.setattr(thesis_extensions.c,'now',lambda: extension.until_at+timedelta(seconds=1))
    assert thesis_extensions.expire_without_council(session,request)
    session.commit()
    session.refresh(request);session.refresh(thesis)
    assert request.state=='EXPIRED' and request.decision_reason=='Khoa đã đối chiếu thời hạn gia hạn'
    assert thesis_extensions.output(session,users[4],request)['defense']['status']=='NOT_PASSED'
    assert not thesis_extensions.expire_without_council(session,request)
    assert thesis.state=='ARCHIVED'
    report = client.get(f"/api/v1/nv6-reports/{thesis.round_id}", headers=hdr(users[4]))
    assert report.status_code == 200, report.text
    rows = report.json()["rows"]
    expired = [row for row in rows if row["thesis_id"] == str(thesis.id)]
    assert expired
    assert report.json()["results"]["EXTENSION_EXPIRED"] == len(expired)
    assert all(row["result"] == "EXTENSION_EXPIRED" and row["grade"] is None for row in expired)
