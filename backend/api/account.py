"""Invitation-only account activation and local credential maintenance."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.auth import _login_throttled, _record_failure, _same_app_origin
from backend.api.dependencies import current_user, get_session
from backend.db.models import entities as m
from backend.services.account_mail import frontend_origin, mail_delivery_ready, send_account_link
from backend.services.account_tokens import make_token, token_account
from backend.services.passwords import hash_password, verify_password
from backend.services.registration import confirmed_student_ids
from backend.services.roster import EMAIL

router = APIRouter(prefix="/api/v1/account", tags=["account"])
GENERIC_LINK_MESSAGE = "Nếu thông tin hợp lệ, hướng dẫn sẽ được gửi tới email đã đăng ký."


class ActivationRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=32)
    email: str = Field(min_length=3, max_length=255)


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class LinkPassword(BaseModel):
    token: str = Field(min_length=1, max_length=2048)
    password: str = Field(min_length=12, max_length=1024)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


def _request_guard(request: Request, identifier: str) -> None:
    if not _same_app_origin(request):
        raise HTTPException(403, "Request origin is not allowed")
    peer = request.client.host if request.client else "unknown"
    keys = (f"account:peer:{peer}", f"account:identity:{peer}:{identifier.lower()}")
    if any(_login_throttled(key) for key in keys):
        raise HTTPException(429, "Too many requests; try again later")
    for key in keys:
        _record_failure(key)


@dataclass(frozen=True)
class AccountMailRecipient:
    """Capture the account and profile at request time for background email."""
    id: UUID
    email: str
    row_version: int
    base_role: str
    display_name: str | None = None
    identifier: str | None = None
    initiated_by: str = "self"


def _mail_recipient(user: m.UserAccount, display_name: str | None, initiated_by: str,
                    identifier: str | None = None) -> AccountMailRecipient:
    return AccountMailRecipient(id=user.id, email=user.email, row_version=user.row_version,
        base_role=user.base_role, display_name=display_name, identifier=identifier, initiated_by=initiated_by)


def _account_display_name(session: Session, user: m.UserAccount) -> str | None:
    profile_type = {"STUDENT": m.StudentProfile, "LECTURER": m.LecturerProfile}.get(user.base_role)
    if profile_type is None:
        return None
    profile = session.scalar(select(profile_type).where(profile_type.user_id == user.id))
    return profile.display_name if profile else None


def _account_identifier(session: Session, user: m.UserAccount) -> str | None:
    if user.base_role == "STUDENT":
        profile = session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == user.id))
        return profile.student_code if profile else None
    if user.base_role == "LECTURER":
        profile = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == user.id))
        return profile.lecturer_code if profile else None
    return None


def _mail_link(user: AccountMailRecipient, purpose: str) -> None:
    frontend = frontend_origin()
    if os.getenv("KLTN_ENV") == "production" and not frontend.startswith("https://"):
        raise RuntimeError("Account links require an HTTPS frontend")
    token = make_token(user, purpose)
    path = "activate" if purpose == "activate" else "reset-password"
    role = {"STUDENT": "sinh viên", "LECTURER": "giảng viên"}.get(getattr(user, "base_role", ""), "")
    name = (getattr(user, "display_name", None) or "").strip()
    greeting = f"Xin chào {role + ' ' if role else ''}{name}," if name else "Xin chào,"
    role_text = f" {role}" if role else ""
    staff = getattr(user, "initiated_by", "self") == "staff"
    if purpose == "activate":
        subject = f"Kích hoạt tài khoản{role_text} - Hệ thống quản lý KLTN"
        intro = f"Đây là liên kết kích hoạt tài khoản{role_text} của bạn trên Hệ thống quản lý khóa luận tốt nghiệp."
        action = "kích hoạt tài khoản và đặt mật khẩu"
        after = "Sau khi kích hoạt, bạn có thể đăng nhập để sử dụng hệ thống."
        lifetime = "24 giờ"
    else:
        subject = "Đặt lại mật khẩu - Hệ thống quản lý KLTN"
        intro = ("Quản trị viên đã gửi liên kết đặt lại mật khẩu tài khoản của bạn."
                 if staff else "Hệ thống đã nhận yêu cầu đặt lại mật khẩu tài khoản của bạn.")
        action = "đặt lại mật khẩu"
        after = "Sau khi đặt lại mật khẩu, hãy đăng nhập bằng mật khẩu mới."
        lifetime = "30 phút"
    identifier = getattr(user, "identifier", None)
    code_label = {"STUDENT": "MSSV", "LECTURER": "Mã giảng viên"}.get(getattr(user, "base_role", ""))
    code_line = f"{code_label}: {identifier}\n" if purpose == "activate" and identifier and code_label else ""
    body = (f"{greeting}\n\n{intro}\n\n"
            f"Email đăng nhập: {user.email}\n"
            f"{code_line}"
            f"Mở liên kết sau để {action}:\n{frontend}/account/{path}?token={token}\n\n"
            f"Liên kết có hiệu lực {lifetime} và chỉ dùng một lần. {after}\n\n"
            "Nếu bạn không nhận biết yêu cầu này, không chia sẻ liên kết và hãy liên hệ bộ phận quản lý KLTN.\n\n"
            "Hệ thống quản lý khóa luận tốt nghiệp\n"
            "Khoa Công nghệ và Kỹ thuật - Trường Đại học Đồng Tháp\n")
    send_account_link(user.email, subject, body)


def _mail_ready() -> None:
    if not mail_delivery_ready():
        raise HTTPException(503, "Email delivery is unavailable")


def _audit(session: Session, user: m.UserAccount, action: str, actor_id=None) -> None:
    session.add(m.AuditEvent(
        id=uuid4(), actor_id=actor_id, action=action, resource_type="user_account",
        resource_id=user.id, occurred_at=datetime.now(timezone.utc), correlation_id=uuid4(),
    ))


def _student_can_activate(session: Session, student: m.StudentProfile) -> bool:
    """A confirmed student may activate or recover access after registration closes."""
    round_ids = session.scalars(select(m.EligibilitySnapshot.round_id).where(
        m.EligibilitySnapshot.student_id == student.id).distinct()).all()
    return any(student.id in confirmed_student_ids(session, round_id, [student.id])
               for round_id in round_ids)


@router.post("/activation-request", status_code=202)
def activation_request(payload: ActivationRequest, request: Request, tasks: BackgroundTasks,
                       session: Session = Depends(get_session)) -> dict[str, str]:
    identifier = payload.identifier.strip()
    email = payload.email.strip().lower()
    if not EMAIL.fullmatch(email):
        raise HTTPException(422, "Invalid email")
    _request_guard(request, f"{identifier}:{email}")
    _mail_ready()
    user = session.scalar(select(m.UserAccount).where(func.lower(m.UserAccount.email) == email,
        m.UserAccount.status == "DISABLED", m.UserAccount.email_verified_at.is_(None),
    ))
    if user and user.base_role == "STUDENT":
        student = session.scalar(select(m.StudentProfile).where(
            m.StudentProfile.user_id == user.id, m.StudentProfile.student_code == identifier))
        if student and _student_can_activate(session, student):
            tasks.add_task(_mail_link, _mail_recipient(user, student.display_name, "self", student.student_code), "activate")
    elif user and user.base_role == "LECTURER":
        lecturer = session.scalar(select(m.LecturerProfile).where(
            m.LecturerProfile.user_id == user.id, m.LecturerProfile.lecturer_code == identifier))
        if lecturer:
            tasks.add_task(_mail_link, _mail_recipient(user, lecturer.display_name, "self", lecturer.lecturer_code), "activate")
    return {"message": GENERIC_LINK_MESSAGE}


@router.post("/activate", status_code=204)
def activate(payload: LinkPassword, request: Request,
             session: Session = Depends(get_session)) -> None:
    if not _same_app_origin(request):
        raise HTTPException(403, "Request origin is not allowed")
    parsed = token_account(payload.token, "activate")
    if parsed is None:
        raise HTTPException(400, "The link is invalid or has expired")
    user_id, email, version = parsed
    user = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if not user or user.email != email or user.row_version != version or user.status != "DISABLED" or user.email_verified_at:
        raise HTTPException(400, "The link is invalid or has expired")
    if user.base_role == "STUDENT":
        student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == user.id))
        if not student or not _student_can_activate(session, student):
            raise HTTPException(403, "Participation approval is no longer active")
    user.password_hash = hash_password(payload.password)
    user.email_verified_at = datetime.now(timezone.utc)
    user.status = "ACTIVE"
    user.row_version += 1
    _audit(session, user, "ACCOUNT_ACTIVATED", user.id)
    session.commit()


@router.post("/password-reset-request", status_code=202)
def password_reset_request(payload: EmailRequest, request: Request, tasks: BackgroundTasks,
                           session: Session = Depends(get_session)) -> dict[str, str]:
    email = payload.email.strip().lower()
    if not EMAIL.fullmatch(email):
        raise HTTPException(422, "Invalid email")
    _request_guard(request, email)
    _mail_ready()
    user = session.scalar(select(m.UserAccount).where(
        func.lower(m.UserAccount.email) == email, m.UserAccount.status == "ACTIVE",
        m.UserAccount.email_verified_at.is_not(None)))
    if user:
        tasks.add_task(_mail_link, _mail_recipient(user, _account_display_name(session, user), "self"), "reset")
    return {"message": GENERIC_LINK_MESSAGE}


@router.post("/password-reset", status_code=204)
def password_reset(payload: LinkPassword, request: Request,
                   session: Session = Depends(get_session)) -> None:
    if not _same_app_origin(request):
        raise HTTPException(403, "Request origin is not allowed")
    parsed = token_account(payload.token, "reset")
    if parsed is None:
        raise HTTPException(400, "The link is invalid or has expired")
    user_id, email, version = parsed
    user = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if not user or user.email != email or user.row_version != version or user.status != "ACTIVE" or not user.email_verified_at:
        raise HTTPException(400, "The link is invalid or has expired")
    user.password_hash = hash_password(payload.password)
    user.row_version += 1
    _audit(session, user, "PASSWORD_RESET", user.id)
    session.commit()


@router.post("/password-change", status_code=204)
def password_change(payload: PasswordChange, request: Request,
                    user: m.UserAccount = Depends(current_user),
                    session: Session = Depends(get_session)) -> None:
    if not user.email_verified_at or not verify_password(user.password_hash, payload.current_password):
        raise HTTPException(400, "Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(400, "Choose a different password")
    user.password_hash = hash_password(payload.new_password)
    user.row_version += 1
    _audit(session, user, "PASSWORD_CHANGED", user.id)
    session.commit()
    request.session.clear()
