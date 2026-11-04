"""Create a traceable print copy of the exact approved PDF/DOCX version.

The system adds the requested footer to an immutable uploaded version; it does
not change the source file or generate an unsigned blank form. Mẫu 9 remains
outside the implemented workflow.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import OpcError
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from fastapi import HTTPException
from fastapi.responses import Response
from lxml.etree import XMLSyntaxError
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.errors import PyPdfError
from pypdf._page import PageObject
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, DecodedStreamObject, IndirectObject
from sqlalchemy import select

from backend.api.core_schemas import PrintExportOut

from backend.db.models import entities as m
from backend.services.account_mail import frontend_origin
from backend.services.proposals import download_version
from backend.services.theses import audit, thesis_access


def _public_url() -> str:
    url = frontend_origin(os.getenv("KLTN_PUBLIC_URL") or os.getenv("KLTN_FRONTEND_URL") or "http://localhost:5173")
    parsed = urlparse(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or len(url) > 120
            or not url.isascii()):
        raise RuntimeError("KLTN_PUBLIC_URL must be a short public origin")
    if os.getenv("KLTN_ENV") == "production" and parsed.scheme != "https":
        raise RuntimeError("The public print URL must use HTTPS in production")
    return url


def _stable_code(session, thesis, doc_prefix: str, version_no: int) -> str:
    round_ = session.get(m.ThesisRound, thesis.round_id)
    if round_ is None:
        raise HTTPException(422, "Không tìm thấy đợt khóa luận để tạo mã xuất ổn định")
    year = session.get(m.AcademicYear, round_.academic_year_id)
    if year is None:
        raise HTTPException(422, "Không tìm thấy năm học để tạo mã xuất ổn định")
    start_year = None
    if year.starts_on:
        start_year = str(year.starts_on.year)
    elif year.code:
        m_year = re.search(r"\b(20\d\d)\b", year.code)
        start_year = m_year.group(1) if m_year else year.code[:4]
    if not start_year:
        raise HTTPException(422, "Không có dữ liệu năm học bắt đầu để tạo mã xuất ổn định")

    topic = session.get(m.Topic, thesis.topic_id)
    if topic is None or not topic.code:
        raise HTTPException(422, "Không có dữ liệu đề tài để tạo mã hồ sơ ổn định")

    m_seq = re.search(r"(\d+)$", topic.code)
    if m_seq:
        seq_code = f"{int(m_seq.group(1)):04d}"
    else:
        seq_code = topic.id.hex[:4].upper()

    return f"{doc_prefix}-{start_year}-{seq_code}-V{version_no:02d}"


def _footer_lines(public_url: str, code: str, instant: datetime) -> list[str]:
    """Exactly three lines at the bottom-left: URL, code, export time."""
    return [
        f"Xuất tại: {public_url}",
        f"Mã số: {code}",
        f"Thời điểm xuất: {instant:%H:%M %d/%m/%Y}",
    ]


def _pdf_text(value: str) -> str:
    # Built-in PDF Helvetica has no Vietnamese glyphs; preserve readable labels.
    return unicodedata.normalize("NFKD", value.replace("đ", "d").replace("Đ", "D")).encode("ascii", "ignore").decode()


def _pdf_literal(value: str) -> bytes:
    # The configured URL, code and timestamp must render in built-in Helvetica.
    if not value.isascii():
        raise HTTPException(422, "Public URL for PDF footer must be ASCII")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("ascii")


def _stamp_pdf(source: bytes, lines: list[str] | str) -> bytes:
    try:
        reader = PdfReader(io.BytesIO(source), strict=True)
        if reader.is_encrypted or not reader.pages or len(reader.pages) > 300:
            raise ValueError("PDF is encrypted or too long")
        line_list = [lines] if isinstance(lines, str) else list(lines)
        writer = PdfWriter()
        source_writer = PdfWriter(clone_from=reader)
        for original in source_writer.pages:
            # Fit the entire visible source above a reserved footer band. Merely
            # painting a white rectangle over an existing page erases signatures,
            # page numbers or text near its bottom edge. Keep the paper size and
            # aspect ratio; transform annotations along with the visible content.
            box = original.cropbox
            rotation = int(original.get("/Rotate", 0)) % 360
            if rotation not in {0, 90, 180, 270}:
                raise ValueError("Invalid page rotation")
            normalize = Transformation().translate(-float(box.left), -float(box.bottom)).rotate(-rotation)
            corners = [normalize.apply_on((x, y)) for x in (float(box.left), float(box.right))
                for y in (float(box.bottom), float(box.top))]
            left, bottom = min(x for x, _ in corners), min(y for _, y in corners)
            width = max(x for x, _ in corners) - left
            height = max(y for _, y in corners) - bottom
            if width < 250 or height < 250:
                raise ValueError("PDF page is too small for a readable footer")
            footer_height = 18.0 + 9.0 * len(line_list)
            scale = (height - footer_height) / height
            page = writer.add_blank_page(width=width, height=height)
            placement = normalize.translate(-left, -bottom).scale(scale).translate(
                (width - width * scale) / 2, footer_height)
            # Direct annotation dictionaries are legal PDF too. Give them owned
            # references so pypdf also transforms their rectangles/appearances.
            if original.get("/Annots"):
                original[NameObject("/Annots")] = ArrayObject([item if isinstance(item, IndirectObject)
                    else source_writer._add_object(item) for item in original["/Annots"]])
            page.merge_transformed_page(original, placement)
            overlay = PageObject.create_blank_page(width=width, height=height)
            overlay[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/KLTN"): DictionaryObject({
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                })})})
            ascii_lines = [_pdf_text(line) for line in line_list]
            stream = DecodedStreamObject()
            y_start = 10.0 + 9.0 * (len(ascii_lines) - 1)
            pdf_ops = [
                "q\n",
                f"BT /KLTN 6.50 Tf 0.16 0.22 0.29 rg 9.0 TL\n",
                f"1 0 0 1 28 {y_start:.2f} Tm\n",
            ]
            for i, aline in enumerate(ascii_lines):
                safe_literal = _pdf_literal(aline).decode("ascii")
                if i < len(ascii_lines) - 1:
                    pdf_ops.append(f"({safe_literal}) Tj T*\n")
                else:
                    pdf_ops.append(f"({safe_literal}) Tj\n")
            pdf_ops.append("ET\nQ")
            stream.set_data("".join(pdf_ops).encode("ascii"))
            overlay[NameObject("/Contents")] = stream
            page.merge_page(overlay)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    except (PyPdfError, ValueError, TypeError, KeyError, OSError) as exc:
        raise HTTPException(422, "Cannot create a print copy from this PDF") from exc


def _stamp_docx(source: bytes, lines: list[str] | str) -> bytes:
    try:
        doc = Document(io.BytesIO(source))
        touched = set()
        line_list = [lines] if isinstance(lines, str) else list(lines)
        for section in doc.sections:
            footers = [section.footer]
            if section.different_first_page_header_footer:
                footers.append(section.first_page_footer)
            if doc.settings.odd_and_even_pages_header_footer:
                footers.append(section.even_page_footer)
            for footer in footers:
                if str(footer.part.partname) in touched:
                    continue
                touched.add(str(footer.part.partname))
                paragraph = footer.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for i, line in enumerate(line_list):
                    run = paragraph.add_run(line + ("\n" if i < len(line_list) - 1 else ""))
                    run.font.size = Pt(8)
                    run.font.name = "Times New Roman"
        output = io.BytesIO()
        doc.save(output)
        return output.getvalue()
    except (ValueError, KeyError, OSError, BadZipFile, OpcError, XMLSyntaxError) as exc:
        raise HTTPException(422, "Không thể xuất bản in: DOCX hỏng hoặc không đúng định dạng Word") from exc


def _print_bytes(source_bytes: bytes, suffix: str, lines: list[str] | str) -> tuple[bytes, str]:
    if suffix == ".pdf":
        return _stamp_pdf(source_bytes, lines), "application/pdf"
    if suffix == ".docx":
        return _stamp_docx(source_bytes, lines), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    raise HTTPException(422, "Print copy supports PDF or DOCX")


def _print_response(result: bytes, media_type: str, code: str, suffix: str,
                    instant: datetime, filename: str | None = None) -> Response:
    from urllib.parse import quote
    safe_name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", filename or (code+suffix))
    return Response(content=result, media_type=media_type, headers={
        "Content-Disposition": "attachment; filename*=UTF-8\x27\x27"+quote(safe_name),
        "X-Document-Code": code,
        "X-Exported-At": instant.isoformat(),
        "X-Print-SHA256": hashlib.sha256(result).hexdigest(),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    })


def export_history(session, *, action, resource_type, resource_id, version, document_id=None):
    """Read existing audited exports, including records made before this UI existed."""
    events = session.scalars(select(m.AuditEvent).where(m.AuditEvent.action == action,
        m.AuditEvent.resource_type == resource_type, m.AuditEvent.resource_id == resource_id,
        m.AuditEvent.before_hash == version.content_sha256)
        .order_by(m.AuditEvent.occurred_at.desc(), m.AuditEvent.id.desc())).all()
    result = []
    for event in events:
        metadata = dict(piece.strip().split("=", 1) for piece in (event.reason or "").split(";") if "=" in piece)
        if metadata.get("version") != str(version.version_no):
            continue
        if document_id and metadata.get("document") != str(document_id):
            continue
        if metadata.get("version_id") and metadata["version_id"] != str(version.id):
            continue
        if not metadata.get("code"):
            continue
        actor_name = "Tài khoản trong hệ thống"
        for cls in (m.StudentProfile, m.LecturerProfile):
            actor = session.scalar(select(cls).where(cls.user_id == event.actor_id))
            if actor:
                actor_name = actor.display_name
                break
        result.append(PrintExportOut(id=event.id, actor_name=actor_name, document_code=metadata["code"],
            version_no=version.version_no, exported_at=event.occurred_at,
            copy_status="SUBMITTED" if action == "REGISTRATION_FORM_PRINT_EXPORTED" else "APPROVED"))
        if len(result) == 50:
            break
    return result


def proposal_print_history(session, user, thesis_id, version_id):
    thesis_access(session, user, thesis_id, action="proposal:view")
    version = session.scalar(select(m.ProposalVersion).join(m.Proposal, m.Proposal.id == m.ProposalVersion.proposal_id)
        .where(m.Proposal.thesis_id == thesis_id, m.ProposalVersion.id == version_id))
    if version is None:
        raise HTTPException(404, "Không tìm thấy phiên bản đề cương trong hồ sơ này")
    return export_history(session, action="PROPOSAL_PRINT_COPY_EXPORTED", resource_type="thesis",
        resource_id=thesis_id, version=version)


def document_print_history(session, user, thesis_id, document_id, version_id):
    from backend.services import documents
    thesis_access(session, user, thesis_id, action="document:view")
    documents.document(session, thesis_id, document_id, user=user)
    version = session.scalar(select(m.DocumentVersion).where(m.DocumentVersion.id == version_id,
        m.DocumentVersion.document_id == document_id))
    if version is None:
        raise HTTPException(404, "Không tìm thấy phiên bản tài liệu trong hồ sơ này")
    return export_history(session, action="DOCUMENT_PRINT_COPY_EXPORTED", resource_type="thesis",
        resource_id=thesis_id, version=version, document_id=document_id)


def export_proposal(session, user, thesis_id, version_id) -> Response:
    thesis = thesis_access(session, user, thesis_id, action="proposal:view")
    proposal = session.scalar(select(m.Proposal).where(m.Proposal.thesis_id == thesis_id))
    if not proposal or proposal.state not in {"DEPARTMENT_FINALIZED", "DEAN_CONFIRMED", "PRINT_READY"}:
        raise HTTPException(409, "Print copy is available after department finalization")
    version = session.scalar(select(m.ProposalVersion).where(
        m.ProposalVersion.id == version_id,
        m.ProposalVersion.proposal_id == proposal.id,
        m.ProposalVersion.version_no == proposal.current_version_no))
    if not version:
        raise HTTPException(404, "Only the current approved version can be printed")
    source = download_version(session, user, thesis_id, version_id)
    source_bytes = Path(source.path).read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != version.content_sha256:
        raise HTTPException(409, "Uploaded file changed before export")
    original = session.get(m.StoredFile, version.stored_file_id)
    code = _stable_code(session, thesis, "DC", version.version_no)
    instant = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    public_url = _public_url()
    lines = _footer_lines(public_url, code, instant)
    suffix = Path(original.original_name).suffix.lower()
    result, media_type = _print_bytes(source_bytes, suffix, lines)
    audit(session, user, "PROPOSAL_PRINT_COPY_EXPORTED", "thesis", thesis_id,
        f"exporter={user.id}; code={code}; version={version.version_no}; version_id={version.id}; exported_at={instant.isoformat()}; url={public_url}/theses/{thesis_id}; file_sha256={version.content_sha256}",
        before_hash=version.content_sha256, after_hash=hashlib.sha256(result).hexdigest())
    session.commit()
    return _print_response(result, media_type, code, suffix, instant, filename="De-cuong-v"+str(version.version_no)+"-"+original.original_name)


def export_document(session, user, thesis_id, document_id, version_id) -> Response:
    from backend.services import documents

    thesis = thesis_access(session, user, thesis_id, action="document:view")
    item = documents.document(session, thesis_id, document_id, lock=True, user=user)
    if item.document_type not in {"PLAN", "REPORT"}:
        raise HTTPException(409, "Only a plan or report can receive a paper copy")
    version = session.scalar(select(m.DocumentVersion).where(
        m.DocumentVersion.id == version_id, m.DocumentVersion.document_id == item.id,
        m.DocumentVersion.state.in_(["ACCEPTED", "FINAL"])))
    latest = session.scalar(select(m.DocumentVersion.id).where(
        m.DocumentVersion.document_id == item.id,
        m.DocumentVersion.state.in_(["ACCEPTED", "FINAL"]))
        .order_by(m.DocumentVersion.version_no.desc()).limit(1))
    if not version or latest != version.id:
        raise HTTPException(409, "Only the current accepted version can be printed")
    source = documents.download_version(session, user, thesis_id, document_id, version_id)
    source_bytes = Path(source.path).read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != version.content_sha256:
        raise HTTPException(409, "Uploaded file changed before export")
    original = session.get(m.StoredFile, version.stored_file_id)
    prefix = "KH" if item.document_type == "PLAN" else "BC"
    code = _stable_code(session, thesis, prefix, version.version_no)
    instant = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    public_url = _public_url()
    lines = _footer_lines(public_url, code, instant)
    suffix = Path(original.original_name).suffix.lower()
    result, media_type = _print_bytes(source_bytes, suffix, lines)
    audit(session, user, "DOCUMENT_PRINT_COPY_EXPORTED", "thesis", thesis_id,
        f"exporter={user.id}; code={code}; document={item.id}; version={version.version_no}; version_id={version.id}; exported_at={instant.isoformat()}; url={public_url}/theses/{thesis_id}; file_sha256={version.content_sha256}",
        before_hash=version.content_sha256, after_hash=hashlib.sha256(result).hexdigest())
    session.commit()
    return _print_response(result, media_type, code, suffix, instant, filename=("Ke-hoach" if item.document_type=="PLAN" else "Bao-cao")+"-v"+str(version.version_no)+"-"+original.original_name)
