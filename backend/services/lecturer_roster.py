"""Lecturer account import: preview first, atomic creation, no mail side effects."""
from __future__ import annotations

import hashlib
import io
from datetime import datetime, timedelta, timezone
from dataclasses import asdict, dataclass
from uuid import uuid4
from zipfile import BadZipFile, ZipFile
from xml.etree.ElementTree import ParseError

from fastapi import HTTPException
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from backend.db.models import entities as m
from backend.services.passwords import unusable_password
from backend.services.account_mail import delivery_mode
from backend.services.roster import CODE, EMAIL, MAX_BYTES, MAX_ROWS, normalize_header

HEADERS = ("Mã GV", "Họ tên", "Email", "Mã bộ môn")
KEYS = ("lecturer_code", "display_name", "email", "department_code")
ALIASES = {normalize_header(alias): key for key, names in {
    "lecturer_code": ("Mã GV", "Mã giảng viên", "lecturer_code"),
    "display_name": ("Họ tên", "Họ và tên", "display_name"),
    "email": ("Email", "Email công vụ", "email"),
    "department_code": ("Mã bộ môn", "department_code"),
}.items() for alias in names}
MAIL_ACTIONS = ("LECTURER_ACTIVATION_SENDING", "LECTURER_ACTIVATION_SENT", "LECTURER_ACTIVATION_FAILED")


@dataclass(frozen=True)
class LecturerRow:
    line: int
    lecturer_code: str
    display_name: str
    email: str
    department_code: str


def parse_file(name: str, content: bytes) -> tuple[list[LecturerRow], str, dict[int, list[str]]]:
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(422, "Tệp danh sách GV phải có dữ liệu và không vượt quá 2 MB.")
    if not name.lower().endswith(".xlsx"):
        raise HTTPException(422, "Danh sách GV cần dùng tệp Excel .xlsx theo mẫu.")
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > 500 or sum(entry.file_size for entry in entries) > 10_000_000:
                raise ValueError("Tệp Excel có dung lượng giải nén quá lớn.")
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        try:
            if len(workbook.worksheets) != 1:
                raise ValueError("Dùng đúng một trang tính.")
            sheet = workbook.active
            if (sheet.max_row and sheet.max_row > MAX_ROWS + 1) or (sheet.max_column and sheet.max_column > 32):
                raise ValueError("Tệp vượt giới hạn dòng hoặc chứa quá nhiều cột; hãy dùng mẫu bốn cột.")
            raw = []
            for row in sheet.iter_rows():
                if len(row) > 32:
                    raise ValueError("Tệp chứa quá nhiều cột; hãy dùng mẫu bốn cột.")
                if any(cell.data_type == "f" for cell in row):
                    raise ValueError("Tệp không được chứa công thức Excel.")
                raw.append([cell.value for cell in row])
                if len(raw) > MAX_ROWS + 1:
                    raise ValueError("Tối đa 1.000 dòng giảng viên.")
        finally:
            workbook.close()
    except (BadZipFile, OSError, ValueError, KeyError, ParseError, InvalidFileException) as exc:
        raise HTTPException(422, f"Không đọc được danh sách GV: {exc}") from exc
    while raw and not any(value is not None and str(value).strip() for value in raw[-1]):
        raw.pop()  # Ignore trailing formatting rows, never skip a blank data row in the middle.
    if len(raw) < 2:
        raise HTTPException(422, "Danh sách cần có tiêu đề và ít nhất một giảng viên.")
    while raw[0] and raw[0][-1] is None:
        raw[0].pop()
    columns = [ALIASES.get(normalize_header(cell)) for cell in raw[0]]
    if len(columns) != 4 or set(columns) != set(KEYS):
        raise HTTPException(422, "Dùng đúng bốn cột ở dòng 1: " + ", ".join(HEADERS))
    rows, errors = [], {}
    code_index = columns.index("lecturer_code")
    for line, cells in enumerate(raw[1:], 2):
        values = {key: str(cells[i] if i < len(cells) and cells[i] is not None else "").strip()
                  for i, key in enumerate(columns)}
        values["email"] = values["email"].lower()
        problems = []
        if isinstance(cells[code_index] if code_index < len(cells) else None, (int, float)):
            problems.append("Mã GV cần định dạng Text để giữ nguyên mã và số 0 đầu.")
        if not CODE.fullmatch(values["lecturer_code"]):
            problems.append("Mã GV cần 1–32 ký tự chữ, số, dấu chấm, gạch ngang hoặc gạch dưới.")
        if not 1 <= len(values["display_name"]) <= 255:
            problems.append("Họ tên cần 1–255 ký tự.")
        if not EMAIL.fullmatch(values["email"]) or len(values["email"]) > 255:
            problems.append("Email bị thiếu hoặc không đúng định dạng.")
        if not CODE.fullmatch(values["department_code"]):
            problems.append("Mã bộ môn bị thiếu hoặc không đúng định dạng.")
        if any(value.startswith(("=", "+", "-", "@")) for value in values.values()):
            problems.append("Không dùng giá trị có dạng công thức Excel.")
        if any(value is not None and str(value).strip() for value in cells[4:]):
            problems.append("Dòng có dữ liệu ngoài bốn cột theo mẫu.")
        rows.append(LecturerRow(line=line, **values))
        errors[line] = problems
    return rows, hashlib.sha256(content).hexdigest(), errors


