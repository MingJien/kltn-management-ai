"""Private lecturer drafts become visible only with a version-specific review."""
from fastapi import HTTPException
from sqlalchemy import func, or_, select

from backend.api.core_schemas import ProgressAnnotationOut, ProgressAnnotationsOut, ReviewAttachmentOut
from backend.db.models import entities as m
from backend.services.documents import require_clean
from backend.services.registration import profile, row_version
from backend.services.theses import EDITABLE, now, rights, thesis_access


def context(session, user, thesis_id, report_id, *, write=False, kind="progress", document_id=None):
    if kind != "progress":
        return file_context(session, user, thesis_id, report_id, write=write, kind=kind, document_id=document_id)
    thesis = thesis_access(session, user, thesis_id, action="progress:view", lock=write, write=write)
    query = select(m.ProgressReport).where(m.ProgressReport.id == report_id, m.ProgressReport.thesis_id == thesis.id)
    report = session.scalar(query.with_for_update() if write else query)
    if report is None:
        raise HTTPException(404, "Không tìm thấy báo cáo trong phạm vi của bạn")
    lecturer = profile(session, user, "LECTURER") if user.base_role == "LECTURER" else None
    latest = session.scalar(select(func.max(m.ProgressReport.version_no)).where(
        m.ProgressReport.thesis_id == thesis.id, m.ProgressReport.milestone_id == report.milestone_id))
    reviewed = lecturer is not None and session.scalar(select(m.ProgressReview.id).where(
        m.ProgressReview.progress_report_id == report.id, m.ProgressReview.reviewer_id == lecturer.id)) is not None
    can_edit = bool(lecturer and not reviewed and report.state == "SUBMITTED" and report.version_no == latest
        and thesis.state in EDITABLE and ({"progress:review", "progress:comment"} & rights(session, user, thesis)))
    if write:
        if not lecturer or not ({"progress:review", "progress:comment"} & rights(session, user, thesis)):
            raise HTTPException(403, "Chỉ GVHD hoặc người được phân công góp ý được tạo nhận xét")
        if not can_edit:
            raise HTTPException(409, "Chỉ GV được phân công mới được sửa bản nháp trên phiên bản mới nhất chưa phản hồi")
        require_clean(session.get(m.StoredFile, report.evidence_file_id), "ghi nhận xét theo vị trí")
    return report, lecturer, can_edit


def file_context(session, user, thesis_id, version_id, *, write, kind, document_id):
    thesis = thesis_access(session, user, thesis_id, action=f"{kind}:view", lock=write, write=write)
    permissions = rights(session, user, thesis)
    lecturer = profile(session, user, "LECTURER") if user.base_role == "LECTURER" else None
    if kind == "document":
        from backend.services.documents import document, is_progress_evidence
        parent = document(session, thesis.id, document_id, lock=write, user=user)
        query = select(m.DocumentVersion).where(m.DocumentVersion.id == version_id, m.DocumentVersion.document_id == parent.id)
        version = session.scalar(query.with_for_update() if write else query)
        latest = session.scalar(select(func.max(m.DocumentVersion.version_no)).where(m.DocumentVersion.document_id == parent.id))
        allowed = "document:review" in permissions and parent.document_type != "PROPOSAL" and not is_progress_evidence(session,parent.id)
        editable = version and version.version_no == latest and version.state == "SUBMITTED"
    else:
        from backend.services.proposals import _proposal
        parent = _proposal(session, thesis.id, lock=write)
        query = select(m.ProposalVersion).where(m.ProposalVersion.id == version_id,
            m.ProposalVersion.proposal_id == (parent.id if parent else None))
        version = session.scalar(query.with_for_update() if write else query)
        allowed = bool({"proposal:review", "proposal:comment"} & permissions)
        reviewed = lecturer and version and session.scalar(select(m.ProposalReview.id).where(
            m.ProposalReview.proposal_version_id == version.id, m.ProposalReview.reviewer_user_id == user.id))
        editable = bool(parent and version and version.version_no == parent.current_version_no and not reviewed and
            (parent.state in {"SUBMITTED", "UNDER_REVIEW"} or
             (parent.state == "ADVISOR_CONFIRMED" and "proposal:comment" in permissions and "proposal:review" not in permissions)))
    if version is None:
        raise HTTPException(404, "Không tìm thấy phiên bản trong phạm vi của bạn")
    can_edit = bool(lecturer and allowed and editable and thesis.state in EDITABLE)
    if write:
        if not lecturer or not allowed:
            raise HTTPException(403, "Chỉ giảng viên được phân công mới được tạo nhận xét")
        if not can_edit:
            raise HTTPException(409, "Chỉ nhận xét bản mới nhất chưa được bạn phản hồi")
        require_clean(session.get(m.StoredFile, version.stored_file_id), "ghi nhận xét theo vị trí")
    return version, lecturer, can_edit


