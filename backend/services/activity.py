"""Read-only, resource-scoped activity history for authenticated accounts."""
from __future__ import annotations

import re
from collections import defaultdict
from sqlalchemy import String, and_, false, func, or_, select

from backend.db.models import entities as m
from backend.services.registration import _is_department_head
from backend.services.theses import effective, is_faculty_dean


ROUND_ACTIONS = (
    "ROUND_CREATED", "ROUND_OPENED", "ROUND_CLOSED", "ROUND_SCHEDULE_UPDATED",
    "MILESTONE_OPENED", "MILESTONE_EXTENDED", "MILESTONE_REOPENED", "MILESTONE_CLOSED",
)


def _ids(session, column, *conditions):
    return set(session.scalars(select(column).where(*conditions)).all()) - {None}


def progress_privacy(session,user):
    private_theses = set()
    if user.base_role == "STUDENT":
        private_theses = _ids(session,m.ThesisMember.thesis_id,m.ThesisMember.active.is_(True),
            m.ThesisMember.student_id.in_(select(m.StudentProfile.id).where(m.StudentProfile.user_id==user.id)))
    elif user.base_role == "LECTURER":
        private_theses = _ids(session,m.AdvisorAssignment.thesis_id,effective(m.AdvisorAssignment),
            m.AdvisorAssignment.lecturer_id.in_(select(m.LecturerProfile.id).where(m.LecturerProfile.user_id==user.id)))
    reports = select(m.ProgressReport.id).where(m.ProgressReport.thesis_id.in_(private_theses))
    related = or_(and_(m.AuditEvent.resource_type=="thesis",m.AuditEvent.resource_id.in_(private_theses)),
        and_(m.AuditEvent.resource_type=="progress_report",m.AuditEvent.resource_id.in_(reports)))
    evidence_versions = select(m.DocumentVersion.id).join(m.ProgressReport,m.ProgressReport.evidence_file_id==m.DocumentVersion.stored_file_id)
    allowed_versions = evidence_versions.where(m.ProgressReport.thesis_id.in_(private_theses))
    return and_(or_(and_(~m.AuditEvent.action.startswith("PROGRESS_",autoescape=True),m.AuditEvent.action!="DOCUMENT_REVIEWED"),related),
        or_(m.AuditEvent.resource_type!="progress_report",m.AuditEvent.resource_id.in_(reports)),
        or_(m.AuditEvent.resource_type!="document_version",~m.AuditEvent.resource_id.in_(evidence_versions),m.AuditEvent.resource_id.in_(allowed_versions)))


