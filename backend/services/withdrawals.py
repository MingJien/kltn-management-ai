"""Student withdrawal requests and recording of externally handled outcomes.

Advisor confirmation is not an administrative approval or an electronic signature.
The original registration, submitted versions and signed records remain historical.
"""
from datetime import datetime, time, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import exists, select

from backend.db.models import entities as m
from backend.services import documents, file_scanner, workflow_notices as notices
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


def is_advisor(session, user, thesis):
    advisor = primary_advisor(session, thesis.id)
    return bool(user.base_role == "LECTURER" and advisor and
        session.get(m.LecturerProfile, advisor.lecturer_id).user_id == user.id)


def can_view(session, user, item):
    thesis = session.get(m.Thesis, item.thesis_id)
    return bool(thesis and (session.get(m.StudentProfile, item.student_id).user_id == user.id
        or item.advisor_reviewed_by == user.id
        or is_advisor(session, user, thesis) or can_record(session, user, thesis)))


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


def history_reason(event):
    if event.action == "WITHDRAWAL_RECEIPT_RECORDED":
        receipt = json.loads(event.reason)
        return (f"Ngày {receipt['received_on']}; đơn vị: {receipt['receiving_unit']}; "
            f"căn cứ: {receipt['reference']}; ghi chú: {receipt['note']}")
    if event.reason and event.action == "WITHDRAWAL_SIGNED_COPY_ADDED":
        return event.reason.split("; previous_file=")[0]
    return event.reason


def output(session, user, item):
    thesis = session.get(m.Thesis, item.thesis_id)
    student = session.get(m.StudentProfile, item.student_id)
    stored = session.get(m.StoredFile, item.evidence_file_id) if item.evidence_file_id else None
    history = session.scalars(select(m.AuditEvent).where(
        m.AuditEvent.resource_type == "thesis_withdrawal_request", m.AuditEvent.resource_id == item.id)
        .order_by(m.AuditEvent.occurred_at, m.AuditEvent.id)).all()
    receipt_events = [h for h in history if h.action == "WITHDRAWAL_RECEIPT_RECORDED"]
    receipt = None
    outcome_file = outcome_evidence(session, item)
    if receipt_events:
        event = receipt_events[-1]
        receipt = {**json.loads(event.reason), "recorded_at": event.occurred_at,
            "recorded_by": notices.actor_name(session, event.actor_id)}
    return {"id": item.id, "code": code(item), "thesis_id": thesis.id, "title": item.application_data["title"],
        "student_name": student.display_name, "student_code": student.student_code,
        "state": item.state, "reason": item.reason, "submitted_at": item.submitted_at,
        "execution_starts_on": item.execution_starts_on, "row_version": item.row_version,
        "advisor_comment": item.advisor_comment, "advisor_reviewed_at": item.advisor_reviewed_at,
        "official_reference": item.official_reference, "outcome_note": item.outcome_note,
        "effective_on": item.effective_on, "recorded_at": item.recorded_at,
        "evidence_name": stored.original_name if stored else None,
        "scan_state": stored.scan_state if stored else None,
        "receipt": receipt,
        "outcome_evidence": {"name":outcome_file.original_name,"scan_state":outcome_file.scan_state} if outcome_file else None,
        "can_export": item.state == "ADVISOR_CONFIRMED",
        "print_data": item.application_data,
        "can_cancel": user.id == student.user_id and item.state == "SUBMITTED",
        "can_confirm": is_advisor(session, user, thesis) and item.state == "SUBMITTED",
        "can_record": can_record(session, user, thesis) and item.state == "ADVISOR_CONFIRMED",
        "can_upload": (user.id == student.user_id or can_record(session, user, thesis)) and item.state == "ADVISOR_CONFIRMED",
        "history": [{"action": h.action, "reason": history_reason(h), "at": h.occurred_at,
            "actor": notices.actor_name(session, h.actor_id)} for h in history]}


