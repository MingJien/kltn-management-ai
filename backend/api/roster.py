"""Round-scoped roster preview, import, confirmation and correction."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.dependencies import current_user, get_session
from backend.db.models import entities as m
from backend.services.roster import (
    CODE, MAX_BYTES, assigned, import_roster, parse_roster, require_assignment, validate_rows,
)

STUDENT_MAIL_ACTIONS = ("STUDENT_ACTIVATION_SENDING", "STUDENT_ACTIVATION_SENT", "STUDENT_ACTIVATION_FAILED")
router = APIRouter(prefix="/api/v1/rounds/{round_id}/roster", tags=["eligibility roster"])
assignment_router = APIRouter(prefix="/api/v1/me", tags=["eligibility roster"])


@assignment_router.get("/roster-catalog")
def roster_catalog(user: m.UserAccount = Depends(current_user),
                   session: Session = Depends(get_session)) -> list[dict]:
    """The same active catalog is used by the import preview and correction UI."""
    now = datetime.now(timezone.utc)
    scope = session.scalar(select(m.ResourceAssignment.id).where(
        m.ResourceAssignment.user_id == user.id,
        m.ResourceAssignment.assignment_type.in_(["ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER"]),
        m.ResourceAssignment.state == "ACTIVE",
        m.ResourceAssignment.effective_from <= now,
        (m.ResourceAssignment.effective_to.is_(None) | (m.ResourceAssignment.effective_to > now)),
    ).limit(1))
    if scope is None:
        raise HTTPException(403, "Round assignment required")
    departments = {row.id: row for row in session.scalars(select(m.Department).where(
        m.Department.active.is_(True))).all()}
    return [{"department_code": departments[row.department_id].code,
             "department_name": departments[row.department_id].name,
             "major_code": row.code, "major_name": row.name}
            for row in session.scalars(select(m.DepartmentMajor).where(
                m.DepartmentMajor.active.is_(True)).order_by(m.DepartmentMajor.code)).all()
            if row.department_id in departments]


@assignment_router.get("/round-assignments")
def my_round_assignments(user: m.UserAccount = Depends(current_user),
                         session: Session = Depends(get_session)) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows = session.execute(select(
        m.ResourceAssignment.round_id, m.ResourceAssignment.assignment_type).where(
        m.ResourceAssignment.user_id == user.id,
        m.ResourceAssignment.assignment_type.in_(["ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER", "ACCOUNT_MANAGER", "KLTN_COORDINATOR"]),
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


class SpecialDecision(BaseModel):
    student_id: UUID
    official_ref: str = Field(min_length=3, max_length=500)
    reason: str = Field(min_length=5, max_length=2000)
    clause_1_verified: bool


class CorrectStudent(BaseModel):
    student_code: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1, max_length=255)
    class_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    major_code: str = Field(min_length=1, max_length=32)
    basis_ref: str = Field(min_length=3, max_length=500)
    reason: str = Field(min_length=5, max_length=1000)


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
    for row in rows:
        student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.student_code == row.student_code))
        if student:
            latest = session.scalar(select(m.EligibilitySnapshot).where(
                m.EligibilitySnapshot.student_id == student.id, m.EligibilitySnapshot.round_id == round_id
            ).order_by(m.EligibilitySnapshot.version.desc()).limit(1))
            if latest and latest.state == "REJECTED":
                raise HTTPException(409, f"Sinh viên {row.student_code} đã bị thu hồi. Hãy khôi phục quyền tham gia với căn cứ mới trước khi nhập lại.")
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
    submitted_rows = session.execute(
        select(
            m.RegistrationMember.student_id,
            func.max(m.TopicRegistration.submitted_at).label("submitted_at"),
        )
        .join(m.TopicRegistration, m.TopicRegistration.id == m.RegistrationMember.registration_id)
        .where(
            m.RegistrationMember.round_id == round_id,
            m.RegistrationMember.active.is_(True),
            m.TopicRegistration.state.in_(("SUBMITTED", "RETURNED", "LECTURER_ACCEPTED", "FINALIZED")),
            m.TopicRegistration.submitted_at.is_not(None),
        )
        .group_by(m.RegistrationMember.student_id)
    ).all()
    registration_by_student = {row.student_id: row.submitted_at for row in submitted_rows}
    snapshots = session.scalars(select(m.EligibilitySnapshot).where(
        m.EligibilitySnapshot.round_id == round_id).order_by(
            m.EligibilitySnapshot.student_id, m.EligibilitySnapshot.version.desc())).all()
    latest: dict[UUID, m.EligibilitySnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.student_id, snapshot)
    from backend.services.account_mail import delivery_mode, mail_delivery_ready
    student_ids = [snapshot.student_id for snapshot in latest.values()]
    profiles = session.scalars(select(m.StudentProfile).where(m.StudentProfile.id.in_(student_ids))).all() if student_ids else []
    user_ids = [profile.user_id for profile in profiles]
    mail_events = {}
    if user.base_role == "ADMIN" and user_ids:
        for event in session.scalars(select(m.AuditEvent).where(
                m.AuditEvent.resource_type == "user_account", m.AuditEvent.resource_id.in_(user_ids),
                m.AuditEvent.action.in_((*STUDENT_MAIL_ACTIONS, "ACCOUNT_EMAIL_CORRECTED")))
                .order_by(m.AuditEvent.occurred_at.desc(), case(
                    (m.AuditEvent.action.in_(("STUDENT_ACTIVATION_SENT", "STUDENT_ACTIVATION_FAILED")), 1),
                    else_=0).desc(), m.AuditEvent.id.desc())):
            mail_events.setdefault(event.resource_id, event)
    now = datetime.now(timezone.utc)
    rows = []
    for snapshot in latest.values():
        student = session.get(m.StudentProfile, snapshot.student_id)
        account = session.get(m.UserAccount, student.user_id)
        event = mail_events.get(account.id)
        retry_at = event.occurred_at + timedelta(seconds=60) if event and event.action in STUDENT_MAIL_ACTIONS else None
        status = event.action.removeprefix("STUDENT_ACTIVATION_") if event and event.action in STUDENT_MAIL_ACTIONS else "NOT_RECORDED"
        if account.email_verified_at:
            status = "ACTIVATED"
        elif account.status != "DISABLED" or snapshot.state != "CONFIRMED":
            status = "BLOCKED"
        elif status == "SENDING" and retry_at and retry_at <= now:
            status = "UNKNOWN"
        rows.append({"snapshot_id": str(snapshot.id), "student_id": str(student.id),
            "student_code": student.student_code, "display_name": student.display_name,
            "class_name": student.class_name, "major_code": student.major_code,
            "birth_date": student.birth_date.isoformat() if student.birth_date else None,
            "department_code": session.get(m.Department, student.department_id).code,
            "email": account.email, "account_status": account.status,
            "mail_status": status if user.base_role == "ADMIN" else None,
            "delivery_mode": ({"Kênh gửi: SMTP": "smtp", "Kênh gửi: hộp thư thử nghiệm trên máy": "development_outbox"}.get(event.source_reference, "unknown") if event else "unknown") if user.base_role == "ADMIN" else None,
            "mail_ready": mail_delivery_ready() if user.base_role == "ADMIN" else False,
            "current_delivery_mode": delivery_mode() if user.base_role == "ADMIN" else None,
            "mail_retry_at": retry_at.isoformat() if retry_at else None,
            "can_send_activation": bool(user.base_role == "ADMIN" and snapshot.state == "CONFIRMED" and account.status == "DISABLED" and not account.email_verified_at and account.email and (not retry_at or retry_at <= now)),
            "account_activated": account.email_verified_at is not None,
            "state": snapshot.state, "version": snapshot.version,
            "evidence_ref": snapshot.evidence_ref,
            "confirmed_at": snapshot.confirmed_at.isoformat() if snapshot.confirmed_at else None,
            "registration_submitted": student.id in registration_by_student,
            "registration_submitted_at": (
                registration_by_student[student.id].isoformat()
                if student.id in registration_by_student else None
            )})
    return sorted(rows, key=lambda row: row["student_code"])


@router.post("/{student_id}/activation-link")
def send_student_activation(round_id: UUID, student_id: UUID,
                            user: m.UserAccount = Depends(current_user),
                            session: Session = Depends(get_session)) -> dict:
    """Send only on explicit admin request; self-activation remains available."""
    from backend.api.account import _mail_link, _mail_recipient
    from backend.services.account_mail import delivery_mode, mail_delivery_ready
    if user.base_role != "ADMIN":
        raise HTTPException(403, "Chỉ Admin được gửi liên kết kích hoạt.")
    if not (assigned(session, user, round_id, "ELIGIBILITY_IMPORTER") or
            assigned(session, user, round_id, "ELIGIBILITY_VERIFIER")):
        raise HTTPException(403, "Không có quyền xem danh sách của đợt này.")
    student = session.get(m.StudentProfile, student_id)
    if student is None:
        raise HTTPException(404, "Không tìm thấy sinh viên.")
    account = session.scalar(select(m.UserAccount).where(m.UserAccount.id == student.user_id).with_for_update())
    snapshot = session.scalar(select(m.EligibilitySnapshot).where(
        m.EligibilitySnapshot.student_id == student_id, m.EligibilitySnapshot.round_id == round_id
    ).order_by(m.EligibilitySnapshot.version.desc()).limit(1).with_for_update())
    if not account or account.base_role != "STUDENT" or not snapshot or snapshot.state != "CONFIRMED":
        raise HTTPException(409, "Sinh viên chưa được xác nhận đủ điều kiện trong đợt này.")
    if account.status != "DISABLED" or account.email_verified_at or not account.email:
        raise HTTPException(409, "Chỉ gửi cho tài khoản sinh viên đang chờ kích hoạt.")
    if not mail_delivery_ready():
        raise HTTPException(503, "Dịch vụ gửi thư chưa sẵn sàng.")
    now = datetime.now(timezone.utc)
    last = session.scalar(select(m.AuditEvent.occurred_at).where(
        m.AuditEvent.resource_type == "user_account", m.AuditEvent.resource_id == account.id,
        m.AuditEvent.action.in_(STUDENT_MAIL_ACTIONS)).order_by(m.AuditEvent.occurred_at.desc()).limit(1))
    if last and last + timedelta(seconds=60) > now:
        raise HTTPException(429, "Vừa gửi cho sinh viên này; vui lòng đợi 60 giây.")
    mode = delivery_mode()
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="STUDENT_ACTIVATION_SENDING",
        resource_type="user_account", resource_id=account.id, occurred_at=now, correlation_id=uuid4()))
    session.commit()
    try:
        _mail_link(_mail_recipient(account, student.display_name, "staff", student.student_code), "activate")
        sent = True
    except Exception:
        sent = False
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id,
        action="STUDENT_ACTIVATION_SENT" if sent else "STUDENT_ACTIVATION_FAILED",
        resource_type="user_account", resource_id=account.id, occurred_at=datetime.now(timezone.utc),
        source_reference="Kênh gửi: SMTP" if mode == "smtp" else "Kênh gửi: hộp thư thử nghiệm trên máy",
        correlation_id=uuid4()))
    session.commit()
    return {"sent": sent, "delivery_mode": mode}


@router.post("/confirm")
def confirm_roster(round_id: UUID, payload: ConfirmRows,
                   user: m.UserAccount = Depends(current_user),
                   session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_VERIFIER")
    raise HTTPException(
        410,
        "Danh sách chính thức được ghi nhận đủ điều kiện ngay khi nhập. Hãy nhập lại danh sách để cập nhật hồ sơ chờ từ quy trình cũ.",
    )

@router.post("/special-decision")
def record_special_decision(round_id: UUID, payload: SpecialDecision,
                            user: m.UserAccount = Depends(current_user),
                            session: Session = Depends(get_session)) -> dict:
    """Record a rector's exception to QĐ5964 clause 2; never self-certify."""
    require_assignment(session, user, round_id, "ELIGIBILITY_VERIFIER")
    if not payload.clause_1_verified:
        raise HTTPException(422, "Ngoại lệ khoản 2 chỉ áp dụng sau khi đối chiếu khoản 1 Điều 2 QĐ5964")
    latest = session.scalar(select(m.EligibilitySnapshot).where(
        m.EligibilitySnapshot.student_id == payload.student_id,
        m.EligibilitySnapshot.round_id == round_id).order_by(
            m.EligibilitySnapshot.version.desc()).limit(1).with_for_update())
    if latest is None:
        raise HTTPException(404, "Sinh viên chưa có trong danh sách đợt này")
    if latest.state == "CONFIRMED":
        raise HTTPException(409, "Kết quả hiện hành đã được xác nhận")
    now = datetime.now(timezone.utc)
    replacement = m.EligibilitySnapshot(id=uuid4(), student_id=latest.student_id,
        round_id=round_id, version=latest.version + 1,
        passed_credit_ratio=latest.passed_credit_ratio, gpa_4=latest.gpa_4,
        evidence_ref=payload.official_ref.strip(), captured_at=now,
        confirmed_by=user.id, confirmed_at=now,
        decision_reason=payload.reason.strip(), state="CONFIRMED")
    session.add(replacement)
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id,
        action="ELIGIBILITY_SPECIAL_DECISION_RECORDED", resource_type="eligibility_snapshot",
        resource_id=replacement.id,
        reason=payload.reason.strip(), source_reference=payload.official_ref.strip(),
        occurred_at=now, correlation_id=uuid4()))
    session.commit()
    return {"state": "CONFIRMED", "snapshot_id": str(replacement.id)}


