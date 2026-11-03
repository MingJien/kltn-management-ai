"""Private append-only file versions. Quarantine is never represented as antivirus clearance."""
from __future__ import annotations

import hashlib
import io
import os
import zipfile
from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from backend.api.core_schemas import DocumentOut, DocumentVersionOut, ReviewOut
from backend.db.models import entities as m
from backend.services.registration import profile, row_version
from backend.services.theses import audit, now, thesis_access
from backend.services import deadlines, file_scanner

MAX_BYTES = 10 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[2]


def storage_root():
    return Path(os.getenv("KLTN_DOCUMENT_DIR", str(ROOT / "local" / "uploads" / "documents"))).resolve()


def require_clean(file, action: str):
    """Unscanned uploads stay quarantined: never downloadable, reviewed or cited as evidence."""
    if file is None:
        raise HTTPException(404, "Tệp không khả dụng")
    if file.scan_state != "CLEAN":
        raise HTTPException(409,
            "Tệp đang cách ly – chưa quét an toàn; chưa thể " + action +
            ". Cần máy quét tệp thật để chuyển trạng thái, hệ thống không tự gán an toàn.")
    return file


def valid_content(name, content):
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf" and content.startswith(b"%PDF-"):
        return "application/pdf"
    if suffix == ".txt":
        try:
            decoded = content.decode("utf-8-sig")
            if decoded.strip() and "\x00" not in decoded:
                return "text/plain"
        except UnicodeDecodeError:
            pass
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = archive.infolist()
                names = {entry.filename for entry in entries}
                if (len(entries) <= 2000 and sum(entry.file_size for entry in entries) <= 50 * 1024 * 1024
                    and {"[Content_Types].xml", "word/document.xml"} <= names
                    and not any(entry.flag_bits & 1 or entry.filename.lower().endswith("vbaproject.bin") for entry in entries)):
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except (zipfile.BadZipFile, ValueError):
            pass
    raise HTTPException(422, "Chỉ nhận PDF, DOCX không macro hoặc TXT UTF-8 với nội dung phù hợp")


async def read_upload(request, *, max_bytes=MAX_BYTES):
    from backend.api.auth import _same_app_origin
    if not _same_app_origin(request):
        raise HTTPException(403, "Nguồn yêu cầu không được phép")
    name = unquote(request.headers.get("X-File-Name", "")).replace("\\", "/").split("/")[-1].strip()
    if not name or len(name) > 180 or any(ord(c) < 32 for c in name):
        raise HTTPException(422, "Tên tệp không hợp lệ")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(413, f"Tệp tối đa {max_bytes // (1024 * 1024)} MB")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise HTTPException(422, "Tệp rỗng")
    return name, content, valid_content(name, content)


def persist_upload(session, name, content, mime):
    root = storage_root()
    root.mkdir(parents=True, exist_ok=True)
    key = uuid4().hex + Path(name).suffix.lower()
    path = root / key
    with path.open("xb") as handle:
        handle.write(content)
    digest = hashlib.sha256(content).hexdigest()
    file = m.StoredFile(id=uuid4(), storage_key="documents/" + key, original_name=name,
        media_type=mime, byte_size=len(content), sha256=digest, scan_state="QUARANTINED")
    session.add(file)
    return file, digest, path


def document(session, thesis_id, document_id, *, lock=False,user=None):
    query = select(m.Document).where(m.Document.id == document_id, m.Document.thesis_id == thesis_id,
        m.Document.state == "ACTIVE", m.Document.visibility == "ASSIGNED")
    item = session.scalar(query.with_for_update() if lock else query)
    if not item:
        raise HTTPException(404, "Không tìm thấy tài liệu")
    if user is not None and is_progress_evidence(session,item.id):
        thesis_access(session,user,thesis_id,action="progress:view")
    return item


def is_progress_evidence(session,document_id):
    return session.scalar(select(m.ProgressReport.id).join(m.DocumentVersion,m.DocumentVersion.stored_file_id==m.ProgressReport.evidence_file_id).where(m.DocumentVersion.document_id==document_id).limit(1)) is not None


