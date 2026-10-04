"""Private registration evidence; no public file URLs and no AI ingestion."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.auth import _same_app_origin
from backend.db.models import entities as m
from backend.services.registration import get_registration, profile, registration_out

MAX_BYTES = 5 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[2]


def storage_root() -> Path:
    return Path(os.getenv("KLTN_EVIDENCE_DIR", str(ROOT / "local" / "uploads" / "registration"))).resolve()


async def upload_evidence(session: Session, user: m.UserAccount, registration_id: UUID, request: Request):
    if not _same_app_origin(request):
        raise HTTPException(403, "Untrusted request origin")
    if user.base_role != "STUDENT":
        raise HTTPException(403, "Only students upload their own evidence")
    student = profile(session, user, "STUDENT")
    written_path = None
    try:
        reg = session.scalar(select(m.TopicRegistration).where(m.TopicRegistration.id == registration_id).with_for_update())
        if not reg:
            raise HTTPException(404, "Registration not found")
        member = session.scalar(select(m.RegistrationMember).where(m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.student_id == student.id, m.RegistrationMember.active.is_(True)))
        if not member:
            raise HTTPException(404, "Registration not found")
        if reg.state not in {"DRAFT", "RETURNED"}:
            raise HTTPException(409, "Evidence is locked after submission")
        # One bounded file per member. A PDF may contain multiple supporting pages.
        from urllib.parse import unquote
        name = unquote(request.headers.get("X-File-Name", "evidence"))
        name = name.replace("\\", "/").split("/")[-1].strip()
        if not name or len(name) > 180 or any(ord(c) < 32 for c in name):
            raise HTTPException(422, "Invalid filename")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(413, "Evidence file must be at most 5 MB")
            chunks.append(chunk)
        content = b"".join(chunks)
        suffix = Path(name).suffix.lower()
        mime = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(suffix)
        valid = ((suffix == ".pdf" and content.startswith(b"%PDF-")) or
            (suffix == ".png" and content.startswith(b"\x89PNG\r\n\x1a\n")) or
            (suffix in {".jpg", ".jpeg"} and content.startswith(b"\xff\xd8\xff")))
        if not content or not mime or not valid:
            raise HTTPException(422, "Use a PDF, PNG or JPEG with matching file content")
        key = uuid4().hex + suffix
        root = storage_root()
        root.mkdir(parents=True, exist_ok=True)
        written_path = root / key
        with written_path.open("xb") as handle:
            handle.write(content)
        file = m.StoredFile(id=uuid4(), storage_key="registration/" + key, original_name=name,
            media_type=mime, byte_size=size, sha256=hashlib.sha256(content).hexdigest(), scan_state="QUARANTINED")
        session.add(file)
        session.flush()
        member.evidence_file_id = file.id
        reg.row_version += 1
        session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action="REGISTRATION_EVIDENCE_UPLOADED",
            resource_type="registration", resource_id=reg.id, after_hash=file.sha256,
            occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
        session.flush()
        result = registration_out(session, reg)
        session.commit()
        return result
    except Exception:
        session.rollback()
        if written_path and written_path.is_file():
            written_path.unlink()
        raise


def download_evidence(session: Session, user: m.UserAccount, registration_id: UUID, student_id: UUID):
    get_registration(session, user, registration_id)  # Authorize group/receiver/head before accessing file.
    member = session.scalar(select(m.RegistrationMember).where(m.RegistrationMember.registration_id == registration_id,
        m.RegistrationMember.student_id == student_id))
    file = session.get(m.StoredFile, member.evidence_file_id) if member and member.evidence_file_id else None
    if not file or file.scan_state in {"INFECTED", "FAILED"} or not file.storage_key.startswith("registration/"):
        raise HTTPException(404, "Evidence unavailable")
    root = storage_root()
    path = (root / file.storage_key.removeprefix("registration/")).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "Evidence unavailable")
    # Forced attachment: never render unscanned PDFs/images as active application content.
    return FileResponse(path, media_type="application/octet-stream", filename=file.original_name,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
