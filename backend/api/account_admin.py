"""Technical account provisioning; academic approval stays round-scoped."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, model_validator
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.account import _account_display_name, _account_identifier, _audit, _mail_link, _mail_recipient, _student_can_activate
from backend.api.dependencies import current_user, get_session
from backend.db.models import entities as m
from backend.services.passwords import unusable_password
from backend.services.roster import EMAIL
from backend.services.account_mail import mail_delivery_ready
from backend.services.account_directory import build_account_directory
from backend.services.lecturer_roster import MAIL_ACTIONS, lock_identities, record_delivery
from backend.services.notifications import format_due, notify_user
from backend.services.workflow_notices import round_announcement

router = APIRouter(prefix="/api/v1/admin", tags=["account administration"])
AccountReason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1000)]


class LecturerInvite(BaseModel):
    lecturer_code: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    department_id: UUID


class RoundAssignment(BaseModel):
    round_id: UUID
    user_id: UUID
    assignment_type: str = Field(pattern="^(ELIGIBILITY_IMPORTER|ELIGIBILITY_VERIFIER|ACCOUNT_MANAGER|KLTN_COORDINATOR|FORM_MANAGER|REVIEW_RECORDS_MANAGER)$")
    basis_ref: str = Field(min_length=3, max_length=500)


class AccountStatus(BaseModel):
    locked: bool
    reason: AccountReason


class AccountChangeReason(BaseModel):
    reason: AccountReason


class StudentEmailCorrection(BaseModel):
    round_id: UUID
    student_code: str = Field(min_length=1, max_length=32)
    email: str = Field(min_length=3, max_length=255)
    basis_ref: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    reason: AccountReason


class StaffEmailCorrection(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    basis_ref: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    reason: AccountReason


class AssignmentRevoke(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class RoundCreate(BaseModel):
    academic_year_code: str = Field(pattern=r"^\d{4}-\d{4}$")
    year_starts_on: date
    year_ends_on: date
    code: str = Field(min_length=1, max_length=32)
    round_type: Literal["MAIN", "SUPPLEMENTARY"] = "MAIN"
    opens_at: datetime
    closes_at: datetime
    basis_ref: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def valid_schedule(self):
        first, last = map(int, self.academic_year_code.split("-"))
        if last != first + 1 or self.year_starts_on.year != first or self.year_ends_on.year != last:
            raise ValueError("Academic year code must match its start and end dates")
        if self.year_ends_on <= self.year_starts_on:
            raise ValueError("Academic year end must follow its start")
        if not self.opens_at.tzinfo or not self.closes_at.tzinfo or self.closes_at <= self.opens_at:
            raise ValueError("Registration dates need time zones and a valid order")
        if self.opens_at.date() < self.year_starts_on or self.closes_at.date() > self.year_ends_on:
            raise ValueError("Registration dates must fall within the academic year")
        return self


class RoundStateChange(BaseModel):
    state: Literal["OPEN", "CLOSED"]
    reason: str = Field(min_length=3, max_length=500)


class RoundExtension(BaseModel):
    closes_at: AwareDatetime
    basis_ref: str = Field(min_length=3, max_length=500)
    reason: str = Field(min_length=5, max_length=1000)
    reopen_closed: bool = False


class RoundScheduleUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    round_type: Literal["MAIN", "SUPPLEMENTARY"]
    opens_at: datetime
    closes_at: datetime
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def valid_window(self):
        if not self.opens_at.tzinfo or not self.closes_at.tzinfo or self.closes_at <= self.opens_at:
            raise ValueError("Registration dates need time zones and a valid order")
        return self


def _admin(user: m.UserAccount) -> None:
    if user.base_role != "ADMIN":
        raise HTTPException(403, "Account administration requires ADMIN")


def _managed_rounds(session: Session, user: m.UserAccount) -> list[UUID]:
    instant = datetime.now(timezone.utc)
    return list(session.scalars(select(m.ResourceAssignment.round_id).where(
        m.ResourceAssignment.user_id == user.id,
        m.ResourceAssignment.assignment_type == "ACCOUNT_MANAGER",
        m.ResourceAssignment.round_id.is_not(None),
        m.ResourceAssignment.state == "ACTIVE",
        m.ResourceAssignment.effective_from <= instant,
        (m.ResourceAssignment.effective_to.is_(None) | (m.ResourceAssignment.effective_to > instant)),
    )).all())


def _manageable_student(session: Session, actor: m.UserAccount, target: m.UserAccount,
                        round_id: UUID | None = None) -> m.StudentProfile | None:
    if actor.base_role == "ADMIN":
        return session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == target.id))
    rounds = _managed_rounds(session, actor)
    if target.base_role != "STUDENT" or not rounds or (round_id is not None and round_id not in rounds):
        raise HTTPException(403, "Account management is limited to assigned rounds")
    profile = session.scalar(select(m.StudentProfile).join(m.EligibilitySnapshot,
        m.EligibilitySnapshot.student_id == m.StudentProfile.id).where(
        m.StudentProfile.user_id == target.id,
        m.EligibilitySnapshot.round_id.in_([round_id] if round_id else rounds)).limit(1))
    if profile is None:
        raise HTTPException(403, "Student is outside assigned rounds")
    return profile


@router.get("/departments")
def departments(user: m.UserAccount = Depends(current_user),
                session: Session = Depends(get_session)) -> list[dict]:
    _admin(user)
    return [{"id": str(row.id), "code": row.code, "name": row.name,
             "major_code": row.major_code} for row in session.scalars(
        select(m.Department).where(m.Department.active.is_(True)).order_by(m.Department.name)).all()]


@router.get("/rounds")
def rounds(user: m.UserAccount = Depends(current_user),
           session: Session = Depends(get_session)) -> list[dict]:
    _admin(user)
    rows = session.scalars(select(m.ThesisRound).order_by(m.ThesisRound.opens_at.desc())).all()
    years = {year.id: year for year in session.scalars(select(m.AcademicYear).where(
        m.AcademicYear.id.in_([row.academic_year_id for row in rows]))).all()}
    return [{"id": str(row.id), "code": row.code, "state": row.state,
             "round_type": row.round_type, "academic_year_code": years[row.academic_year_id].code,
             "year_starts_on": years[row.academic_year_id].starts_on,
             "year_ends_on": years[row.academic_year_id].ends_on,
             "opens_at": row.opens_at, "closes_at": row.closes_at,
             "row_version": row.row_version} for row in rows]


@router.post("/rounds", status_code=201)
def create_round(payload: RoundCreate, user: m.UserAccount = Depends(current_user),
                 session: Session = Depends(get_session)) -> dict:
    _admin(user)
    code = payload.code.strip()
    basis = payload.basis_ref.strip()
    if not code or not basis:
        raise HTTPException(422, "Round code and schedule reference are required")
    year = session.scalar(select(m.AcademicYear).where(
        m.AcademicYear.code == payload.academic_year_code).with_for_update())
    if year:
        if (year.starts_on, year.ends_on) != (payload.year_starts_on, payload.year_ends_on):
            raise HTTPException(409, "Academic year dates differ from the existing year")
        if year.state == "CLOSED":
            raise HTTPException(409, "Academic year is closed")
    else:
        year = m.AcademicYear(id=uuid4(), code=payload.academic_year_code,
            starts_on=payload.year_starts_on, ends_on=payload.year_ends_on, state="DRAFT")
        session.add(year)
        try:
            session.flush()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(409, "Academic year was created concurrently") from exc
    if session.scalar(select(m.ThesisRound.id).where(
        m.ThesisRound.academic_year_id == year.id, m.ThesisRound.code == code)):
        raise HTTPException(409, "Round code already exists in this academic year")
    round_ = m.ThesisRound(id=uuid4(), academic_year_id=year.id, code=code,
        round_type=payload.round_type, opens_at=payload.opens_at,
        closes_at=payload.closes_at, state="DRAFT")
    session.add(round_)
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ROUND_CREATED",
        resource_type="thesis_round", resource_id=round_.id,
        source_reference=basis, occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Academic year or round was created concurrently") from exc
    return {"id": str(round_.id), "state": round_.state}


@router.patch("/rounds/{round_id}/schedule")
def update_round_schedule(round_id: UUID, payload: RoundScheduleUpdate,
                          if_match: int = Header(alias="If-Match"),
                          user: m.UserAccount = Depends(current_user),
                          session: Session = Depends(get_session)) -> dict:
    _admin(user)
    round_ = session.scalar(select(m.ThesisRound).where(
        m.ThesisRound.id == round_id).with_for_update())
    if not round_:
        raise HTTPException(404, "Round not found")
    if round_.state != "DRAFT":
        raise HTTPException(409, "Only a draft round can be edited")
    if round_.row_version != if_match:
        raise HTTPException(409, "Round has changed; reload it")
    year = session.get(m.AcademicYear, round_.academic_year_id)
    if payload.opens_at.date() < year.starts_on or payload.closes_at.date() > year.ends_on:
        raise HTTPException(422, "Registration dates must fall within the academic year")
    code, reason = payload.code.strip(), payload.reason.strip()
    if not code or not reason:
        raise HTTPException(422, "Round code and change reason are required")
    if session.scalar(select(m.ThesisRound.id).where(
        m.ThesisRound.academic_year_id == year.id,
        m.ThesisRound.code == code, m.ThesisRound.id != round_.id)):
        raise HTTPException(409, "Round code already exists in this academic year")
    round_.code = code
    round_.round_type = payload.round_type
    round_.opens_at = payload.opens_at
    round_.closes_at = payload.closes_at
    round_.row_version += 1
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ROUND_SCHEDULE_UPDATED",
        resource_type="thesis_round", resource_id=round_.id,
        reason=reason, occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Round code was changed concurrently") from exc
    return {"id": str(round_.id), "state": round_.state, "row_version": round_.row_version}


@router.post("/rounds/{round_id}/extend")
def extend_round_registration(round_id: UUID, payload: RoundExtension,
                              if_match: int = Header(alias="If-Match", ge=1),
                              user: m.UserAccount = Depends(current_user),
                              session: Session = Depends(get_session)) -> dict:
    _admin(user)
    round_ = session.scalar(select(m.ThesisRound).where(
        m.ThesisRound.id == round_id).with_for_update())
    if not round_:
        raise HTTPException(404, "Không tìm thấy đợt KLTN")
    if round_.row_version != if_match:
        raise HTTPException(409, "Đợt đã thay đổi. Hãy tải lại trước khi gia hạn")
    reopening = round_.state == "CLOSED" and payload.reopen_closed
    if round_.state != "OPEN" and not reopening:
        raise HTTPException(409, "Chọn xác nhận mở lại khi gia hạn đợt đã đóng")
    instant = datetime.now(timezone.utc)
    new_end = payload.closes_at.astimezone(timezone.utc)
    if new_end <= round_.closes_at or new_end <= instant:
        raise HTTPException(422, "Hạn mới phải sau hạn cũ và sau thời điểm hiện tại")
    year = session.get(m.AcademicYear, round_.academic_year_id)
    if year.state == "CLOSED" or new_end.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date() > year.ends_on:
        raise HTTPException(422, "Hạn mới phải thuộc năm học đang hoạt động")
    basis = payload.basis_ref.strip()
    reason = payload.reason.strip()
    if len(basis) < 3 or len(reason) < 5:
        raise HTTPException(422, "Nhập căn cứ và lý do gia hạn")
    previous_end = round_.closes_at
    round_.closes_at = new_end
    round_.state = "OPEN"
    round_.row_version += 1
    event = "ROUND_REGISTRATION_REOPENED" if reopening else "ROUND_REGISTRATION_EXTENDED"
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action=event,
        resource_type="thesis_round", resource_id=round_.id, source_reference=basis,
        reason=f"Hạn cũ: {previous_end.isoformat()} · Hạn mới: {new_end.isoformat()} · {reason}",
        occurred_at=instant, correlation_id=uuid4()))
    round_announcement(session, user.id, round_.id, event,
        f"Khoa đã {'gia hạn và mở lại' if reopening else 'gia hạn'} đăng ký KLTN đợt {round_.code} đến {format_due(new_end)}.", "/topics")
    session.commit()
    return {"id": str(round_.id), "state": round_.state, "row_version": round_.row_version,
            "closes_at": round_.closes_at}


@router.get("/rounds/{round_id}/history")
def round_history(round_id: UUID, user=Depends(current_user), session=Depends(get_session)):
    _admin(user)
    if not session.get(m.ThesisRound,round_id):
        raise HTTPException(404,"Không tìm thấy đợt")
    from backend.services.workflow_notices import actor_name
    rows = session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_type=="thesis_round",
        m.AuditEvent.resource_id==round_id).order_by(m.AuditEvent.occurred_at.desc(),m.AuditEvent.id.desc())).all()
    return [{"id":row.id,"action":row.action,"reason":row.reason,"reference":row.source_reference,
        "at":row.occurred_at,"actor":actor_name(session,row.actor_id)} for row in rows]


@router.patch("/rounds/{round_id}")
def change_round_state(round_id: UUID, payload: RoundStateChange,
                       if_match: int = Header(alias="If-Match"),
                       user: m.UserAccount = Depends(current_user),
                       session: Session = Depends(get_session)) -> dict:
    _admin(user)
    round_ = session.scalar(select(m.ThesisRound).where(
        m.ThesisRound.id == round_id).with_for_update())
    if not round_:
        raise HTTPException(404, "Round not found")
    if round_.row_version != if_match:
        raise HTTPException(409, "Round has changed; reload it")
    if (round_.state, payload.state) not in {("DRAFT", "OPEN"), ("OPEN", "CLOSED")}:
        raise HTTPException(409, "Only draft rounds can open and only open rounds can close")
    if not payload.reason.strip():
        raise HTTPException(422, "A reason or schedule reference is required")
    if payload.state == "OPEN":
        if round_.closes_at <= datetime.now(timezone.utc):
            raise HTTPException(409, "Registration deadline has passed")
        year = session.scalar(select(m.AcademicYear).where(
            m.AcademicYear.id == round_.academic_year_id).with_for_update())
        if year.state == "CLOSED":
            raise HTTPException(409, "Academic year is closed")
        year.state = "ACTIVE"
        year.row_version += 1
    round_.state = payload.state
    round_.row_version += 1
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id,
        action="ROUND_OPENED" if payload.state == "OPEN" else "ROUND_CLOSED",
        resource_type="thesis_round", resource_id=round_.id,
        reason=payload.reason.strip(), occurred_at=datetime.now(timezone.utc),
        correlation_id=uuid4()))
    if payload.state == "OPEN":
        round_announcement(session, user.id, round_.id, "ROUND_OPENED",
            f"Khoa đã mở đợt đăng ký KLTN {round_.code}. Thời gian đăng ký từ {format_due(round_.opens_at)} đến {format_due(round_.closes_at)}.",
            "/topics")
    else:
        round_announcement(session, user.id, round_.id, "ROUND_CLOSED",
            f"Khoa đã đóng đợt đăng ký KLTN {round_.code}.", "/topics")
    session.commit()
    return {"id": str(round_.id), "state": round_.state, "row_version": round_.row_version}


@router.get("/users/directory")
def users_directory(search: str = "", category: Literal[
        "ALL", "STUDENT", "LECTURER", "ADMIN", "LECTURER_WITH_DUTIES"] = "ALL",
        additional_role: str = "", account_status: Literal["ALL", "PENDING", "ACTIVE", "LOCKED", "DISABLED"] = "ALL", offset: int = 0, limit: int = 20,
        user: m.UserAccount = Depends(current_user),
        session: Session = Depends(get_session)) -> dict:
    """Admin account directory with real, currently effective lecturer duties."""
    _admin(user)
    if len(search) > 100 or len(additional_role) > 50:
        raise HTTPException(422, "Search or role filter is too long")
    if not 0 <= offset <= 100_000 or not 1 <= limit <= 100:
        raise HTTPException(422, "Invalid paging range")
    return build_account_directory(
        session, search=search, category=category, additional_role=additional_role,
        offset=offset, limit=limit, account_status=account_status,
    )


@router.get("/users")
def users(search: str = "", offset: int = 0, limit: int = 100,
          account_status: Literal["ALL", "PENDING", "ACTIVE", "LOCKED", "DISABLED"] = "ALL",
          user: m.UserAccount = Depends(current_user),
          session: Session = Depends(get_session)) -> list[dict]:
    rounds = _managed_rounds(session, user) if user.base_role != "ADMIN" else []
    if user.base_role != "ADMIN" and not rounds:
        raise HTTPException(403, "Account management assignment required")
    if len(search) > 100:
        raise HTTPException(422, "Search is too long")
    if not 0 <= offset <= 100_000 or not 1 <= limit <= 100:
        raise HTTPException(422, "Invalid paging range")
    query = select(m.UserAccount).order_by(m.UserAccount.created_at.desc()).offset(offset).limit(limit)
    if user.base_role != "ADMIN":
        query = query.where(m.UserAccount.id.in_(select(m.StudentProfile.user_id)
            .join(m.EligibilitySnapshot, m.EligibilitySnapshot.student_id == m.StudentProfile.id)
            .where(m.EligibilitySnapshot.round_id.in_(rounds))))
    if account_status == "PENDING":
        query = query.where(m.UserAccount.status == "DISABLED", m.UserAccount.email_verified_at.is_(None))
    elif account_status == "DISABLED":
        query = query.where(m.UserAccount.status == "DISABLED", m.UserAccount.email_verified_at.is_not(None))
    elif account_status != "ALL":
        query = query.where(m.UserAccount.status == account_status)
    if search.strip():
        term = search.strip().lower()
        query = query.where(or_(func.lower(m.UserAccount.email).contains(term),
            m.UserAccount.id.in_(select(m.StudentProfile.user_id).where(
                func.lower(m.StudentProfile.student_code).contains(term)))))
    result = []
    for row in session.scalars(query).all():
        student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == row.id)) if row.base_role == "STUDENT" else None
        result.append({"id": str(row.id), "email": row.email, "base_role": row.base_role,
            "status": row.status, "verified": row.email_verified_at is not None,
            "student_code": student.student_code if student else None,
            "display_name": student.display_name if student else row.email})
    return result


@router.get("/staff")
def staff_accounts(user: m.UserAccount = Depends(current_user),
                   session: Session = Depends(get_session)) -> list[dict]:
    """Active assignment candidates with identity; never return credentials."""
    _admin(user)
    rows = session.execute(select(
        m.UserAccount.id, m.UserAccount.email, m.UserAccount.base_role,
        m.UserAccount.status, m.UserAccount.email_verified_at,
        m.LecturerProfile.display_name, m.LecturerProfile.lecturer_code,
    ).select_from(m.UserAccount).outerjoin(m.LecturerProfile,
        m.LecturerProfile.user_id == m.UserAccount.id).where(
        m.UserAccount.status == "ACTIVE",
        m.UserAccount.base_role.in_(["ADMIN", "LECTURER"]),
    ).order_by(m.LecturerProfile.display_name, m.UserAccount.email, m.UserAccount.id)).all()
    return [{"id": str(row.id), "email": row.email, "base_role": row.base_role,
             "status": row.status, "verified": row.email_verified_at is not None,
             "student_code": None, "display_name": row.display_name or row.email,
             "lecturer_code": row.lecturer_code} for row in rows]


@router.post("/lecturers", status_code=201)
def invite_lecturer(payload: LecturerInvite, user: m.UserAccount = Depends(current_user),
                    session: Session = Depends(get_session)) -> dict:
    _admin(user)
    email = payload.email.strip().lower()
    if not EMAIL.fullmatch(email):
        raise HTTPException(422, "Invalid email")
    department = session.get(m.Department, payload.department_id)
    if not department or not department.active:
        raise HTTPException(422, "Department is unavailable")
    if not payload.lecturer_code.strip() or not payload.display_name.strip():
        raise HTTPException(422, "Lecturer code and name are required")
    lock_identities(session, [(payload.lecturer_code.strip(), email)])
    if session.scalar(select(m.UserAccount.id).where(func.lower(m.UserAccount.email) == email)):
        raise HTTPException(409, "Email is already assigned")
    if session.scalar(select(m.LecturerProfile.id).where(func.lower(m.LecturerProfile.lecturer_code) == payload.lecturer_code.strip().lower())):
        raise HTTPException(409, "Lecturer code is already assigned")
    account = m.UserAccount(id=uuid4(), email=email,
        password_hash=unusable_password(), base_role="LECTURER", status="DISABLED")
    session.add(account)
    session.flush()
    profile = m.LecturerProfile(id=uuid4(), user_id=account.id,
        lecturer_code=payload.lecturer_code.strip(), display_name=payload.display_name.strip(),
        department_id=department.id)
    session.add(profile)
    _audit(session, account, "LECTURER_INVITED", user.id)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Lecturer code or email was assigned concurrently") from exc
    try:
        _mail_link(_mail_recipient(account, profile.display_name, "staff", profile.lecturer_code), "activate")
        delivered = True
    except Exception:
        # The account remains unverified. Staff can request a fresh activation link.
        delivered = False
    record_delivery(session, user, account, delivered)
    session.commit()
    return {"user_id": str(account.id), "invitation_sent": delivered}


@router.post("/round-assignments", status_code=201)
def grant_round_assignment(payload: RoundAssignment,
                           user: m.UserAccount = Depends(current_user),
                           session: Session = Depends(get_session)) -> dict:
    _admin(user)
    target = session.get(m.UserAccount, payload.user_id)
    round_ = session.get(m.ThesisRound, payload.round_id)
    if not target or target.status != "ACTIVE" or target.base_role not in {"ADMIN", "LECTURER"}:
        raise HTTPException(422, "An active staff account is required")
    if payload.assignment_type in {"ACCOUNT_MANAGER", "KLTN_COORDINATOR", "REVIEW_RECORDS_MANAGER"} and target.base_role != "LECTURER":
        raise HTTPException(422, "Round account/progress coordination must be assigned to a lecturer")
    allowed_states = {"DRAFT", "OPEN", "CLOSED"} if payload.assignment_type in {"FORM_MANAGER","REVIEW_RECORDS_MANAGER"} else {"DRAFT", "OPEN"}
    if not round_ or round_.state not in allowed_states:
        raise HTTPException(422, "Round is unavailable")
    existing = session.scalar(select(m.ResourceAssignment.id).where(
        m.ResourceAssignment.user_id == target.id,
        m.ResourceAssignment.round_id == round_.id,
        m.ResourceAssignment.assignment_type == payload.assignment_type,
        m.ResourceAssignment.state == "ACTIVE"))
    if existing:
        raise HTTPException(409, "This assignment already exists")
    assignment_id = uuid4()
    try:
        session.execute(m.ResourceAssignment.__table__.insert().values(
            id=assignment_id, user_id=target.id, round_id=round_.id,
            assignment_type=payload.assignment_type,
            effective_from=datetime.now(timezone.utc), state="ACTIVE"))
        session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ROUND_PERMISSION_GRANTED",
            resource_type="resource_assignment", resource_id=assignment_id,
            source_reference=payload.basis_ref.strip(), occurred_at=datetime.now(timezone.utc),
            correlation_id=uuid4()))
        from backend.services.workflow_notices import assignment_event
        assignment_event(session,user.id,target.id,round_.id,payload.assignment_type)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Assignment was created concurrently") from exc
    return {"assignment_id": str(assignment_id)}


@router.get("/round-assignments")
def round_assignments(user: m.UserAccount = Depends(current_user),
                      session: Session = Depends(get_session)) -> list[dict]:
    _admin(user)
    rows = session.execute(select(
        m.ResourceAssignment.id, m.ResourceAssignment.round_id,
        m.ResourceAssignment.user_id, m.ResourceAssignment.assignment_type).where(
        m.ResourceAssignment.assignment_type.in_(["ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER", "ACCOUNT_MANAGER", "KLTN_COORDINATOR", "FORM_MANAGER", "REVIEW_RECORDS_MANAGER"]),
        m.ResourceAssignment.round_id.is_not(None),
        m.ResourceAssignment.state == "ACTIVE").order_by(m.ResourceAssignment.effective_from.desc()).limit(200)).all()
    return [{"id": str(row.id), "round_id": str(row.round_id),
             "round_code": session.get(m.ThesisRound, row.round_id).code,
             "user_id": str(row.user_id), "email": session.get(m.UserAccount, row.user_id).email,
             "assignment_type": row.assignment_type} for row in rows]


@router.post("/round-assignments/{assignment_id}/revoke", status_code=204)
def revoke_assignment(assignment_id: UUID, payload: AssignmentRevoke,
                      user: m.UserAccount = Depends(current_user),
                      session: Session = Depends(get_session)) -> None:
    _admin(user)
    assignment = session.execute(select(
        m.ResourceAssignment.id, m.ResourceAssignment.state, m.ResourceAssignment.user_id, m.ResourceAssignment.round_id,
        m.ResourceAssignment.assignment_type).where(
        m.ResourceAssignment.id == assignment_id).with_for_update()).one_or_none()
    if not assignment or assignment.state != "ACTIVE" or assignment.assignment_type not in {
            "ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER", "ACCOUNT_MANAGER", "KLTN_COORDINATOR", "FORM_MANAGER", "REVIEW_RECORDS_MANAGER"}:
        raise HTTPException(404, "Active assignment not found")
    session.execute(update(m.ResourceAssignment).where(
        m.ResourceAssignment.id == assignment_id).values(
        state="REVOKED", effective_to=datetime.now(timezone.utc),
        row_version=m.ResourceAssignment.row_version + 1))
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ROUND_PERMISSION_REVOKED",
        resource_type="resource_assignment", resource_id=assignment.id,
        reason=payload.reason.strip(), occurred_at=datetime.now(timezone.utc),
        correlation_id=uuid4()))
    from backend.services.workflow_notices import assignment_event
    assignment_event(session,user.id,assignment.user_id,assignment.round_id,assignment.assignment_type,revoked=True)
    session.commit()


@router.post("/users/{user_id}/lock", status_code=204)
def lock_account(user_id: UUID, payload: AccountStatus,
                 user: m.UserAccount = Depends(current_user),
                 session: Session = Depends(get_session)) -> None:
    if user_id == user.id:
        raise HTTPException(409, "An administrator cannot change their own lock state")
    target = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(404, "Account not found")
    _manageable_student(session, user, target)
    desired = "LOCKED" if payload.locked else ("ACTIVE" if target.email_verified_at else "DISABLED")
    if target.status == desired:
        return
    target.status = desired
    target.row_version += 1
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id,
        action="ACCOUNT_LOCKED" if payload.locked else "ACCOUNT_UNLOCKED",
        resource_type="user_account", resource_id=target.id,
        reason=payload.reason.strip(), occurred_at=datetime.now(timezone.utc),
        correlation_id=uuid4()))
    notify_user(session, recipient_user_id=target.id, actor_user_id=user.id,
        kind="ACCOUNT_LOCKED" if payload.locked else "ACCOUNT_UNLOCKED",
        message=("Tài khoản của bạn đã bị khóa. Lý do: " if payload.locked
                 else "Tài khoản của bạn đã được mở khóa. Lý do: ") + payload.reason.strip())
    session.commit()


@router.post("/users/{user_id}/disable", status_code=204)
def disable_account(user_id: UUID, payload: AccountChangeReason,
                    user: m.UserAccount = Depends(current_user),
                    session: Session = Depends(get_session)) -> None:
    if user_id == user.id:
        raise HTTPException(409, "Cannot disable your own account")
    target = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(404, "Account not found")
    _manageable_student(session, user, target)
    if target.status == "DISABLED":
        raise HTTPException(409, "Account is already disabled")
    target.status = "DISABLED"
    target.row_version += 1
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ACCOUNT_DISABLED",
        resource_type="user_account", resource_id=target.id, reason=payload.reason.strip(),
        occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    notify_user(session, recipient_user_id=target.id, actor_user_id=user.id,
        kind="ACCOUNT_DISABLED",
        message="Tài khoản của bạn đã bị vô hiệu hóa; hồ sơ và lịch sử vẫn được giữ. Lý do: " + payload.reason.strip())
    session.commit()


@router.post("/users/{user_id}/restore", status_code=204)
def restore_account(user_id: UUID, payload: AccountChangeReason,
                    user: m.UserAccount = Depends(current_user),
                    session: Session = Depends(get_session)) -> None:
    if user_id == user.id:
        raise HTTPException(409, "Cannot restore your own account")
    target = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(404, "Account not found")
    _manageable_student(session, user, target)
    if target.status != "DISABLED" or target.email_verified_at is None:
        raise HTTPException(409, "Only previously verified disabled accounts can be restored")
    target.status = "ACTIVE"
    target.row_version += 1
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ACCOUNT_RESTORED",
        resource_type="user_account", resource_id=target.id, reason=payload.reason.strip(),
        occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    notify_user(session, recipient_user_id=target.id, actor_user_id=user.id,
        kind="ACCOUNT_RESTORED",
        message="Tài khoản của bạn đã được mở lại. Hãy đăng nhập và tiếp tục công việc.")
    session.commit()


@router.post("/users/{user_id}/reissue-link")
def reissue_link(user_id: UUID, payload: AccountChangeReason,
                 user: m.UserAccount = Depends(current_user),
                 session: Session = Depends(get_session)) -> dict:
    target = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(404, "Account not found")
    _manageable_student(session, user, target)
    if target.status == "LOCKED" or (target.status == "DISABLED" and target.email_verified_at):
        raise HTTPException(409, "Unlock or restore the account before issuing a link")
    student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == target.id)) if target.base_role == "STUDENT" else None
    if student and not _student_can_activate(session, student):
        raise HTTPException(409, "Student participation is not confirmed")
    if not mail_delivery_ready():
        raise HTTPException(503, "Email delivery is unavailable")
    purpose = "activate" if target.status == "DISABLED" else "reset"
    if target.base_role == "LECTURER" and purpose == "activate":
        last = session.scalar(select(m.AuditEvent.occurred_at).where(
            m.AuditEvent.resource_type == "user_account", m.AuditEvent.resource_id == target.id,
            m.AuditEvent.action.in_(MAIL_ACTIONS)).order_by(m.AuditEvent.occurred_at.desc()).limit(1))
        if last and last + timedelta(seconds=60) > datetime.now(timezone.utc):
            raise HTTPException(429, "Vừa gửi liên kết; vui lòng đợi 60 giây rồi thử lại.")
        _audit(session, target, "LECTURER_ACTIVATION_SENDING", user.id)
    target.row_version += 1  # Invalidate earlier links and sessions before issuing a new link.
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ACCOUNT_LINK_REISSUED",
        resource_type="user_account", resource_id=target.id, reason=payload.reason.strip(),
        occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    notify_user(session, recipient_user_id=target.id, actor_user_id=user.id,
        kind="ACCOUNT_LINK_REISSUED",
        message="Khoa đã cấp lại liên kết đăng nhập cho tài khoản của bạn qua email đang lưu.")
    session.commit()
    try:
        _mail_link(_mail_recipient(target, _account_display_name(session, target), "staff", _account_identifier(session, target)), purpose)
        delivered = True
    except Exception:
        delivered = False
    if target.base_role == "LECTURER" and purpose == "activate":
        record_delivery(session, user, target, delivered)
        session.commit()
    return {"link_sent": delivered, "purpose": purpose}


def _replace_email(session: Session, actor: m.UserAccount, target: m.UserAccount,
                   email: str, basis_ref: str, reason: str) -> None:
    """Keep the UUID and history; make every old link and password unusable."""
    previous = target.email
    target.email = email
    target.email_verified_at = None
    target.password_hash = unusable_password()
    if target.status != "LOCKED":
        target.status = "DISABLED"
    target.row_version += 1
    session.add(m.AuditEvent(id=uuid4(), actor_id=actor.id, action="ACCOUNT_EMAIL_CORRECTED",
        resource_type="user_account", resource_id=target.id,
        before_hash=hashlib.sha256((previous or "").encode()).hexdigest(),
        after_hash=hashlib.sha256(email.encode()).hexdigest(),
        reason=reason.strip(), source_reference=basis_ref.strip(),
        occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    notify_user(session, recipient_user_id=target.id, actor_user_id=actor.id,
        kind="ACCOUNT_EMAIL_CORRECTED",
        message="Email đăng nhập của bạn đã được Khoa cập nhật. Hãy dùng liên kết kích hoạt mới gửi tới email này.")
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Email was assigned concurrently") from exc


@router.patch("/users/{user_id}/email")
def correct_student_email(user_id: UUID, payload: StudentEmailCorrection,
                          user: m.UserAccount = Depends(current_user),
                          session: Session = Depends(get_session)) -> dict:
    target = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if target is None or target.base_role != "STUDENT":
        raise HTTPException(404, "Student account not found")
    student = _manageable_student(session, user, target, payload.round_id)
    if student is None or student.student_code != payload.student_code.strip():
        raise HTTPException(409, "Student code does not match the official roster entry")
    if session.scalar(select(m.EligibilitySnapshot.id).where(m.EligibilitySnapshot.student_id == student.id,
            m.EligibilitySnapshot.round_id == payload.round_id).limit(1)) is None:
        raise HTTPException(409, "Student is not in the specified round")
    email = payload.email.strip().lower()
    if not EMAIL.fullmatch(email) or len(payload.basis_ref.strip()) < 3 or len(payload.reason.strip()) < 5:
        raise HTTPException(422, "Valid email, official reference and reason are required")
    if target.email == email:
        raise HTTPException(409, "Email is unchanged")
    if session.scalar(select(m.UserAccount.id).where(func.lower(m.UserAccount.email) == email,
            m.UserAccount.id != target.id).limit(1)):
        raise HTTPException(409, "Email is assigned to another account")
    _replace_email(session, user, target, email, payload.basis_ref, payload.reason)
    delivered = False
    if target.status == "DISABLED" and _student_can_activate(session, student) and mail_delivery_ready():
        try:
            _mail_link(_mail_recipient(target, student.display_name, "staff", student.student_code), "activate")
            delivered = True
        except Exception:
            pass
    return {"user_id": str(target.id), "activation_required": True, "activation_sent": delivered}


@router.patch("/users/{user_id}/contact-email")
def correct_staff_email(user_id: UUID, payload: StaffEmailCorrection,
                        user: m.UserAccount = Depends(current_user),
                        session: Session = Depends(get_session)) -> dict:
    """ADMIN corrects a lecturer/administrator email after checking the Faculty reference."""
    _admin(user)
    if user_id == user.id:
        raise HTTPException(409, "Another administrator must correct your own email")
    target = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(404, "Account not found")
    if target.base_role == "STUDENT":
        raise HTTPException(409, "Student email correction uses the official roster check")
    email = payload.email.strip().lower()
    if not EMAIL.fullmatch(email) or len(payload.reason.strip()) < 5:
        raise HTTPException(422, "Valid email, official reference and reason are required")
    if target.email == email:
        raise HTTPException(409, "Email is unchanged")
    if session.scalar(select(m.UserAccount.id).where(func.lower(m.UserAccount.email) == email,
            m.UserAccount.id != target.id).limit(1)):
        raise HTTPException(409, "Email is assigned to another account")
    _replace_email(session, user, target, email, payload.basis_ref, payload.reason)
    delivered = False
    if target.status == "DISABLED" and mail_delivery_ready():
        try:
            _mail_link(_mail_recipient(target, _account_display_name(session, target), "staff", _account_identifier(session, target)), "activate")
            delivered = True
        except Exception:
            pass
        if target.base_role == "LECTURER":
            record_delivery(session, user, target, delivered)
            session.commit()
    return {"user_id": str(target.id), "activation_required": True, "activation_sent": delivered}


@router.get("/dashboard")
def dashboard(user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    _admin(user)
    def grouped(column):
        return dict(session.execute(select(column, func.count()).group_by(column)).all())
    return {"generated_at": datetime.now(timezone.utc),
        "accounts": grouped(m.UserAccount.base_role), "account_status": grouped(case(((m.UserAccount.status == "DISABLED") & m.UserAccount.email_verified_at.is_(None), "PENDING_ACTIVATION"), else_=m.UserAccount.status)),
        "rounds": grouped(m.ThesisRound.state), "topics": grouped(case((m.Topic.archived_at.is_not(None), "ARCHIVED"), else_=m.Topic.state)),
        "registrations": grouped(m.TopicRegistration.state), "theses": grouped(m.Thesis.state),
        "documents": grouped(m.DocumentVersion.state), "reports": grouped(m.ProgressReport.state)}
