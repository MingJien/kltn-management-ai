"""Versioned Mẫu 1a/1b submissions. A receipt is never an academic approval."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import documents, file_scanner
from backend.services.registration import _registration, get_registration, profile, row_version
from backend.services.theses import audit, now


def access(session, user, registration_id, *, lock=False):
    reg = _registration(session, registration_id, lock=lock)
    get_registration(session, user, registration_id)
    if user.base_role == "STUDENT":
        student = profile(session, user, "STUDENT")
        if not session.scalar(select(m.RegistrationMember.id).where(
            m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.student_id == student.id, m.RegistrationMember.active.is_(True))):
            raise HTTPException(404, "Bạn không còn trong nhóm đăng ký này")
    return reg


def fingerprint(session, reg):
    topic = session.get(m.Topic, reg.topic_id)
    students = sorted(str(x) for x in session.scalars(select(m.RegistrationMember.student_id).where(
        m.RegistrationMember.registration_id == reg.id, m.RegistrationMember.active.is_(True))))
    data = [str(reg.topic_id), str(reg.round_id), topic.current_title, str(topic.receiving_lecturer_id), students]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest(), "1A" if len(students) == 1 else "1B"


def rows(session, reg):
    return session.scalars(select(m.RegistrationFormVersion).where(
        m.RegistrationFormVersion.registration_id == reg.id).order_by(m.RegistrationFormVersion.version_no.desc())).all()


def can_submit(session, user, reg):
    if user.base_role != "STUDENT" or reg.state not in {"DRAFT", "RETURNED", "SUBMITTED"}:
        return False
    from backend.services.registration import confirmed_student_ids
    student = profile(session, user, "STUDENT")
    if student.id not in confirmed_student_ids(session, reg.round_id, [student.id]):
        return False
    round_ = session.get(m.ThesisRound, reg.round_id)
    return round_.state == "OPEN" and round_.opens_at <= now() <= round_.closes_at


def output(session, user, reg):
    current_hash, code = fingerprint(session, reg)
    versions = []
    for index, item in enumerate(rows(session, reg)):
        file = session.get(m.StoredFile, item.stored_file_id)
        versions.append(dict(id=item.id, version_no=item.version_no, form_code=item.form_code,
            file_name=file.original_name, byte_size=file.byte_size, scan_state=file.scan_state,
            submitted_at=item.submitted_at, submitted_by_name=session.get(m.StudentProfile, item.submitted_by).display_name,
            current=index == 0 and item.registration_fingerprint == current_hash and item.form_code == code))
    return dict(form_code=code, can_submit=can_submit(session, user, reg), registration_version=reg.row_version, versions=versions)


def listing(session, user, registration_id):
    return output(session, user, access(session, user, registration_id))


async def upload(session, user, registration_id, request, expected):
    path = None
    try:
        reg = access(session, user, registration_id, lock=True)
        row_version(expected, reg.row_version)
        if not can_submit(session, user, reg):
            raise HTTPException(409, "Chỉ SV trong nhóm được nộp đơn khi đợt còn hạn và GV chưa tiếp nhận")
        digest_registration, code = fingerprint(session, reg)
        name, content, mime = await documents.read_upload(request, max_bytes=20 * 1024 * 1024)
        if Path(name).suffix.lower() not in {".pdf", ".docx"}:
            raise HTTPException(422, "Đơn Mẫu 1a/1b phải là PDF hoặc DOCX")
        if request.headers.get("X-Form-Code") != code:
            raise HTTPException(409, "Số thành viên đã thay đổi; tải lại và sử dụng đúng Mẫu 1a/1b")
        previous = rows(session, reg)
        file, digest, path = documents.persist_upload(session, name, content, mime)
        file_scanner.scan(file, path)
        session.flush()
        item = m.RegistrationFormVersion(id=uuid4(), registration_id=reg.id, stored_file_id=file.id,
            submitted_by=profile(session, user, "STUDENT").id, form_code=code,
            version_no=previous[0].version_no + 1 if previous else 1,
            content_sha256=digest, registration_fingerprint=digest_registration, submitted_at=now())
        session.add(item)
        reg.row_version += 1
        audit(session, user, "REGISTRATION_FORM_SUBMITTED", "topic_registration", reg.id,
            f"Mẫu {code}; version={item.version_no}; bản nộp, chưa xác nhận Khoa duyệt", after_hash=digest)
        session.flush()
        if reg.state in {"SUBMITTED", "RETURNED"}:
            # The receiving lecturer and the department head already follow this
            # registration; a new Mẫu 1a/1b file must reach their bell, no one else.
            from backend.services.notifications import add_notice, notify_department_heads

            topic = session.get(m.Topic, reg.topic_id)
            student = session.get(m.StudentProfile, item.submitted_by)
            message = (f"{student.display_name} đã nộp đơn Mẫu {code.lower()} "
                       f"phiên bản {item.version_no} cho đề tài {topic.current_title}.")
            url = f"/registrations?focus={reg.id}"
            lecturer = (session.get(m.LecturerProfile, topic.receiving_lecturer_id)
                        if topic.receiving_lecturer_id else
                        session.scalar(select(m.LecturerProfile).where(
                            m.LecturerProfile.user_id == topic.proposer_user_id))
                        if topic.proposer_type == "LECTURER" else None)
            if lecturer is not None and lecturer.user_id != user.id:
                add_notice(session, topic=topic, actor_user_id=user.id, registration_id=reg.id,
                           kind="REGISTRATION_FORM_SUBMITTED",
                           recipient_user_id=lecturer.user_id, message=message,
                           url=url, subject_type="registration", subject_id=reg.id)
            notify_department_heads(session, topic=topic, actor_user_id=user.id,
                registration_id=reg.id, kind="REGISTRATION_FORM_SUBMITTED", message=message, url=url)
        result = output(session, user, reg)
        session.commit()
        return result
    except Exception:
        session.rollback()
        if path and path.is_file():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass  # Preserve the original error; orphan inspection is handled separately.
        raise


def version(session, reg, version_id):
    item = session.scalar(select(m.RegistrationFormVersion).where(
        m.RegistrationFormVersion.registration_id == reg.id, m.RegistrationFormVersion.id == version_id))
    if not item:
        raise HTTPException(404, "Không tìm thấy phiên bản đơn trong hồ sơ đăng ký")
    return item


def download(session, user, registration_id, version_id):
    reg = access(session, user, registration_id)
    return documents.stored_download(session, version(session, reg, version_id))


def rescan(session, user, registration_id, version_id):
    reg = access(session, user, registration_id, lock=True)
    item = version(session, reg, version_id)
    file_scanner.require_available()
    file = session.get(m.StoredFile, item.stored_file_id)
    path = documents.storage_root() / Path(file.storage_key).name
    if not path.is_file():
        raise HTTPException(404, "Không tìm thấy tệp để quét")
    file_scanner.scan(file, path)
    audit(session, user, "REGISTRATION_FORM_SCANNED", "topic_registration", reg.id, f"version={item.version_no}; {file.scan_state}")
    session.commit()
    return output(session, user, reg)


def print_copy(session, user, registration_id, version_id):
    from backend.services.proposal_export import _print_bytes, _print_response, _footer_lines, _public_url
    reg = access(session, user, registration_id, lock=True)
    item = version(session, reg, version_id)
    registration_hash, form_code = fingerprint(session, reg)
    latest = rows(session, reg)[0]
    if item.id != latest.id or item.registration_fingerprint != registration_hash or item.form_code != form_code:
        raise HTTPException(409, "Đơn không còn khớp hồ sơ hiện tại; nhóm cần nộp phiên bản mới")
    source = documents.stored_download(session, item)
    file = session.get(m.StoredFile, item.stored_file_id)
    code = f"DK{form_code}-{reg.id.hex.upper()}-V{item.version_no:02d}"
    instant = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    lines = _footer_lines(_public_url(), code, instant)
    lines[1] += " · Bản nộp, chưa xác nhận Khoa duyệt"
    suffix = Path(file.original_name).suffix.lower()
    source_bytes = Path(source.path).read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != item.content_sha256:
        raise HTTPException(409, "Tệp đã thay đổi trước khi xuất; chưa thể tạo bản in")
    result, mime = _print_bytes(source_bytes, suffix, lines)
    audit(session, user, "REGISTRATION_FORM_PRINT_EXPORTED", "topic_registration", reg.id,
        f"code={code}; version={item.version_no}; version_id={item.id}; receipt_only; exported_at={instant.isoformat()}",
        before_hash=item.content_sha256, after_hash=hashlib.sha256(result).hexdigest())
    session.commit()
    return _print_response(result, mime, code, suffix, instant)


def print_history(session, user, registration_id, version_id):
    from backend.services.proposal_export import export_history
    reg = access(session, user, registration_id)
    item = version(session, reg, version_id)
    return export_history(session, action="REGISTRATION_FORM_PRINT_EXPORTED", resource_type="topic_registration",
        resource_id=reg.id, version=item)