@router.post("/revoke")
def revoke_eligibility(round_id: UUID, payload: RevokeStudent,
                       user: m.UserAccount = Depends(current_user),
                       session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_VERIFIER")
    if len(payload.basis_ref.strip()) < 3 or len(payload.reason.strip()) < 5:
        raise HTTPException(422, "A reference and reason are required")
    session.scalar(select(m.StudentProfile.id).where(m.StudentProfile.id == payload.student_id).with_for_update())
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
        reason=payload.reason.strip(), source_reference=payload.basis_ref.strip(), occurred_at=now, correlation_id=uuid4()))
    from backend.services.notifications import notify_user
    student = session.get(m.StudentProfile, payload.student_id)
    notify_user(session, recipient_user_id=student.user_id, actor_user_id=user.id,
        kind="WORKFLOW_NOTICE", message="Quyền tham gia đợt KLTN của bạn đã bị thu hồi. Bạn vẫn được đăng nhập và xem hồ sơ nhưng không thể đăng ký hoặc nộp nội dung trong đợt này.", url="/registrations")
    session.commit()
    return {"state": "REJECTED", "snapshot_id": str(replacement.id),
            "note": "Existing academic records were preserved for manual review"}


@router.post("/restore")
def restore_eligibility(round_id: UUID, payload: RevokeStudent,
                        user: m.UserAccount = Depends(current_user),
                        session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_VERIFIER")
    if len(payload.basis_ref.strip()) < 3 or len(payload.reason.strip()) < 5:
        raise HTTPException(422, "Cần căn cứ và lý do khôi phục")
    session.scalar(select(m.StudentProfile.id).where(m.StudentProfile.id == payload.student_id).with_for_update())
    latest = session.scalar(select(m.EligibilitySnapshot).where(
        m.EligibilitySnapshot.student_id == payload.student_id,
        m.EligibilitySnapshot.round_id == round_id,
    ).order_by(m.EligibilitySnapshot.version.desc()).limit(1).with_for_update())
    if latest is None or latest.state != "REJECTED":
        raise HTTPException(409, "Chỉ khôi phục sinh viên đang bị thu hồi trong đợt này")
    now = datetime.now(timezone.utc)
    replacement = m.EligibilitySnapshot(id=uuid4(), student_id=payload.student_id,
        round_id=round_id, version=latest.version + 1, evidence_ref=payload.basis_ref.strip(),
        captured_at=now, confirmed_by=user.id, confirmed_at=now,
        decision_reason=payload.reason.strip(), state="CONFIRMED")
    session.add(replacement)
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ELIGIBILITY_RESTORED",
        resource_type="eligibility_snapshot", resource_id=replacement.id,
        reason=payload.reason.strip(), source_reference=payload.basis_ref.strip(), occurred_at=now, correlation_id=uuid4()))
    from backend.services.notifications import notify_user
    student = session.get(m.StudentProfile, payload.student_id)
    notify_user(session, recipient_user_id=student.user_id, actor_user_id=user.id,
        kind="WORKFLOW_NOTICE", message="Quyền tham gia đợt KLTN của bạn đã được khôi phục theo căn cứ mới. Trạng thái khóa tài khoản và thời hạn nộp vẫn áp dụng.", url="/registrations")
    session.commit()
    return {"state": "CONFIRMED", "snapshot_id": str(replacement.id)}


