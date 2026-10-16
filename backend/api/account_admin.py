"""Technical account provisioning; academic approval stays round-scoped."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.account import _audit, _mail_link
from backend.api.dependencies import current_user, get_session
from backend.db.models import entities as m
from backend.services.passwords import unusable_password
from backend.services.roster import EMAIL

router = APIRouter(prefix="/api/v1/admin", tags=["account administration"])


class LecturerInvite(BaseModel):
    lecturer_code: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    department_id: UUID


class RoundAssignment(BaseModel):
    round_id: UUID
    user_id: UUID
    assignment_type: str = Field(pattern="^(ELIGIBILITY_IMPORTER|ELIGIBILITY_VERIFIER)$")
    basis_ref: str = Field(min_length=3, max_length=500)


class AccountStatus(BaseModel):
    locked: bool
    reason: str = Field(min_length=5, max_length=1000)


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
        reason=basis, occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
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
    session.commit()
    return {"id": str(round_.id), "state": round_.state, "row_version": round_.row_version}


@router.get("/users")
def users(search: str = "", user: m.UserAccount = Depends(current_user),
          session: Session = Depends(get_session)) -> list[dict]:
    _admin(user)
    if len(search) > 100:
        raise HTTPException(422, "Search is too long")
    query = select(m.UserAccount).order_by(m.UserAccount.created_at.desc()).limit(100)
    if search.strip():
        query = query.where(func.lower(m.UserAccount.email).contains(search.strip().lower()))
    return [{"id": str(row.id), "email": row.email, "base_role": row.base_role,
             "status": row.status, "verified": row.email_verified_at is not None}
            for row in session.scalars(query).all()]


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
    if session.scalar(select(m.UserAccount.id).where(func.lower(m.UserAccount.email) == email)):
        raise HTTPException(409, "Email is already assigned")
    if session.scalar(select(m.LecturerProfile.id).where(m.LecturerProfile.lecturer_code == payload.lecturer_code.strip())):
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
        _mail_link(account, "activate")
        delivered = True
    except Exception:
        # The account remains unverified. Staff can request a fresh activation link.
        delivered = False
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
    if not round_ or round_.state not in {"DRAFT", "OPEN"}:
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
            reason=payload.basis_ref.strip(), occurred_at=datetime.now(timezone.utc),
            correlation_id=uuid4()))
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
        m.ResourceAssignment.assignment_type.in_(["ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER"]),
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
        m.ResourceAssignment.id, m.ResourceAssignment.state,
        m.ResourceAssignment.assignment_type).where(
        m.ResourceAssignment.id == assignment_id).with_for_update()).one_or_none()
    if not assignment or assignment.state != "ACTIVE" or assignment.assignment_type not in {
            "ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER"}:
        raise HTTPException(404, "Active assignment not found")
    session.execute(update(m.ResourceAssignment).where(
        m.ResourceAssignment.id == assignment_id).values(
        state="REVOKED", effective_to=datetime.now(timezone.utc),
        row_version=m.ResourceAssignment.row_version + 1))
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ROUND_PERMISSION_REVOKED",
        resource_type="resource_assignment", resource_id=assignment.id,
        reason=payload.reason.strip(), occurred_at=datetime.now(timezone.utc),
        correlation_id=uuid4()))
    session.commit()


@router.post("/users/{user_id}/lock", status_code=204)
def lock_account(user_id: UUID, payload: AccountStatus,
                 user: m.UserAccount = Depends(current_user),
                 session: Session = Depends(get_session)) -> None:
    _admin(user)
    if user_id == user.id:
        raise HTTPException(409, "An administrator cannot change their own lock state")
    target = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(404, "Account not found")
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
    session.commit()
