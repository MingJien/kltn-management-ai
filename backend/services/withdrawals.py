"""On-system withdrawal decisions with an audit history."""
from datetime import datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import workflow_notices as notices
from backend.services.registration import profile, row_version
from backend.services.theses import EDITABLE, audit, effective, now, primary_advisor, resource_role

VN = ZoneInfo("Asia/Ho_Chi_Minh")
OPEN = {"SUBMITTED", "ADVISOR_CONFIRMED"}


def coordinators(session, round_id):
    return set(session.scalars(select(m.ResourceAssignment.user_id).where(
        m.ResourceAssignment.round_id == round_id,
        m.ResourceAssignment.assignment_type == "KLTN_COORDINATOR", effective(m.ResourceAssignment))))


def can_record(session, user, thesis):
    return user.base_role == "LECTURER" and bool(resource_role(session, user.id, "KLTN_COORDINATOR", round_id=thesis.round_id))


def can_view(session, user, item):
    thesis = session.get(m.Thesis, item.thesis_id)
    return bool(thesis and (session.get(m.StudentProfile, item.student_id).user_id == user.id
        or can_record(session, user, thesis)))


def get(session, user, identifier, *, lock=False):
    query = select(m.ThesisWithdrawalRequest).where(m.ThesisWithdrawalRequest.id == identifier)
    item = session.scalar(query.with_for_update() if lock else query)
    if not item or not can_view(session, user, item):
        raise HTTPException(404, "Không tìm thấy yêu cầu xin thôi trong phạm vi của bạn")
    return item


def deadline(starts_on):
    # Fourteen calendar days, including the start date, in Vietnam time.
    return datetime.combine(starts_on + timedelta(days=14), time.min, VN)


def code(item):
    return "RUT-" + item.submitted_at.astimezone(VN).strftime("%Y") + "-" + item.id.hex.upper()


def output(session, user, item):
    thesis = session.get(m.Thesis, item.thesis_id)
    student = session.get(m.StudentProfile, item.student_id)
    history = session.scalars(select(m.AuditEvent).where(
        m.AuditEvent.resource_type == "thesis_withdrawal_request", m.AuditEvent.resource_id == item.id)
        .order_by(m.AuditEvent.occurred_at, m.AuditEvent.id)).all()
    return {"id": item.id, "code": code(item), "thesis_id": thesis.id, "title": item.application_data["title"],
        "student_name": student.display_name, "student_code": student.student_code,
        "advisor_name": item.application_data.get("advisor_name"),
        "state": item.state, "reason": item.reason, "submitted_at": item.submitted_at,
        "row_version": item.row_version, "outcome_note": item.outcome_note,
        "effective_on": item.effective_on, "recorded_at": item.recorded_at,
        "can_cancel": user.id == student.user_id and item.state in OPEN,
        "can_record": can_record(session, user, thesis) and item.state in OPEN and thesis.state in EDITABLE,
        "history": [{"action": h.action, "at": h.occurred_at,
            "actor": notices.actor_name(session, h.actor_id)} for h in history]}


def competing_request_message(session, thesis):
    from backend.services.thesis_changes import open_request
    from backend.services.thesis_extensions import pending as pending_extension

    if open_request(session, thesis):
        return "Hủy hoặc xử lý yêu cầu đổi đề tài trước khi gửi xin thôi"
    if pending_extension(session, thesis.id):
        return "Hủy hoặc xử lý yêu cầu gia hạn trước khi gửi xin thôi"
    return None