@router.patch("/{student_id}")
def correct_student(round_id: UUID, student_id: UUID, payload: CorrectStudent,
                    user: m.UserAccount = Depends(current_user),
                    session: Session = Depends(get_session)) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_VERIFIER")
    if payload.birth_date and (payload.birth_date > date.today() or payload.birth_date.year < 1900):
        raise HTTPException(422,"Ngày sinh phải từ năm 1900 đến hiện tại")
    code = payload.student_code.strip()
    name = payload.display_name.strip()
    class_name = payload.class_name.strip()
    major_code = payload.major_code.strip()
    if (not CODE.fullmatch(code) or not name
            or not class_name or not CODE.fullmatch(major_code)
            or len(payload.basis_ref.strip()) < 3 or len(payload.reason.strip()) < 5):
        raise HTTPException(422, "Invalid correction or missing document reference/reason")
    snapshot = session.scalar(select(m.EligibilitySnapshot.id).where(
        m.EligibilitySnapshot.student_id == student_id,
        m.EligibilitySnapshot.round_id == round_id).limit(1))
    if snapshot is None:
        raise HTTPException(404, "Student is not in this round")
    student = session.scalar(select(m.StudentProfile).where(
        m.StudentProfile.id == student_id).with_for_update())
    department = session.get(m.Department, student.department_id)
    if (code == student.student_code and name == student.display_name
            and class_name == student.class_name and major_code == student.major_code
            and ("birth_date" not in payload.model_fields_set or payload.birth_date == student.birth_date)):
        raise HTTPException(422, "No student information has changed")
    allowed = session.scalar(select(m.DepartmentMajor.id).where(
        m.DepartmentMajor.department_id == department.id,
        m.DepartmentMajor.code == major_code,
        m.DepartmentMajor.active.is_(True)))
    if major_code != student.major_code and allowed is None:
        raise HTTPException(422, "Mã ngành không thuộc bộ môn quản lý của sinh viên trong danh mục đang hoạt động")
    duplicate_code = session.scalar(select(m.StudentProfile.id).where(
        m.StudentProfile.student_code == code, m.StudentProfile.id != student.id))
    if duplicate_code:
        raise HTTPException(409, "Student code is already assigned")
    def fingerprint() -> str:
        fields = {"code": student.student_code, "name": student.display_name,
                  "class": student.class_name, "major": student.major_code,
                  "birth_date": str(student.birth_date or "")}
        return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    before = fingerprint()
    student.student_code = code
    student.display_name = name
    student.class_name = class_name
    if "birth_date" in payload.model_fields_set:
        student.birth_date = payload.birth_date
    student.major_code = major_code
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ROSTER_IDENTITY_CORRECTED",
        resource_type="student_profile", resource_id=student.id,
        before_hash=before, after_hash=fingerprint(),
        reason=payload.reason.strip(), source_reference=payload.basis_ref.strip(),
        occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Identity changed concurrently; reload and retry") from exc
    return {"student_id": str(student.id)}