def target_column(kind):
    return getattr(m.ProgressReviewAnnotation, {"progress": "progress_report_id", "document": "document_version_id", "proposal": "proposal_version_id"}[kind])


def file_id(record, kind):
    return record.evidence_file_id if kind == "progress" else record.stored_file_id


def annotation_out(session, note):
    attachment = session.get(m.StoredFile, note.attachment_file_id) if note.attachment_file_id else None
    return ProgressAnnotationOut(id=note.id, reviewer_id=note.reviewer_id,
        annotation_kind=note.annotation_kind,
        attachment=ReviewAttachmentOut(file_name=attachment.original_name, byte_size=attachment.byte_size, scan_state=attachment.scan_state) if attachment else None,
        reviewer_name=session.get(m.LecturerProfile, note.reviewer_id).display_name,
        page_number=note.page_number, x=note.x, y=note.y, location_label=note.location_label,
        quoted_text=note.quoted_text, comment=note.comment, state=note.state,
        row_version=note.row_version, updated_at=note.updated_at, published_at=note.published_at)


def read_only_reason(session, user, thesis_id, record, *, kind, can_edit):
    if can_edit:
        return None
    if user.base_role == "STUDENT":
        return "Bạn đang xem bằng tài khoản sinh viên. SV được đọc tệp và góp ý đã gửi; chỉ giảng viên được phân công mới tạo và gửi nhận xét."
    thesis = session.get(m.Thesis, thesis_id)
    permissions = rights(session, user, thesis)
    required = {"document:review"} if kind == "document" else {f"{kind}:review", f"{kind}:comment"}
    if not required & permissions:
        return "Tài khoản này chưa được phân công nhận xét tài liệu này. Quyền Trưởng bộ môn hoặc quản lý biểu mẫu không tự thay quyền GVHD."
    if thesis.state not in EDITABLE:
        return "Hồ sơ khóa luận đã khóa xử lý. Bạn chỉ được xem lại tệp và phản hồi đã gửi."
    if kind == "document":
        from backend.services.documents import is_progress_evidence
        if is_progress_evidence(session,record.document_id):
            return "Đây là minh chứng báo cáo tiến độ. Mở mục Tiến độ để nhận xét theo đúng lần nộp, không duyệt như tài liệu độc lập."
        latest = session.scalar(select(func.max(m.DocumentVersion.version_no)).where(m.DocumentVersion.document_id == record.document_id))
        if record.version_no != latest:
            return "Đã có phiên bản nộp mới hơn. Quay lại hồ sơ và mở bản mới nhất đang chờ phản hồi để nhận xét đúng tệp."
        if record.state in {"ACCEPTED", "FINAL"}:
            return "Phiên bản này đã được GVHD tiếp nhận. Chỉ xem lại tệp và kết quả đã gửi; không sửa đè nhận xét trên bản đã duyệt."
        if record.state == "REVISION_REQUESTED":
            return "GVHD đã gửi yêu cầu chỉnh sửa cho phiên bản này. Chỉ xem lại phản hồi; nhận xét tiếp trên bản mới sau khi SV nộp lại."
    elif kind == "progress":
        latest = session.scalar(select(func.max(m.ProgressReport.version_no)).where(m.ProgressReport.thesis_id == thesis_id, m.ProgressReport.milestone_id == record.milestone_id))
        if record.version_no != latest:
            return "Đã có lần nộp báo cáo mới hơn. Quay lại mốc tiến độ và mở lần nộp mới nhất để nhận xét."
    else:
        parent = session.get(m.Proposal, record.proposal_id)
        if record.version_no != parent.current_version_no:
            return "Đã có phiên bản đề cương mới hơn. Quay lại hồ sơ và mở bản hiện hành để nhận xét."
    return "Phiên bản này đã được xử lý hoặc bạn đã gửi phản hồi. Bạn chỉ được xem lại nội dung và nhận xét đã gửi."


def list_annotations(session, user, thesis_id, report_id, *, kind="progress", document_id=None):
    report, lecturer, can_edit = context(session, user, thesis_id, report_id, kind=kind, document_id=document_id)
    visible = m.ProgressReviewAnnotation.state == "PUBLISHED"
    if lecturer:
        visible = or_(visible, m.ProgressReviewAnnotation.reviewer_id == lecturer.id)
    notes = session.scalars(select(m.ProgressReviewAnnotation).where(
        target_column(kind) == report.id, visible)
        .order_by(m.ProgressReviewAnnotation.created_at, m.ProgressReviewAnnotation.id)).all()
    return ProgressAnnotationsOut(annotations=[annotation_out(session, note) for note in notes], can_edit=can_edit,
        read_only_reason=read_only_reason(session, user, thesis_id, report, kind=kind, can_edit=can_edit))