def visibility(session, user):
    """Filter before searching/counting/pagination; browser filters never grant access."""
    if user.base_role == "ADMIN":
        return progress_privacy(session,user), "Nhật ký quản trị"
    scopes = defaultdict(set)
    scopes["user_account"].add(user.id)
    full_theses, proposal_theses, progress_theses, rounds, topics, registrations = (set() for _ in range(6))
    advisor_theses = set()
    managed_rounds = set()
    label = "Tài khoản và hồ sơ của tôi"
    if user.base_role == "STUDENT":
        student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == user.id))
        if student:
            scopes["student_profile"].add(student.id)
            scopes["eligibility_snapshot"] |= _ids(session, m.EligibilitySnapshot.id, m.EligibilitySnapshot.student_id == student.id)
            rounds |= _ids(session, m.EligibilitySnapshot.round_id, m.EligibilitySnapshot.student_id == student.id)
            registrations |= _ids(session, m.RegistrationMember.registration_id,
                m.RegistrationMember.student_id == student.id, m.RegistrationMember.active.is_(True))
            registrations |= _ids(session, m.TopicRegistration.id, m.TopicRegistration.created_by == student.id)
            full_theses |= _ids(session, m.ThesisMember.thesis_id,
                m.ThesisMember.student_id == student.id, m.ThesisMember.active.is_(True))
            topics |= _ids(session, m.Topic.id, m.Topic.proposer_user_id == user.id)
    elif user.base_role == "LECTURER":
        label = "Tài khoản và hồ sơ được phân công"
        lecturer = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == user.id))
        if lecturer:
            scopes["lecturer_profile"].add(lecturer.id)
            heads = {dep for dep in session.scalars(select(m.Department.id))
                     if _is_department_head(session, lecturer.id, dep)}
            dean_departments = {dep for dep in session.scalars(select(m.Department.id))
                                if is_faculty_dean(session, lecturer.id, dep)}
            if heads:
                label = "Tài khoản và nghiệp vụ thuộc bộ môn được giao"
                full_theses |= _ids(session, m.Thesis.id, m.Thesis.department_id.in_(heads))
            if dean_departments:
                proposal_theses |= _ids(session, m.Thesis.id, m.Thesis.department_id.in_(dean_departments))
            topics |= _ids(session, m.Topic.id, or_(m.Topic.proposer_user_id == user.id,
                and_(m.Topic.state != "DRAFT", or_(m.Topic.receiving_lecturer_id == lecturer.id,
                    m.Topic.department_id.in_(heads)))))
            registrations |= _ids(session, m.TopicRegistration.id,
                m.TopicRegistration.topic_id.in_(topics), m.TopicRegistration.submitted_at.is_not(None),
                m.TopicRegistration.state != "DRAFT")
            full_theses |= _ids(session, m.AdvisorAssignment.thesis_id,
                m.AdvisorAssignment.lecturer_id == lecturer.id, effective(m.AdvisorAssignment))
            advisor_theses |= _ids(session, m.AdvisorAssignment.thesis_id,
                m.AdvisorAssignment.lecturer_id == lecturer.id, effective(m.AdvisorAssignment))
            review_proposals = _ids(session, m.ReviewerAssignment.proposal_id,
                m.ReviewerAssignment.lecturer_id == lecturer.id,
                m.ReviewerAssignment.review_scope == "PROPOSAL", m.ReviewerAssignment.state == "ACTIVE")
            proposal_theses |= _ids(session, m.Proposal.thesis_id, m.Proposal.id.in_(review_proposals))
            progress_theses |= _ids(session, m.ResourceAssignment.thesis_id,
                m.ResourceAssignment.user_id == user.id,
                m.ResourceAssignment.assignment_type == "PROGRESS_REVIEWER", effective(m.ResourceAssignment))
        assignments = _ids(session, m.ResourceAssignment.id, m.ResourceAssignment.user_id == user.id)
        scopes["resource_assignment"] |= assignments
        rounds |= _ids(session, m.ResourceAssignment.round_id, m.ResourceAssignment.user_id == user.id,
            effective(m.ResourceAssignment))
        managed_rounds = _ids(session, m.ResourceAssignment.round_id,
            m.ResourceAssignment.user_id == user.id, m.ResourceAssignment.assignment_type.in_(
                ["ACCOUNT_MANAGER", "ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER"]), effective(m.ResourceAssignment))
        # Account administration remains limited to students in assigned rounds.
        if managed_rounds:
            student_ids = _ids(session, m.EligibilitySnapshot.student_id, m.EligibilitySnapshot.round_id.in_(managed_rounds))
            scopes["eligibility_snapshot"] |= _ids(session, m.EligibilitySnapshot.id,
                m.EligibilitySnapshot.round_id.in_(managed_rounds))
            scopes["student_profile"] |= student_ids
            account_rounds = _ids(session, m.ResourceAssignment.round_id, m.ResourceAssignment.user_id == user.id,
                m.ResourceAssignment.assignment_type == "ACCOUNT_MANAGER", effective(m.ResourceAssignment))
            account_students = _ids(session, m.EligibilitySnapshot.student_id, m.EligibilitySnapshot.round_id.in_(account_rounds))
            scopes["user_account"] |= _ids(session, m.StudentProfile.user_id, m.StudentProfile.id.in_(account_students))
    else:
        return false(), label
    form_rounds = _ids(session, m.ResourceAssignment.round_id, m.ResourceAssignment.user_id == user.id,
        m.ResourceAssignment.assignment_type == "FORM_MANAGER", effective(m.ResourceAssignment))
    scopes["official_form"] |= _ids(session, m.OfficialForm.id, m.OfficialForm.round_id.in_(form_rounds))
    topics |= _ids(session, m.TopicRegistration.topic_id, m.TopicRegistration.id.in_(registrations))
    rounds |= _ids(session, m.TopicRegistration.round_id, m.TopicRegistration.id.in_(registrations))
    scopes["topic"] |= topics
    scopes["topic_registration"] |= registrations
    scopes["registration"] |= registrations  # Earlier evidence events used this resource name.
    scopes["thesis"] |= full_theses
    all_theses = full_theses | proposal_theses | progress_theses
    rounds |= _ids(session, m.Thesis.round_id, m.Thesis.id.in_(all_theses))
    proposals = _ids(session, m.Proposal.id, m.Proposal.thesis_id.in_(full_theses | proposal_theses))
    scopes["proposal"] |= proposals
    scopes["proposal_version"] |= _ids(session, m.ProposalVersion.id, m.ProposalVersion.proposal_id.in_(proposals))
    docs = _ids(session, m.Document.id, m.Document.thesis_id.in_(full_theses))
    scopes["document"] |= docs
    scopes["document_version"] |= _ids(session, m.DocumentVersion.id, m.DocumentVersion.document_id.in_(docs))
    scopes["progress_report"] |= _ids(session, m.ProgressReport.id,
        m.ProgressReport.thesis_id.in_(
            full_theses if user.base_role == "STUDENT" else (advisor_theses | progress_theses)))
    scopes["document_deadline"] |= _ids(session, m.DocumentDeadline.id, m.DocumentDeadline.round_id.in_(rounds))
    clauses = [and_(m.AuditEvent.resource_type == kind, m.AuditEvent.resource_id.in_(ids))
               for kind, ids in scopes.items() if ids]
    # A reviewer sees only the portion assigned to them, even when the event is keyed by thesis.
    for ids, prefix in ((proposal_theses, "PROPOSAL_"),
                        (full_theses if user.base_role == "STUDENT" else (advisor_theses | progress_theses), "PROGRESS_")):
        if ids:
            clauses.append(and_(m.AuditEvent.resource_type == "thesis", m.AuditEvent.resource_id.in_(ids),
                m.AuditEvent.action.startswith(prefix, autoescape=True)))
    if rounds:
        clauses.append(and_(m.AuditEvent.resource_type.in_(["round", "thesis_round"]),
            m.AuditEvent.resource_id.in_(rounds), m.AuditEvent.action.in_(ROUND_ACTIONS)))
    if managed_rounds:
        clauses.append(and_(m.AuditEvent.resource_type == "thesis_round",
            m.AuditEvent.resource_id.in_(managed_rounds), m.AuditEvent.action == "ELIGIBILITY_ROSTER_IMPORTED"))
    # An actor can retain their own recorded actions after their assignment ends.
    clauses.append(m.AuditEvent.actor_id == user.id)
    return and_(or_(*clauses),progress_privacy(session,user)), label


