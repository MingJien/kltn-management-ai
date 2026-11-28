"""Prepare a synthetic eligible thesis and council candidates in an isolated E2E schema."""
from datetime import timedelta
from uuid import uuid4
import secrets

from sqlalchemy import select
from backend.db.models import entities as m
from backend.services import documents
from backend.services.passwords import hash_password
from tools.seed_demo import uid


def add_council_candidates(session, instant, accounts):
    head = session.get(m.LecturerProfile, uid('lecturer-2'))
    for index in range(3):
        key = 'council' + str(index + 1)
        password = secrets.token_urlsafe(20)
        user = m.UserAccount(id=uuid4(), email=key+'@e2e.test', password_hash=hash_password(password),
            email_verified_at=instant, base_role='LECTURER', status='ACTIVE')
        session.add(user); session.flush()
        session.add(m.LecturerProfile(id=uuid4(), user_id=user.id, department_id=head.department_id,
            lecturer_code='E2E-HD-'+str(index+1), display_name='GV Hội đồng '+str(index+1)))
        accounts[key] = {'email': user.email, 'password': password}


def add_ready_thesis(session, instant, report_pdf, accounts):
    student = session.get(m.StudentProfile, uid('student-1'))
    advisor = session.get(m.LecturerProfile, uid('lecturer-1'))
    head = session.get(m.LecturerProfile, uid('lecturer-2'))
    session.add(m.ResourceAssignment(id=uuid4(), user_id=head.user_id, round_id=uid('round'),
        assignment_type='KLTN_COORDINATOR', state='ACTIVE', effective_from=instant-timedelta(days=1)))
    major = session.scalar(select(m.DepartmentMajor).where(m.DepartmentMajor.department_id == student.department_id,
        m.DepartmentMajor.active.is_(True), ~m.DepartmentMajor.name.startswith('Chưa xác minh')).limit(1))
    if not major:
        raise RuntimeError('The isolated demo needs an active major')
    student.class_name, student.major_code, student.training_cohort = 'LOP-E2E', major.code, '2022-2026'
    from datetime import date
    student.birth_date = date(2004, 3, 15)
    add_council_candidates(session, instant, accounts)
    topic = m.Topic(id=uuid4(), round_id=uid('round'), department_id=student.department_id,
        code='E2E-DEFENSE-LIVE', current_title='Hội đồng kiểm thử thực tế', proposer_type='LECTURER',
        proposer_user_id=advisor.user_id, receiving_lecturer_id=advisor.id, max_students=1, state='LOCKED')
    session.add(topic); session.flush()
    registration = m.TopicRegistration(id=uuid4(), topic_id=topic.id, round_id=topic.round_id,
        created_by=student.id, expected_member_count=1, state='FINALIZED')
    session.add(registration); session.flush()
    thesis = m.Thesis(id=uuid4(), topic_id=topic.id, round_id=topic.round_id, registration_id=registration.id,
        department_id=student.department_id, current_title=topic.current_title, state='READY_FOR_DEFENSE')
    session.add(thesis); session.flush()
    member = m.ThesisMember(id=uuid4(), thesis_id=thesis.id, student_id=student.id,
        is_coordinator=True, joined_at=instant-timedelta(days=2))
    assignment = m.AdvisorAssignment(id=uuid4(), thesis_id=thesis.id, lecturer_id=advisor.id,
        assigned_by=head.user_id, effective_from=instant-timedelta(days=2))
    session.add_all([member, assignment]); session.flush()
    report = m.Document(id=uuid4(), thesis_id=thesis.id, document_type='REPORT',
        title='Báo cáo bảo vệ kiểm thử', visibility='ASSIGNED', state='ACTIVE')
    stored, digest, path = documents.persist_upload(session, 'bao-cao-e2e.pdf', report_pdf, 'application/pdf')
    documents.file_scanner.scan(stored, path)
    documents.require_clean(stored, 'chuẩn bị báo cáo kiểm thử')
    session.add(report); session.flush()
    version = m.DocumentVersion(id=uuid4(), document_id=report.id, version_no=1, stored_file_id=stored.id,
        submitted_by=student.id, submitted_at=instant-timedelta(days=1), content_sha256=digest, state='FINAL')
    session.add(version); session.flush()
    review = m.ThesisReview(id=uuid4(), thesis_id=thesis.id, thesis_member_id=member.id,
        lecturer_id=advisor.id, advisor_assignment_id=assignment.id, report_version_id=version.id,
        kind='ADVISOR', version_no=1, sections={}, thesis_completed=True, allow_defense=True,
        revision_reason='Synthetic review', state='SUBMITTED', submitted_at=instant-timedelta(hours=1))
    session.add(review); session.flush()
    session.add(m.DefenseEligibilityCheck(id=uuid4(), thesis_id=thesis.id, thesis_member_id=member.id,
        version_no=1, report_version_id=version.id, advisor_review_id=review.id, discipline_status='CLEAR',
        source_reference='E2E-ELIGIBILITY', reason='Synthetic eligibility check', state='ELIGIBLE',
        checked_by=head.user_id, checked_at=instant))
    return thesis.id