def document_out(session, item):
    versions = session.scalars(select(m.DocumentVersion).where(m.DocumentVersion.document_id == item.id)
        .order_by(m.DocumentVersion.version_no.desc())).all()
    def version_out(version):
        file = session.get(m.StoredFile, version.stored_file_id)
        decisions = session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_type == "document_version",
            m.AuditEvent.resource_id == version.id, m.AuditEvent.action.in_(["DOCUMENT_ACCEPT", "DOCUMENT_REVISION_REQUIRED"]))
            .order_by(m.AuditEvent.occurred_at)).all()
        def reviewer_name(event):
            lecturer = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == event.actor_id))
            return lecturer.display_name if lecturer else "Giảng viên"
        return DocumentVersionOut(id=version.id, version_no=version.version_no, row_version=version.row_version,
            state=version.state, file_name=file.original_name, byte_size=file.byte_size,
            sha256=version.content_sha256, scan_state=file.scan_state, submitted_at=version.submitted_at,
            due_at_at_submission=version.due_at_at_submission,
            late=bool(version.due_at_at_submission and version.submitted_at > version.due_at_at_submission),
            submitted_by_name=session.get(m.StudentProfile, version.submitted_by).display_name,
            reviews=[ReviewOut(reviewer_name=reviewer_name(event), decision=event.action.removeprefix("DOCUMENT_"),
                comment=event.reason or "", created_at=event.occurred_at) for event in decisions])
    return DocumentOut(id=item.id, title=item.title, document_type=item.document_type, row_version=item.row_version,
        visibility=item.visibility, versions=[version_out(version) for version in versions])


def rescan_version(session, user, thesis_id, document_id, version_id):
    thesis_access(session, user, thesis_id, action="document:view", lock=True, write=True)
    item = document(session, thesis_id, document_id, lock=True,user=user)
    version = session.scalar(select(m.DocumentVersion).where(
        m.DocumentVersion.id == version_id, m.DocumentVersion.document_id == item.id).with_for_update())
    if not version:
        raise HTTPException(404, "Không tìm thấy phiên bản")
    file = session.get(m.StoredFile, version.stored_file_id)
    if file.scan_state == "CLEAN":
        return document_out(session, item)
    if file.scan_state == "INFECTED":
        raise HTTPException(409, "Tệp nhiễm mã độc; hãy nộp phiên bản mới")
    file_scanner.require_available()
    state = file_scanner.scan(file, storage_root() / Path(file.storage_key).name)
    audit(session, user, "DOCUMENT_FILE_SCANNED", "document_version", version.id, state)
    session.flush()
    result = document_out(session, item)
    session.commit()
    return result


def create_document(session, user, thesis_id, data):
    thesis_access(session, user, thesis_id, action="document:submit", lock=True, write=True)
    if data.document_type == "PROPOSAL":
        raise HTTPException(409, "Đề cương phải nộp tại luồng đề cương có xét duyệt riêng")
    if data.document_type in {"PLAN", "REPORT"} and session.scalar(select(m.Document.id).where(
            m.Document.thesis_id == thesis_id, m.Document.document_type == data.document_type,
            m.Document.state == "ACTIVE").limit(1)):
        label = "Kế hoạch thực hiện Mẫu 2" if data.document_type == "PLAN" else "Cuốn báo cáo KLTN"
        raise HTTPException(409, f"{label} đã có; hãy nộp phiên bản mới vào hồ sơ đó")
    item = m.Document(id=uuid4(), thesis_id=thesis_id, title=data.title, document_type=data.document_type,
        visibility="ASSIGNED", state="ACTIVE")
    session.add(item)
    audit(session, user, "DOCUMENT_CREATED", "thesis", thesis_id, data.title)
    session.flush()
    result = document_out(session, item)
    session.commit()
    return result


