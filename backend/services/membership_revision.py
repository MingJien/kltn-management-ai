"""Keep academic evidence tied to the group that actually continues the thesis."""
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.db.models import entities as m


def changed_at(session, thesis_id):
    # Use recording time, not a backdated administrative effective date. Files
    # submitted before the system knew the new group cannot confirm that group.
    return session.scalar(select(func.max(m.ThesisWithdrawalRequest.recorded_at)).where(
        m.ThesisWithdrawalRequest.thesis_id == thesis_id,
        m.ThesisWithdrawalRequest.state == "RECORDED"))


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
    if (not version or version.submitted_at <= cutoff or
            proposal.state not in {"DEPARTMENT_FINALIZED", "DEAN_CONFIRMED", "PRINT_READY"}):
        result.append({"key": "proposal", "message": "Nhóm đã thay đổi thành viên. Cần nộp đề cương mới, được GVHD xác nhận và TBM chốt lại."})
    if not report or report.submitted_at <= cutoff:
        result.append({"key": "report", "message": "Cần nộp bản báo cáo cập nhật theo thành viên còn lại trước khi lập nhận xét và xét bảo vệ."})
    return result


def ensure_ready(session, thesis, report):
    pending = blockers(session, thesis, report)
    if pending:
        raise HTTPException(409, " ".join(item["message"] for item in pending))
