"""Versioned progress submissions and individual work evidence."""
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from backend.api.core_schemas import MilestoneOut, ProgressOut, ReviewOut, WorkOut
from backend.db.models import entities as m
from backend.services.documents import require_clean
from backend.services.registration import profile, row_version
from backend.services.theses import audit, eligible_lecturer, now, rights, thesis_access


def milestones(session, thesis):
    return session.scalars(select(m.ProgressMilestone).where(m.ProgressMilestone.round_id == thesis.round_id)
        .order_by(m.ProgressMilestone.due_at, m.ProgressMilestone.code, m.ProgressMilestone.version_no)).all()


def milestone_out(item):
    return MilestoneOut(id=item.id, code=item.code, title=item.title, version_no=item.version_no,
        row_version=item.row_version, state=item.state, due_at=item.due_at, expected_ratio=item.expected_ratio)


def create_milestone(session, user, thesis_id, data):
    thesis = thesis_access(session, user, thesis_id, action="milestone:manage", write=True)
    round_ = session.scalar(select(m.ThesisRound).where(m.ThesisRound.id == thesis.round_id).with_for_update())
    if round_.state == "ARCHIVED":
        raise HTTPException(409, "Đợt đã lưu trữ")
    previous = session.scalar(select(m.ProgressMilestone).where(m.ProgressMilestone.round_id == thesis.round_id,
        m.ProgressMilestone.code == data.code).order_by(m.ProgressMilestone.version_no.desc()).limit(1))
    if previous and previous.state == "OPEN":
        raise HTTPException(409, "Đóng phiên bản mốc đang mở trước khi ban hành phiên bản mới")
    item = m.ProgressMilestone(id=uuid4(), round_id=thesis.round_id, code=data.code, title=data.title,
        due_at=data.due_at, expected_ratio=data.expected_ratio, source_type="ROUND_POLICY",
        version_no=previous.version_no + 1 if previous else 1, state="OPEN")
    session.add(item)
    audit(session, user, "MILESTONE_OPENED", "round", thesis.round_id, f"{data.code}: {data.title}")
    session.flush()
    result = milestone_out(item)
    session.commit()
    return result


def close_milestone(session, user, thesis_id, milestone_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="milestone:manage", write=True)
    session.scalar(select(m.ThesisRound).where(m.ThesisRound.id == thesis.round_id).with_for_update())
    item = session.scalar(select(m.ProgressMilestone).where(m.ProgressMilestone.id == milestone_id,
        m.ProgressMilestone.round_id == thesis.round_id).with_for_update())
    if not item:
        raise HTTPException(404, "Không tìm thấy mốc trong đợt này")
    row_version(expected, item.row_version)
    if item.state != "OPEN":
        raise HTTPException(409, "Mốc đã đóng")
    item.state = "CLOSED"
    item.row_version += 1
    audit(session, user, "MILESTONE_CLOSED", "round", thesis.round_id, f"{item.code}: {data.reason}")
    session.flush()
    result = milestone_out(item)
    session.commit()
    return result


def extend_milestone(session, user, thesis_id, milestone_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="milestone:manage", write=True)
    round_ = session.scalar(select(m.ThesisRound).where(m.ThesisRound.id == thesis.round_id).with_for_update())
    if round_.state == "ARCHIVED":
        raise HTTPException(409, "Đợt đã lưu trữ")
    item = session.scalar(select(m.ProgressMilestone).where(m.ProgressMilestone.id == milestone_id,
        m.ProgressMilestone.round_id == thesis.round_id).with_for_update())
    if not item:
        raise HTTPException(404, "Không tìm thấy mốc trong đợt này")
    row_version(expected, item.row_version)
    if item.state != "OPEN" or item.due_at is None:
        raise HTTPException(409, "Chỉ gia hạn mốc đang mở và đã có hạn nộp")
    if data.due_at <= item.due_at or data.due_at <= now():
        raise HTTPException(422, "Hạn mới phải sau hạn cũ và sau thời điểm hiện tại")
    old_due = item.due_at
    item.due_at = data.due_at
    item.row_version += 1
    audit(session, user, "MILESTONE_EXTENDED", "round", thesis.round_id,
        f"{item.code}: {old_due.isoformat()} -> {data.due_at.isoformat()}; {data.reason}")
    session.flush()
    result = milestone_out(item)
    session.commit()
    return result


def progress_out(session, item):
    reviews = session.scalars(select(m.ProgressReview).where(m.ProgressReview.progress_report_id == item.id)
        .order_by(m.ProgressReview.created_at, m.ProgressReview.id)).all()
    version = session.scalar(select(m.DocumentVersion.id).join(m.Document, m.Document.id == m.DocumentVersion.document_id)
        .where(m.Document.thesis_id == item.thesis_id, m.DocumentVersion.stored_file_id == item.evidence_file_id)
        .limit(1)) if item.evidence_file_id else None
    return ProgressOut(id=item.id, milestone_id=item.milestone_id, version_no=item.version_no,
        row_version=item.row_version, state=item.state, summary=item.summary, reported_ratio=item.reported_ratio,
        submitted_by_name=session.get(m.StudentProfile, item.submitted_by).display_name, submitted_at=item.created_at,
        due_at_at_submission=item.due_at_at_submission,
        late=bool(item.due_at_at_submission and item.created_at > item.due_at_at_submission), evidence_document_version_id=version,
        reviews=[ReviewOut(reviewer_name=session.get(m.LecturerProfile, review.reviewer_id).display_name,
            decision=review.decision, comment=review.comment, created_at=review.created_at) for review in reviews])


