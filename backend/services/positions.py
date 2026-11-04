"""Record, replace and revoke head appointments while preserving historical decisions."""
from datetime import timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from backend.db.models import entities as m
from backend.services.registration import row_version
from backend.services.theses import audit, now
from backend.services.workflow_notices import emit


def admin(user):
    if user.base_role != "ADMIN":
        raise HTTPException(403, "Chỉ Admin được ghi nhận, thay đổi hoặc thu hồi chức vụ")


def position(session):
    session.execute(insert(m.OrganizationalPosition).values(id=uuid4(), code="DEPARTMENT_HEAD",
        name="Trưởng bộ môn").on_conflict_do_nothing(index_elements=["code"]))
    return session.scalar(select(m.OrganizationalPosition).where(m.OrganizationalPosition.code == "DEPARTMENT_HEAD"))


def catalog(session, user):
    admin(user)
    departments = session.scalars(select(m.Department).order_by(m.Department.name, m.Department.code)).all()
    candidates = session.execute(select(m.LecturerProfile, m.UserAccount.email).join(m.UserAccount,
        m.UserAccount.id == m.LecturerProfile.user_id).where(m.UserAccount.base_role == "LECTURER",
        m.UserAccount.status == "ACTIVE").order_by(m.LecturerProfile.display_name, m.LecturerProfile.lecturer_code)).all()
    return dict(departments=[dict(id=r.id, code=r.code, name=r.name) for r in departments],
        lecturers=[dict(id=r.id, user_id=r.user_id, department_id=r.department_id, name=r.display_name,
            code=r.lecturer_code, email=email) for r, email in candidates])


def output(session, row):
    lecturer = session.get(m.LecturerProfile, row.lecturer_id)
    department = session.get(m.Department, row.department_id)
    events = session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_type == "position_assignment",
        m.AuditEvent.resource_id == row.id).order_by(m.AuditEvent.occurred_at, m.AuditEvent.id)).all()
    origin = next((event for event in events if event.action == "POSITION_ASSIGNED"), None)
    instant = now()
    status = row.state if row.state != "ACTIVE" else (
        "EXPIRED" if row.effective_to and row.effective_to <= instant else
        "SCHEDULED" if row.effective_from > instant else "EFFECTIVE")
    return dict(id=row.id, row_version=row.row_version, lecturer_id=lecturer.id, lecturer_name=lecturer.display_name,
        lecturer_code=lecturer.lecturer_code, department_id=department.id, department_name=department.name,
        effective_from=row.effective_from, effective_to=row.effective_to, state=row.state, status=status,
        basis_ref=origin.source_reference if origin else None,
        changes=[dict(action=e.action, at=e.occurred_at, reason=e.reason, basis_ref=e.source_reference) for e in events])


def listing(session, user, department_id, offset, limit):
    admin(user)
    query = select(m.PositionAssignment).join(m.OrganizationalPosition,
        m.OrganizationalPosition.id == m.PositionAssignment.position_id).where(
        m.OrganizationalPosition.code == "DEPARTMENT_HEAD", m.PositionAssignment.department_id.is_not(None))
    if department_id:
        query = query.where(m.PositionAssignment.department_id == department_id)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.scalars(query.order_by(m.PositionAssignment.effective_from.desc(), m.PositionAssignment.id)
        .offset(offset).limit(limit)).all()
    return dict(items=[output(session, r) for r in rows], total=total)



def available_appointments(session, user):
    """All current and scheduled department-head decisions available for action."""
    admin(user)
    instant = now()
    rows = session.scalars(select(m.PositionAssignment).join(m.OrganizationalPosition,
        m.OrganizationalPosition.id == m.PositionAssignment.position_id).where(
        m.OrganizationalPosition.code == "DEPARTMENT_HEAD",
        m.PositionAssignment.department_id.is_not(None),
        m.PositionAssignment.state == "ACTIVE",
        (m.PositionAssignment.effective_to.is_(None) | (m.PositionAssignment.effective_to > instant)))
        .order_by(m.PositionAssignment.effective_from.desc(), m.PositionAssignment.id)).all()
    return [output(session, row) for row in rows]

def scope_lock(session, department_id):
    # All writes for a department share this lock, including new empty scopes.
    row = session.scalar(select(m.Department).where(m.Department.id == department_id).with_for_update())
    if not row:
        raise HTTPException(404, "Không tìm thấy bộ môn")
    return row


def candidate(session, identifier, department_id):
    row = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.id == identifier)
        .with_for_update().execution_options(populate_existing=True))
    if not row or row.department_id != department_id:
        raise HTTPException(422, "Chọn giảng viên thuộc đúng bộ môn được bổ nhiệm")
    account = session.scalar(select(m.UserAccount).where(m.UserAccount.id == row.user_id)
        .with_for_update().execution_options(populate_existing=True))
    if not account or account.base_role != "LECTURER" or account.status != "ACTIVE":
        raise HTTPException(422, "Người được bổ nhiệm phải có tài khoản giảng viên đang hoạt động")
    return row


def period(data, instant):
    start = data.effective_from.astimezone(timezone.utc) if data.effective_from else instant
    end = data.effective_to.astimezone(timezone.utc) if data.effective_to else None
    if data.effective_from and start < instant:
        raise HTTPException(422, "Ngày hiệu lực phải ở tương lai; để trống để áp dụng ngay khi lưu")
    if end and end <= start:
        raise HTTPException(422, "Ngày kết thúc phải sau ngày bắt đầu hiệu lực")
    return start, end


