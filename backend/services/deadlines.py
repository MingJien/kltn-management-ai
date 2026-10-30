"""Faculty-wide document-type cutoffs for one KLTN round."""
from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.api.core_schemas import DocumentDeadlineOut
from backend.db.models import entities as m
from backend.services.registration import row_version
from backend.services.theses import audit, now, thesis_access


def output(item: m.DocumentDeadline) -> DocumentDeadlineOut:
    return DocumentDeadlineOut(id=item.id, document_type=item.document_type,
        due_at=item.due_at, state=item.state, row_version=item.row_version, reason=item.reason)


def list_for_thesis(session, user, thesis_id):
    thesis = thesis_access(session, user, thesis_id)
    rows = session.scalars(select(m.DocumentDeadline).where(
        m.DocumentDeadline.round_id == thesis.round_id).order_by(m.DocumentDeadline.document_type)).all()
    return [output(item) for item in rows]


def for_submission(session, thesis, document_type: str) -> m.DocumentDeadline:
    item = session.scalar(select(m.DocumentDeadline).where(
        m.DocumentDeadline.round_id == thesis.round_id,
        m.DocumentDeadline.document_type == document_type).with_for_update())
    if not item:
        raise HTTPException(409, f"Khoa chưa thiết lập hạn nộp {document_type} cho đợt này")
    return item


def ensure_submission_allowed(item: m.DocumentDeadline, *, revision_requested: bool,
                              previous_submitted: bool = False, reviewed: bool = False) -> None:
    if revision_requested:
        return  # An explicit GVHD request unlocks exactly the next immutable version.
    if item.state != "OPEN":
        raise HTTPException(409, "Hạn tài liệu đã đóng; chỉ nộp lại khi GVHD yêu cầu sửa")
    if previous_submitted and (reviewed or now() > item.due_at):
        raise HTTPException(409, "Chỉ tự nộp phiên bản mới trước hạn khi GVHD chưa phản hồi")


def set_deadline(session, user, thesis_id, data, expected: int | None):
    thesis = thesis_access(session, user, thesis_id, action="milestone:manage", lock=True, write=True)
    round_ = session.scalar(select(m.ThesisRound).where(m.ThesisRound.id == thesis.round_id).with_for_update())
    if round_.state == "ARCHIVED":
        raise HTTPException(409, "Đợt đã lưu trữ; không thể thay đổi hạn tài liệu")
    item = session.scalar(select(m.DocumentDeadline).where(
        m.DocumentDeadline.round_id == thesis.round_id,
        m.DocumentDeadline.document_type == data.document_type).with_for_update())
    reason = data.reason.strip()
    if len(reason) < 3:
        raise HTTPException(422, "Phải ghi lý do hoặc căn cứ thời hạn")
    if item:
        if expected is None:
            raise HTTPException(428, "Cần If-Match để đổi hạn đã ban hành")
        row_version(expected, item.row_version)
        if data.due_at <= item.due_at:
            raise HTTPException(409, "Hạn mới phải muộn hơn hạn cũ")
        if data.due_at <= now():
            raise HTTPException(422, "Hạn gia hạn phải sau thời điểm hiện tại")
        old_due = item.due_at
        reopening = item.state == "CLOSED"
        item.due_at = data.due_at
        item.state = "OPEN"
        item.row_version += 1
        action = "DOCUMENT_DEADLINE_REOPENED" if reopening else "DOCUMENT_DEADLINE_EXTENDED"
        detail = f"{data.document_type}: {old_due.isoformat()} -> {data.due_at.isoformat()}; {reason}"
    else:
        if expected is not None:
            raise HTTPException(409, "Hạn này chưa tồn tại; tải lại dữ liệu")
        item = m.DocumentDeadline(id=uuid4(), round_id=thesis.round_id,
            document_type=data.document_type, due_at=data.due_at, state="OPEN",
            set_by=user.id, reason=reason)
        session.add(item)
        action = "DOCUMENT_DEADLINE_SET"
        detail = f"{data.document_type}: {data.due_at.isoformat()}; {reason}"
    item.set_by = user.id
    item.reason = reason
    try:
        session.flush()
        audit(session, user, action, "document_deadline", item.id, detail)
        from backend.services.notifications import (DOCUMENT_TYPE_LABELS, format_due,
                                                    notify_round_participants)

        label = DOCUMENT_TYPE_LABELS.get(data.document_type, data.document_type)
        notice_kind = {"DOCUMENT_DEADLINE_SET": "DOCUMENT_DEADLINE_SET",
                       "DOCUMENT_DEADLINE_EXTENDED": "DOCUMENT_DEADLINE_EXTENDED",
                       "DOCUMENT_DEADLINE_REOPENED": "DOCUMENT_DEADLINE_REOPENED"}.get(action, action)
        if action == "DOCUMENT_DEADLINE_SET":
            message = f"Khoa đã thiết lập hạn nộp {label} cho đợt {round_.code}: {format_due(data.due_at)}."
        elif action == "DOCUMENT_DEADLINE_REOPENED":
            message = f"Khoa đã gia hạn và mở nhận lại {label} cho đợt {round_.code} đến {format_due(data.due_at)}."
        else:
            message = f"Khoa đã gia hạn {label} cho đợt {round_.code} đến {format_due(data.due_at)}."
        notify_round_participants(session, round_id=thesis.round_id, actor_user_id=user.id,
                                  kind=notice_kind, message=message, section="documents")
        result = output(item)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Hạn tài liệu đã được cập nhật đồng thời; tải lại")
    return result


def close_deadline(session, user, thesis_id, document_type: str, reason: str, expected: int):
    thesis = thesis_access(session, user, thesis_id, action="milestone:manage", lock=True, write=True)
    round_ = session.scalar(select(m.ThesisRound).where(m.ThesisRound.id == thesis.round_id).with_for_update())
    if round_.state == "ARCHIVED":
        raise HTTPException(409, "Đợt đã lưu trữ; không thể đóng hạn tài liệu")
    item = for_submission(session, thesis, document_type)
    row_version(expected, item.row_version)
    if item.state != "OPEN":
        raise HTTPException(409, "Hạn đã đóng")
    reason = reason.strip()
    if len(reason) < 3:
        raise HTTPException(422, "Phải ghi lý do đóng hạn")
    item.state = "CLOSED"
    item.row_version += 1
    item.set_by = user.id
    item.reason = reason
    audit(session, user, "DOCUMENT_DEADLINE_CLOSED", "document_deadline", item.id,
        f"{document_type}: {reason}")
    session.flush()
    from backend.services.notifications import (DOCUMENT_TYPE_LABELS, notify_round_participants)

    label = DOCUMENT_TYPE_LABELS.get(document_type, document_type)
    notify_round_participants(session, round_id=thesis.round_id, actor_user_id=user.id,
        kind="DOCUMENT_DEADLINE_CLOSED",
        message=f"Khoa đã đóng nhận {label} cho đợt {round_.code}. Chỉ nộp lại khi GVHD yêu cầu sửa.",
        section="documents")
    result = output(item)
    session.commit()
    return result