def withdraw_document(session, user, thesis_id, document_id, data, expected):
    """Hide a mistaken submission while retaining its versions, bytes and audit trail."""
    thesis_access(session, user, thesis_id, action="document:submit", lock=True, write=True)
    item = document(session, thesis_id, document_id, lock=True,user=user)
    row_version(expected, item.row_version)
    if item.document_type == "PROPOSAL":
        raise HTTPException(409, "Đề cương phải xử lý ở luồng đề cương")
    versions = session.scalars(select(m.DocumentVersion).where(
        m.DocumentVersion.document_id == item.id).with_for_update()).all()
    if any(version.state not in {"SUBMITTED", "SUPERSEDED"} for version in versions):
        raise HTTPException(409, "Tài liệu đã được xử lý; cần giữ trong hồ sơ và nộp phiên bản sửa")
    if versions:
        version_ids = [version.id for version in versions]
        if session.scalar(select(m.AuditEvent.id).where(
            m.AuditEvent.resource_type == "document_version",
            m.AuditEvent.resource_id.in_(version_ids),
            m.AuditEvent.action.in_(["DOCUMENT_ACCEPT", "DOCUMENT_REVISION_REQUIRED"])).limit(1)):
            raise HTTPException(409, "GVHD đã nhận xét; không thể rút hồ sơ này")
        file_ids = [version.stored_file_id for version in versions]
        if session.scalar(select(m.ProgressReport.id).where(
            m.ProgressReport.evidence_file_id.in_(file_ids)).limit(1)):
            raise HTTPException(409, "Tệp đang là minh chứng tiến độ; không thể rút hồ sơ")
    item.state = "REVOKED"
    item.row_version += 1
    audit(session, user, "DOCUMENT_WITHDRAWN", "thesis", thesis_id,
        f"{item.id} · {item.title}: {data.reason}")
    session.commit()


async def upload_version(session, user, thesis_id, document_id, request, expected):
    path = None
    try:
        thesis = thesis_access(session, user, thesis_id, action="document:submit", lock=True, write=True)
        item = document(session, thesis_id, document_id, lock=True,user=user)
        row_version(expected, item.row_version)
        if item.document_type == "PROPOSAL":
            raise HTTPException(409, "Đề cương phải nộp tại mục Đề cương")
        latest = session.scalar(select(m.DocumentVersion).where(m.DocumentVersion.document_id == item.id)
            .order_by(m.DocumentVersion.version_no.desc()).limit(1))
        deadline = deadlines.for_submission(session, thesis, item.document_type)
        if latest and latest.state not in {"SUBMITTED", "REVISION_REQUESTED"}:
            raise HTTPException(409, "Bản đã được duyệt hoặc khóa; chỉ nộp lại khi GVHD yêu cầu sửa")
        deadlines.ensure_submission_allowed(deadline,
            revision_requested=bool(latest and latest.state == "REVISION_REQUESTED"),
            previous_submitted=bool(latest and latest.state == "SUBMITTED"))
        name, content, mime = await read_upload(request)
        if item.document_type in {"PLAN", "REPORT"} and Path(name).suffix.lower() not in {".pdf", ".docx"}:
            raise HTTPException(422, "Kế hoạch Mẫu 2 và Cuốn báo cáo KLTN phải là PDF hoặc DOCX để xuất bản có footer")
        file, digest, path = persist_upload(session, name, content, mime)
        file_scanner.scan(file, path)
        if latest and latest.state == "SUBMITTED":
            latest.state = "SUPERSEDED"
            latest.row_version += 1
        student = profile(session, user, "STUDENT")
        version = m.DocumentVersion(id=uuid4(), document_id=item.id, version_no=latest.version_no + 1 if latest else 1,
            stored_file_id=file.id, submitted_by=student.id,
            submitted_at=now(), due_at_at_submission=deadline.due_at,
            content_sha256=digest, state="SUBMITTED")
        session.add(version)
        item.row_version += 1
        audit(session, user, "DOCUMENT_SELF_CORRECTED" if latest and latest.state == "SUPERSEDED" else "DOCUMENT_UPLOADED",
            "thesis", thesis_id, f"{item.title} v{version.version_no}", after_hash=digest)
        session.flush()
        from backend.services.notifications import DOCUMENT_TYPE_LABELS, notify_thesis_advisor

        label = DOCUMENT_TYPE_LABELS.get(item.document_type, item.title)
        notify_thesis_advisor(session, thesis=thesis, actor_user_id=user.id,
            kind="DOCUMENT_SUBMITTED",
            message=f"{student.display_name} đã nộp {label} — {item.title} (phiên bản {version.version_no}).",
            section="submissions&kind=" + item.document_type)
        if item.document_type == "REPORT":
            from backend.services.evaluation import report_submitted
            report_submitted(session, user, thesis)
        result = document_out(session, item)
        session.commit()
        return result
    except Exception:
        session.rollback()
        if path and path.is_file():
            try:
                path.unlink()
            except OSError:
                # A leftover file is reported by tools/check_file_integrity; never mask
                # the original storage/database error or fabricate a clean rollback.
                pass
        raise


