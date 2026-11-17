from datetime import timedelta
from copy import copy
from io import BytesIO
from uuid import uuid4, UUID

from sqlalchemy import select,func
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText
from backend.db.models import entities as m
from backend.services import defense,evaluation as evaluation_service,defense_templates,form_templates
from backend.services.theses import now
from test_registration import hdr,scenario
from test_core_workspace import workspace
from test_nv6_evaluation import evaluation,complete_review,check,get,assign


def test_two_active_reviewers_must_each_submit_for_each_student(evaluation):
    ctx,_=evaluation;client,users,_,_,session,path=ctx
    assert assign(ctx).status_code==201
    assert assign(ctx,4).status_code==201
    for index in range(2):
        complete_review(ctx,index)
        assert check(ctx,index).status_code==200
    thesis=session.get(m.Thesis,UUID(path.split('/')[-1]));report=evaluation_service.report(session,thesis)
    assert len(evaluation_service.pending_reviewer_forms(session,thesis,report))==4
    for index in range(2):complete_review(ctx,index,user=5,kind='REVIEWER')
    assert len(evaluation_service.pending_reviewer_forms(session,thesis,report))==2
    for index in range(2):complete_review(ctx,index,user=4,kind='REVIEWER')
    assert evaluation_service.pending_reviewer_forms(session,thesis,report)==[]


def test_batch_schedule_is_atomic_and_accepts_adjacent_slots(evaluation):
    ctx,_=evaluation;client,users,students,lecturers,session,path=ctx
    for index in range(2):complete_review(ctx,index);assert check(ctx,index).status_code==200
    thesis=session.get(m.Thesis,UUID(path.split('/')[-1]));report=evaluation_service.report(session,thesis)
    topic=m.Topic(round_id=thesis.round_id,department_id=thesis.department_id,proposer_user_id=users[3].id,proposer_type='LECTURER',code='BATCH-'+uuid4().hex[:12],current_title='Second synthetic thesis',max_students=1,state='LOCKED')
    session.add(topic);session.flush()
    reg=m.TopicRegistration(round_id=thesis.round_id,topic_id=topic.id,created_by=students[2].id,expected_member_count=1,state='FINALIZED')
    session.add(reg);session.flush()
    second=m.Thesis(round_id=thesis.round_id,topic_id=topic.id,department_id=thesis.department_id,registration_id=reg.id,current_title=topic.current_title,state='READY_FOR_DEFENSE')
    session.add(second);session.flush()
    member=m.ThesisMember(thesis_id=second.id,student_id=students[2].id,is_coordinator=True,joined_at=now());session.add(member);session.flush()
    advisor=m.AdvisorAssignment(thesis_id=second.id,lecturer_id=lecturers[0].id,assigned_by=users[4].id,effective_from=now());session.add(advisor);session.flush()
    doc=m.Document(thesis_id=second.id,document_type='REPORT',title='Second report',state='ACTIVE',visibility='ASSIGNED');session.add(doc);session.flush()
    version=m.DocumentVersion(document_id=doc.id,version_no=1,stored_file_id=report.stored_file_id,submitted_by=students[2].id,submitted_at=now(),content_sha256=report.content_sha256,state='ACCEPTED');session.add(version);session.flush()
    review=m.ThesisReview(thesis_id=second.id,thesis_member_id=member.id,lecturer_id=lecturers[0].id,advisor_assignment_id=advisor.id,report_version_id=version.id,kind='ADVISOR',version_no=1,sections={},thesis_completed=True,allow_defense=True,revision_reason='Synthetic setup',state='SUBMITTED',submitted_at=now());session.add(review);session.flush()
    session.add(m.DefenseEligibilityCheck(thesis_id=second.id,thesis_member_id=member.id,version_no=1,report_version_id=version.id,advisor_review_id=review.id,discipline_status='CLEAR',source_reference='SYNTHETIC',reason='Fixture',state='ELIGIBLE',checked_by=users[4].id,checked_at=now()))
    people=[lecturers[1],lecturers[2]]
    for i in range(3):
        user=m.UserAccount(external_subject='batch-'+uuid4().hex,base_role='LECTURER',status='ACTIVE');session.add(user);session.flush()
        person=m.LecturerProfile(user_id=user.id,department_id=thesis.department_id,lecturer_code='B-'+uuid4().hex[:10],display_name='Synthetic member');session.add(person);session.flush();people.append(person)
    session.commit()
    response=client.post('/api/v1/defense/councils',headers=hdr(users[4]),json={'round_id':str(thesis.round_id),'department_id':str(thesis.department_id),'name':'Batch council','reference':'SYNTHETIC-BATCH','thesis_ids':[str(thesis.id),str(second.id)],'confirmed_no_conflict':True,'members':[{'lecturer_id':str(p.id),'role':r} for p,r in zip(people,['CHAIR','SECRETARY','REVIEWER','REVIEWER','MEMBER'])]})
    assert response.status_code==201,response.text
    council=response.json()['id'];start=now()+timedelta(days=1)
    def item(t,offset):return {'council_id':council,'thesis_id':str(t.id),'starts_at':(start+timedelta(minutes=offset)).isoformat(),'ends_at':(start+timedelta(minutes=offset+45)).isoformat(),'room':'BATCH-A1','confirmed_no_conflict':True}
    failed=client.post('/api/v1/defense/slots-batch',headers=hdr(users[4]),json={'slots':[item(thesis,0),item(second,20)]})
    assert failed.status_code==409,failed.text
    assert session.scalar(select(func.count()).select_from(m.DefenseSlot).where(m.DefenseSlot.council_id==UUID(council)))==0
    response=client.post('/api/v1/defense/slots-batch',headers=hdr(users[4]),json={'slots':[item(thesis,0),item(second,45)]})
    assert response.status_code==201,response.text
    assert len(response.json()['slots'])==2


def test_m6_retains_template_rich_runs_and_styles_only_inserted_note():
    path=form_templates.OFFICIAL_DIR/next(x['filename'] for x in form_templates.OFFICIAL_FORMS if x['id']=='mau-06')
    original=load_workbook(path,rich_text=True).active
    result=defense_templates.score_sheet(path,{'name':'Synthetic student','code':'0026999999','class_name':'CNTT22','major':'Công nghệ thông tin','training_cohort':'2022–2026'}, {'name':'Synthetic lecturer'},'Phản biện','Synthetic thesis','Synthetic advisor',{'scores':['0']*12,'note':'Nội dung kiểm thử'},0,0,False,'SYNTHETIC',defense_templates.PrintLayout(tabs={'note':[9]},field_styles={'note':{'italic':True}}),now())
    out=BytesIO();result.save(out);sheet=load_workbook(BytesIO(out.getvalue()),rich_text=True).active
    for address in ['A1','C1','A2','A12','B18','B19','B25','B26','B28']:
        assert str(sheet[address].value)==str(original[address].value)
        assert copy(sheet[address].font)==copy(original[address].font)
        if isinstance(original[address].value,CellRichText):assert sheet[address].value==original[address].value
    assert '\t' in str(sheet['A30'].value)
    assert sheet['A30'].value[-1].font.i
