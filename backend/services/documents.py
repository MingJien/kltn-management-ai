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


def document(session, thesis_id, document_id, *, lock=False):
    query = select(m.Document).where(m.Document.id == document_id, m.Document.thesis_id == thesis_id,
        m.Document.state == "ACTIVE", m.Document.visibility == "ASSIGNED")
    item = session.scalar(query.with_for_update() if lock else query)
    if not item:
        raise HTTPException(404, "Không tìm thấy tài liệu")
    return item


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
            submitted_by_name=session.get(m.StudentProfile, version.submitted_by).display_name,
            reviews=[ReviewOut(reviewer_name=reviewer_name(event), decision=event.action.removeprefix("DOCUMENT_"),
                comment=event.reason or "", created_at=event.occurred_at) for event in decisions])
    return DocumentOut(id=item.id, title=item.title, document_type=item.document_type, row_version=item.row_version,
        visibility=item.visibility, versions=[version_out(version) for version in versions])


def create_document(session, user, thesis_id, data):
    thesis_access(session, user, thesis_id, action="document:submit", lock=True, write=True)
    if data.document_type == "PROPOSAL":
        raise HTTPException(409, "Đề cương phải nộp tại luồng đề cương có xét duyệt riêng")
    if data.document_type == "PLAN" and session.scalar(select(m.Document.id).where(
            m.Document.thesis_id == thesis_id, m.Document.document_type == "PLAN",
            m.Document.state == "ACTIVE").limit(1)):
        raise HTTPException(409, "Kế hoạch đã có; hãy nộp phiên bản mới vào hồ sơ đó")
    item = m.Document(id=uuid4(), thesis_id=thesis_id, title=data.title, document_type=data.document_type,
        visibility="ASSIGNED", state="ACTIVE")
    session.add(item)
    audit(session, user, "DOCUMENT_CREATED", "thesis", thesis_id, data.title)
    session.flush()
    result = document_out(session, item)
    session.commit()
    return result


async def upload_version(session, user, thesis_id, document_id, request, expected):
    from backend.api.auth import _same_app_origin
    if not _same_app_origin(request):
        raise HTTPException(403, "Nguồn yêu cầu không được phép")
    path = None
    try:
        thesis_access(session, user, thesis_id, action="document:submit", lock=True, write=True)
        item = document(session, thesis_id, document_id, lock=True)
        row_version(expected, item.row_version)
        name = unquote(request.headers.get("X-File-Name", "")).replace("\\", "/").split("/")[-1].strip()
        if not name or len(name) > 180 or any(ord(c) < 32 for c in name):
            raise HTTPException(422, "Tên tệp không hợp lệ")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(413, "Tệp tối đa 10 MB")
            chunks.append(chunk)
        content = b"".join(chunks)
        if not content:
            raise HTTPException(422, "Tệp rỗng")
        mime = valid_content(name, content)
        latest = session.scalar(select(m.DocumentVersion).where(m.DocumentVersion.document_id == item.id)
            .order_by(m.DocumentVersion.version_no.desc()).limit(1))
        if latest and latest.state == "FINAL":
            raise HTTPException(409, "Bản cuối đã khóa")
        root = storage_root()
        root.mkdir(parents=True, exist_ok=True)
        key = uuid4().hex + Path(name).suffix.lower()
        path = root / key
        with path.open("xb") as handle:
            handle.write(content)
        digest = hashlib.sha256(content).hexdigest()
        file = m.StoredFile(id=uuid4(), storage_key="documents/" + key, original_name=name,
            media_type=mime, byte_size=size, sha256=digest, scan_state="QUARANTINED")
        session.add(file)
        session.flush()
        version = m.DocumentVersion(id=uuid4(), document_id=item.id, version_no=latest.version_no + 1 if latest else 1,
            stored_file_id=file.id, submitted_by=profile(session, user, "STUDENT").id,
            submitted_at=now(), content_sha256=digest, state="SUBMITTED")
        session.add(version)
        item.row_version += 1
        audit(session, user, "DOCUMENT_UPLOADED", "thesis", thesis_id, f"{item.title} v{version.version_no}", after_hash=digest)
        session.flush()
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
    thesis_access(session, user, thesis_id, action="document:review", lock=True, write=True)
    item = document(session, thesis_id, document_id, lock=True)
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
    require_clean(file, "duyệt tài liệu")
    if data.decision == "ACCEPT":
        prior = session.scalars(select(m.DocumentVersion).where(
            m.DocumentVersion.document_id == item.id,
            m.DocumentVersion.version_no < version.version_no,
            m.DocumentVersion.state == "ACCEPTED").with_for_update()).all()
        for old in prior:
            old.state = "SUPERSEDED"
            old.row_version += 1
    version.state = "ACCEPTED" if data.decision == "ACCEPT" else "REVISION_REQUESTED"
    version.row_version += 1
    item.row_version += 1
    audit(session, user, "DOCUMENT_" + data.decision, "document_version", version.id, data.comment, after_hash=version.content_sha256)
    audit(session, user, "DOCUMENT_REVIEWED", "thesis", thesis_id, f"{item.title} v{version.version_no}: {data.comment}")
    session.flush()
    result = document_out(session, item)
    session.commit()
    return result


def download_version(session, user, thesis_id, document_id, version_id):
    thesis_access(session, user, thesis_id, action="document:view")
    document(session, thesis_id, document_id)
    version = session.scalar(select(m.DocumentVersion).where(m.DocumentVersion.id == version_id,
        m.DocumentVersion.document_id == document_id))
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