def workspace(session, user):
    if user.base_role not in {"STUDENT", "LECTURER"}:
        raise HTTPException(403, "Luồng xin thôi dành cho SV, GVHD và điều phối KLTN được giao")
    own_student = profile(session, user, "STUDENT") if user.base_role == "STUDENT" else None
    managed = set(session.scalars(select(m.ResourceAssignment.round_id).where(
        m.ResourceAssignment.user_id == user.id, m.ResourceAssignment.assignment_type == "KLTN_COORDINATOR",
        effective(m.ResourceAssignment)))) if user.base_role == "LECTURER" else set()
    # Filter in SQL before loading reasons/files; no list of another student's request.
    predicate = m.ThesisWithdrawalRequest.student_id == own_student.id if own_student else (
        (m.ThesisWithdrawalRequest.advisor_reviewed_by == user.id) |
        m.ThesisWithdrawalRequest.thesis_id.in_(select(m.Thesis.id).where(
            m.Thesis.round_id.in_(managed) | m.Thesis.id.in_(select(m.AdvisorAssignment.thesis_id)
                .join(m.LecturerProfile, m.LecturerProfile.id == m.AdvisorAssignment.lecturer_id)
                .where(m.LecturerProfile.user_id == user.id, effective(m.AdvisorAssignment))))))
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
            theses.append({"id": thesis.id, "title": thesis.current_title, "round_id": round_.id,
                "round_code": round_.code, "starts_on": start,
                "last_request_on": start + timedelta(days=13) if start else None,
                "can_submit": can_submit, "message": message})
    rounds = []
    for round_ in session.scalars(select(m.ThesisRound).where(m.ThesisRound.id.in_(managed)).order_by(m.ThesisRound.opens_at.desc())):
        has_requests = bool(session.scalar(select(m.ThesisWithdrawalRequest.id).join(m.Thesis,
            m.Thesis.id == m.ThesisWithdrawalRequest.thesis_id).where(m.Thesis.round_id == round_.id).limit(1)))
        rounds.append({"id": round_.id, "code": round_.code, "starts_on": round_.execution_starts_on,
            "reference": round_.execution_start_reference, "row_version": round_.row_version,
            "can_edit": not has_requests and round_.state != "ARCHIVED"})
    return {"requests": [output(session, user, i) for i in items], "theses": theses, "rounds": rounds}


def set_start(session, user, round_id, data, expected):
    round_ = session.scalar(select(m.ThesisRound).where(m.ThesisRound.id == round_id).with_for_update())
    if not round_ or user.base_role != "LECTURER" or not resource_role(session, user.id, "KLTN_COORDINATOR", round_id=round_id):
        raise HTTPException(403, "Chỉ điều phối được giao cho đợt mới ghi nhận ngày bắt đầu")
    row_version(expected, round_.row_version)
    if round_.state == "ARCHIVED" or session.scalar(select(m.ThesisWithdrawalRequest.id).join(m.Thesis,
            m.Thesis.id == m.ThesisWithdrawalRequest.thesis_id).where(m.Thesis.round_id == round_id).limit(1)):
        raise HTTPException(409, "Đã có đơn hoặc đợt đã lưu trữ; không đổi ngày dùng tính hạn của hồ sơ")
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
        advisor = primary_advisor(session, thesis.id)
        if advisor:
            recipients.add(session.get(m.LecturerProfile, advisor.lecturer_id).user_id)
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
    if not advisor:
        raise HTTPException(409, "Chưa có GVHD chính để xác nhận đơn")
    lecturer = session.get(m.LecturerProfile, advisor.lecturer_id)
    item = m.ThesisWithdrawalRequest(id=uuid4(), thesis_id=thesis.id, student_id=student.id,
        reason=data.reason, submitted_at=now(), execution_starts_on=round_.execution_starts_on, state="SUBMITTED",
        application_data={"title": thesis.current_title, "student_name": student.display_name,
            "student_code": student.student_code, "class_name": student.class_name or "",
            "advisor_name": lecturer.display_name, "round_code": round_.code,
            "department": session.get(m.Department, thesis.department_id).name})
    session.add(item)
    session.flush()
    audit(session, user, "WITHDRAWAL_SUBMITTED", "thesis_withdrawal_request", item.id, data.reason)
    notify(session, user, item, "WITHDRAWAL_SUBMITTED", "đã gửi yêu cầu xin thôi KLTN, chờ GVHD xác nhận")
    session.commit()
    return output(session, user, item)