def check_window(session, department_id, position_id, lecturer_id, start, end, instant):
    rows = session.scalars(select(m.PositionAssignment).where(m.PositionAssignment.department_id == department_id,
        m.PositionAssignment.position_id == position_id, m.PositionAssignment.state == "ACTIVE").with_for_update()).all()
    for row in rows:
        if row.effective_to and row.effective_to <= instant:
            row.state = "EXPIRED"
            row.row_version += 1
            continue
        if (end is None or row.effective_from < end) and (row.effective_to is None or start < row.effective_to):
            raise HTTPException(409, "Bộ môn đã có bổ nhiệm trùng thời gian. Hãy chọn Thay người trên quyết định đang có")
        if row.lecturer_id == lecturer_id:
            raise HTTPException(409, "Giảng viên đã có quyết định đang hiệu lực hoặc chờ hiệu lực; không tạo quyết định trùng người")
    session.flush()


def new_record(session, user, department_id, lecturer, pos, start, end, data):
    row = m.PositionAssignment(id=uuid4(), lecturer_id=lecturer.id, position_id=pos.id,
        department_id=department_id, effective_from=start, effective_to=end, state="ACTIVE")
    session.add(row)
    session.flush()
    audit(session, user, "POSITION_ASSIGNED", "position_assignment", row.id, data.reason, source_reference=data.basis_ref)
    department=session.get(m.Department,department_id)
    vn=timezone(timedelta(hours=7))
    dates=start.astimezone(vn).strftime("%H:%M %d/%m/%Y")
    until=end.astimezone(vn).strftime("%H:%M %d/%m/%Y") if end else "chưa ấn định ngày kết thúc"
    emit(session, user.id, {lecturer.user_id}, "POSITION_ASSIGNED", "position_assignment", row.id,
        f"Khoa đã ghi nhận bổ nhiệm Trưởng bộ môn {department.name} cho bạn, hiệu lực từ {dates} đến {until}. Quyền áp dụng theo thời gian này.", "/account")
    return row


def grant(session, user, data):
    admin(user)
    scope_lock(session, data.department_id)
    lecturer = candidate(session, data.lecturer_id, data.department_id)
    instant = now()
    start, end = period(data, instant)
    pos = position(session)
    check_window(session, data.department_id, pos.id, lecturer.id, start, end, instant)
    row = new_record(session, user, data.department_id, lecturer, pos, start, end, data)
    session.flush()
    result = output(session, row)
    session.commit()
    return result


def locked_assignment(session, identifier, expected):
    initial = session.get(m.PositionAssignment, identifier)
    if not initial or not initial.department_id:
        raise HTTPException(404, "Không tìm thấy bổ nhiệm Trưởng bộ môn")
    scope_lock(session, initial.department_id)
    row = session.scalar(select(m.PositionAssignment).where(m.PositionAssignment.id == identifier)
        .with_for_update().execution_options(populate_existing=True))
    pos = session.get(m.OrganizationalPosition, row.position_id)
    if pos.code != "DEPARTMENT_HEAD":
        raise HTTPException(404, "Không tìm thấy bổ nhiệm Trưởng bộ môn")
    row_version(expected, row.row_version)
    if row.state != "ACTIVE" or (row.effective_to and row.effective_to <= now()):
        raise HTTPException(409, "Quyết định đã kết thúc hoặc thu hồi; vui lòng làm mới danh sách")
    return row, pos


def end_assignment(session, user, row, instant, data, action):
    # Cancel a not-yet-effective appointment without inventing a negative interval.
    if instant > row.effective_from:
        row.effective_to = instant
    row.state = "REVOKED"
    row.row_version += 1
    audit(session, user, action, "position_assignment", row.id, data.reason, source_reference=data.basis_ref)


def replace(session, user, identifier, data, expected):
    admin(user)
    old, pos = locked_assignment(session, identifier, expected)
    if old.lecturer_id == data.lecturer_id:
        raise HTTPException(422, "Thay người cần chọn giảng viên khác với người đang được bổ nhiệm")
    lecturer = candidate(session, data.lecturer_id, old.department_id)
    instant = now()
    start, end = period(data, instant)
    if old.effective_to and start >= old.effective_to:
        raise HTTPException(422, "Thời điểm thay người phải trước khi quyết định cũ kết thúc")
    if start <= instant or start <= old.effective_from:
        end_assignment(session, user, old, instant, data, "POSITION_REPLACED")
    else:
        old.effective_to = start
        old.row_version += 1
        audit(session, user, "POSITION_REPLACED", "position_assignment", old.id, data.reason, source_reference=data.basis_ref)
    session.flush()
    check_window(session, old.department_id, pos.id, lecturer.id, start, end, instant)
    row = new_record(session, user, old.department_id, lecturer, pos, start, end, data)
    previous = session.get(m.LecturerProfile, old.lecturer_id)
    emit(session, user.id, {previous.user_id}, "POSITION_REPLACED", "position_assignment", old.id,
        "Khoa đã ghi nhận thay đổi người giữ chức vụ Trưởng bộ môn. Quyền của bạn kết thúc theo thời gian hiệu lực đã ghi nhận.", "/account")
    session.flush()
    result = output(session, row)
    session.commit()
    return result


def revoke(session, user, identifier, data, expected):
    admin(user)
    row, _ = locked_assignment(session, identifier, expected)
    end_assignment(session, user, row, now(), data, "POSITION_REVOKED")
    lecturer = session.get(m.LecturerProfile, row.lecturer_id)
    emit(session, user.id, {lecturer.user_id}, "POSITION_REVOKED", "position_assignment", row.id,
        "Khoa đã thu hồi bổ nhiệm Trưởng bộ môn của bạn. Các hồ sơ và lịch sử xử lý được giữ lại.", "/account")
    session.flush()
    result = output(session, row)
    session.commit()
    return result
