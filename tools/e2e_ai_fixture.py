"""Create two synthetic reports for real UI similarity checks in an isolated schema."""
from datetime import timedelta
from io import BytesIO
from uuid import uuid4

from docx import Document as WordDocument
from PIL import Image, ImageDraw, ImageFont

from backend.db.models import entities as m
from backend.services import documents
from tools.seed_demo import uid


def add_report_pair(session, instant):
    phrases = [
        "Hệ thống quản lý khóa luận tốt nghiệp",
        "Phân tích dữ liệu và đánh giá kết quả",
        "Sinh viên trình bày phương pháp nghiên cứu",
    ]
    try:
        font = ImageFont.truetype("arial.ttf", 44)
    except OSError:
        font = ImageFont.truetype("DejaVuSans.ttf", 44)
    picture = Image.new("RGB", (1400, 440), "white")
    painter = ImageDraw.Draw(picture)
    for index, line in enumerate(phrases):
        painter.text((80, 80 + index * 90), line, font=font, fill="black")
    scan, png = BytesIO(), BytesIO()
    picture.save(scan, "PDF", resolution=180)
    picture.save(png, "PNG")
    word = WordDocument()
    word.add_paragraph(" ".join(phrases))
    word.add_picture(BytesIO(png.getvalue()))
    docx = BytesIO()
    word.save(docx)

    for number, (name, content, mime) in enumerate([
        ("scan-e2e.pdf", scan.getvalue(), "application/pdf"),
        ("chu-va-anh-e2e.docx", docx.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ], 1):
        student = session.get(m.StudentProfile, uid(f"student-{number}"))
        advisor = session.get(m.LecturerProfile, uid("lecturer-1"))
        topic = m.Topic(id=uuid4(), round_id=uid("round"), department_id=student.department_id,
            code=f"E2E-OCR-{number}", current_title=f"Đối chiếu báo cáo OCR {number}",
            proposer_type="LECTURER", proposer_user_id=advisor.user_id, receiving_lecturer_id=advisor.id,
            max_students=1, state="LOCKED")
        session.add(topic); session.flush()
        registration = m.TopicRegistration(id=uuid4(), topic_id=topic.id, round_id=topic.round_id,
            created_by=student.id, expected_member_count=1, state="FINALIZED")
        session.add(registration); session.flush()
        thesis = m.Thesis(id=uuid4(), topic_id=topic.id, round_id=topic.round_id, registration_id=registration.id,
            department_id=student.department_id, current_title=topic.current_title, state="IN_PROGRESS")
        session.add(thesis); session.flush()
        session.add(m.ThesisMember(id=uuid4(), thesis_id=thesis.id, student_id=student.id,
            is_coordinator=True, joined_at=instant-timedelta(days=1)))
        report = m.Document(id=uuid4(), thesis_id=thesis.id, document_type="REPORT",
            title=f"Báo cáo đối chiếu OCR {number}", visibility="ASSIGNED", state="ACTIVE")
        stored, digest, path = documents.persist_upload(session, name, content, mime)
        documents.file_scanner.scan(stored, path)
        documents.require_clean(stored, "chuẩn bị báo cáo thử đối chiếu")
        session.add(report); session.flush()
        session.add(m.DocumentVersion(id=uuid4(), document_id=report.id, version_no=1,
            stored_file_id=stored.id, submitted_by=student.id, submitted_at=instant,
            content_sha256=digest, state="FINAL"))
