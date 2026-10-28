"""Admin-only lecturer spreadsheet provisioning and explicit activation delivery."""
from datetime import datetime, timedelta, timezone
import io
from urllib.parse import unquote
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from backend.api.account import _mail_link
from backend.api.account_admin import _admin
from backend.api.dependencies import current_user, get_session
from backend.db.models import entities as m
from backend.services.account_mail import delivery_mode, mail_delivery_ready
from backend.services.lecturer_roster import HEADERS, MAIL_ACTIONS, create_accounts, parse_file, preview, record_delivery
from backend.services.roster import MAX_BYTES

router = APIRouter(prefix="/api/v1/admin/lecturers", tags=["lecturer import"])


async def read_upload(request):
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Tệp danh sách GV không được vượt quá 2 MB.")
    return bytes(data)


@router.get("/import-template")
def template(user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)):
    _admin(user)
    department = session.scalar(select(m.Department).where(m.Department.active.is_(True)).order_by(m.Department.code))
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Danh sách giảng viên"
    sheet.append(HEADERS)
    for i, name in enumerate(("Lê Quang Huy", "Nguyễn Thu Hà", "Phạm Văn Khang"), 1):
        sheet.append((f"DEMO-GV-{i:03}", name, f"gv{i:02}@demo.test", department.code if department else "BM-CNTT"))
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="193B59")
    for column, width in zip("ABCD", (24, 30, 42, 22)):
        sheet.column_dimensions[column].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.number_format = "@"
    sheet.freeze_panes = "A2"
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return Response(output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="danh-sach-giang-vien-mau.xlsx"'})


@router.post("/import/preview")
async def preview_file(request: Request, file_name: str = Header(alias="X-File-Name"),
                       user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)):
    _admin(user)
    rows, digest, errors = parse_file(unquote(file_name), await read_upload(request))
    checked, _ = preview(session, rows, errors)
    valid = sum(not row["errors"] for row in checked)
    return {"sha256": digest, "count": len(rows), "valid_count": valid,
            "can_import": valid == len(rows), "rows": checked}


@router.post("/import", status_code=201)
async def import_file(request: Request, file_name: str = Header(alias="X-File-Name"),
                      preview_sha256: str = Header(alias="X-Preview-SHA256"),
                      user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)):
    _admin(user)
    rows, digest, errors = parse_file(unquote(file_name), await read_upload(request))
    if digest != preview_sha256:
        raise HTTPException(409, "Tệp đã thay đổi sau khi xem trước. Hãy kiểm tra lại tệp.")
    return create_accounts(session, user, rows, digest, errors)


@router.get("")
def list_lecturers(user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)):
    _admin(user)
    records = session.execute(select(m.UserAccount, m.LecturerProfile, m.Department)
        .join(m.LecturerProfile, m.LecturerProfile.user_id == m.UserAccount.id)
        .join(m.Department, m.Department.id == m.LecturerProfile.department_id)
        .where(m.UserAccount.base_role == "LECTURER").order_by(m.LecturerProfile.lecturer_code)).all()
    ids = [account.id for account, _, _ in records]
    latest = {}
    for event in session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_type == "user_account",
        m.AuditEvent.resource_id.in_(ids), m.AuditEvent.action.in_((*MAIL_ACTIONS, "ACCOUNT_EMAIL_CORRECTED")))
        .order_by(m.AuditEvent.occurred_at.desc(), case(
            (m.AuditEvent.action.in_(("LECTURER_ACTIVATION_SENT", "LECTURER_ACTIVATION_FAILED")), 1),
            else_=0).desc(), m.AuditEvent.id.desc())):
        latest.setdefault(event.resource_id, event)
    now = datetime.now(timezone.utc)
    items = []
    for account, profile, department in records:
        event = latest.get(account.id)
        retry_at = event.occurred_at + timedelta(seconds=60) if event and event.action in MAIL_ACTIONS else None
        pending = account.status == "DISABLED" and account.email_verified_at is None
        status = event.action.removeprefix("LECTURER_ACTIVATION_") if event and event.action in MAIL_ACTIONS else "NOT_RECORDED"
        if account.status == "LOCKED" or (account.status == "DISABLED" and account.email_verified_at):
            status = "BLOCKED"
        elif account.email_verified_at:
            status = "ACTIVATED"
        elif status == "SENDING" and retry_at and retry_at <= now:
            status = "UNKNOWN"  # The process may have stopped after SMTP accepted the message.
        items.append({"user_id": str(account.id), "lecturer_code": profile.lecturer_code,
            "display_name": profile.display_name, "email": account.email,
            "department_code": department.code, "department_name": department.name,
            "account_status": account.status, "mail_status": status,
            "delivery_mode": {"Kênh gửi: SMTP": "smtp", "Kênh gửi: hộp thư thử nghiệm trên máy": "development_outbox"}
                .get(event.source_reference if event else None, "unknown"),
            "last_attempt_at": event.occurred_at if event else None,
            "retry_at": retry_at, "can_send": bool(pending and account.email and (not retry_at or retry_at <= now))})
    return {"items": items, "delivery_mode": delivery_mode(), "mail_ready": mail_delivery_ready()}


@router.post("/{user_id}/activation-link")
def send_activation(user_id: UUID, user: m.UserAccount = Depends(current_user),
                    session: Session = Depends(get_session)):
    _admin(user)
    account = session.scalar(select(m.UserAccount).where(m.UserAccount.id == user_id).with_for_update())
    if not account or account.base_role != "LECTURER" or not session.scalar(select(m.LecturerProfile.id).where(
            m.LecturerProfile.user_id == user_id)):
        raise HTTPException(404, "Không tìm thấy tài khoản giảng viên.")
    if account.status != "DISABLED" or account.email_verified_at or not account.email:
        raise HTTPException(409, "Chỉ gửi kích hoạt cho giảng viên đang chờ kích hoạt, chưa bị khóa.")
    if not mail_delivery_ready():
        raise HTTPException(503, "Chưa cấu hình đầy đủ dịch vụ gửi thư.")
    now = datetime.now(timezone.utc)
    last = session.scalar(select(m.AuditEvent.occurred_at).where(m.AuditEvent.resource_type == "user_account",
        m.AuditEvent.resource_id == user_id, m.AuditEvent.action.in_(MAIL_ACTIONS))
        .order_by(m.AuditEvent.occurred_at.desc()).limit(1))
    if last and last + timedelta(seconds=60) > now:
        raise HTTPException(429, "Vừa có yêu cầu gửi thư cho giảng viên này. Vui lòng đợi 60 giây rồi làm mới.")
    account.row_version += 1
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="LECTURER_ACTIVATION_SENDING",
        resource_type="user_account", resource_id=user_id, occurred_at=now, correlation_id=uuid4()))
    session.commit()
    try:
        _mail_link(account, "activate")
        sent = True
    except Exception:
        sent = False
    record_delivery(session, user, account, sent, now)
    session.commit()
    return {"user_id": str(user_id), "sent": sent, "delivery_mode": delivery_mode()}