def create_progress(session, user, thesis_id, data):
    thesis = thesis_access(session, user, thesis_id, action="progress:submit", lock=True, write=True)
    milestone = session.scalar(select(m.ProgressMilestone).where(m.ProgressMilestone.id == data.milestone_id,
        m.ProgressMilestone.round_id == thesis.round_id).with_for_update())
    if not milestone or milestone.state != "OPEN":
        raise HTTPException(409, "Mốc phải đang mở và thuộc đúng đợt khóa luận")
    latest = session.scalar(select(m.ProgressReport).where(m.ProgressReport.thesis_id == thesis.id,
        m.ProgressReport.milestone_id == milestone.id).order_by(m.ProgressReport.version_no.desc()).limit(1))
    if latest and latest.state != "REVISION_REQUIRED":
        raise HTTPException(409, "Chỉ nộp bản mới khi GVHD yêu cầu sửa báo cáo trước")
    file_id = None
    if data.document_version_id:
        version = session.scalar(select(m.DocumentVersion).join(m.Document, m.Document.id == m.DocumentVersion.document_id)
            .where(m.DocumentVersion.id == data.document_version_id, m.Document.thesis_id == thesis.id,
                m.Document.state == "ACTIVE", m.DocumentVersion.state != "DRAFT"))
        file = session.get(m.StoredFile, version.stored_file_id) if version else None
        if not file:
            raise HTTPException(422, "Minh chứng phải là phiên bản tài liệu hợp lệ của khóa luận này")
        require_clean(file, "dùng làm minh chứng")
        file_id = file.id
    student = profile(session, user, "STUDENT")
    item = m.ProgressReport(id=uuid4(), thesis_id=thesis.id, milestone_id=milestone.id,
        version_no=latest.version_no + 1 if latest else 1, summary=data.summary,
        reported_ratio=data.reported_ratio, submitted_by=student.id, evidence_file_id=file_id,
        due_at_at_submission=milestone.due_at, created_at=now(), state="SUBMITTED")
    session.add(item)
    audit(session, user, "PROGRESS_SUBMITTED", "thesis", thesis.id, milestone.code)
    session.flush()
    result = progress_out(session, item)
    session.commit()
    return result


def review_progress(session, user, thesis_id, report_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, lock=True, write=True)
    permissions = rights(session, user, thesis)
    if data.decision == "COMMENT_ONLY" and "progress:comment" not in permissions:
        raise HTTPException(403, "Góp ý chéo cần phân công riêng; GVHD chính chọn xác nhận hoặc yêu cầu sửa")
    if "progress:review" not in permissions and not (data.decision == "COMMENT_ONLY" and "progress:comment" in permissions):
        raise HTTPException(403, "Chỉ GVHD chính được xác nhận/yêu cầu sửa; người góp ý chéo chỉ nhận xét")
    report = session.scalar(select(m.ProgressReport).where(m.ProgressReport.id == report_id,
        m.ProgressReport.thesis_id == thesis.id).with_for_update())
    if not report:
        raise HTTPException(404, "Không tìm thấy báo cáo")
    row_version(expected, report.row_version)
    latest = session.scalar(select(func.max(m.ProgressReport.version_no)).where(m.ProgressReport.thesis_id == thesis.id,
        m.ProgressReport.milestone_id == report.milestone_id))
    if report.version_no != latest or report.state != "SUBMITTED":
        raise HTTPException(409, "Chỉ nhận xét phiên bản mới nhất đang chờ duyệt")
    lecturer = profile(session, user, "LECTURER")
    if session.scalar(select(m.ProgressReview.id).where(m.ProgressReview.progress_report_id == report.id,
            m.ProgressReview.reviewer_id == lecturer.id)):
        raise HTTPException(409, "Bạn đã gửi nhận xét cho phiên bản này")
    session.add(m.ProgressReview(id=uuid4(), progress_report_id=report.id, reviewer_id=lecturer.id,
        decision=data.decision, comment=data.comment))
    if data.decision != "COMMENT_ONLY":
        report.state = "CONFIRMED" if data.decision == "CONFIRM" else "REVISION_REQUIRED"
    report.row_version += 1
    audit(session, user, "PROGRESS_" + data.decision, "thesis", thesis.id, data.comment)
    session.flush()
    result = progress_out(session, report)
    session.commit()
    return result