def save_annotation(session, user, thesis_id, report_id, annotation_id, data, expected, *, kind="progress", document_id=None):
    report, lecturer, _ = context(session, user, thesis_id, report_id, write=True, kind=kind, document_id=document_id)
    if (data.x is None) != (data.y is None) or (data.x is not None and data.page_number is None):
        raise HTTPException(422, "Ghim PDF cần đủ trang và hai tọa độ")
    stored_file_id = file_id(report, kind)
    column = target_column(kind)
    file = session.get(m.StoredFile, stored_file_id)
    if data.annotation_kind != "PIN" and any(value is not None for value in (data.page_number, data.x, data.y)):
        raise HTTPException(422, "Nhận xét chung và tệp phản hồi không có tọa độ ghim")
    if data.x is not None and file.media_type != "application/pdf":
        raise HTTPException(422, "Chỉ ghim tọa độ trên PDF; DOCX/TXT dùng mục và đoạn trích")
    note = session.get(m.ProgressReviewAnnotation, annotation_id)
    if note:
        if getattr(note, column.key) != report.id or note.reviewer_id != lecturer.id:
            raise HTTPException(404, "Không tìm thấy bản nháp của bạn")
        if note.state != "DRAFT" or note.stored_file_id != stored_file_id:
            raise HTTPException(409, "Nhận xét đã gửi hoặc tệp đã thay đổi; không thể ghi đè")
        if data.annotation_kind != note.annotation_kind:
            raise HTTPException(409, "Không đổi loại của nhận xét đã tạo")
        row_version(expected, note.row_version)
        note.row_version += 1
    else:
        if data.annotation_kind == "ATTACHMENT":
            raise HTTPException(422, "Tệp phản hồi phải được tải qua chức năng đính kèm")
        if data.annotation_kind == "SUMMARY" and session.scalar(select(m.ProgressReviewAnnotation.id).where(
                column == report.id, m.ProgressReviewAnnotation.reviewer_id == lecturer.id,
                m.ProgressReviewAnnotation.annotation_kind == "SUMMARY")):
            raise HTTPException(409, "Nhận xét chung đã có ở phiên khác; mở lại để đồng bộ")
        row_version(expected, 0)
        count = session.scalar(select(func.count()).select_from(m.ProgressReviewAnnotation).where(
            column == report.id, m.ProgressReviewAnnotation.reviewer_id == lecturer.id))
        if count >= 100:
            raise HTTPException(422, "Tối đa 100 ghim nhận xét cho một phiên bản")
        note = m.ProgressReviewAnnotation(id=annotation_id, **{column.key: report.id},
            reviewer_id=lecturer.id, stored_file_id=stored_file_id, state="DRAFT", annotation_kind=data.annotation_kind)
        session.add(note)
    for key, value in data.model_dump().items():
        setattr(note, key, value)
    session.flush()
    result = annotation_out(session, note)
    session.commit()
    return result


def delete_annotation(session, user, thesis_id, report_id, annotation_id, expected, *, kind="progress", document_id=None):
    report, lecturer, _ = context(session, user, thesis_id, report_id, write=True, kind=kind, document_id=document_id)
    note = session.get(m.ProgressReviewAnnotation, annotation_id)
    if not note or getattr(note, target_column(kind).key) != report.id or note.reviewer_id != lecturer.id:
        raise HTTPException(404, "Không tìm thấy bản nháp của bạn")
    if note.state != "DRAFT":
        raise HTTPException(409, "Nhận xét đã gửi được giữ nguyên để đối chiếu")
    row_version(expected, note.row_version)
    session.delete(note)
    session.commit()


def publish_annotations(session, report, lecturer, *, kind="progress", summary_comment=None):
    """Called inside the same locked transaction as the official review decision."""
    notes = session.scalars(select(m.ProgressReviewAnnotation).where(
        target_column(kind) == report.id,
        m.ProgressReviewAnnotation.reviewer_id == lecturer.id,
        m.ProgressReviewAnnotation.state == "DRAFT").with_for_update()).all()
    for note in notes:
        if note.annotation_kind == "SUMMARY":
            if not note.comment.strip():
                session.delete(note)
                continue
            if summary_comment is not None:
                note.comment = summary_comment
        if note.annotation_kind == "ATTACHMENT":
            require_clean(session.get(m.StoredFile, note.attachment_file_id), "gửi tệp phản hồi cho sinh viên")
        if note.stored_file_id != file_id(report, kind) or not note.comment.strip():
            raise HTTPException(409, "Có ghim chưa có nội dung hoặc không đúng tệp; hãy hoàn tất hoặc bỏ ghim trước khi gửi")
        note.state = "PUBLISHED"
        note.published_at = now()
        note.row_version += 1


