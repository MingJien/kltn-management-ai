"""Technical account provisioning; academic approval stays round-scoped."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
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
    return [{"id": str(row.id), "code": row.code, "state": row.state}
            for row in session.scalars(select(m.ThesisRound).where(
                m.ThesisRound.state.in_(["DRAFT", "OPEN"])).order_by(m.ThesisRound.opens_at.desc())).all()]


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
    existing = session.scalar(select(m.ResourceAssignment).where(
        m.ResourceAssignment.user_id == target.id,
        m.ResourceAssignment.round_id == round_.id,
        m.ResourceAssignment.assignment_type == payload.assignment_type,
        m.ResourceAssignment.state == "ACTIVE"))
    if existing:
        raise HTTPException(409, "This assignment already exists")
    grant = m.ResourceAssignment(id=uuid4(), user_id=target.id,
        round_id=round_.id, assignment_type=payload.assignment_type,
        effective_from=datetime.now(timezone.utc), state="ACTIVE")
    session.add(grant)
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ROUND_PERMISSION_GRANTED",
        resource_type="resource_assignment", resource_id=grant.id,
        reason=payload.basis_ref.strip(), occurred_at=datetime.now(timezone.utc),
        correlation_id=uuid4()))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Assignment was created concurrently") from exc
    return {"assignment_id": str(grant.id)}


@router.get("/round-assignments")
def round_assignments(user: m.UserAccount = Depends(current_user),
                      session: Session = Depends(get_session)) -> list[dict]:
    _admin(user)
    rows = session.scalars(select(m.ResourceAssignment).where(
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
    assignment = session.scalar(select(m.ResourceAssignment).where(
        m.ResourceAssignment.id == assignment_id).with_for_update())
    if not assignment or assignment.state != "ACTIVE" or assignment.assignment_type not in {
            "ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER"}:
        raise HTTPException(404, "Active assignment not found")
    assignment.state = "REVOKED"
    assignment.effective_to = datetime.now(timezone.utc)
    assignment.row_version += 1
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