def assign_cross_reviewer(session, user, thesis_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="progress:assign_reviewer", lock=True, write=True)
    row_version(expected, thesis.row_version)
    lecturer = eligible_lecturer(session, data.lecturer_id, thesis.department_id)
    from backend.services.theses import primary_advisor, resource_role
    advisor = primary_advisor(session, thesis.id)
    if advisor and advisor.lecturer_id == lecturer.id:
        raise HTTPException(422, "GVHD chính không đồng thời là người góp ý chéo")
    if resource_role(session, lecturer.user_id, "PROGRESS_REVIEWER", thesis_id=thesis.id):
        raise HTTPException(409, "Giảng viên đã được phân công góp ý chéo")
    session.add(m.ResourceAssignment(id=uuid4(), user_id=lecturer.user_id, thesis_id=thesis.id,
        assignment_type="PROGRESS_REVIEWER", state="ACTIVE", effective_from=now()))
    thesis.row_version += 1
    audit(session, user, "PROGRESS_REVIEWER_ASSIGNED", "thesis", thesis.id, f"{lecturer.lecturer_code}: {data.reason}")
    session.commit()


def work_out(session, item):
    member = session.get(m.ThesisMember, item.thesis_member_id)
    student = session.get(m.StudentProfile, member.student_id)
    return WorkOut(id=item.id, student_id=student.id, student_name=student.display_name,
        version_no=item.version_no, row_version=item.row_version, work_description=item.work_description,
        expected_output=item.expected_output, state=item.state, review_comment=item.review_comment,
        reviewed_by_name=session.get(m.LecturerProfile, item.reviewed_by).display_name if item.reviewed_by else None)


def revoke_cross_reviewer(session, user, thesis_id, lecturer_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="progress:assign_reviewer", lock=True, write=True)
    row_version(expected, thesis.row_version)
    lecturer = session.get(m.LecturerProfile, lecturer_id)
    from backend.services.theses import resource_role
    assignment = resource_role(session, lecturer.user_id, "PROGRESS_REVIEWER", thesis_id=thesis.id) if lecturer else None
    if not assignment:
        raise HTTPException(404, "Không tìm thấy phân công góp ý chéo")
    assignment.state = "REVOKED"
    assignment.effective_to = now()
    thesis.row_version += 1
    audit(session, user, "PROGRESS_REVIEWER_REVOKED", "thesis", thesis.id, f"{lecturer.lecturer_code}: {data.reason}")
    session.commit()


def create_work(session, user, thesis_id, data):
    thesis = thesis_access(session, user, thesis_id, action="work:submit", lock=True, write=True)
    student = profile(session, user, "STUDENT")
    member = session.scalar(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.student_id == data.student_id, m.ThesisMember.active.is_(True)))
    coordinator = session.scalar(select(m.ThesisMember.id).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.student_id == student.id, m.ThesisMember.active.is_(True), m.ThesisMember.is_coordinator.is_(True)))
    if not member or (data.student_id != student.id and not coordinator):
        raise HTTPException(403, "Chỉ khai phần việc của mình hoặc nhóm trưởng khai cho thành viên đang hoạt động")
    latest = session.scalar(select(m.MemberWorkAssignment).where(m.MemberWorkAssignment.thesis_member_id == member.id)
        .order_by(m.MemberWorkAssignment.version_no.desc()).limit(1))
    if latest and latest.state == "SUBMITTED":
        raise HTTPException(409, "Phân công trước đang chờ GVHD duyệt")
    item = m.MemberWorkAssignment(id=uuid4(), thesis_member_id=member.id,
        version_no=latest.version_no + 1 if latest else 1, work_description=data.work_description,
        expected_output=data.expected_output, state="SUBMITTED")
    session.add(item)
    audit(session, user, "WORK_SUBMITTED", "thesis", thesis.id, student.student_code)
    session.flush()
    result = work_out(session, item)
    session.commit()
    return result


def review_work(session, user, thesis_id, work_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="work:review", lock=True, write=True)
    item = session.scalar(select(m.MemberWorkAssignment).join(m.ThesisMember, m.ThesisMember.id == m.MemberWorkAssignment.thesis_member_id)
        .where(m.MemberWorkAssignment.id == work_id, m.ThesisMember.thesis_id == thesis.id).with_for_update())
    if not item:
        raise HTTPException(404, "Không tìm thấy phân công")
    row_version(expected, item.row_version)
    latest = session.scalar(select(func.max(m.MemberWorkAssignment.version_no)).where(m.MemberWorkAssignment.thesis_member_id == item.thesis_member_id))
    if item.state != "SUBMITTED" or item.version_no != latest:
        raise HTTPException(409, "Chỉ duyệt bản phân công mới nhất đang chờ")
    item.state = "APPROVED" if data.decision == "APPROVE" else "REVISION_REQUIRED"
    item.reviewed_by = profile(session, user, "LECTURER").id
    item.reviewed_at = now()
    item.review_comment = data.comment
    item.row_version += 1
    audit(session, user, "WORK_" + data.decision, "thesis", thesis.id, data.comment)
    session.flush()
    result = work_out(session, item)
    session.commit()
    return result