def advisor_decision(session, user, identifier, data, expected):
    item = get(session, user, identifier, lock=True)
    thesis = session.get(m.Thesis, item.thesis_id)
    row_version(expected, item.row_version)
    if not is_advisor(session, user, thesis):
        raise HTTPException(403, "Chỉ GVHD chính được xác nhận đơn")
    if item.state != "SUBMITTED":
        raise HTTPException(409, "Đơn không còn chờ GVHD xác nhận")
    item.state = "ADVISOR_CONFIRMED" if data.decision == "CONFIRM" else "RETURNED"
    item.advisor_reviewed_by, item.advisor_reviewed_at, item.advisor_comment = user.id, now(), data.comment
    item.row_version += 1
    audit(session, user, "WITHDRAWAL_" + item.state, "thesis_withdrawal_request", item.id, data.comment)
    notify(session, user, item, "WITHDRAWAL_" + item.state,
        "GVHD đã xác nhận, cần nộp đơn đã ký và chờ ghi nhận kết quả bên ngoài" if data.decision == "CONFIRM" else "GVHD trả lại yêu cầu: " + data.comment)
    session.commit()
    return output(session, user, item)


def cancel(session, user, identifier, expected):
    item = get(session, user, identifier, lock=True)
    row_version(expected, item.row_version)
    if session.get(m.StudentProfile, item.student_id).user_id != user.id or item.state != "SUBMITTED":
        raise HTTPException(409, "Chỉ người gửi được hủy đơn khi GVHD chưa xác nhận")
    item.state, item.row_version = "CANCELLED", item.row_version + 1
    audit(session, user, "WITHDRAWAL_CANCELLED", "thesis_withdrawal_request", item.id, "SV hủy yêu cầu; không rút khỏi KLTN")
    notify(session, user, item, "WITHDRAWAL_CANCELLED", "đã hủy yêu cầu xin thôi; tiếp tục thực hiện KLTN")
    session.commit()
    return output(session, user, item)


def upload_access(session, user, identifier, expected):
    item = get(session, user, identifier, lock=True)
    row_version(expected, item.row_version)
    if item.state != "ADVISOR_CONFIRMED" or not (session.get(m.StudentProfile, item.student_id).user_id == user.id
            or can_record(session, user, session.get(m.Thesis, item.thesis_id))):
        raise HTTPException(403, "SV có đơn hoặc điều phối mới nộp bản có xác nhận khi chờ kết quả")
    return item


async def upload(session, user, identifier, request, expected):
    path = None
    try:
        item = upload_access(session, user, identifier, expected)
        name, content, mime = await documents.read_upload(request)
        if Path(name).suffix.lower() not in {".pdf", ".docx"}:
            raise HTTPException(422, "Đơn có xác nhận phải là PDF/DOCX, tối đa 10 MB")
        stored, digest, path = documents.persist_upload(session, name, content, mime)
        session.flush()
        file_scanner.scan(stored, path)
        previous = item.evidence_file_id
        item.evidence_file_id, item.row_version = stored.id, item.row_version + 1
        audit(session, user, "WITHDRAWAL_SIGNED_COPY_ADDED", "thesis_withdrawal_request", item.id,
            f"{name}; previous_file={previous}; new_file={stored.id}", after_hash=digest)
        notify(session, user, item, "WITHDRAWAL_SIGNED_COPY_ADDED", "đã bổ sung bản đơn có xác nhận")
        session.commit()
        return output(session, user, item)
    except Exception:
        session.rollback()
        if path and path.is_file():
            path.unlink()
        raise


def rescan(session, user, identifier, expected):
    item = upload_access(session, user, identifier, expected)
    stored = session.get(m.StoredFile, item.evidence_file_id) if item.evidence_file_id else None
    if not stored:
        raise HTTPException(404, "Chưa có bản đơn có xác nhận")
    file_scanner.scan(stored, documents.storage_root() / Path(stored.storage_key).name)
    item.row_version += 1
    audit(session, user, "WITHDRAWAL_FILE_SCANNED", "thesis_withdrawal_request", item.id, stored.scan_state)
    session.commit()
    return output(session, user, item)


