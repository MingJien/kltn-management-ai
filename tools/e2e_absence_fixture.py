"""Add a second eligible synthetic member to the isolated defense fixture."""
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import select

from backend.db.models import entities as m
from tools.seed_demo import uid


def add_second_member(session, instant, thesis_id):
    thesis = session.get(m.Thesis, thesis_id)
    student = session.get(m.StudentProfile, uid('student-2'))
    first = session.get(m.StudentProfile, uid('student-1'))
    student.class_name, student.major_code, student.training_cohort = 'LOP-E2E', first.major_code, '2022-2026'
    student.birth_date = date(2004, 4, 20)
    session.get(m.Topic, thesis.topic_id).max_students = 2
    session.get(m.TopicRegistration, thesis.registration_id).expected_member_count = 2
    assignment = session.scalar(select(m.AdvisorAssignment).where(m.AdvisorAssignment.thesis_id == thesis_id))
    report = session.scalar(select(m.DocumentVersion).join(m.Document).where(
        m.Document.thesis_id == thesis_id, m.Document.document_type == 'REPORT'))
    member = m.ThesisMember(id=uuid4(), thesis_id=thesis_id, student_id=student.id,
        is_coordinator=False, joined_at=instant-timedelta(days=2))
    session.add(member); session.flush()
    review = m.ThesisReview(id=uuid4(), thesis_id=thesis_id, thesis_member_id=member.id,
        lecturer_id=assignment.lecturer_id, advisor_assignment_id=assignment.id, report_version_id=report.id,
        kind='ADVISOR', version_no=1, sections={}, thesis_completed=True, allow_defense=True,
        revision_reason='Synthetic review for absent student', state='SUBMITTED', submitted_at=instant-timedelta(hours=1))
    session.add(review); session.flush()
    head = session.get(m.LecturerProfile, uid('lecturer-2'))
    session.add(m.DefenseEligibilityCheck(id=uuid4(), thesis_id=thesis_id, thesis_member_id=member.id,
        version_no=1, report_version_id=report.id, advisor_review_id=review.id, discipline_status='CLEAR',
        source_reference='E2E-ELIGIBILITY-2', reason='Synthetic eligibility check', state='ELIGIBLE',
        checked_by=head.user_id, checked_at=instant))
