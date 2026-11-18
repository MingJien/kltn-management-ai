"""Create a synthetic, already defended thesis for the isolated archive UI test."""
from datetime import timedelta
from uuid import uuid4

from backend.db.models import entities as m
from backend.services import documents
from tools.seed_demo import uid


def add_defended_thesis(session, instant, report_pdf):
    student = session.get(m.StudentProfile, uid("student-1"))
    advisor = session.get(m.LecturerProfile, uid("lecturer-1"))
    head = session.get(m.LecturerProfile, uid("lecturer-2"))
    topic = m.Topic(id=uuid4(), round_id=uid("round"), department_id=student.department_id,
        code="E2E-KHO-001", current_title="Ứng dụng tra cứu khóa luận", proposer_type="LECTURER",
        proposer_user_id=advisor.user_id, receiving_lecturer_id=advisor.id, max_students=1, state="LOCKED")
    session.add(topic)
    session.flush()
    registration = m.TopicRegistration(id=uuid4(), topic_id=topic.id, round_id=topic.round_id,
        created_by=student.id, expected_member_count=1, state="FINALIZED")
    session.add(registration)
    session.flush()
    thesis = m.Thesis(id=uuid4(), topic_id=topic.id, round_id=topic.round_id, registration_id=registration.id,
        department_id=topic.department_id, current_title=topic.current_title, state="DEFENDED")
    session.add(thesis)
    session.flush()
    member = m.ThesisMember(id=uuid4(), thesis_id=thesis.id, student_id=student.id,
        is_coordinator=True, joined_at=instant-timedelta(days=2))
    session.add_all([member, m.AdvisorAssignment(thesis_id=thesis.id, lecturer_id=advisor.id,
        assigned_by=head.user_id, effective_from=instant-timedelta(days=2))])
    report = m.Document(id=uuid4(), thesis_id=thesis.id, document_type="REPORT",
        title="Báo cáo đã dùng bảo vệ", visibility="ASSIGNED", state="ACTIVE")
    stored, digest, path = documents.persist_upload(session, "bao-cao-bao-ve.pdf", report_pdf, "application/pdf")
    documents.file_scanner.scan(stored, path)
    documents.require_clean(stored, "chuẩn bị báo cáo kiểm thử")
    session.add(report)
    session.flush()
    version = m.DocumentVersion(id=uuid4(), document_id=report.id, version_no=1, stored_file_id=stored.id,
        submitted_by=student.id, submitted_at=instant-timedelta(days=1), content_sha256=digest, state="FINAL")
    council = m.DefenseCouncil(id=uuid4(), round_id=thesis.round_id, department_id=thesis.department_id,
        name="Hội đồng kiểm thử nộp lưu", reference="E2E-KHO", members=[], created_by=head.user_id, closed_at=instant)
    session.add_all([version, council])
    session.flush()
    roster = [{"id":str(member.id), "student_id":str(student.id), "name":student.display_name, "code":student.student_code,
               "class_name":"LỚP E2E"}]
    attendance = {"status":"PRESENT", "bonus":"0"}
    session.add(m.DefenseSlot(thesis_id=thesis.id, council_id=council.id, report_version_id=version.id,
        starts_at=instant-timedelta(hours=2), ends_at=instant-timedelta(hours=1), room="Phòng kiểm thử",
        roster=roster, marks={}, attendance={str(member.id):attendance}, finalized_at=instant, finalized_by=head.user_id,
        minutes={"title":thesis.current_title, "classifications":{str(member.id):"Giỏi"},
                 "results_snapshot":{str(member.id):{"attendance":attendance,"scores":["8.2"],"average":"8.2"}}}))
    return thesis.id