def attachment_note(session, user, thesis_id, version_id, annotation_id, *, kind, document_id=None, write=False):
    record, lecturer, _ = context(session, user, thesis_id, version_id, kind=kind, document_id=document_id, write=write)
    note = session.get(m.ProgressReviewAnnotation, annotation_id)
    if not note or getattr(note, target_column(kind).key) != record.id or note.annotation_kind != "ATTACHMENT":
        raise HTTPException(404, "Không tìm thấy tệp phản hồi")
    if note.state != "PUBLISHED" and (not lecturer or note.reviewer_id != lecturer.id):
        raise HTTPException(404, "Không tìm thấy tệp phản hồi")
    if write and (not lecturer or note.reviewer_id != lecturer.id or note.state != "DRAFT"):
        raise HTTPException(403, "Chỉ sửa tệp phản hồi nháp của chính bạn")
    return note, session.get(m.StoredFile, note.attachment_file_id)


async def upload_attachment(session, user, thesis_id, version_id, annotation_id, request, expected, *, kind, document_id=None):
    from pathlib import Path
    import hashlib
    from backend.services.documents import read_upload, persist_upload
    from backend.services import file_scanner
    from backend.services.theses import audit
    path = None
    try:
        record, lecturer, _ = context(session, user, thesis_id, version_id, kind=kind, document_id=document_id, write=True)
        row_version(expected, 0)
        name, content, mime = await read_upload(request)
        if Path(name).suffix.lower() not in {".pdf", ".docx"}:
            raise HTTPException(422, "Bản phản hồi nhận PDF hoặc DOCX, tối đa 10 MB")
        existing = session.get(m.ProgressReviewAnnotation, annotation_id)
        if existing:
            if getattr(existing, target_column(kind).key) != record.id or existing.reviewer_id != lecturer.id:
                raise HTTPException(404, "Không tìm thấy tệp phản hồi của bạn")
            file = session.get(m.StoredFile, existing.attachment_file_id) if existing.attachment_file_id else None
            if existing.state == "DRAFT" and file and file.original_name == name and file.sha256 == hashlib.sha256(content).hexdigest():
                return annotation_out(session, existing)  # safe retry after a lost response
            raise HTTPException(409, "Mã tệp đã được dùng; không ghi đè tệp phản hồi")
        count = session.scalar(select(func.count()).select_from(m.ProgressReviewAnnotation).where(
            target_column(kind) == record.id, m.ProgressReviewAnnotation.reviewer_id == lecturer.id,
            m.ProgressReviewAnnotation.annotation_kind == "ATTACHMENT"))
        if count >= 5:
            raise HTTPException(422, "Tối đa 5 tệp phản hồi cho một phiên bản và một giảng viên")
        file, digest, path = persist_upload(session, name, content, mime)
        file_scanner.scan(file, path)
        session.flush()  # Insert the new stored_file before the annotation's second FK to it.
        note = m.ProgressReviewAnnotation(id=annotation_id, **{target_column(kind).key:record.id},
            reviewer_id=lecturer.id, stored_file_id=file_id(record, kind), attachment_file_id=file.id,
            annotation_kind="ATTACHMENT", comment="Tệp phản hồi: " + name, state="DRAFT")
        session.add(note)
        audit(session, user, "REVIEW_ATTACHMENT_DRAFT_UPLOADED", "review_annotation", note.id, name, after_hash=digest)
        session.flush(); result = annotation_out(session, note); session.commit()
        return result
    except Exception:
        session.rollback()
        if path and path.is_file():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass  # Integrity tooling can report an orphan; keep the original failure.
        raise


def download_attachment(session, user, thesis_id, version_id, annotation_id, *, kind, document_id=None):
    from types import SimpleNamespace
    from backend.services.documents import stored_download
    note, file = attachment_note(session, user, thesis_id, version_id, annotation_id, kind=kind, document_id=document_id)
    from backend.services.download_names import thesis_identity
    return stored_download(session, SimpleNamespace(stored_file_id=file.id, content_sha256=file.sha256,
        download_label="Gop-y-dinh-kem",download_identity=thesis_identity(session,thesis_id)))


def rescan_attachment(session, user, thesis_id, version_id, annotation_id, expected, *, kind, document_id=None):
    from pathlib import Path
    from backend.services.documents import storage_root
    from backend.services import file_scanner
    note, file = attachment_note(session, user, thesis_id, version_id, annotation_id, kind=kind, document_id=document_id, write=True)
    row_version(expected, note.row_version)
    if file.scan_state == "INFECTED":
        raise HTTPException(409, "Tệp có mã độc; hãy bỏ bản nháp và đính kèm tệp sạch")
    if file.scan_state != "CLEAN":
        file_scanner.require_available()
        file_scanner.scan(file, storage_root() / Path(file.storage_key).name)
        note.row_version += 1
    session.flush(); result = annotation_out(session, note); session.commit()
    return result