def _legacy_reference(event):
    reference, reason = event.source_reference, event.reason
    if not reference and reason:
        match = re.search(r"(?:^|;\s*)(?:reference|ref)=([^;]+)", reason)
        if match:
            reference = match.group(1).strip()
            reason = (reason[:match.start()] + reason[match.end():]).strip(" ;") or None
        elif event.action in {"ROUND_CREATED", "ROUND_PERMISSION_GRANTED"}:
            reference, reason = reason, None
    return reference, reason


def _names(session, ids):
    names = {row.user_id: row.display_name for row in session.scalars(
        select(m.StudentProfile).where(m.StudentProfile.user_id.in_(ids)))}
    names.update({row.user_id: row.display_name for row in session.scalars(
        select(m.LecturerProfile).where(m.LecturerProfile.user_id.in_(ids)))})
    for row in session.scalars(select(m.UserAccount).where(m.UserAccount.id.in_(ids))):
        names.setdefault(row.id, "Quản trị viên" if row.base_role == "ADMIN" else "Tài khoản")
    return names


def _target_search(term):
    topics = select(m.Topic.id).where(or_(m.Topic.code.ilike(term, escape="\\"), m.Topic.current_title.ilike(term, escape="\\")))
    registrations = select(m.TopicRegistration.id).where(m.TopicRegistration.topic_id.in_(topics))
    theses = select(m.Thesis.id).where(or_(m.Thesis.topic_id.in_(topics), m.Thesis.current_title.ilike(term, escape="\\")))
    rounds = select(m.ThesisRound.id).where(m.ThesisRound.code.ilike(term, escape="\\"))
    students = select(m.StudentProfile.id).where(or_(m.StudentProfile.display_name.ilike(term, escape="\\"), m.StudentProfile.student_code.ilike(term, escape="\\")))
    accounts = select(m.UserAccount.id).where(m.UserAccount.email.ilike(term, escape="\\")).union(
        select(m.StudentProfile.user_id).where(m.StudentProfile.id.in_(students)),
        select(m.LecturerProfile.user_id).where(or_(m.LecturerProfile.display_name.ilike(term, escape="\\"), m.LecturerProfile.lecturer_code.ilike(term, escape="\\"))))
    return or_(
        and_(m.AuditEvent.resource_type == "topic", m.AuditEvent.resource_id.in_(topics)),
        and_(m.AuditEvent.resource_type.in_(["topic_registration", "registration"]), m.AuditEvent.resource_id.in_(registrations)),
        and_(m.AuditEvent.resource_type == "thesis", m.AuditEvent.resource_id.in_(theses)),
        and_(m.AuditEvent.resource_type.in_(["round", "thesis_round"]), m.AuditEvent.resource_id.in_(rounds)),
        and_(m.AuditEvent.resource_type == "user_account", m.AuditEvent.resource_id.in_(accounts)),
        and_(m.AuditEvent.resource_type == "student_profile", m.AuditEvent.resource_id.in_(students)))