def workspace(session, user):
    if user.base_role not in {"STUDENT", "LECTURER"}:
        raise HTTPException(403, "Luồng xin thôi dành cho SV và điều phối KLTN được giao")
    own_student = profile(session, user, "STUDENT") if user.base_role == "STUDENT" else None
    managed = set(session.scalars(select(m.ResourceAssignment.round_id).where(
        m.ResourceAssignment.user_id == user.id, m.ResourceAssignment.assignment_type == "KLTN_COORDINATOR",
        effective(m.ResourceAssignment)))) if user.base_role == "LECTURER" else set()
    # Filter in SQL before loading reasons/files; no list of another student's request.
    predicate = m.ThesisWithdrawalRequest.student_id == own_student.id if own_student else (
        m.ThesisWithdrawalRequest.thesis_id.in_(select(m.Thesis.id).where(m.Thesis.round_id.in_(managed))))
    items = session.scalars(select(m.ThesisWithdrawalRequest).where(predicate)
        .order_by(m.ThesisWithdrawalRequest.submitted_at.desc())).all()
    theses = []
    if own_student:
        rows = session.scalars(select(m.Thesis).join(m.ThesisMember, m.ThesisMember.thesis_id == m.Thesis.id)
            .where(m.ThesisMember.student_id == own_student.id, m.ThesisMember.active.is_(True))).all()
        for thesis in rows:
            round_ = session.get(m.ThesisRound, thesis.round_id)
            start = round_.execution_starts_on
            in_window = bool(start and datetime.combine(start, time.min, VN) <= now() < deadline(start))
            blocked = bool(session.scalar(select(m.ThesisWithdrawalRequest.id).where(
                m.ThesisWithdrawalRequest.student_id == own_student.id,
                m.ThesisWithdrawalRequest.state == "RECORDED").limit(1)))
            pending = any(i.thesis_id == thesis.id and i.state in OPEN for i in items)
            can_submit = thesis.state in EDITABLE and in_window and not pending and not blocked
            message = "" if can_submit else "Đang có yêu cầu chờ xử lý" if pending else (
                "Khoa chưa ghi nhận ngày bắt đầu thực hiện" if not start else
                "Ngoài thời hạn 02 tuần; liên hệ đơn vị phụ trách. Hồ sơ KLTN chưa tự động bị hủy." if not in_window else
                "Hồ sơ đã chốt đủ điều kiện bảo vệ; liên hệ TBM mở xét lại trước khi xử lý thay đổi thành viên." if thesis.state == "READY_FOR_DEFENSE" else
                "Khóa luận hoặc quyền đăng ký không còn cho phép xin thôi theo luồng này")
            if can_submit:
                message = competing_request_message(session, thesis) or ""
                can_submit = not message
            advisor = primary_advisor(session, thesis.id)
            lecturer = session.get(m.LecturerProfile, advisor.lecturer_id) if advisor else None
            theses.append({"id": thesis.id, "title": thesis.current_title, "round_id": round_.id,
                "student_name": own_student.display_name, "advisor_name": lecturer.display_name if lecturer else None,
                "round_code": round_.code, "starts_on": start,
                "last_request_on": start + timedelta(days=13) if start else None,
                "can_submit": can_submit, "message": message})
    rounds = []
    for round_ in session.scalars(select(m.ThesisRound).where(m.ThesisRound.id.in_(managed)).order_by(m.ThesisRound.opens_at.desc())):
        has_requests = bool(session.scalar(select(m.ThesisWithdrawalRequest.id).join(m.Thesis,
            m.Thesis.id == m.ThesisWithdrawalRequest.thesis_id).where(m.Thesis.round_id == round_.id).limit(1)))
        has_requests = has_requests or bool(session.scalar(select(m.ThesisChangeRequest.id).join(m.Thesis,
            m.Thesis.id == m.ThesisChangeRequest.thesis_id).where(m.Thesis.round_id == round_.id).limit(1)))
        rounds.append({"id": round_.id, "code": round_.code, "starts_on": round_.execution_starts_on,
            "reference": round_.execution_start_reference, "row_version": round_.row_version,
            "can_edit": not has_requests and round_.state != "ARCHIVED"})
    return {"requests": [output(session, user, i) for i in items], "theses": theses, "rounds": rounds}