def review_version(session, user, thesis_id, document_id, version_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="document:review", lock=True, write=True)
    item = document(session, thesis_id, document_id, lock=True,user=user)
    if is_progress_evidence(session,item.id):
        raise HTTPException(409,"Minh chứng tiến độ cần nhận xét ở mục Tiến độ")
    if item.document_type == "PROPOSAL":
        raise HTTPException(409, "Đề cương cần quy trình xét duyệt riêng; không dùng duyệt tài liệu thay TBM/Trưởng khoa")
    version = session.scalar(select(m.DocumentVersion).where(m.DocumentVersion.document_id == item.id,
        m.DocumentVersion.id == version_id).with_for_update())
    if not version:
        raise HTTPException(404, "Không tìm thấy phiên bản")
    row_version(expected, version.row_version)
    latest = session.scalar(select(func.max(m.DocumentVersion.version_no)).where(m.DocumentVersion.document_id == item.id))
    if version.version_no != latest or version.state != "SUBMITTED":
        raise HTTPException(409, "Chỉ duyệt phiên bản mới nhất đang chờ")
    file = session.get(m.StoredFile, version.stored_file_id)
    if data.decision == "ACCEPT":
        require_clean(file, "tiếp nhận tài liệu")
        prior = session.scalars(select(m.DocumentVersion).where(
            m.DocumentVersion.document_id == item.id,
            m.DocumentVersion.version_no < version.version_no,
            m.DocumentVersion.state == "ACCEPTED").with_for_update()).all()
        for old in prior:
            old.state = "SUPERSEDED"
            old.row_version += 1
    from backend.services.progress_annotations import publish_annotations
    publish_annotations(session, version, profile(session, user, "LECTURER"), kind="document", summary_comment=data.comment)
    version.state = "ACCEPTED" if data.decision == "ACCEPT" else "REVISION_REQUESTED"
    version.row_version += 1
    item.row_version += 1
    audit(session, user, "DOCUMENT_" + data.decision, "document_version", version.id, data.comment, after_hash=version.content_sha256)
    audit(session, user, "DOCUMENT_REVIEWED", "thesis", thesis_id, f"{item.title} v{version.version_no}: {data.comment}")
    session.flush()
    from backend.services.notifications import notify_thesis_students

    action_label = "tiếp nhận" if data.decision == "ACCEPT" else "yêu cầu sửa"
    notify_thesis_students(session, thesis=thesis, actor_user_id=user.id,
        kind="DOCUMENT_ACCEPTED" if data.decision == "ACCEPT" else "DOCUMENT_REVISION_REQUESTED",
        message=f"GVHD đã {action_label} {item.title} phiên bản {version.version_no}. Nhận xét: {data.comment[:200]}",
        section="submissions&kind=" + item.document_type)
    result = document_out(session, item)
    session.commit()
    return result


def download_version(session, user, thesis_id, document_id, version_id):
    thesis_access(session, user, thesis_id, action="document:view")
    document(session, thesis_id, document_id,user=user)
    version = session.scalar(select(m.DocumentVersion).where(m.DocumentVersion.id == version_id,
        m.DocumentVersion.document_id == document_id))
    return stored_download(session, version)


def stored_download(session, version):
    """Read an immutable document version after its caller checks resource-specific access."""
    file = session.get(m.StoredFile, version.stored_file_id) if version else None
    if not file or not file.storage_key.startswith("documents/"):
        raise HTTPException(404, "Tệp không khả dụng")
    require_clean(file, "tải tệp")
    root = storage_root()
    path = (root / file.storage_key.removeprefix("documents/")).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "Tệp không khả dụng")
    if path.stat().st_size != file.byte_size or hashlib.sha256(path.read_bytes()).hexdigest() != version.content_sha256:
        raise HTTPException(409, "Tệp lưu trữ không khớp mã kiểm tra; cần phục hồi bản gốc")
    return FileResponse(path, media_type="application/octet-stream", filename=file.original_name,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