def preview(session, rows, errors):
    departments = {}
    for department in session.scalars(select(m.Department).where(m.Department.active.is_(True))):
        departments.setdefault(department.code, []).append(department)
    emails = set(session.scalars(select(func.lower(m.UserAccount.email)).where(
        func.lower(m.UserAccount.email).in_([row.email for row in rows]))))
    codes = set(session.scalars(select(func.lower(m.LecturerProfile.lecturer_code)).where(
        func.lower(m.LecturerProfile.lecturer_code).in_([row.lecturer_code.lower() for row in rows]))))
    code_lines, email_lines = {}, {}
    for row in rows:
        code_lines.setdefault(row.lecturer_code.lower(), []).append(row.line)
        email_lines.setdefault(row.email, []).append(row.line)
    output = []
    for row in rows:
        issues = list(errors[row.line])
        matches = departments.get(row.department_code, [])
        if len(matches) != 1:
            issues.append("Mã bộ môn không tồn tại, đã ngừng hoạt động hoặc bị trùng trong danh mục.")
        if len(code_lines[row.lecturer_code.lower()]) > 1:
            issues.append("Mã GV bị trùng trong tệp (không phân biệt hoa/thường).")
        if len(email_lines[row.email]) > 1:
            issues.append("Email bị trùng trong tệp.")
        if row.lecturer_code.lower() in codes:
            issues.append("Mã GV đã có trong hệ thống; hãy quản lý hồ sơ hiện có.")
        if row.email in emails:
            issues.append("Email đã thuộc một tài khoản trong hệ thống.")
        output.append({**asdict(row), "department_name": matches[0].name if len(matches) == 1 else None,
                       "errors": issues})
    return output, departments


def create_accounts(session, actor, rows, digest, errors):
    lock_identities(session, [(row.lecturer_code, row.email) for row in rows])
    checked, departments = preview(session, rows, errors)
    if any(row["errors"] for row in checked):
        raise HTTPException(409, "Danh sách còn lỗi hoặc dữ liệu đã thay đổi. Hãy xem trước lại trước khi tạo.")
    # Lock departments against deactivation between validation and insertion.
    for department_id in sorted({departments[row.department_code][0].id for row in rows}, key=str):
        department = session.scalar(select(m.Department).where(m.Department.id == department_id).with_for_update())
        if not department or not department.active:
            raise HTTPException(409, "Danh mục bộ môn đã thay đổi; hãy xem trước lại.")
    created = []
    try:
        for row in rows:
            account = m.UserAccount(id=uuid4(), email=row.email, password_hash=unusable_password(),
                                    base_role="LECTURER", status="DISABLED")
            session.add(account)
            session.flush()
            session.add(m.LecturerProfile(id=uuid4(), user_id=account.id, lecturer_code=row.lecturer_code,
                display_name=row.display_name, department_id=departments[row.department_code][0].id))
            session.add(m.AuditEvent(id=uuid4(), actor_id=actor.id, action="LECTURER_IMPORTED",
                resource_type="user_account", resource_id=account.id, correlation_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                source_reference="sha256:" + digest))
            created.append(str(account.id))
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Mã GV hoặc email vừa được sử dụng. Chưa tạo tài khoản nào; hãy xem trước lại.") from exc
    return {"created_count": len(created), "user_ids": created, "invitations_sent": 0}


def lock_identities(session, identities):
    """Serialize identity checks, including case-insensitive codes, on PostgreSQL."""
    keys = {prefix + value.lower() for code, email in identities
            for prefix, value in (("lecturer-code:", code), ("account-email:", email))}
    for key in sorted(keys):
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key})


def record_delivery(session, actor, account, sent, started_at=None):
    occurred = datetime.now(timezone.utc)
    if started_at:
        occurred = max(occurred, started_at + timedelta(microseconds=1))
    session.add(m.AuditEvent(id=uuid4(), actor_id=actor.id,
        action="LECTURER_ACTIVATION_SENT" if sent else "LECTURER_ACTIVATION_FAILED",
        resource_type="user_account", resource_id=account.id, occurred_at=occurred,
        source_reference="Kênh gửi: SMTP" if delivery_mode() == "smtp" else "Kênh gửi: hộp thư thử nghiệm trên máy",
        correlation_id=uuid4()))