def set_start(session, user, round_id, data, expected):
    round_ = session.scalar(select(m.ThesisRound).where(m.ThesisRound.id == round_id).with_for_update())
    if not round_ or user.base_role != "LECTURER" or not resource_role(session, user.id, "KLTN_COORDINATOR", round_id=round_id):
        raise HTTPException(403, "Chỉ điều phối được giao cho đợt mới ghi nhận ngày bắt đầu")
    row_version(expected, round_.row_version)
    changes = session.scalar(select(m.ThesisChangeRequest.id).join(m.Thesis,
        m.Thesis.id == m.ThesisChangeRequest.thesis_id).where(m.Thesis.round_id == round_id).limit(1))
    if changes or round_.state == "ARCHIVED" or session.scalar(select(m.ThesisWithdrawalRequest.id).join(m.Thesis,
            m.Thesis.id == m.ThesisWithdrawalRequest.thesis_id).where(m.Thesis.round_id == round_id).limit(1)):
        raise HTTPException(409, "Đã có yêu cầu đổi/xin thôi hoặc đợt đã lưu trữ; không đổi ngày dùng tính hạn")
    previous = round_.execution_starts_on
    round_.execution_starts_on, round_.execution_start_reference = data.starts_on, data.reference
    round_.row_version += 1
    audit(session, user, "WITHDRAWAL_START_RECORDED", "thesis_round", round_id,
        f"{previous} → {data.starts_on}; {data.reference}")
    session.commit()
    return workspace(session, user)


def notify(session, user, item, event, text, recipients=None):
    thesis = session.get(m.Thesis, item.thesis_id)
    student = session.get(m.StudentProfile, item.student_id)
    if recipients is None:
        recipients = coordinators(session, thesis.round_id) | {student.user_id}
    notices.emit(session, user.id, recipients, event, "thesis_withdrawal_request", item.id,
        f"{student.display_name}: {text} · {thesis.current_title}", f"/withdrawals?focus={item.id}")


def create(session, user, thesis_id, data):
    student = profile(session, user, "STUDENT")
    # Serialize with topic-registration checks and other requests by this student.
    session.scalar(select(m.StudentProfile).where(m.StudentProfile.id == student.id).with_for_update())
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == thesis_id).with_for_update())
    if not thesis or not session.scalar(select(m.ThesisMember.id).where(
        m.ThesisMember.thesis_id == thesis_id, m.ThesisMember.student_id == student.id, m.ThesisMember.active.is_(True))):
        raise HTTPException(404, "Bạn không phải thành viên đang thực hiện khóa luận này")
    if thesis.state not in EDITABLE:
        raise HTTPException(409, "Khóa luận đã khóa hoặc đã chuyển sang giai đoạn bảo vệ")
    conflict = competing_request_message(session, thesis)
    if conflict:
        raise HTTPException(409, conflict)
    round_ = session.scalar(select(m.ThesisRound).where(m.ThesisRound.id == thesis.round_id).with_for_update())
    if not round_.execution_starts_on:
        raise HTTPException(409, "Khoa chưa ghi nhận ngày bắt đầu thực hiện theo kế hoạch")
    if not datetime.combine(round_.execution_starts_on, time.min, VN) <= now() < deadline(round_.execution_starts_on):
        raise HTTPException(409, "Ngoài 02 tuần đầu; liên hệ đơn vị phụ trách. Hệ thống không tự hủy đăng ký hay gán điểm F.")
    if session.scalar(select(m.ThesisWithdrawalRequest.id).where(
        m.ThesisWithdrawalRequest.student_id == student.id,
        m.ThesisWithdrawalRequest.state.in_([*OPEN, "RECORDED"])).limit(1)):
        raise HTTPException(409, "Đang có yêu cầu chờ xử lý hoặc đã ghi nhận xin thôi chính thức")
    advisor = primary_advisor(session, thesis.id)
    lecturer = session.get(m.LecturerProfile, advisor.lecturer_id) if advisor else None
    item = m.ThesisWithdrawalRequest(id=uuid4(), thesis_id=thesis.id, student_id=student.id,
        reason=data.reason, submitted_at=now(), execution_starts_on=round_.execution_starts_on, state="SUBMITTED",
        application_data={"title": thesis.current_title, "student_name": student.display_name,
            "student_code": student.student_code, "class_name": student.class_name or "",
            "advisor_name": lecturer.display_name if lecturer else "", "round_code": round_.code,
            "department": session.get(m.Department, thesis.department_id).name})
    session.add(item)
    session.flush()
    audit(session, user, "WITHDRAWAL_SUBMITTED", "thesis_withdrawal_request", item.id, data.reason)
    notify(session, user, item, "WITHDRAWAL_SUBMITTED", "đã gửi yêu cầu xin thôi KLTN, chờ điều phối đợt xử lý")
    session.commit()
    return output(session, user, item)


