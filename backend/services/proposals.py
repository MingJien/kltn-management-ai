"""Append-only proposal submissions and scoped academic decisions.

The dean endpoint records a reference to an already signed paper copy; it is
not an electronic-signature implementation.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from backend.api.core_schemas import PendingAdvisorOut, ProposalOut, ProposalVersionOut, ReviewOut
from backend.db.models import entities as m
from backend.services.documents import MAX_BYTES, require_clean, valid_content
from backend.services import deadlines, file_scanner
from backend.services.registration import profile, row_version
from backend.services.theses import audit, eligible_lecturer, now, primary_advisor, rights, thesis_access


def storage_root() -> Path:
    root = Path(__file__).resolve().parents[2]
    return Path(os.getenv("KLTN_PROPOSAL_DIR", str(root / "local" / "uploads" / "proposals"))).resolve()


def _proposal(session, thesis_id, *, lock=False):
    query = select(m.Proposal).where(m.Proposal.thesis_id == thesis_id)
    return session.scalar(query.with_for_update() if lock else query)


def _version(session, proposal):
    if not proposal or proposal.current_version_no is None:
        return None
    return session.scalar(select(m.ProposalVersion).where(
        m.ProposalVersion.proposal_id == proposal.id,
        m.ProposalVersion.version_no == proposal.current_version_no))


def proposal_out(session, thesis_id, proposal):
    if proposal is None:
        return ProposalOut(id=None, thesis_id=thesis_id, state="DRAFT", row_version=0,
            current_version_no=None, versions=[], reviewers=[], department_confirmed=False,
            dean_confirmed=False)
    versions = session.scalars(select(m.ProposalVersion).where(
        m.ProposalVersion.proposal_id == proposal.id).order_by(m.ProposalVersion.version_no.desc())).all()
    assignments = session.scalars(select(m.ReviewerAssignment).where(
        m.ReviewerAssignment.proposal_id == proposal.id,
        m.ReviewerAssignment.state == "ACTIVE").order_by(m.ReviewerAssignment.assigned_at)).all()
    signed = set(session.scalars(select(m.SignatureConfirmation.signature_type).where(
        m.SignatureConfirmation.proposal_id == proposal.id)).all())

    def version_out(version):
        file = session.get(m.StoredFile, version.stored_file_id)
        student = session.get(m.StudentProfile, version.submitted_by)
        rows = session.scalars(select(m.ProposalReview).where(
            m.ProposalReview.proposal_version_id == version.id).order_by(m.ProposalReview.created_at)).all()
        reviews = []
        for item in rows:
            lecturer = session.scalar(select(m.LecturerProfile).where(
                m.LecturerProfile.user_id == item.reviewer_user_id))
            reviews.append(ReviewOut(reviewer_name=lecturer.display_name if lecturer else "Giảng viên",
                decision=item.decision, comment=item.comment, created_at=item.created_at))
        return ProposalVersionOut(id=version.id, version_no=version.version_no,
            file_name=file.original_name, byte_size=file.byte_size, sha256=version.content_sha256,
            submitted_by_name=student.display_name, submitted_at=version.submitted_at,
            due_at_at_submission=version.due_at_at_submission,
            late=bool(version.due_at_at_submission and version.submitted_at > version.due_at_at_submission),
            scan_state=file.scan_state, reviews=reviews)

    reviewers = []
    for assignment in assignments:
        lecturer = session.get(m.LecturerProfile, assignment.lecturer_id)
        reviewers.append(PendingAdvisorOut(lecturer_id=lecturer.id, display_name=lecturer.display_name))
    return ProposalOut(id=proposal.id, thesis_id=thesis_id, state=proposal.state,
        row_version=proposal.row_version, current_version_no=proposal.current_version_no,
        versions=[version_out(v) for v in versions], reviewers=reviewers,
        department_confirmed="DEPARTMENT_FINALIZATION" in signed,
        dean_confirmed="DEAN_CONFIRMATION" in signed)


def rescan_version(session, user, thesis_id, version_id):
    thesis_access(session, user, thesis_id, action="proposal:view", lock=True, write=True)
    proposal = _proposal(session, thesis_id, lock=True)
    version = session.scalar(select(m.ProposalVersion).where(
        m.ProposalVersion.proposal_id == proposal.id,
        m.ProposalVersion.id == version_id).with_for_update()) if proposal else None
    if not version:
        raise HTTPException(404, "Không tìm thấy phiên bản")
    file = session.get(m.StoredFile, version.stored_file_id)
    if file.scan_state == "CLEAN":
        return proposal_out(session, thesis_id, proposal)
    if file.scan_state == "INFECTED":
        raise HTTPException(409, "Tệp nhiễm mã độc; hãy nộp phiên bản mới")
    file_scanner.require_available()
    state = file_scanner.scan(file, storage_root() / Path(file.storage_key).name)
    audit(session, user, "PROPOSAL_FILE_SCANNED", "proposal_version", version.id, state)
    session.flush()
    result = proposal_out(session, thesis_id, proposal)
    session.commit()
    return result


def get_proposal(session, user, thesis_id):
    thesis_access(session, user, thesis_id, action="proposal:view")
    return proposal_out(session, thesis_id, _proposal(session, thesis_id))


async def upload_version(session, user, thesis_id, request, expected):
    from backend.api.auth import _same_app_origin

    if not _same_app_origin(request):
        raise HTTPException(403, "Nguồn yêu cầu không được phép")
    path = None
    try:
        thesis = thesis_access(session, user, thesis_id, action="proposal:submit", lock=True, write=True)
        proposal = _proposal(session, thesis_id, lock=True)
        row_version(expected, proposal.row_version if proposal else 0)
        deadline = deadlines.for_submission(session, thesis, "PROPOSAL")
        if proposal and proposal.state not in {"DRAFT", "SUBMITTED", "UNDER_REVIEW", "REVISION_REQUIRED"}:
            raise HTTPException(409, "Đề cương đã được xác nhận hoặc chốt; không thể tự nộp bản mới")
        previous = _version(session, proposal)
        reviewed = bool(previous and session.scalar(select(m.ProposalReview.id).where(
            m.ProposalReview.proposal_version_id == previous.id).limit(1)))
        if proposal and proposal.state == "UNDER_REVIEW" and reviewed:
            raise HTTPException(409, "GV đã góp ý phiên bản này; cần GVHD yêu cầu sửa")
        revision_requested = bool(proposal and proposal.state == "REVISION_REQUIRED")
        deadlines.ensure_submission_allowed(deadline,
            revision_requested=revision_requested,
            previous_submitted=bool(previous and proposal.state in {"SUBMITTED", "UNDER_REVIEW"}),
            reviewed=reviewed)
        name = unquote(request.headers.get("X-File-Name", "")).replace("\\", "/").split("/")[-1].strip()
        if not name or len(name) > 180 or any(ord(ch) < 32 for ch in name):
            raise HTTPException(422, "Tên tệp không hợp lệ")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(413, "Đề cương tối đa 10 MB")
            chunks.append(chunk)
        content = b"".join(chunks)
        if not content or Path(name).suffix.lower() not in {".pdf", ".docx"}:
            raise HTTPException(422, "Đề cương phải là PDF hoặc DOCX không rỗng")
        media_type = valid_content(name, content)
        root = storage_root()
        root.mkdir(parents=True, exist_ok=True)
        key = uuid4().hex + Path(name).suffix.lower()
        path = root / key
        with path.open("xb") as handle:
            handle.write(content)
        digest = hashlib.sha256(content).hexdigest()
        if proposal is None:
            proposal = m.Proposal(id=uuid4(), thesis_id=thesis_id, state="DRAFT")
            session.add(proposal)
            session.flush()
        file = m.StoredFile(id=uuid4(), storage_key="proposals/" + key,
            original_name=name, media_type=media_type, byte_size=size, sha256=digest,
            scan_state="QUARANTINED")
        file_scanner.scan(file, path)
        session.add(file)
        session.flush()
        next_version = (proposal.current_version_no or 0) + 1
        student = profile(session, user, "STUDENT")
        session.add(m.ProposalVersion(id=uuid4(), proposal_id=proposal.id,
            version_no=next_version, stored_file_id=file.id,
            submitted_by=student.id,
            submitted_at=now(), due_at_at_submission=deadline.due_at, content_sha256=digest))
        proposal.current_version_no = next_version
        proposal.state = "SUBMITTED"
        proposal.row_version += 1
        audit(session, user, "PROPOSAL_SELF_CORRECTED" if previous and not revision_requested else "PROPOSAL_SUBMITTED", "thesis", thesis_id,
            f"Đề cương v{next_version}", after_hash=digest)
        session.flush()
        from backend.services.notifications import notify_thesis_advisor

        notify_thesis_advisor(session, thesis=thesis, actor_user_id=user.id, kind="PROPOSAL_SUBMITTED",
            message=(f"{student.display_name} đã nộp đề cương lần {next_version} cho khóa luận "
                     f"{thesis.current_title}. Mời bạn góp ý hoặc xác nhận."),
            section="proposal")
        result = proposal_out(session, thesis_id, proposal)
        session.commit()
        return result
    except Exception:
        session.rollback()
        if path and path.is_file():
            try:
                path.unlink()
            except OSError:
                pass  # The integrity check reports the orphan instead of hiding the original error.
        raise


def assign_reviewer(session, user, thesis_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="proposal:assign_reviewer", lock=True, write=True)
    proposal = _proposal(session, thesis_id, lock=True)
    if not proposal:
        raise HTTPException(409, "Sinh viên chưa nộp đề cương")
    row_version(expected, proposal.row_version)
    if proposal.state in {"DEPARTMENT_FINALIZED", "DEAN_CONFIRMED", "PRINT_READY"}:
        raise HTTPException(409, "Đề cương đã chốt")
    lecturer = eligible_lecturer(session, data.lecturer_id, thesis.department_id)
    current = primary_advisor(session, thesis_id)
    if current and current.lecturer_id == lecturer.id:
        raise HTTPException(422, "GVHD chính không là người góp ý chéo")
    if session.scalar(select(m.ReviewerAssignment.id).where(
        m.ReviewerAssignment.proposal_id == proposal.id,
        m.ReviewerAssignment.lecturer_id == lecturer.id,
        m.ReviewerAssignment.state == "ACTIVE")):
        raise HTTPException(409, "Giảng viên đã được phân công")
    session.add(m.ReviewerAssignment(id=uuid4(), lecturer_id=lecturer.id,
        proposal_id=proposal.id, review_scope="PROPOSAL", assigned_by=user.id,
        assigned_at=now(), state="ACTIVE"))
    proposal.row_version += 1
    audit(session, user, "PROPOSAL_REVIEWER_ASSIGNED", "thesis", thesis_id,
        f"{lecturer.lecturer_code}: {data.reason}")
    session.flush()
    from backend.services.notifications import notify_user

    notify_user(session, recipient_user_id=lecturer.user_id, actor_user_id=user.id,
        kind="PROPOSAL_REVIEWER_ASSIGNED",
        message=(f"Bạn được phân công góp ý đề cương khóa luận {thesis.current_title}. "
                 f"Lý do: {data.reason[:200]}"),
        url=f"/theses/{thesis_id}?section=proposal")
    result = proposal_out(session, thesis_id, proposal)
    session.commit()
    return result


def review(session, user, thesis_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="proposal:view", lock=True, write=True)
    permissions = rights(session, user, thesis)
    if data.decision == "COMMENT":
        if "proposal:comment" not in permissions:
            raise HTTPException(403, "Chỉ giảng viên được phân công mới góp ý chéo")
    elif "proposal:review" not in permissions:
        raise HTTPException(403, "Chỉ GVHD chính được xác nhận hoặc yêu cầu sửa đề cương")
    proposal = _proposal(session, thesis_id, lock=True)
    if not proposal:
        raise HTTPException(404, "Chưa có đề cương")
    row_version(expected, proposal.row_version)
    if proposal.state not in {"SUBMITTED", "UNDER_REVIEW", "ADVISOR_CONFIRMED"}:
        raise HTTPException(409, "Đề cương không còn chờ nhận xét")
    if data.decision != "COMMENT" and proposal.state == "ADVISOR_CONFIRMED":
        raise HTTPException(409, "GVHD đã xác nhận phiên bản này")
    version = _version(session, proposal)
    require_clean(session.get(m.StoredFile, version.stored_file_id), "nhận xét đề cương")
    lecturer = profile(session, user, "LECTURER")
    assignment = session.scalar(select(m.ReviewerAssignment).where(
        m.ReviewerAssignment.proposal_id == proposal.id,
        m.ReviewerAssignment.lecturer_id == lecturer.id,
        m.ReviewerAssignment.state == "ACTIVE"))
    if data.decision != "COMMENT":
        advisor = primary_advisor(session, thesis_id)
        if not advisor or advisor.lecturer_id != lecturer.id:
            raise HTTPException(403, "Phân công GVHD chính không còn hiệu lực")
        if assignment is None:
            assignment = m.ReviewerAssignment(id=uuid4(), lecturer_id=lecturer.id,
                proposal_id=proposal.id, review_scope="PROPOSAL", assigned_by=advisor.assigned_by,
                assigned_at=now(), state="ACTIVE")
            session.add(assignment)
            session.flush()
    if assignment is None or session.scalar(select(m.ProposalReview.id).where(
        m.ProposalReview.proposal_version_id == version.id,
        m.ProposalReview.reviewer_assignment_id == assignment.id)):
        raise HTTPException(409, "Bạn đã nhận xét phiên bản này hoặc phân công không còn hiệu lực")
    from backend.services.progress_annotations import publish_annotations
    publish_annotations(session, version, lecturer, kind="proposal", summary_comment=data.comment)
    session.add(m.ProposalReview(id=uuid4(), proposal_version_id=version.id,
        reviewer_assignment_id=assignment.id, reviewer_user_id=user.id,
        decision=data.decision, comment=data.comment))
    if data.decision == "CONFIRM":
        proposal.state = "ADVISOR_CONFIRMED"
    elif data.decision == "REVISION_REQUIRED":
        proposal.state = "REVISION_REQUIRED"
    elif proposal.state == "SUBMITTED":
        proposal.state = "UNDER_REVIEW"
    proposal.row_version += 1
    audit(session, user, "PROPOSAL_" + data.decision, "thesis", thesis_id,
        f"v{version.version_no}: {data.comment}", after_hash=version.content_sha256)
    session.flush()
    from backend.services.notifications import (notify_department_heads_of,
                                                notify_thesis_advisor, notify_thesis_students)

    decision_label = {"COMMENT": "góp ý", "CONFIRM": "xác nhận", "REVISION_REQUIRED": "yêu cầu sửa"}[data.decision]
    message = (f"{lecturer.display_name} đã {decision_label} đề cương {thesis.current_title} "
               f"(phiên bản {version.version_no}): {data.comment[:200]}")
    notify_thesis_students(session, thesis=thesis, actor_user_id=user.id,
        kind="PROPOSAL_REVIEWED", message=message, section="proposal")
    notify_thesis_advisor(session, thesis=thesis, actor_user_id=user.id,
        kind="PROPOSAL_REVIEWED", message=message, section="proposal")
    notify_department_heads_of(session, department_id=thesis.department_id, actor_user_id=user.id,
        kind="PROPOSAL_REVIEWED", thesis=thesis, message=message)
    result = proposal_out(session, thesis_id, proposal)
    session.commit()
    return result


def finalize(session, user, thesis_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="proposal:finalize", lock=True, write=True)
    proposal = _proposal(session, thesis_id, lock=True)
    if not proposal:
        raise HTTPException(404, "Chưa có đề cương")
    row_version(expected, proposal.row_version)
    if proposal.state != "ADVISOR_CONFIRMED":
        raise HTTPException(409, "Cần GVHD chính xác nhận bản đề cương hiện hành trước")
    version = _version(session, proposal)
    advisor = primary_advisor(session, thesis_id)
    if advisor is None:
        raise HTTPException(409, "Chưa có phân công GVHD chính còn hiệu lực")
    valid = session.scalar(select(m.ProposalReview.id).join(m.ReviewerAssignment,
        m.ReviewerAssignment.id == m.ProposalReview.reviewer_assignment_id).where(
        m.ProposalReview.proposal_version_id == version.id,
        m.ProposalReview.decision == "CONFIRM",
        m.ReviewerAssignment.lecturer_id == advisor.lecturer_id))
    if not valid:
        raise HTTPException(409, "Xác nhận GVHD không khớp phân công hiện hành")
    session.add(m.SignatureConfirmation(id=uuid4(), proposal_id=proposal.id,
        proposal_version_no=version.version_no, signature_type="DEPARTMENT_FINALIZATION",
        signer_user_id=user.id, confirmed_at=now()))
    proposal.state = "DEPARTMENT_FINALIZED"
    proposal.row_version += 1
    audit(session, user, "PROPOSAL_DEPARTMENT_FINALIZED", "thesis", thesis_id,
        f"v{version.version_no}: {data.reason}", after_hash=version.content_sha256)
    session.flush()
    from backend.services.notifications import notify_thesis_students

    notify_thesis_students(session, thesis=thesis, actor_user_id=user.id,
        kind="PROPOSAL_FINALIZED",
        message=f"Bộ môn đã chốt đề cương {thesis.current_title} (phiên bản {version.version_no}).",
        section="proposal", include_advisor=True)
    result = proposal_out(session, thesis_id, proposal)
    session.commit()
    return result


def record_dean_confirmation(session, user, thesis_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="proposal:dean_confirm", lock=True, write=True)
    proposal = _proposal(session, thesis_id, lock=True)
    if not proposal:
        raise HTTPException(404, "Chưa có đề cương")
    row_version(expected, proposal.row_version)
    if proposal.state != "DEPARTMENT_FINALIZED":
        raise HTTPException(409, "Cần Trưởng bộ môn chốt trước khi ghi nhận bản ký của Trưởng khoa")
    version = _version(session, proposal)
    session.add(m.SignatureConfirmation(id=uuid4(), proposal_id=proposal.id,
        proposal_version_no=version.version_no, signature_type="DEAN_CONFIRMATION",
        signer_user_id=user.id, confirmed_at=now(), official_ref=data.official_ref))
    proposal.state = "DEAN_CONFIRMED"
    proposal.row_version += 1
    audit(session, user, "PROPOSAL_DEAN_COPY_RECORDED", "thesis", thesis_id,
        data.official_ref, after_hash=version.content_sha256)
    session.flush()
    from backend.services.notifications import notify_department_heads_of, notify_thesis_students

    message = (f"Trưởng khoa đã ghi nhận bản đề cương {thesis.current_title} "
               f"(phiên bản {version.version_no}, căn cứ {data.official_ref}).")
    notify_thesis_students(session, thesis=thesis, actor_user_id=user.id,
        kind="PROPOSAL_DEAN_CONFIRMED", message=message, section="proposal",
        include_advisor=True)
    notify_department_heads_of(session, department_id=thesis.department_id,
        actor_user_id=user.id, kind="PROPOSAL_DEAN_CONFIRMED", thesis=thesis,
        message=message)
    result = proposal_out(session, thesis_id, proposal)
    session.commit()
    return result


def download_version(session, user, thesis_id, version_id):
    thesis_access(session, user, thesis_id, action="proposal:view")
    proposal = _proposal(session, thesis_id)
    version = session.scalar(select(m.ProposalVersion).where(
        m.ProposalVersion.proposal_id == proposal.id,
        m.ProposalVersion.id == version_id)) if proposal else None
    file = session.get(m.StoredFile, version.stored_file_id) if version else None
    if not file or not file.storage_key.startswith("proposals/"):
        raise HTTPException(404, "Tệp không khả dụng")
    require_clean(file, "tải tệp")
    root = storage_root()
    path = (root / file.storage_key.removeprefix("proposals/")).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "Tệp không khả dụng")
    if path.stat().st_size != file.byte_size or hashlib.sha256(path.read_bytes()).hexdigest() != version.content_sha256:
        raise HTTPException(409, "Tệp lưu trữ không khớp mã kiểm tra")
    return FileResponse(path, media_type="application/octet-stream", filename=file.original_name,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
