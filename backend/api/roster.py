"""Round-scoped roster preview, import, confirmation and correction."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.dependencies import current_user, get_session
from backend.db.models import entities as m
from backend.services.roster import (
    CODE, EMAIL, MAX_BYTES, assigned, import_roster, parse_roster, require_assignment, validate_rows,
)
from backend.services.passwords import unusable_password

router = APIRouter(prefix="/api/v1/rounds/{round_id}/roster", tags=["eligibility roster"])
assignment_router = APIRouter(prefix="/api/v1/me", tags=["eligibility roster"])


@assignment_router.get("/round-assignments")
def my_round_assignments(user: m.UserAccount = Depends(current_user),
                         session: Session = Depends(get_session)) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows = session.scalars(select(m.ResourceAssignment).where(
        m.ResourceAssignment.user_id == user.id,
        m.ResourceAssignment.assignment_type.in_(["ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER"]),
        m.ResourceAssignment.round_id.is_not(None),
        m.ResourceAssignment.state == "ACTIVE",
        m.ResourceAssignment.effective_from <= now,
        (m.ResourceAssignment.effective_to.is_(None) | (m.ResourceAssignment.effective_to > now)),
    )).all()
    return [{"round_id": str(row.round_id), "round_code": session.get(m.ThesisRound, row.round_id).code,
             "assignment_type": row.assignment_type} for row in rows]


class ConfirmRows(BaseModel):
    snapshot_ids: list[UUID] = Field(min_length=1, max_length=1000)
    basis_ref: str = Field(min_length=3, max_length=500)


class RevokeStudent(BaseModel):
    student_id: UUID
    reason: str = Field(min_length=5, max_length=2000)
    basis_ref: str = Field(min_length=3, max_length=500)


class CorrectStudent(BaseModel):
    student_code: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    class_name: str = Field(min_length=1, max_length=100)
    major_code: str = Field(min_length=1, max_length=32)
    basis_ref: str = Field(min_length=3, max_length=500)


async def _read_file(request: Request, name: str) -> tuple[list, str]:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BYTES:
        raise HTTPException(413, "Roster exceeds 2 MB")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Roster exceeds 2 MB")
    return parse_roster(name, bytes(data))


@router.post("/preview")
async def preview(round_id: UUID, request: Request,
                  file_name: str = Header(alias="X-File-Name"),
                  user: m.UserAccount = Depends(current_user),
                  session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_IMPORTER")
    rows, digest = await _read_file(request, file_name)
    validate_rows(session, rows)
    # Only authorized staff see names. Never return passwords, GPA or transcript data.
    return {"sha256": digest, "count": len(rows), "rows": [row.__dict__ for row in rows]}


@router.post("")
async def import_file(round_id: UUID, request: Request,
                      reference: str = Query(min_length=3, max_length=500),
                      file_name: str = Header(alias="X-File-Name"),
                      preview_sha256: str = Header(alias="X-Preview-SHA256"),
                      user: m.UserAccount = Depends(current_user),
                      session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_IMPORTER")
    rows, digest = await _read_file(request, file_name)
    if digest != preview_sha256:
        raise HTTPException(409, "File changed since preview")
    if len(reference.strip()) < 3:
        raise HTTPException(422, "A document reference is required")
    return import_roster(session, user, round_id, rows, reference.strip())


@router.get("")
def list_roster(round_id: UUID, user: m.UserAccount = Depends(current_user),
                session: Session = Depends(get_session)) -> list[dict]:
    if not (assigned(session, user, round_id, "ELIGIBILITY_IMPORTER")
            or assigned(session, user, round_id, "ELIGIBILITY_VERIFIER")):
        raise HTTPException(403, "Round assignment required")
    snapshots = session.scalars(select(m.EligibilitySnapshot).where(
        m.EligibilitySnapshot.round_id == round_id).order_by(
            m.EligibilitySnapshot.student_id, m.EligibilitySnapshot.version.desc())).all()
    latest: dict[UUID, m.EligibilitySnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.student_id, snapshot)
    rows = []
    for snapshot in latest.values():
        student = session.get(m.StudentProfile, snapshot.student_id)
        account = session.get(m.UserAccount, student.user_id)
        rows.append({"snapshot_id": str(snapshot.id), "student_id": str(student.id),
            "student_code": student.student_code, "display_name": student.display_name,
            "class_name": student.class_name, "major_code": student.major_code,
            "email": account.email, "account_status": account.status,
            "state": snapshot.state, "version": snapshot.version,
            "evidence_ref": snapshot.evidence_ref,
            "confirmed_at": snapshot.confirmed_at.isoformat() if snapshot.confirmed_at else None})
    return sorted(rows, key=lambda row: row["student_code"])


@router.post("/confirm")
def confirm_roster(round_id: UUID, payload: ConfirmRows,
                   user: m.UserAccount = Depends(current_user),
                   session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_VERIFIER")
    if len(set(payload.snapshot_ids)) != len(payload.snapshot_ids):
        raise HTTPException(422, "Duplicate snapshot IDs")
    if len(payload.basis_ref.strip()) < 3:
        raise HTTPException(422, "A confirmation reference is required")
    snapshots = session.scalars(select(m.EligibilitySnapshot).where(
        m.EligibilitySnapshot.id.in_(payload.snapshot_ids)).with_for_update()).all()
    if len(snapshots) != len(payload.snapshot_ids) or any(
            row.round_id != round_id or row.state != "SUBMITTED" for row in snapshots):
        raise HTTPException(409, "Selection changed; reload the roster")
    now = datetime.now(timezone.utc)
    for row in snapshots:
        latest = session.scalar(select(m.EligibilitySnapshot.version).where(
            m.EligibilitySnapshot.student_id == row.student_id,
            m.EligibilitySnapshot.round_id == round_id).order_by(
                m.EligibilitySnapshot.version.desc()).limit(1))
        if row.version != latest:
            raise HTTPException(409, "A newer eligibility decision exists")
        row.state = "CONFIRMED"
        row.confirmed_by = user.id
        row.confirmed_at = now
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ELIGIBILITY_ROSTER_CONFIRMED",
        resource_type="thesis_round", resource_id=round_id,
        reason=f"basis={payload.basis_ref.strip()}; count={len(snapshots)}",
        occurred_at=now, correlation_id=uuid4()))
    session.commit()
    return {"confirmed": len(snapshots)}


@router.post("/revoke")
def revoke_eligibility(round_id: UUID, payload: RevokeStudent,
                       user: m.UserAccount = Depends(current_user),
                       session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_VERIFIER")
    if len(payload.basis_ref.strip()) < 3 or len(payload.reason.strip()) < 5:
        raise HTTPException(422, "A reference and reason are required")
    latest = session.scalar(select(m.EligibilitySnapshot).where(
        m.EligibilitySnapshot.student_id == payload.student_id,
        m.EligibilitySnapshot.round_id == round_id,
    ).order_by(m.EligibilitySnapshot.version.desc()).limit(1).with_for_update())
    if latest is None or latest.state != "CONFIRMED":
        raise HTTPException(409, "Only a current confirmed result can be revoked")
    now = datetime.now(timezone.utc)
    replacement = m.EligibilitySnapshot(id=uuid4(), student_id=payload.student_id,
        round_id=round_id, version=latest.version + 1, evidence_ref=payload.basis_ref.strip(),
        captured_at=now, confirmed_by=user.id, confirmed_at=now,
        decision_reason=payload.reason.strip(), state="REJECTED")
    session.add(replacement)
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ELIGIBILITY_REVOKED",
        resource_type="eligibility_snapshot", resource_id=replacement.id,
        reason=payload.reason.strip(), occurred_at=now, correlation_id=uuid4()))
    session.commit()
    return {"state": "REJECTED", "snapshot_id": str(replacement.id),
            "note": "Existing academic records were preserved for manual review"}


@router.patch("/{student_id}")
def correct_student(round_id: UUID, student_id: UUID, payload: CorrectStudent,
                    user: m.UserAccount = Depends(current_user),
                    session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_VERIFIER")
    code = payload.student_code.strip()
    name = payload.display_name.strip()
    email = payload.email.strip().lower()
    class_name = payload.class_name.strip()
    major_code = payload.major_code.strip()
    if (not CODE.fullmatch(code) or not EMAIL.fullmatch(email) or not name
            or not class_name or not CODE.fullmatch(major_code)
            or len(payload.basis_ref.strip()) < 3):
        raise HTTPException(422, "Invalid correction or missing document reference")
    snapshot = session.scalar(select(m.EligibilitySnapshot.id).where(
        m.EligibilitySnapshot.student_id == student_id,
        m.EligibilitySnapshot.round_id == round_id).limit(1))
    if snapshot is None:
        raise HTTPException(404, "Student is not in this round")
    student = session.scalar(select(m.StudentProfile).where(
        m.StudentProfile.id == student_id).with_for_update())
    account = session.scalar(select(m.UserAccount).where(
        m.UserAccount.id == student.user_id).with_for_update())
    department = session.get(m.Department, student.department_id)
    if department.major_code and department.major_code != major_code:
        raise HTTPException(422, "Major does not match the department; review assignment separately")
    duplicate_code = session.scalar(select(m.StudentProfile.id).where(
        m.StudentProfile.student_code == code, m.StudentProfile.id != student.id))
    duplicate_email = session.scalar(select(m.UserAccount.id).where(
        func.lower(m.UserAccount.email) == email, m.UserAccount.id != account.id))
    if duplicate_code or duplicate_email:
        raise HTTPException(409, "Student code or email is already assigned")
    def fingerprint() -> str:
        fields = {"code": student.student_code, "name": student.display_name,
                  "class": student.class_name, "major": student.major_code, "email": account.email}
        return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    before = fingerprint()
    email_changed = account.email != email
    student.student_code = code
    student.display_name = name
    student.class_name = class_name
    student.major_code = major_code
    if email_changed:
        account.email = email
        account.email_verified_at = None
        account.password_hash = unusable_password()
        if account.status == "ACTIVE":
            account.status = "DISABLED"
        account.row_version += 1
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ROSTER_IDENTITY_CORRECTED",
        resource_type="student_profile", resource_id=student.id,
        before_hash=before, after_hash=fingerprint(), reason=payload.basis_ref.strip(),
        occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Identity changed concurrently; reload and retry") from exc
    return {"student_id": str(student.id), "activation_required": email_changed}