def cancel(session, user, identifier, expected):
    item = get(session, user, identifier, lock=True)
    row_version(expected, item.row_version)
    if session.get(m.StudentProfile, item.student_id).user_id != user.id or item.state not in OPEN:
        raise HTTPException(409, "Chỉ người gửi được hủy đơn khi yêu cầu còn chờ xử lý")
    item.state, item.row_version = "CANCELLED", item.row_version + 1
    audit(session, user, "WITHDRAWAL_CANCELLED", "thesis_withdrawal_request", item.id, "SV hủy yêu cầu; không rút khỏi KLTN")
    notify(session, user, item, "WITHDRAWAL_CANCELLED", "đã hủy yêu cầu xin thôi; tiếp tục thực hiện KLTN")
    session.commit()
    return output(session, user, item)


def record(session, user, identifier, data, expected):
    item = get(session, user, identifier, lock=True)
    # Same lock order as registration: student -> thesis; the request row is unique per student.
    session.scalar(select(m.StudentProfile).where(m.StudentProfile.id == item.student_id).with_for_update())
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == item.thesis_id).with_for_update())
    row_version(expected, item.row_version)
    if not can_record(session, user, thesis):
        raise HTTPException(403, "Chỉ điều phối đợt được giải quyết yêu cầu xin thôi")
    if item.state not in OPEN or thesis.state not in EDITABLE:
        raise HTTPException(409, "Yêu cầu đã xử lý hoặc khóa luận đã khóa")
    effective_on = now().astimezone(VN).date()
    reference = code(item)
    recipients = coordinators(session, thesis.round_id) | {session.get(m.StudentProfile, item.student_id).user_id}
    advisor = primary_advisor(session, thesis.id)
    if data.outcome == "WITHDRAWN":
        if advisor:
            advisor_user = session.get(m.LecturerProfile, advisor.lecturer_id).user_id
            notices.emit(session, user.id, {advisor_user}, "WITHDRAWAL_MEMBERSHIP_CHANGED", "account", advisor_user,
                f"Sinh viên đã được chấp thuận xin thôi · {thesis.current_title}", "/theses")
        member = session.scalar(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
            m.ThesisMember.student_id == item.student_id, m.ThesisMember.active.is_(True)).with_for_update())
        if not member:
            raise HTTPException(409, "Thành viên không còn hoạt động; cần đối chiếu hồ sơ")
        member.active, member.is_coordinator, member.left_at = False, False, now()
        reg_member = session.scalar(select(m.RegistrationMember).where(
            m.RegistrationMember.registration_id == thesis.registration_id,
            m.RegistrationMember.student_id == item.student_id).with_for_update())
        registration = session.get(m.TopicRegistration, thesis.registration_id)
        if reg_member:
            reg_member.active, reg_member.is_coordinator = False, False
        registration.row_version += 1
        session.flush()
        remaining = session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
            m.ThesisMember.active.is_(True)).order_by(m.ThesisMember.joined_at, m.ThesisMember.id).with_for_update()).all()
        peers = set(session.scalars(select(m.StudentProfile.user_id).where(m.StudentProfile.id.in_([r.student_id for r in remaining]))))
        if remaining:
            registration.expected_member_count = len(remaining)
            from backend.services import evaluation
            academic = peers | notices.department_heads(session, thesis.department_id)
            academic |= {session.get(m.LecturerProfile, a.lecturer_id).user_id
                for a in evaluation.assignments(session, thesis) if a.state == "ACTIVE"}
            if advisor:
                academic.add(session.get(m.LecturerProfile, advisor.lecturer_id).user_id)
            # Keep private withdrawal reasons out of the group notification.
            notices.emit(session, user.id, academic, "WITHDRAWAL_GROUP_UPDATED", "defense", thesis.id,
                "Nhóm có thành viên xin thôi KLTN theo kết quả xử lý đã ghi nhận. Các thành viên còn lại tiếp tục đề tài và nộp phiên bản đề cương mới để duyệt lại.",
                f"/evaluation/{thesis.id}")
        if remaining:
            if not any(r.is_coordinator for r in remaining):
                remaining[0].is_coordinator = True
                successor = session.scalar(select(m.RegistrationMember).where(
                    m.RegistrationMember.registration_id == thesis.registration_id,
                    m.RegistrationMember.student_id == remaining[0].student_id))
                if successor:
                    successor.is_coordinator = True
            proposal = session.scalar(select(m.Proposal).where(m.Proposal.thesis_id == thesis.id).with_for_update())
            if proposal:
                proposal.state, proposal.row_version = "REVISION_REQUIRED", proposal.row_version + 1
            # Allow one corrected report even after acceptance or deadline close.
            # Existing bytes, decisions and signed reviews stay in history.
            for document in session.scalars(select(m.Document).where(m.Document.thesis_id == thesis.id,
                    m.Document.document_type.in_(["PLAN", "REPORT"]), m.Document.state == "ACTIVE").with_for_update()):
                latest = session.scalar(select(m.DocumentVersion).where(m.DocumentVersion.document_id == document.id)
                    .order_by(m.DocumentVersion.version_no.desc()).limit(1).with_for_update())
                if latest:
                    latest.state, latest.row_version = "REVISION_REQUESTED", latest.row_version + 1
                    document.row_version += 1
                    audit(session, user, "DOCUMENT_MEMBERSHIP_REVISION_REQUIRED", "document_version", latest.id,
                        "Nhóm thay đổi thành viên; nộp báo cáo cập nhật trong cùng hồ sơ, giữ bản cũ để đối chiếu")
            thesis.state = "ACTIVE"
            audit(session, user, "PROPOSAL_MEMBERSHIP_REVISION_REQUIRED", "thesis", thesis.id,
                f"SV {item.student_id} xin thôi; nhóm còn lại phải nộp phiên bản đề cương mới để duyệt lại")
        else:
            thesis.state = "WITHDRAWN"
            registration.state = "CANCELLED"
            if advisor:
                advisor.state, advisor.effective_to, advisor.row_version = "ENDED", now(), advisor.row_version + 1
            for assignment in session.scalars(select(m.ReviewerAssignment).where(
                    (m.ReviewerAssignment.thesis_id == thesis.id) |
                    m.ReviewerAssignment.proposal_id.in_(select(m.Proposal.id).where(m.Proposal.thesis_id == thesis.id)),
                    m.ReviewerAssignment.state == "ACTIVE").with_for_update()):
                assignment.state, assignment.row_version = "REVOKED", assignment.row_version + 1
                lecturer = session.get(m.LecturerProfile, assignment.lecturer_id)
                notices.emit(session, user.id, {lecturer.user_id}, "WITHDRAWAL_THESIS_CLOSED", "account", lecturer.user_id,
                    f"Khóa luận {thesis.current_title} không còn thành viên thực hiện; phân công nhận xét đã kết thúc.", "/evaluation")
                audit(session, user, "WITHDRAWAL_REVIEW_ASSIGNMENT_ENDED", "thesis", thesis.id,
                    "Không còn thành viên thực hiện; kết thúc phân công nhận xét", source_reference=str(assignment.id))
        thesis.row_version += 1
    item.state = "RECORDED" if data.outcome == "WITHDRAWN" else "NOT_GRANTED"
    item.official_reference, item.outcome_note, item.effective_on = reference, data.note, effective_on
    item.recorded_by, item.recorded_at, item.row_version = user.id, now(), item.row_version + 1
    audit(session, user, "WITHDRAWAL_" + item.state, "thesis_withdrawal_request", item.id,
        f"{reference}; ngày {effective_on}; {data.note}")
    notify(session, user, item, "WITHDRAWAL_" + item.state,
        "đã được chấp thuận xin thôi KLTN" if item.state == "RECORDED" else
        "không được chấp thuận xin thôi; tiếp tục thực hiện KLTN", recipients)
    session.commit()
    return output(session, user, item)