def record_receipt(session, user, identifier, data, expected):
    item = get(session, user, identifier, lock=True)
    thesis = session.get(m.Thesis, item.thesis_id)
    row_version(expected, item.row_version)
    if not can_record(session, user, thesis):
        raise HTTPException(403, "Chỉ điều phối đợt được ghi nhận thông tin tiếp nhận")
    if item.state != "ADVISOR_CONFIRMED":
        raise HTTPException(409, "Chỉ ghi nhận tiếp nhận khi đơn đã được GVHD xác nhận và đang chờ kết quả")
    if not item.submitted_at.astimezone(VN).date() <= data.received_on <= now().astimezone(VN).date():
        raise HTTPException(422, "Ngày tiếp nhận phải từ ngày gửi yêu cầu đến hôm nay")
    payload = {"received_on": data.received_on.isoformat(), "receiving_unit": data.receiving_unit,
        "reference": data.reference, "note": data.note}
    item.row_version += 1
    audit(session, user, "WITHDRAWAL_RECEIPT_RECORDED", "thesis_withdrawal_request", item.id,
        json.dumps(payload, ensure_ascii=False))
    notify(session, user, item, "WITHDRAWAL_RECEIPT_RECORDED",
        "đã ghi nhận hồ sơ được tiếp nhận; đang chờ kết quả xử lý bên ngoài")
    session.commit()
    return output(session, user, item)


def record(session, user, identifier, data, expected):
    item = get(session, user, identifier, lock=True)
    # Same lock order as registration: student -> thesis; the request row is unique per student.
    session.scalar(select(m.StudentProfile).where(m.StudentProfile.id == item.student_id).with_for_update())
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == item.thesis_id).with_for_update())
    row_version(expected, item.row_version)
    if not can_record(session, user, thesis):
        raise HTTPException(403, "Chỉ điều phối đợt được ghi nhận kết quả xử lý bên ngoài")
    if item.state != "ADVISOR_CONFIRMED" or thesis.state not in EDITABLE:
        raise HTTPException(409, "Đơn chưa được GVHD xác nhận hoặc khóa luận đã khóa")
    if not item.submitted_at.astimezone(VN).date() <= data.effective_on <= now().astimezone(VN).date():
        raise HTTPException(422, "Ngày kết quả phải từ ngày gửi đơn đến hôm nay")
    stored = session.get(m.StoredFile, item.evidence_file_id) if item.evidence_file_id else None
    documents.require_clean(stored, "ghi nhận kết quả xử lý đơn")
    outcome_file = outcome_evidence(session, item)
    if outcome_file:
        documents.require_clean(outcome_file, "đối chiếu minh chứng kết quả")
        documents.stored_download(session, SimpleNamespace(stored_file_id=outcome_file.id, content_sha256=outcome_file.sha256))
    # Check that the actual immutable bytes are still present and match the checksum.
    documents.stored_download(session, SimpleNamespace(stored_file_id=stored.id, content_sha256=stored.sha256))
    recipients = coordinators(session, thesis.round_id) | {session.get(m.StudentProfile, item.student_id).user_id}
    advisor = primary_advisor(session, thesis.id)
    if advisor:
        recipients.add(session.get(m.LecturerProfile, advisor.lecturer_id).user_id)
    if data.outcome == "WITHDRAWN":
        member = session.scalar(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
            m.ThesisMember.student_id == item.student_id, m.ThesisMember.active.is_(True)).with_for_update())
        if not member:
            raise HTTPException(409, "Thành viên không còn hoạt động; cần đối chiếu hồ sơ")
        member.active, member.is_coordinator, member.left_at = False, False, datetime.combine(data.effective_on, time.min, VN)
        reg_member = session.scalar(select(m.RegistrationMember).where(
            m.RegistrationMember.registration_id == thesis.registration_id,
            m.RegistrationMember.student_id == item.student_id).with_for_update())
        if reg_member:
            reg_member.active, reg_member.is_coordinator = False, False
            registration = session.get(m.TopicRegistration, thesis.registration_id)
            registration.row_version += 1
        session.flush()
        remaining = session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
            m.ThesisMember.active.is_(True)).order_by(m.ThesisMember.joined_at, m.ThesisMember.id).with_for_update()).all()
        peers = set(session.scalars(select(m.StudentProfile.user_id).where(m.StudentProfile.id.in_([r.student_id for r in remaining]))))
        if remaining:
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
            registration = session.get(m.TopicRegistration, thesis.registration_id)
            registration.state, registration.row_version = "CANCELLED", registration.row_version + 1
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
    item.official_reference, item.outcome_note, item.effective_on = data.reference, data.note, data.effective_on
    item.recorded_by, item.recorded_at, item.row_version = user.id, now(), item.row_version + 1
    audit(session, user, "WITHDRAWAL_" + item.state, "thesis_withdrawal_request", item.id,
        f"{data.reference}; ngày {data.effective_on}; {data.note}")
    notify(session, user, item, "WITHDRAWAL_" + item.state,
        "đã ghi nhận xin thôi KLTN theo kết quả xử lý bên ngoài" if item.state == "RECORDED" else
        "kết quả bên ngoài không chấp thuận xin thôi; tiếp tục thực hiện KLTN", recipients)
    session.commit()
    return output(session, user, item)


