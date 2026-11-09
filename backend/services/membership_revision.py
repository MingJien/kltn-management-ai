"""Keep academic evidence tied to the group that actually continues the thesis."""
from fastapi import HTTPException
from sqlalchemy import func, or_, select

from backend.db.models import entities as m


def changed_at(session, thesis_id):
    # Use recording time, not a backdated administrative effective date. Files
    # submitted before the system knew the new group cannot confirm that group.
    withdrawn = session.scalar(select(func.max(m.ThesisWithdrawalRequest.recorded_at)).where(
        m.ThesisWithdrawalRequest.thesis_id == thesis_id,
        m.ThesisWithdrawalRequest.state == "RECORDED"))
    changed = session.scalar(select(func.max(m.ThesisChangeRequest.decided_at)).where(
        or_(m.ThesisChangeRequest.thesis_id == thesis_id,
            m.ThesisChangeRequest.snapshot["result_thesis_id"].astext == str(thesis_id)),
        m.ThesisChangeRequest.state == "APPROVED"))
    return max((instant for instant in (withdrawn,changed) if instant), default=None)


def blockers(session, thesis, report):
    if thesis.state == "WITHDRAWN":
        return []
    cutoff = changed_at(session, thesis.id)
    if not cutoff:
        return []
    proposal = session.scalar(select(m.Proposal).where(m.Proposal.thesis_id == thesis.id))
    version = session.scalar(select(m.ProposalVersion).where(
        m.ProposalVersion.proposal_id == proposal.id,
        m.ProposalVersion.version_no == proposal.current_version_no)) if proposal else None
    result = []
    from backend.services.registration_forms import fingerprint, rows
    reg = session.get(m.TopicRegistration, thesis.registration_id)
    forms = rows(session, reg)
    current_hash, form_code = fingerprint(session, reg)
    form = forms[0] if forms else None
    stored = session.get(m.StoredFile, form.stored_file_id) if form else None
    if not (form and form.submitted_at > cutoff and form.registration_fingerprint == current_hash
            and form.form_code == form_code and stored.scan_state == "CLEAN"):
        result.append({"key": "registration", "message": "Cần nộp lại Mẫu 1a/1b theo thành viên hiện tại tại Hồ sơ đăng ký."})
    plan = session.scalar(select(m.DocumentVersion).join(m.Document, m.Document.id == m.DocumentVersion.document_id)
        .where(m.Document.thesis_id == thesis.id, m.Document.document_type == "PLAN", m.Document.state == "ACTIVE")
        .order_by(m.DocumentVersion.submitted_at.desc()).limit(1))
    if not plan or plan.submitted_at <= cutoff or plan.state != "ACCEPTED":
        result.append({"key": "plan", "message": "Cần nộp kế hoạch Mẫu 2 cập nhật và được GVHD tiếp nhận."})
    if (not version or version.submitted_at <= cutoff or
            proposal.state not in {"DEPARTMENT_FINALIZED", "DEAN_CONFIRMED", "PRINT_READY"}):
        result.append({"key": "proposal", "message": "Hồ sơ đã đổi đề tài hoặc thành viên. Cần nộp đề cương mới, được GVHD xác nhận và TBM chốt lại."})
    if not report or report.submitted_at <= cutoff:
        result.append({"key": "report", "message": "Cần nộp bản báo cáo theo đề tài và thành viên hiện tại trước khi lập nhận xét và xét bảo vệ."})
    return result


def ensure_ready(session, thesis, report):
    pending = blockers(session, thesis, report)
    if pending:
        raise HTTPException(409, " ".join(item["message"] for item in pending))
