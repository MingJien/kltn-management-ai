"""Enforce the agreed limit on active primary supervision across rounds."""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from backend.db.models import entities as m

MAX_ACTIVE_THESES = 3
ACTIVE_THESIS_STATES = ("ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED", "READY_FOR_DEFENSE", "DEFENDED")
CAPACITY_MESSAGE = "Giảng viên đã hướng dẫn đủ 3 khóa luận đang thực hiện. Vui lòng chọn giảng viên khác hoặc liên hệ bộ môn."


def require_capacity(session, lecturer_id, *, excluding_thesis_id=None, lock=False):
    # Serialize formal assignments for the same lecturer, including across rounds.
    if lock:
        session.scalar(select(m.LecturerProfile.id).where(m.LecturerProfile.id == lecturer_id).with_for_update())
    instant = datetime.now(timezone.utc)
    query = (select(func.count(func.distinct(m.AdvisorAssignment.thesis_id)))
        .join(m.Thesis, m.Thesis.id == m.AdvisorAssignment.thesis_id)
        .where(m.AdvisorAssignment.lecturer_id == lecturer_id,
            m.AdvisorAssignment.assignment_type == "PRIMARY", m.AdvisorAssignment.state == "ACTIVE",
            m.AdvisorAssignment.effective_from <= instant,
            or_(m.AdvisorAssignment.effective_to.is_(None), m.AdvisorAssignment.effective_to > instant),
            m.Thesis.state.in_(ACTIVE_THESIS_STATES)))
    if excluding_thesis_id is not None:
        query = query.where(m.Thesis.id != excluding_thesis_id)
    count = session.scalar(query) or 0
    if count >= MAX_ACTIVE_THESES:
        raise HTTPException(409, CAPACITY_MESSAGE)
    return count