def list_activity(session, user, *, search="", action="", date_from=None, date_to=None,
                  resource_type="", resource_id=None, limit=25, offset=0):
    allowed, scope = visibility(session, user)
    conditions = [allowed]
    if resource_type:
        conditions.append(m.AuditEvent.resource_type == resource_type)
    if resource_id:
        conditions.append(m.AuditEvent.resource_id == resource_id)
    if action:
        conditions.append(m.AuditEvent.action == action)
    if date_from:
        conditions.append(m.AuditEvent.occurred_at >= date_from)
    if date_to:
        conditions.append(m.AuditEvent.occurred_at < date_to)
    if search:
        term = "%" + search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        actor_ids = select(m.StudentProfile.user_id).where(m.StudentProfile.display_name.ilike(term, escape="\\")).union(
            select(m.LecturerProfile.user_id).where(m.LecturerProfile.display_name.ilike(term, escape="\\")))
        conditions.append(or_(m.AuditEvent.reason.ilike(term, escape="\\"),
            m.AuditEvent.source_reference.ilike(term, escape="\\"), m.AuditEvent.action.ilike(term, escape="\\"),
            m.AuditEvent.resource_type.ilike(term, escape="\\"), m.AuditEvent.actor_id.in_(actor_ids),
            func.cast(m.AuditEvent.id, String).ilike(term, escape="\\"),
            _target_search(term),
            func.cast(m.AuditEvent.resource_id, String).ilike(term, escape="\\")))
    total = session.scalar(select(func.count()).select_from(m.AuditEvent).where(*conditions))
    events = session.scalars(select(m.AuditEvent).where(*conditions)
        .order_by(m.AuditEvent.occurred_at.desc(), m.AuditEvent.id.desc()).offset(offset).limit(limit)).all()
    names = _names(session, {row.actor_id for row in events if row.actor_id})
    labels = resource_labels(session, events, user)
    items = []
    for event in events:
        reference, reason = _legacy_reference(event)
        items.append(dict(id=event.id, action=event.action, actor_name=names.get(event.actor_id, "Hệ thống"),
            resource_type=event.resource_type, resource_id=event.resource_id,
            resource_label=labels.get((event.resource_type, event.resource_id), event.resource_type),
            reason=reason, source_reference=reference, occurred_at=event.occurred_at))
    actions = session.scalars(select(m.AuditEvent.action).where(allowed).distinct().order_by(m.AuditEvent.action)).all()
    return dict(items=items, total=total, actions=actions, scope=scope)