def download(session, user, identifier):
    item = get(session, user, identifier)
    stored = session.get(m.StoredFile, item.evidence_file_id) if item.evidence_file_id else None
    return documents.stored_download(session, SimpleNamespace(stored_file_id=stored.id, content_sha256=stored.sha256) if stored else None)


def print_copy(session, user, identifier):
    item = get(session, user, identifier, lock=True)
    if item.state != "ADVISOR_CONFIRMED":
        raise HTTPException(409, "Chỉ xuất đơn đang được GVHD xác nhận và chờ xử lý")
    from backend.services.withdrawal_export import export
    return export(session, user, item)


def outcome_evidence(session, item):
    event = session.scalar(select(m.AuditEvent).where(m.AuditEvent.resource_type == "thesis_withdrawal_request",
        m.AuditEvent.resource_id == item.id, m.AuditEvent.action == "WITHDRAWAL_OUTCOME_FILE_ADDED")
        .order_by(m.AuditEvent.occurred_at.desc(), m.AuditEvent.id.desc()).limit(1))
    return session.get(m.StoredFile, UUID(event.source_reference)) if event else None


async def upload_outcome(session, user, identifier, request, expected):
    path = None
    try:
        item = upload_access(session, user, identifier, expected)
        if not can_record(session, user, session.get(m.Thesis, item.thesis_id)):
            raise HTTPException(403, "Chỉ điều phối bổ sung minh chứng kết quả")
        name, content, mime = await documents.read_upload(request)
        if Path(name).suffix.lower() not in {".pdf", ".docx"}:
            raise HTTPException(422, "Minh chứng kết quả phải là PDF/DOCX")
        stored, digest, path = documents.persist_upload(session, name, content, mime)
        session.flush()
        file_scanner.scan(stored, path)
        item.row_version += 1
        audit(session, user, "WITHDRAWAL_OUTCOME_FILE_ADDED", "thesis_withdrawal_request", item.id,
            name, after_hash=digest, source_reference=str(stored.id))
        session.commit()
        return output(session, user, item)
    except Exception:
        session.rollback()
        if path and path.is_file():
            path.unlink()
        raise


def outcome_file_action(session, user, identifier, expected=None):
    item = get(session, user, identifier, lock=expected is not None)
    stored = outcome_evidence(session, item)
    if not stored:
        raise HTTPException(404, "Chưa có minh chứng kết quả")
    if expected is not None:
        upload_access(session, user, identifier, expected)
        if not can_record(session, user, session.get(m.Thesis, item.thesis_id)):
            raise HTTPException(403, "Chỉ điều phối quét lại minh chứng kết quả")
        file_scanner.scan(stored, documents.storage_root() / Path(stored.storage_key).name)
        item.row_version += 1
        audit(session, user, "WITHDRAWAL_OUTCOME_FILE_SCANNED", "thesis_withdrawal_request", item.id, stored.scan_state)
        session.commit()
        return output(session, user, item)
    return documents.stored_download(session, SimpleNamespace(stored_file_id=stored.id, content_sha256=stored.sha256))
