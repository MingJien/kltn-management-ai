"""Faculty-approved roster import; no transcript or sensitive eligibility detail is stored."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.db.models import entities as m
from backend.services.passwords import unusable_password

MAX_BYTES = 2_000_000
MAX_ROWS = 1000
REQUIRED = ("student_code", "display_name", "email", "department_code", "class_name", "major_code")
OPTIONAL: tuple[str, ...] = ()
ROSTER_HEADERS_VI = ("MSSV", "Họ tên", "Email", "Mã bộ môn", "Lớp", "Mã ngành")


def normalize_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold().replace("đ", "d")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text))


HEADER_ALIASES = {
    normalize_header(alias): key
    for key, aliases in {
        "student_code": ("student_code", "MSSV", "Mã SV", "Mã sinh viên", "Mã số sinh viên"),
        "display_name": ("display_name", "Họ tên", "Họ và tên", "Tên sinh viên"),
        "email": ("email", "E-mail", "Thư điện tử", "Địa chỉ email"),
        "department_code": ("department_code", "Mã bộ môn", "Bộ môn"),
        "class_name": ("class_name", "Lớp", "Tên lớp", "Mã lớp"),
        "major_code": ("major_code", "Mã ngành", "Ngành", "Ngành học"),
    }.items()
    for alias in aliases
}
EMAIL = re.compile(r"^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$")
CODE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")


@dataclass(frozen=True)
class RosterRow:
    line: int
    student_code: str
    display_name: str
    email: str
    department_code: str
    class_name: str
    major_code: str


def assigned(session: Session, user: m.UserAccount, round_id: UUID, kind: str) -> bool:
    now = datetime.now(timezone.utc)
    return session.scalar(select(m.ResourceAssignment.id).where(
        m.ResourceAssignment.user_id == user.id,
        m.ResourceAssignment.round_id == round_id,
        m.ResourceAssignment.assignment_type == kind,
        m.ResourceAssignment.state == "ACTIVE",
        m.ResourceAssignment.effective_from <= now,
        (m.ResourceAssignment.effective_to.is_(None) | (m.ResourceAssignment.effective_to > now)),
    ).limit(1)) is not None


def require_assignment(session: Session, user: m.UserAccount, round_id: UUID, kind: str) -> None:
    if not assigned(session, user, round_id, kind):
        raise HTTPException(403, "Round assignment required")


def parse_roster(name: str, content: bytes) -> tuple[list[RosterRow], str]:
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(422, "Roster must contain at most 2 MB")
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    try:
        if suffix == "csv":
            text = content.decode("utf-8-sig")
            first_line = text.splitlines()[0] if text.splitlines() else ""
            delimiter = max((",", ";", "\t"), key=first_line.count)
            reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
            raw = list(reader)
        elif suffix == "xlsx":
            if not content.startswith(b"PK"):
                raise ValueError("Invalid XLSX")
            with ZipFile(io.BytesIO(content)) as archive:
                infos = archive.infolist()
                if len(infos) > 500 or sum(item.file_size for item in infos) > 10_000_000:
                    raise ValueError("XLSX is too large")
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
            try:
                if len(workbook.worksheets) != 1:
                    raise ValueError("Use one worksheet")
                sheet = workbook.active
                if sheet.max_row and sheet.max_row > MAX_ROWS + 1:
                    raise ValueError("Too many rows")
                raw = []
                for row in sheet.iter_rows():
                    if any(cell.data_type == "f" for cell in row):
                        raise ValueError("Formula cells are not allowed")
                    raw.append([cell.value for cell in row])
                    if len(raw) > MAX_ROWS + 1:
                        raise ValueError("Too many rows")
            finally:
                workbook.close()
        else:
            raise ValueError("Use a UTF-8 CSV or XLSX file")
    except (UnicodeError, csv.Error, BadZipFile, OSError, ValueError) as exc:
        raise HTTPException(422, f"Invalid roster: {exc}") from exc
    if not raw or len(raw) < 2 or len(raw) > MAX_ROWS + 1:
        raise HTTPException(422, "Roster must have 1 to 1000 data rows")
    while raw[0] and not str(raw[0][-1] or "").strip():
        raw[0].pop()
    labels = [normalize_header(value) for value in raw[0]]
    header = [HEADER_ALIASES.get(label) for label in labels]
    if any(key is None for key in header):
        raise HTTPException(422, "Cột không được hỗ trợ. Dùng đúng mẫu: " + ", ".join(ROSTER_HEADERS_VI))
    if len(header) != len(set(header)) or any(key not in header for key in REQUIRED):
        raise HTTPException(422, "Thiếu hoặc trùng cột. Cần có: " + ", ".join(ROSTER_HEADERS_VI))
    student_code_column = header.index("student_code")
    rows: list[RosterRow] = []
    codes: set[str] = set()
    emails: set[str] = set()
    for line, cells in enumerate(raw[1:], start=2):
        if suffix == "xlsx" and student_code_column < len(cells) and isinstance(
                cells[student_code_column], (int, float)):
            raise HTTPException(422, f"Dòng {line}: MSSV đang là số Excel, có thể mất số 0 đầu. Hãy định dạng cột MSSV là Text rồi nhập lại.")
        if (any(value is not None and str(value).strip() for value in cells[len(header):])
                or not any(value is not None and str(value).strip() for value in cells)):
            raise HTTPException(422, f"Row {line} is empty or has extra cells")
        values = {key: str(cells[index] if index < len(cells) and cells[index] is not None else "").strip()
                  for index, key in enumerate(header)}
        code, name_value, email = values["student_code"], values["display_name"], values["email"].lower()
        dept = values["department_code"]
        if (not CODE.fullmatch(code) or not CODE.fullmatch(dept) or not EMAIL.fullmatch(email)
                or len(email) > 255 or not 1 <= len(name_value) <= 255
                or not 1 <= len(values["class_name"]) <= 100
                or not CODE.fullmatch(values["major_code"])):
            raise HTTPException(422, f"Row {line} has an invalid required value")
        if any(value.startswith(("=", "+", "-", "@")) for value in values.values()):
            raise HTTPException(422, f"Row {line} contains a spreadsheet formula-like value")
        if code in codes or email in emails:
            raise HTTPException(422, f"Row {line} duplicates a student code or email")
        codes.add(code)
        emails.add(email)
        rows.append(RosterRow(line, code, name_value, email, dept,
                              values.get("class_name", ""), values.get("major_code", "")))
    return rows, hashlib.sha256(content).hexdigest()


def validate_rows(session: Session, rows: list[RosterRow]) -> dict[str, m.Department]:
    departments: dict[str, m.Department] = {}
    for item in session.scalars(select(m.Department).where(m.Department.active.is_(True))).all():
        if item.code in departments:
            departments[item.code] = None  # Ambiguous department codes require correction.
        else:
            departments[item.code] = item
    allowed = {(item.department_id, item.code) for item in session.scalars(
        select(m.DepartmentMajor).where(m.DepartmentMajor.active.is_(True))).all()}
    for row in rows:
        if row.department_code not in departments:
            raise HTTPException(422, f"Dòng {row.line}: mã bộ môn '{row.department_code}' chưa có trong danh mục bộ môn đang hoạt động. Hãy đối chiếu danh mục trước khi nhập.")
        department = departments[row.department_code]
        if department is None:
            raise HTTPException(422, f"Dòng {row.line}: mã bộ môn '{row.department_code}' đang thuộc nhiều bộ môn; cần làm rõ mã trong danh mục trước khi nhập.")
        if (department.id, row.major_code) not in allowed:
            raise HTTPException(422, f"Dòng {row.line}: mã ngành '{row.major_code}' không thuộc bộ môn '{row.department_code}' trong danh mục đang hoạt động.")
        existing = session.scalar(select(m.StudentProfile).where(m.StudentProfile.student_code == row.student_code))
        email_account = session.scalar(select(m.UserAccount).where(func.lower(m.UserAccount.email) == row.email))
        if existing:
            account = session.get(m.UserAccount, existing.user_id)
            if (account.email != row.email or existing.display_name != row.display_name
                    or existing.department_id != department.id
                    or (existing.class_name is not None and existing.class_name != row.class_name)
                    or (existing.major_code is not None and existing.major_code != row.major_code)):
                raise HTTPException(409, f"Row {row.line}: existing student information differs; correct it separately")
        elif email_account:
            raise HTTPException(409, f"Row {row.line}: email already belongs to another account")
    return departments


def import_roster(session: Session, user: m.UserAccount, round_id: UUID,
                  rows: list[RosterRow], reference: str) -> dict:
    require_assignment(session, user, round_id, "ELIGIBILITY_IMPORTER")
    round_ = session.get(m.ThesisRound, round_id)
    if round_ is None or round_.state not in {"DRAFT", "OPEN"}:
        raise HTTPException(409, "The round is not open for roster import")
    departments = validate_rows(session, rows)
    created = 0
    added = 0
    skipped = 0
    snapshot_ids = []
    now = datetime.now(timezone.utc)
    try:
        for row in rows:
            student = session.scalar(select(m.StudentProfile).where(
                m.StudentProfile.student_code == row.student_code))
            if student is None:
                account = m.UserAccount(id=uuid4(), email=row.email,
                    password_hash=unusable_password(),
                    base_role="STUDENT", status="DISABLED")
                session.add(account)
                session.flush()
                student = m.StudentProfile(id=uuid4(), user_id=account.id,
                    student_code=row.student_code, display_name=row.display_name,
                    class_name=row.class_name, major_code=row.major_code,
                    department_id=departments[row.department_code].id)
                session.add(student)
                session.flush()
                created += 1
            else:
                if student.class_name is None:
                    student.class_name = row.class_name
                if student.major_code is None:
                    student.major_code = row.major_code
            latest = session.scalar(select(m.EligibilitySnapshot).where(
                m.EligibilitySnapshot.student_id == student.id,
                m.EligibilitySnapshot.round_id == round_id,
            ).order_by(m.EligibilitySnapshot.version.desc()).limit(1).with_for_update())
            if latest and latest.state == "CONFIRMED":
                skipped += 1
                continue
            snapshot = m.EligibilitySnapshot(id=uuid4(), student_id=student.id, round_id=round_id,
                version=latest.version + 1 if latest else 1, evidence_ref=reference,
                captured_at=now, confirmed_by=user.id, confirmed_at=now, state="CONFIRMED")
            session.add(snapshot)
            snapshot_ids.append(str(snapshot.id))
            added += 1
        session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="ELIGIBILITY_ROSTER_IMPORTED",
            resource_type="thesis_round", resource_id=round_id,
            reason=f"reference={reference}; new_accounts={created}; confirmed={added}; skipped={skipped}",
            occurred_at=now, correlation_id=uuid4()))
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "A concurrent import changed the roster; preview and retry") from exc
    return {"new_accounts": created, "confirmed": added, "unchanged": skipped,
            "snapshot_ids": snapshot_ids}
