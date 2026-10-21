"""Lecturer-proposed topic workflow with department-scoped decisions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.schemas import OpenRoundOut, RequirementInput, TitleVersionOut, TopicCreate, TopicDecision, TopicOut, TopicUpdate
from backend.db.models import entities as m
from backend.services.registration import _is_department_head, profile, row_version


def _fail(status: int, detail: str):
    raise HTTPException(status, detail)


def _fingerprint(topic: m.Topic, session: Session) -> str:
    requirements = sorted(
        [(row.requirement_type, row.value_text or "", str(row.preferred_gpa) if row.preferred_gpa is not None else None)
         for row in session.scalars(select(m.TopicRequirement).where(m.TopicRequirement.topic_id == topic.id)).all()],
        key=lambda value: (value[0], value[1], value[2] or ""),
    )
    content = json.dumps({
        "title": topic.current_title, "description": topic.description,
        "max_students": topic.max_students, "state": topic.state,
        "code": topic.code,
        "receiving_lecturer_id": str(topic.receiving_lecturer_id) if topic.receiving_lecturer_id else None,
        "requirements": requirements,
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _audit(session: Session, topic: m.Topic, actor: UUID, action: str,
           before: str | None, reason: str | None = None) -> None:
    session.add(m.AuditEvent(
        id=uuid4(), actor_id=actor, action=action, resource_type="topic", resource_id=topic.id,
        before_hash=before, after_hash=_fingerprint(topic, session), reason=reason,
        occurred_at=datetime.now(timezone.utc), correlation_id=uuid4(),
    ))


def _title_version(session: Session, topic: m.Topic, actor: UUID, title: str,
                   reason: str | None = None) -> None:
    last = session.scalar(select(func.max(m.TopicTitleVersion.version_no)).where(
        m.TopicTitleVersion.topic_id == topic.id,
    )) or 0
    session.add(m.TopicTitleVersion(
        id=uuid4(), topic_id=topic.id, version_no=last + 1,
        title=title, changed_by=actor, change_reason=reason,
    ))


def topic_out(session: Session, topic: m.Topic) -> TopicOut:
    return topics_out(session, [topic])[0]


def topics_out(session: Session, topics: list[m.Topic]) -> list[TopicOut]:
    """Batch related reads so list size does not multiply database round trips."""
    if not topics:
        return []
    ids = [t.id for t in topics]
    requirements = session.scalars(select(m.TopicRequirement).where(m.TopicRequirement.topic_id.in_(ids))
        .order_by(m.TopicRequirement.created_at, m.TopicRequirement.id)).all()
    versions = session.scalars(select(m.TopicTitleVersion).where(m.TopicTitleVersion.topic_id.in_(ids))
        .order_by(m.TopicTitleVersion.version_no)).all()
    lecturers = {l.id: l for l in session.scalars(select(m.LecturerProfile).where(
        m.LecturerProfile.id.in_([t.receiving_lecturer_id for t in topics if t.receiving_lecturer_id]))).all()}
    rounds = {r.id: r for r in session.scalars(select(m.ThesisRound).where(
        m.ThesisRound.id.in_({t.round_id for t in topics}))).all()}
    years = {y.id: y for y in session.scalars(select(m.AcademicYear).where(
        m.AcademicYear.id.in_({r.academic_year_id for r in rounds.values()}))).all()}
    year_rounds = session.scalars(select(m.ThesisRound).where(m.ThesisRound.academic_year_id.in_(years))
        .order_by(m.ThesisRound.opens_at, m.ThesisRound.code, m.ThesisRound.id)).all()
    registrations = session.scalars(select(m.TopicRegistration).where(m.TopicRegistration.topic_id.in_(ids),
        m.TopicRegistration.state.in_(["DRAFT", "RETURNED", "SUBMITTED", "LECTURER_ACCEPTED", "FINALIZED"]))).all()
    counts = dict(session.execute(select(m.RegistrationMember.registration_id, func.count()).where(
        m.RegistrationMember.registration_id.in_([r.id for r in registrations]), m.RegistrationMember.active.is_(True))
        .group_by(m.RegistrationMember.registration_id)).all())
    reasons: dict[UUID, str | None] = {}
    for event in session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_type == "topic",
        m.AuditEvent.resource_id.in_([t.id for t in topics if t.state in {"RETURNED", "REJECTED"}]),
        m.AuditEvent.action.in_(["TOPIC_RETURNED", "TOPIC_REJECTED"]))
        .order_by(m.AuditEvent.occurred_at.desc(), m.AuditEvent.id)).all():
        reasons.setdefault(event.resource_id, event.reason)
    now = datetime.now(timezone.utc)
    result = []
    for topic in topics:
        round_ = rounds[topic.round_id]
        year = years[round_.academic_year_id]
        same_year = [r.id for r in year_rounds if r.academic_year_id == year.id]
        label = f"Năm học {year.starts_on.year}-{year.ends_on.year}"
        if len(same_year) > 1:
            label += f" (đợt {same_year.index(round_.id) + 1})"
        regs = [r for r in registrations if r.topic_id == topic.id]
        state = "LEGACY_REVIEW" if len(regs) > 1 else regs[0].state if regs else None
        count = sum(counts.get(r.id, 0) for r in regs)
        remaining = max(0, topic.max_students - count)
        available = topic.state == "APPROVED" and state not in {"LECTURER_ACCEPTED", "FINALIZED", "LEGACY_REVIEW"} and remaining > 0
        available = available and round_.state == "OPEN" and round_.opens_at <= now <= round_.closes_at
        lecturer = lecturers.get(topic.receiving_lecturer_id)
        result.append(TopicOut(id=topic.id, round_id=topic.round_id, department_id=topic.department_id,
            proposer_user_id=topic.proposer_user_id, title=topic.current_title, description=topic.description,
            max_students=topic.max_students, state=topic.state, row_version=topic.row_version,
            decision_reason=reasons.get(topic.id), code=topic.code, round_label=label, proposer_type=topic.proposer_type,
            receiving_lecturer_id=topic.receiving_lecturer_id, receiving_lecturer_name=lecturer.display_name if lecturer else None,
            requirements=[RequirementInput(requirement_type=r.requirement_type, value_text=r.value_text or "",
                preferred_gpa=float(r.preferred_gpa) if r.preferred_gpa is not None else None)
                for r in requirements if r.topic_id == topic.id],
            title_versions=[TitleVersionOut(version_no=v.version_no, title=v.title, change_reason=v.change_reason,
                created_at=v.created_at) for v in versions if v.topic_id == topic.id],
            registered_member_count=count, remaining_slots=remaining, registration_state=state, available=available))
    return result


def open_rounds(session: Session) -> list[m.ThesisRound]:
    now = datetime.now(timezone.utc)
    return session.scalars(select(m.ThesisRound).where(
        m.ThesisRound.state == "OPEN", m.ThesisRound.opens_at <= now,
        m.ThesisRound.closes_at >= now,
    ).order_by(m.ThesisRound.closes_at)).all()


def round_out(session: Session, round_: m.ThesisRound) -> OpenRoundOut:
    year = session.get(m.AcademicYear, round_.academic_year_id)
    year_label = f"{year.starts_on.year}-{year.ends_on.year}"
    rounds = session.scalars(select(m.ThesisRound).where(
        m.ThesisRound.academic_year_id == year.id,
    ).order_by(m.ThesisRound.opens_at, m.ThesisRound.created_at, m.ThesisRound.id)).all()
    number = next(i for i, row in enumerate(rounds, 1) if row.id == round_.id)
    kind = "Đợt chính" if round_.round_type == "MAIN" else "Đợt bổ sung"
    suffix = f" · Đợt {number}" if len(rounds) > 1 else ""
    return OpenRoundOut(id=round_.id, code=round_.code, closes_at=round_.closes_at,
                        academic_year=year_label, label=f"Năm học {year_label}{suffix} · {kind}")


def visible_topics(session: Session, user: m.UserAccount,
                   round_id: UUID | None, limit: int, offset: int = 0,
                   search: str | None = None, view: str = "all") -> list[TopicOut]:
    if user.base_role == "STUDENT":
        viewer = profile(session, user, "STUDENT")
        group_topics = select(m.TopicRegistration.topic_id).join(m.RegistrationMember,
            m.RegistrationMember.registration_id == m.TopicRegistration.id).where(m.RegistrationMember.student_id == viewer.id)
        allowed = or_(m.Topic.state == "APPROVED",
                      m.Topic.proposer_user_id == user.id, m.Topic.id.in_(group_topics))
    elif user.base_role == "LECTURER":
        viewer = profile(session, user, "LECTURER")
        head = _is_department_head(session, viewer.id, viewer.department_id)
        allowed = or_(
            m.Topic.state == "APPROVED", m.Topic.proposer_user_id == user.id,
            and_(m.Topic.proposer_type == "STUDENT",
                 m.Topic.state.in_(["SUBMITTED", "RETURNED", "REJECTED"]),
                 m.Topic.receiving_lecturer_id == viewer.id),
            m.Topic.state == "SUBMITTED" if head else m.Topic.proposer_user_id == user.id,
        )
    else:
        return []
    query = select(m.Topic).where(m.Topic.department_id == viewer.department_id, allowed)
    if view == "all":
        query = query.where(m.Topic.state == "APPROVED")
    if round_id is not None:
        query = query.where(m.Topic.round_id == round_id)
    if search:
        term = "%" + search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        receivers = select(m.LecturerProfile.id).where(m.LecturerProfile.display_name.ilike(term, escape="\\"))
        query = query.where(or_(m.Topic.code.ilike(term, escape="\\"),
            m.Topic.current_title.ilike(term, escape="\\"), m.Topic.receiving_lecturer_id.in_(receivers)))
    if view == "pending":
        query = query.where(m.Topic.state == "SUBMITTED")
    elif view == "mine":
        query = query.where(m.Topic.proposer_user_id == user.id)
    elif view == "suggested":
        if user.base_role != "LECTURER":
            _fail(403, "Only lecturers can view proposals addressed to them")
        query = query.where(m.Topic.proposer_type == "STUDENT",
            m.Topic.receiving_lecturer_id == viewer.id,
            m.Topic.state.in_(["SUBMITTED", "RETURNED", "REJECTED", "APPROVED"]))
    rows = session.scalars(query.order_by(m.Topic.created_at.desc(), m.Topic.id).offset(offset).limit(limit)).all()
    return topics_out(session, rows)


def get_visible_topic(session: Session, user: m.UserAccount, topic_id: UUID) -> TopicOut:
    row = session.get(m.Topic, topic_id)
    if row is None:
        _fail(404, "Topic not found")
    if user.base_role == "STUDENT":
        viewer = profile(session, user, "STUDENT")
        allowed = row.state == "APPROVED" or row.proposer_user_id == user.id or session.scalar(
            select(m.RegistrationMember.id).join(m.TopicRegistration,
                m.TopicRegistration.id == m.RegistrationMember.registration_id).where(
                m.TopicRegistration.topic_id == row.id, m.RegistrationMember.student_id == viewer.id).limit(1)) is not None
    elif user.base_role == "LECTURER":
        viewer = profile(session, user, "LECTURER")
        allowed = row.state == "APPROVED" or row.proposer_user_id == user.id or (
            row.state == "SUBMITTED" and _is_department_head(session, viewer.id, row.department_id)
        ) or (
            row.proposer_type == "STUDENT" and row.state in {"SUBMITTED", "RETURNED", "REJECTED"}
            and row.receiving_lecturer_id == viewer.id
        )
    else:
        _fail(404, "Topic not found")
    if viewer.department_id != row.department_id or not allowed:
        _fail(404, "Topic not found")
    return topic_out(session, row)


def _own_editable_topic(session: Session, user: m.UserAccount,
                        topic_id: UUID) -> m.Topic:
    if user.base_role not in {"LECTURER", "STUDENT"}:
        _fail(403, "Student or lecturer account required")
    lecturer = profile(session, user, user.base_role)
    topic = session.scalar(select(m.Topic).where(m.Topic.id == topic_id).with_for_update())
    if topic is None or topic.proposer_user_id != user.id or topic.department_id != lecturer.department_id:
        _fail(404, "Topic not found")
    if topic.state not in {"DRAFT", "RETURNED"}:
        _fail(409, "Only a draft or returned topic can be edited or submitted")
    return topic


def receiving_lecturer(session: Session, lecturer_id: UUID | None, department_id: UUID) -> m.LecturerProfile:
    lecturer = session.get(m.LecturerProfile, lecturer_id) if lecturer_id else None
    account = session.get(m.UserAccount, lecturer.user_id) if lecturer else None
    if not lecturer or lecturer.department_id != department_id or not account or account.status != "ACTIVE" or account.base_role != "LECTURER":
        _fail(422, "Choose an active lecturer in the same department")
    return lecturer


def allocate_topic_code(session: Session, round_: m.ThesisRound) -> str:
    year = session.get(m.AcademicYear, round_.academic_year_id)
    prefix = f"DT-{year.starts_on.year}-{year.ends_on.year}-"
    # Serialize allocation for this year, even if two rounds create topics together.
    session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:prefix))"), {"prefix": prefix})
    codes = session.scalars(select(m.Topic.code).where(m.Topic.code.startswith(prefix))).all()
    number = max((int(code[len(prefix):]) for code in codes), default=0) + 1
    return prefix + str(number).zfill(4)


def save_requirements(session: Session, topic: m.Topic, items: list[RequirementInput]) -> None:
    for old in session.scalars(select(m.TopicRequirement).where(m.TopicRequirement.topic_id == topic.id)).all():
        session.delete(old)
    for item in items:
        session.add(m.TopicRequirement(id=uuid4(), topic_id=topic.id, **item.model_dump(), enforcement="DESIRED"))


def create_topic(session: Session, user: m.UserAccount, data: TopicCreate, *, student_proposal=False) -> TopicOut:
    if user.base_role != "LECTURER" and not (student_proposal and user.base_role == "STUDENT"):
        _fail(403, "Only lecturers propose topics")
    lecturer = profile(session, user, user.base_role)
    if student_proposal and data.requirements:
        _fail(422, "Students describe their proposal; lecturer requirements are not student-editable")
    round_ = session.get(m.ThesisRound, data.round_id)
    now = datetime.now(timezone.utc)
    if not round_ or round_.state != "OPEN" or not round_.opens_at <= now <= round_.closes_at:
        _fail(409, "The selected round is not open")
    title = data.title.strip()
    if len(title) < 5:
        _fail(422, "Topic title is too short")
    try:
        topic = m.Topic(
            id=uuid4(), round_id=round_.id, department_id=lecturer.department_id,
            code=allocate_topic_code(session, round_),
            receiving_lecturer_id=(receiving_lecturer(session, data.receiving_lecturer_id, lecturer.department_id).id
                if student_proposal else lecturer.id),
            proposer_user_id=user.id, proposer_type=user.base_role, current_title=title,
            description=data.description.strip() if data.description else None,
            max_students=data.max_students, state="DRAFT",
        )
        session.add(topic)
        session.flush()
        _title_version(session, topic, user.id, title, "Initial proposal")
        save_requirements(session, topic, data.requirements)
        _audit(session, topic, user.id, "TOPIC_CREATED", None)
        session.flush()
        result = topic_out(session, topic)
        if not student_proposal:
            session.commit()
        return result
    except IntegrityError:
        session.rollback()
        _fail(409, "Topic creation conflicts with existing data")
    except Exception:
        session.rollback()
        raise


def update_topic(session: Session, user: m.UserAccount, topic_id: UUID,
                 data: TopicUpdate, expected_version: int) -> TopicOut:
    try:
        topic = _own_editable_topic(session, user, topic_id)
        row_version(expected_version, topic.row_version)
        if not data.model_fields_set:
            _fail(422, "Provide a field to update")
        before = _fingerprint(topic, session)
        if data.title is not None:
            title = data.title.strip()
            if len(title) < 5:
                _fail(422, "Topic title is too short")
            if title != topic.current_title:
                topic.current_title = title
                _title_version(session, topic, user.id, title, "Lecturer revised proposal")
        if "description" in data.model_fields_set:
            topic.description = data.description.strip() if data.description else None
        if data.max_students is not None:
            if topic.proposer_type == "STUDENT":
                _fail(422, "Student proposal membership is fixed in its registration")
            topic.max_students = data.max_students
        if data.requirements is not None:
            if user.base_role != "LECTURER":
                _fail(422, "Students describe their proposal; lecturer requirements are not student-editable")
            save_requirements(session, topic, data.requirements)
        if "receiving_lecturer_id" in data.model_fields_set:
            if topic.proposer_type != "STUDENT":
                _fail(422, "Lecturer topics are received by their proposer")
            topic.receiving_lecturer_id = receiving_lecturer(session, data.receiving_lecturer_id, topic.department_id).id
        topic.row_version += 1
        _audit(session, topic, user.id, "TOPIC_UPDATED", before)
        session.flush()
        result = topic_out(session, topic)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def submit_topic(session: Session, user: m.UserAccount, topic_id: UUID,
                 expected_version: int) -> TopicOut:
    try:
        topic = _own_editable_topic(session, user, topic_id)
        if topic.proposer_type == "STUDENT":
            _fail(409, "Submit the student registration after all members confirm")
        round_ = session.get(m.ThesisRound, topic.round_id)
        now = datetime.now(timezone.utc)
        if not round_ or round_.state != "OPEN" or not round_.opens_at <= now <= round_.closes_at:
            _fail(409, "The selected round is not open")
        row_version(expected_version, topic.row_version)
        before = _fingerprint(topic, session)
        topic.state = "SUBMITTED"
        topic.row_version += 1
        _audit(session, topic, user.id, "TOPIC_SUBMITTED", before)
        session.flush()
        result = topic_out(session, topic)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def department_decision(session: Session, user: m.UserAccount, topic_id: UUID,
                        data: TopicDecision, expected_version: int) -> TopicOut:
    if user.base_role != "LECTURER":
        _fail(403, "Department head assignment required")
    head = profile(session, user, "LECTURER")
    try:
        topic = session.scalar(select(m.Topic).where(m.Topic.id == topic_id).with_for_update())
        if topic is None:
            _fail(404, "Topic not found")
        if head.department_id != topic.department_id or not _is_department_head(session, head.id, topic.department_id):
            _fail(403, "Department head assignment is not active for this department")
        if topic.proposer_user_id == user.id:
            _fail(403, "A proposer cannot approve their own topic")
        row_version(expected_version, topic.row_version)
        if topic.state != "SUBMITTED":
            _fail(409, "Topic is not awaiting department decision")
        if data.decision in {"RETURN", "REJECT"} and not (data.reason and data.reason.strip()):
            _fail(422, "Returning or rejecting a topic requires a reason")
        if data.revised_title and data.decision != "APPROVE":
            _fail(422, "A revised title must be approved")
        before = _fingerprint(topic, session)
        if data.decision == "APPROVE":
            if topic.proposer_type == "STUDENT":
                previous_receiver_id = topic.receiving_lecturer_id
                topic.receiving_lecturer_id = receiving_lecturer(session, data.receiving_lecturer_id, topic.department_id).id
                registration = session.scalar(select(m.TopicRegistration).where(
                    m.TopicRegistration.topic_id == topic.id,
                    m.TopicRegistration.state == "SUBMITTED").limit(1))
                if registration is not None:
                    from backend.services.notifications import add_notice, revoke_proposal_notice

                    if previous_receiver_id and previous_receiver_id != topic.receiving_lecturer_id:
                        revoke_proposal_notice(session, registration_id=registration.id,
                                               lecturer_id=previous_receiver_id, now=datetime.now(timezone.utc))
                    add_notice(session, topic=topic,
                               actor_user_id=topic.proposer_user_id, registration_id=registration.id,
                               kind="PROPOSAL_APPROVED")
            elif data.receiving_lecturer_id is not None and data.receiving_lecturer_id != topic.receiving_lecturer_id:
                _fail(422, "Lecturer topics remain with the proposing lecturer")
        if data.revised_title:
            revised = data.revised_title.strip()
            if len(revised) < 5:
                _fail(422, "Revised title is too short")
            if revised != topic.current_title:
                topic.current_title = revised
                _title_version(session, topic, user.id, revised, data.reason or "Department title correction")
        topic.state = {"APPROVE": "APPROVED", "RETURN": "RETURNED", "REJECT": "REJECTED"}[data.decision]
        topic.decided_by = user.id
        topic.decided_at = datetime.now(timezone.utc)
        topic.row_version += 1
        if topic.proposer_type == "STUDENT" and data.decision in {"RETURN", "REJECT"}:
            for reg in session.scalars(select(m.TopicRegistration).where(m.TopicRegistration.topic_id == topic.id,
                m.TopicRegistration.state == "SUBMITTED").with_for_update()).all():
                from backend.services.notifications import revoke_proposal_notice

                revoke_proposal_notice(session, registration_id=reg.id,
                                       lecturer_id=None, now=datetime.now(timezone.utc))
                reg.state = "RETURNED" if data.decision == "RETURN" else "CANCELLED"
                reg.row_version += 1
                if data.decision == "REJECT":
                    for member in session.scalars(select(m.RegistrationMember).where(m.RegistrationMember.registration_id == reg.id)).all():
                        member.active = False
        _audit(session, topic, user.id, f"TOPIC_{topic.state}", before, data.reason.strip() if data.reason else None)
        session.flush()
        result = topic_out(session, topic)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