def resource_labels(session, events, viewer):
    ids = defaultdict(set)
    for event in events:
        ids[event.resource_type].add(event.resource_id)
    result = {}
    for kind, cls, attr in (("topic", m.Topic, "current_title"), ("thesis", m.Thesis, "current_title"),
                            ("round", m.ThesisRound, "code"), ("thesis_round", m.ThesisRound, "code"),
                            ("official_form", m.OfficialForm, "title")):
        for row in session.scalars(select(cls).where(cls.id.in_(ids[kind]))):
            result[kind, row.id] = (f"{row.code} · {getattr(row, attr)}" if kind == "topic" else getattr(row, attr))
    for row in session.execute(select(m.TopicRegistration.id, m.Topic.code, m.Topic.current_title)
            .join(m.Topic, m.Topic.id == m.TopicRegistration.topic_id)
            .where(m.TopicRegistration.id.in_(ids["topic_registration"] | ids["registration"]))):
        result["topic_registration", row.id] = f"{row.code} · {row.current_title}"
        result["registration", row.id] = result["topic_registration", row.id]
    accounts = ids["user_account"]
    names = _names(session, accounts)
    for row in session.scalars(select(m.UserAccount).where(m.UserAccount.id.in_(accounts))):
        result["user_account", row.id] = names.get(row.id, "Tài khoản") + (
            f" · {row.email}" if viewer.base_role == "ADMIN" and row.email else "")
    for row in session.scalars(select(m.StudentProfile).where(m.StudentProfile.id.in_(ids["student_profile"]))):
        result["student_profile", row.id] = f"{row.student_code} · {row.display_name}"
    for row in session.execute(select(m.DocumentVersion.id, m.DocumentVersion.version_no, m.Document.title)
            .join(m.Document, m.Document.id == m.DocumentVersion.document_id)
            .where(m.DocumentVersion.id.in_(ids["document_version"]))):
        result["document_version", row.id] = f"{row.title} · phiên bản {row.version_no}"
    for row in session.execute(select(m.EligibilitySnapshot.id, m.StudentProfile.student_code,
            m.StudentProfile.display_name).join(m.StudentProfile, m.StudentProfile.id == m.EligibilitySnapshot.student_id)
            .where(m.EligibilitySnapshot.id.in_(ids["eligibility_snapshot"]))):
        result["eligibility_snapshot", row.id] = f"{row.student_code} · {row.display_name}"
    assignments = session.scalars(select(m.ResourceAssignment).where(m.ResourceAssignment.id.in_(ids["resource_assignment"]))).all()
    assigned_names = _names(session, {row.user_id for row in assignments})
    for row in assignments:
        round_ = session.get(m.ThesisRound, row.round_id) if row.round_id else None
        duty = {"KLTN_COORDINATOR": "Điều phối KLTN", "ACCOUNT_MANAGER": "Quản lý tài khoản",
            "ELIGIBILITY_IMPORTER": "Nhập danh sách đủ điều kiện", "ELIGIBILITY_VERIFIER": "Xác nhận điều kiện",
            "FORM_MANAGER": "Quản lý biểu mẫu", "PROGRESS_REVIEWER": "Góp ý tiến độ"}.get(row.assignment_type, row.assignment_type)
        result["resource_assignment", row.id] = f"{assigned_names.get(row.user_id, 'Cán bộ')} · {duty}" + (f" · {round_.code}" if round_ else "")
    for row in session.execute(select(m.DocumentDeadline.id, m.DocumentDeadline.document_type, m.ThesisRound.code)
            .join(m.ThesisRound, m.ThesisRound.id == m.DocumentDeadline.round_id)
            .where(m.DocumentDeadline.id.in_(ids["document_deadline"]))):
        kind = {"PROPOSAL": "Đề cương", "PLAN": "Kế hoạch", "SUPPORTING": "Tài liệu bổ sung"}.get(row.document_type, row.document_type)
        result["document_deadline", row.id] = f"{row.code} · {kind}"
    for row in session.execute(select(m.ProposalVersion.id, m.ProposalVersion.version_no, m.Thesis.current_title)
            .join(m.Proposal, m.Proposal.id == m.ProposalVersion.proposal_id)
            .join(m.Thesis, m.Thesis.id == m.Proposal.thesis_id)
            .where(m.ProposalVersion.id.in_(ids["proposal_version"]))):
        result["proposal_version", row.id] = f"{row.current_title} · đề cương phiên bản {row.version_no}"
    return result
