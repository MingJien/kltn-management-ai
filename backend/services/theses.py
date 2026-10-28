"""Resource-scoped thesis access and assigned review roles."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.api.core_schemas import AdvisorOut, PendingAdvisorOut, ThesisMemberOut, ThesisWorkspaceOut
from backend.db.models import entities as m
from backend.services.registration import _is_department_head, profile, row_version

EDITABLE = {"ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"}


def now():
    return datetime.now(timezone.utc)


def effective(cls):
    instant = now()
    return and_(cls.state == "ACTIVE", cls.effective_from <= instant,
        or_(cls.effective_to.is_(None), cls.effective_to > instant))


def audit(session, user, action, resource_type, resource_id, reason=None, before_hash=None, after_hash=None,
          source_reference=None):
    session.add(m.AuditEvent(id=uuid4(), actor_id=user.id, action=action,
        resource_type=resource_type, resource_id=resource_id, reason=reason, source_reference=source_reference,
        before_hash=before_hash, after_hash=after_hash, occurred_at=now(), correlation_id=uuid4()))


def primary_advisor(session, thesis_id):
    return session.scalar(select(m.AdvisorAssignment).where(
        m.AdvisorAssignment.thesis_id == thesis_id, effective(m.AdvisorAssignment)))


def resource_role(session, user_id, role, *, thesis_id=None, round_id=None):
    query = select(m.ResourceAssignment).where(m.ResourceAssignment.user_id == user_id,
        m.ResourceAssignment.assignment_type == role, effective(m.ResourceAssignment))
    if thesis_id is not None:
        query = query.where(m.ResourceAssignment.thesis_id == thesis_id)
    if round_id is not None:
        query = query.where(m.ResourceAssignment.round_id == round_id)
    return session.scalar(query)


def is_faculty_dean(session, lecturer_id, department_id):
    department = session.get(m.Department, department_id)
    if department is None:
        return False
    instant = now()
    return session.scalar(select(m.PositionAssignment.id).join(m.OrganizationalPosition,
        m.PositionAssignment.position_id == m.OrganizationalPosition.id).where(
        m.PositionAssignment.lecturer_id == lecturer_id,
        m.PositionAssignment.faculty_id == department.faculty_id,
        m.PositionAssignment.state == "ACTIVE",
        m.PositionAssignment.effective_from <= instant,
        or_(m.PositionAssignment.effective_to.is_(None), m.PositionAssignment.effective_to > instant),
        m.OrganizationalPosition.code == "FACULTY_DEAN").limit(1)) is not None


def rights(session, user, thesis):
    result = set()
    if user.base_role == "STUDENT":
        student = profile(session, user, "STUDENT")
        if session.scalar(select(m.ThesisMember.id).where(m.ThesisMember.thesis_id == thesis.id,
                m.ThesisMember.student_id == student.id, m.ThesisMember.active.is_(True))):
            result.update({"view", "document:view", "progress:view", "work:view", "progress:submit", "document:submit", "work:submit", "proposal:view", "proposal:submit"})
    elif user.base_role == "LECTURER":
        lecturer = profile(session, user, "LECTURER")
        advisor = primary_advisor(session, thesis.id)
        if advisor and advisor.lecturer_id == lecturer.id:
            result.update({"view", "document:view", "progress:view", "work:view", "progress:review", "document:review", "work:review", "proposal:view", "proposal:review"})
        if _is_department_head(session, lecturer.id, thesis.department_id):
            result.update({"view", "document:view", "work:view", "audit:view", "proposal:view", "proposal:assign_reviewer", "proposal:finalize"})
        if is_faculty_dean(session, lecturer.id, thesis.department_id):
            result.update({"view", "proposal:view", "proposal:dean_confirm"})
        proposal = session.scalar(select(m.Proposal).where(m.Proposal.thesis_id == thesis.id))
        if proposal and session.scalar(select(m.ReviewerAssignment.id).where(
            m.ReviewerAssignment.proposal_id == proposal.id,
            m.ReviewerAssignment.lecturer_id == lecturer.id,
            m.ReviewerAssignment.review_scope == "PROPOSAL",
            m.ReviewerAssignment.state == "ACTIVE").limit(1)):
            result.update({"view", "proposal:view", "proposal:comment"})
        if resource_role(session, user.id, "KLTN_COORDINATOR", round_id=thesis.round_id):
            result.update({"view", "milestone:manage"})
    return result


def thesis_access(session, user, thesis_id, *, action="view", lock=False, write=False):
    query = select(m.Thesis).where(m.Thesis.id == thesis_id)
    if lock:
        query = query.with_for_update()
    thesis = session.scalar(query)
    if thesis is None or "view" not in rights(session, user, thesis):
        raise HTTPException(404, "Không tìm thấy khóa luận trong phạm vi của bạn")
    if action not in rights(session, user, thesis):
        raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này trên khóa luận")
    if write and thesis.state not in EDITABLE:
        raise HTTPException(409, "Khóa luận đã khóa các thao tác thực hiện")
    return thesis


def workspace_out(session, user, thesis):
    members = session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.active.is_(True)).order_by(m.ThesisMember.is_coordinator.desc(), m.ThesisMember.id)).all()
    history = session.scalars(select(m.AdvisorAssignment).where(m.AdvisorAssignment.thesis_id == thesis.id)
        .order_by(m.AdvisorAssignment.effective_from.desc())).all()
    current = primary_advisor(session, thesis.id)
    cross_reviewers = session.scalars(select(m.LecturerProfile).join(m.ResourceAssignment, m.ResourceAssignment.user_id == m.LecturerProfile.user_id)
        .where(m.ResourceAssignment.thesis_id == thesis.id, m.ResourceAssignment.assignment_type == "PROGRESS_REVIEWER", effective(m.ResourceAssignment))
        .order_by(m.LecturerProfile.display_name)).all()
    round_ = session.get(m.ThesisRound, thesis.round_id)
    year = session.get(m.AcademicYear, round_.academic_year_id)
    def member_out(member):
        student = session.get(m.StudentProfile, member.student_id)
        return ThesisMemberOut(student_id=student.id, display_name=student.display_name,
            student_code=student.student_code, is_coordinator=member.is_coordinator)
    actions = rights(session, user, thesis)
    if thesis.state not in EDITABLE:
        actions.difference_update({"progress:submit", "document:submit", "work:submit", "progress:review", "document:review",
            "work:review", "progress:assign_reviewer", "progress:comment", "milestone:manage", "proposal:submit", "proposal:review", "proposal:comment", "proposal:assign_reviewer", "proposal:finalize", "proposal:dean_confirm"})
    return ThesisWorkspaceOut(id=thesis.id, registration_id=thesis.registration_id, title=thesis.current_title, state=thesis.state,
        row_version=thesis.row_version, round_id=thesis.round_id, round_label=f"{year.code} / {round_.code}",
        member_student_ids=[member.student_id for member in members], members=[member_out(member) for member in members],
        advisor_lecturer_id=current.lecturer_id if current else None,
        advisor_name=session.get(m.LecturerProfile, current.lecturer_id).display_name if current else None,
        advisor_history=[AdvisorOut(id=item.id, lecturer_id=item.lecturer_id,
            display_name=session.get(m.LecturerProfile, item.lecturer_id).display_name, state=item.state,
            effective_from=item.effective_from, effective_to=item.effective_to) for item in history],
        pending_advisor=None,
        cross_reviewers=[],
        actions=sorted(actions))


def list_theses(session, user):
    if user.base_role == "STUDENT":
        student = profile(session, user, "STUDENT")
        query = select(m.Thesis).join(m.ThesisMember, m.ThesisMember.thesis_id == m.Thesis.id).where(
            m.ThesisMember.student_id == student.id, m.ThesisMember.active.is_(True))
    elif user.base_role == "LECTURER":
        lecturer = profile(session, user, "LECTURER")
        heads = [dep for dep in session.scalars(select(m.Department.id)) if _is_department_head(session, lecturer.id, dep) or is_faculty_dean(session, lecturer.id, dep)]
        advisors = select(m.AdvisorAssignment.thesis_id).where(m.AdvisorAssignment.lecturer_id == lecturer.id,
            effective(m.AdvisorAssignment))
        resources = select(m.ResourceAssignment.thesis_id).where(m.ResourceAssignment.user_id == user.id,
            m.ResourceAssignment.assignment_type == "PROGRESS_REVIEWER", effective(m.ResourceAssignment))
        rounds = select(m.ResourceAssignment.round_id).where(m.ResourceAssignment.user_id == user.id,
            m.ResourceAssignment.assignment_type == "KLTN_COORDINATOR", effective(m.ResourceAssignment))
        proposal_reviews = select(m.Proposal.thesis_id).join(m.ReviewerAssignment,
            m.ReviewerAssignment.proposal_id == m.Proposal.id).where(
            m.ReviewerAssignment.lecturer_id == lecturer.id,
            m.ReviewerAssignment.review_scope == "PROPOSAL",
            m.ReviewerAssignment.state == "ACTIVE")
        query = select(m.Thesis).where(or_(m.Thesis.department_id.in_(heads), m.Thesis.id.in_(advisors),
            m.Thesis.round_id.in_(rounds), m.Thesis.id.in_(proposal_reviews)))
    else:
        return []
    return [workspace_out(session, user, row) for row in session.scalars(query.order_by(m.Thesis.created_at.desc(), m.Thesis.id)).all()]


def eligible_lecturer(session, lecturer_id, department_id):
    lecturer = session.get(m.LecturerProfile, lecturer_id)
    account = session.get(m.UserAccount, lecturer.user_id) if lecturer else None
    if not lecturer or lecturer.department_id != department_id or not account or account.status != "ACTIVE":
        raise HTTPException(422, "Chọn giảng viên đang hoạt động thuộc đúng bộ môn")
    return lecturer
