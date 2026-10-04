from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.schemas import MemberResponse, RegistrationCreate, RegistrationMemberOut, RegistrationOut, LecturerDecision
from backend.db.models import entities as m


def fail(code: int, message: str) -> None:
    raise HTTPException(code, message)


def profile(session: Session, user: m.UserAccount, kind: str):
    model = m.StudentProfile if kind == "STUDENT" else m.LecturerProfile
    found = session.scalar(select(model).where(model.user_id == user.id))
    if found is None:
        fail(403, "Profile unavailable")
    return found


def row_version(expected: int, actual: int) -> None:
    if expected != actual:
        fail(409, "Version conflict; reload before deciding")


def confirmed_student_ids(session: Session, round_id: UUID, student_ids: list[UUID]) -> set[UUID]:
    latest = select(m.EligibilitySnapshot.student_id, func.max(m.EligibilitySnapshot.version).label("version")).where(
        m.EligibilitySnapshot.round_id == round_id, m.EligibilitySnapshot.student_id.in_(student_ids)
    ).group_by(m.EligibilitySnapshot.student_id).subquery()
    return set(session.scalars(select(m.EligibilitySnapshot.student_id).join(latest,
        (latest.c.student_id == m.EligibilitySnapshot.student_id) & (latest.c.version == m.EligibilitySnapshot.version))
        .where(m.EligibilitySnapshot.round_id == round_id, m.EligibilitySnapshot.state == "CONFIRMED")).all())


def registration_out(session: Session, reg: m.TopicRegistration) -> RegistrationOut:
    members = session.scalars(
        select(m.RegistrationMember).where(
            m.RegistrationMember.registration_id == reg.id,
        ).order_by(m.RegistrationMember.is_coordinator.desc())
    ).all()
    profiles = {
        student.id: student
        for student in session.scalars(
            select(m.StudentProfile).where(
                m.StudentProfile.id.in_([item.student_id for item in members])
            )
        ).all()
    } if members else {}
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.registration_id == reg.id))
    topic = session.get(m.Topic, reg.topic_id)
    receiver = session.get(m.LecturerProfile, topic.receiving_lecturer_id) if topic.receiving_lecturer_id else None
    return RegistrationOut(
        id=reg.id, topic_id=reg.topic_id, round_id=reg.round_id, state=reg.state, row_version=reg.row_version,
        member_student_ids=[item.student_id for item in members],
        members=[RegistrationMemberOut(
            student_id=item.student_id,
            student_code=profiles[item.student_id].student_code,
            display_name=profiles[item.student_id].display_name,
            is_coordinator=item.is_coordinator,
            active=item.active,
            consent_status=item.consent_status,
            evidence_file_name=session.get(m.StoredFile, item.evidence_file_id).original_name if item.evidence_file_id else None,
        ) for item in members],
        lecturer_decided_at=reg.lecturer_decided_at,
        thesis_id=thesis.id if thesis else None,
        topic_title=topic.current_title,
        topic_proposer_user_id=topic.proposer_user_id,
        topic_code=topic.code, topic_state=topic.state, proposer_type=topic.proposer_type,
        receiving_lecturer_user_id=receiver.user_id if receiver else (topic.proposer_user_id if topic.proposer_type == "LECTURER" else None),
        receiving_lecturer_name=receiver.display_name if receiver else None,
        lecturer_reason=reg.lecturer_reason,
    )


def create_registration(session: Session, user: m.UserAccount, data: RegistrationCreate) -> RegistrationOut:
    if user.base_role != "STUDENT":
        fail(403, "Only students create a registration group")
    student = profile(session, user, "STUDENT")
    members = data.member_student_ids
    if student.id not in members or len(set(members)) != len(members):
        fail(422, "The creator must be a member and each member must appear once")
    now = datetime.now(timezone.utc)
    try:
        topic = session.scalar(select(m.Topic).where(m.Topic.id == data.topic_id).with_for_update())
        if topic is None:
            fail(404, "Topic not found")
        round_ = session.get(m.ThesisRound, topic.round_id)
        student_proposal = topic.proposer_type == "STUDENT" and topic.proposer_user_id == user.id
        allowed_state = topic.state == "APPROVED" or (student_proposal and topic.state == "DRAFT")
        if not allowed_state or round_ is None or round_.state != "OPEN" or not (round_.opens_at <= now <= round_.closes_at):
            fail(409, "Topic or registration round is not open")
        if topic.proposer_type == "STUDENT" and not student_proposal:
            fail(403, "Student proposals belong to their proposing group")
        if session.scalar(select(m.TopicRegistration.id).where(m.TopicRegistration.topic_id == topic.id,
            m.TopicRegistration.state.in_(["LECTURER_ACCEPTED", "FINALIZED"])).limit(1)):
            fail(409, "This topic already has an accepted group")
        if len(members) > topic.max_students:
            fail(422, "Group exceeds topic capacity")
        students = session.scalars(
            select(m.StudentProfile).where(m.StudentProfile.id.in_(members)).with_for_update()
        ).all()
        if len(students) != len(members) or any(item.department_id != topic.department_id for item in students):
            fail(422, "Group members must be valid students in the topic department")
        if confirmed_student_ids(session, topic.round_id, members) != set(members):
            fail(409, "Every member needs a current confirmed eligibility snapshot")
        existing = session.scalar(select(m.RegistrationMember.id).where(
            m.RegistrationMember.student_id.in_(members),
            m.RegistrationMember.round_id == topic.round_id,
            m.RegistrationMember.active.is_(True),
        ).limit(1))
        if existing is not None:
            fail(409, "A member already has an active registration in this round")
        reg = m.TopicRegistration(
            id=uuid4(), topic_id=topic.id, round_id=topic.round_id,
            created_by=student.id, state="DRAFT",
        )
        session.add(reg)
        session.flush()
        for member_id in members:
            session.add(m.RegistrationMember(
                id=uuid4(), registration_id=reg.id, round_id=topic.round_id,
                student_id=member_id, is_coordinator=(member_id == student.id), active=True,
                consent_status="ACCEPTED" if data.confirm_creator and member_id == student.id else "PENDING",
                responded_by_user_id=user.id if data.confirm_creator and member_id == student.id else None,
                responded_at=now if data.confirm_creator and member_id == student.id else None,
            ))
        session.flush()
        result = registration_out(session, reg)
        session.commit()
        return result
    except IntegrityError:
        session.rollback()
        fail(409, "Concurrent registration conflict")
    except Exception:
        session.rollback()
        raise


def respond_to_registration(session: Session, user: m.UserAccount, registration_id: UUID, data: MemberResponse) -> RegistrationOut:
    if user.base_role != "STUDENT":
        fail(403, "Only an invited student can respond to a group registration")
    student = profile(session, user, "STUDENT")
    try:
        reg = _registration(session, registration_id, lock=True)
        if reg.state != "DRAFT":
            fail(409, "Member confirmation is closed after the draft is submitted")
        member = session.scalar(select(m.RegistrationMember).where(
            m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.student_id == student.id,
            m.RegistrationMember.active.is_(True),
        ).with_for_update())
        if member is None:
            fail(403, "Your account is not an active member of this draft")
        if member.consent_status != "PENDING":
            fail(409, "You have already responded; ask the group coordinator to cancel and recreate the draft if needed")
        member.consent_status = data.consent_status
        member.responded_by_user_id = user.id
        member.responded_at = datetime.now(timezone.utc)
        reg.row_version += 1
        session.flush()
        result = registration_out(session, reg)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def submit_registration(session: Session, user: m.UserAccount, registration_id: UUID) -> RegistrationOut:
    if user.base_role != "STUDENT":
        fail(403, "Only the group coordinator can submit this registration")
    student = profile(session, user, "STUDENT")
    try:
        reg = _registration(session, registration_id, lock=True)
        if reg.state not in {"DRAFT", "RETURNED"}:
            fail(409, "Only a draft or returned student registration can be submitted")
        coordinator = session.scalar(select(m.RegistrationMember.id).where(
            m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.student_id == student.id,
            m.RegistrationMember.is_coordinator.is_(True),
            m.RegistrationMember.active.is_(True),
        ))
        if coordinator is None:
            fail(403, "Only the student who created the group can submit it")
        members = session.scalars(select(m.RegistrationMember).where(
            m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.active.is_(True),
        ).with_for_update()).all()
        topic = session.scalar(select(m.Topic).where(m.Topic.id == reg.topic_id).with_for_update())
        round_ = session.get(m.ThesisRound, reg.round_id)
        now = datetime.now(timezone.utc)
        if not (1 <= len(members) <= 3) or len(members) > topic.max_students:
            fail(409, "The active group must contain 1 to 3 students and fit the topic capacity")
        if any(member.consent_status != "ACCEPTED" for member in members):
            fail(409, "Every active group member must confirm participation before submission")
        student_proposal = topic.proposer_type == "STUDENT" and topic.proposer_user_id == user.id
        allowed_state = topic.state == "APPROVED" or (student_proposal and topic.state in {"DRAFT", "RETURNED"})
        if not allowed_state or round_ is None or round_.state != "OPEN" or not (round_.opens_at <= now <= round_.closes_at):
            fail(409, "The topic or registration round is no longer open")
        if reg.state == "RETURNED" and not student_proposal:
            fail(409, "Only a returned student proposal can be resubmitted")
        if session.scalar(select(m.TopicRegistration.id).where(m.TopicRegistration.topic_id == topic.id,
            m.TopicRegistration.state.in_(["LECTURER_ACCEPTED", "FINALIZED"])).limit(1)):
            fail(409, "Another group has already been accepted")
        eligible_ids = confirmed_student_ids(session, reg.round_id, [member.student_id for member in members])
        if eligible_ids != {member.student_id for member in members}:
            fail(409, "Every group member must still have a confirmed eligibility snapshot")
        if student_proposal and topic.state in {"DRAFT", "RETURNED"}:
            from backend.services.topics import _audit, _fingerprint
            before = _fingerprint(topic, session)
            topic.state = "SUBMITTED"
            topic.row_version += 1
            _audit(session, topic, user.id, "TOPIC_SUBMITTED", before)
        reg.state = "SUBMITTED"
        reg.submitted_at = now
        reg.row_version += 1
        session.flush()
        result = registration_out(session, reg)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def cancel_registration(session: Session, user: m.UserAccount, registration_id: UUID) -> RegistrationOut:
    if user.base_role != "STUDENT":
        fail(403, "Only the group coordinator can cancel this draft")
    student = profile(session, user, "STUDENT")
    try:
        reg = _registration(session, registration_id, lock=True)
        if reg.state not in {"DRAFT", "RETURNED"}:
            fail(409, "Only a draft or returned registration can be cancelled")
        coordinator = session.scalar(select(m.RegistrationMember.id).where(
            m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.student_id == student.id,
            m.RegistrationMember.is_coordinator.is_(True),
            m.RegistrationMember.active.is_(True),
        ))
        if coordinator is None:
            fail(403, "Only the student who created the group can cancel it")
        reg.state = "CANCELLED"
        reg.row_version += 1
        for member in session.scalars(select(m.RegistrationMember).where(
            m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.active.is_(True),
        )).all():
            member.active = False
        session.flush()
        result = registration_out(session, reg)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def _registration(session: Session, registration_id: UUID, *, lock: bool = False) -> m.TopicRegistration:
    query = select(m.TopicRegistration).where(m.TopicRegistration.id == registration_id)
    if lock:
        # Keep the same lock order as topic approval: topic, then registration.
        # Otherwise a simultaneous submission and department decision can deadlock.
        topic_id = session.scalar(select(m.TopicRegistration.topic_id).where(
            m.TopicRegistration.id == registration_id,
        ))
        if topic_id is None:
            fail(404, "Registration not found")
        session.scalar(select(m.Topic).where(m.Topic.id == topic_id).with_for_update())
        query = query.with_for_update()
    reg = session.scalar(query)
    if reg is None:
        fail(404, "Registration not found")
    return reg


def _topic_proposer(session: Session, topic: m.Topic, user: m.UserAccount) -> m.LecturerProfile:
    lecturer = profile(session, user, "LECTURER")
    receiver_id = topic.receiving_lecturer_id
    allowed = receiver_id == lecturer.id if receiver_id else (topic.proposer_type == "LECTURER" and topic.proposer_user_id == user.id)
    if not allowed:
        fail(403, "Only the receiving lecturer can decide this registration")
    return lecturer


def get_registration(session: Session, user: m.UserAccount, registration_id: UUID) -> RegistrationOut:
    reg = _registration(session, registration_id)
    topic = session.get(m.Topic, reg.topic_id)
    allowed = False
    if user.base_role == "STUDENT":
        student = profile(session, user, "STUDENT")
        allowed = session.scalar(select(m.RegistrationMember.id).where(
            m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.student_id == student.id,
        ).limit(1)) is not None
    elif user.base_role == "LECTURER":
        lecturer = profile(session, user, "LECTURER")
        allowed = reg.submitted_at is not None and reg.state != "DRAFT" and (
            topic.receiving_lecturer_id == lecturer.id or (topic.proposer_type == "LECTURER" and topic.proposer_user_id == user.id) or _is_department_head(session, lecturer.id, topic.department_id)
        )
    if not allowed:
        fail(404, "Registration not found")
    return registration_out(session, reg)


def lecturer_decision(
    session: Session, user: m.UserAccount, registration_id: UUID,
    data: LecturerDecision, expected_version: int,
) -> RegistrationOut:
    try:
        reg = _registration(session, registration_id, lock=True)
        topic = session.scalar(select(m.Topic).where(m.Topic.id == reg.topic_id).with_for_update())
        lecturer = _topic_proposer(session, topic, user)
        row_version(expected_version, reg.row_version)
        if reg.state != "SUBMITTED" or topic.state != "APPROVED":
            fail(409, "Department topic approval is required before the lecturer decision")
        if data.decision == "ACCEPT":
            other = session.scalar(select(m.TopicRegistration.id).where(
                m.TopicRegistration.topic_id == topic.id,
                m.TopicRegistration.id != reg.id,
                m.TopicRegistration.state.in_(["LECTURER_ACCEPTED", "FINALIZED"]),
            ).limit(1))
            if other is not None:
                fail(409, "Another group has already been accepted for this topic")
        if data.decision == "REJECT" and not (data.reason and data.reason.strip()):
            fail(422, "A rejection requires a reason")
        reg.state = "LECTURER_ACCEPTED" if data.decision == "ACCEPT" else "LECTURER_REJECTED"
        reg.lecturer_decided_by = lecturer.id
        reg.lecturer_decided_at = datetime.now(timezone.utc)
        reg.lecturer_reason = data.reason
        reg.row_version += 1
        if data.decision == "REJECT":
            for member in session.scalars(select(m.RegistrationMember).where(
                m.RegistrationMember.registration_id == reg.id
            )).all():
                member.active = False
        session.flush()
        result = registration_out(session, reg)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def _is_department_head(session: Session, lecturer_id: UUID, department_id: UUID) -> bool:
    now = datetime.now(timezone.utc)
    return session.scalar(
        select(m.PositionAssignment.id)
        .join(m.OrganizationalPosition, m.PositionAssignment.position_id == m.OrganizationalPosition.id)
        .where(
            m.PositionAssignment.lecturer_id == lecturer_id,
            m.PositionAssignment.department_id == department_id,
            m.PositionAssignment.state == "ACTIVE",
            m.PositionAssignment.effective_from <= now,
            (m.PositionAssignment.effective_to.is_(None) | (m.PositionAssignment.effective_to > now)),
            m.OrganizationalPosition.code == "DEPARTMENT_HEAD",
        ).limit(1)
    ) is not None


def finalize_registration(
    session: Session, user: m.UserAccount, registration_id: UUID, expected_version: int,
) -> RegistrationOut:
    if user.base_role != "LECTURER":
        fail(403, "Department head assignment required")
    try:
        reg = _registration(session, registration_id, lock=True)
        topic = session.scalar(select(m.Topic).where(m.Topic.id == reg.topic_id).with_for_update())
        head = profile(session, user, "LECTURER")
        if not _is_department_head(session, head.id, topic.department_id):
            fail(403, "Department head assignment is not active for this department")
        if reg.state == "FINALIZED":
            result = registration_out(session, reg)
            session.rollback()
            return result
        row_version(expected_version, reg.row_version)
        if reg.state != "LECTURER_ACCEPTED":
            fail(409, "Lecturer acceptance is required")
        proposer = session.get(m.LecturerProfile, topic.receiving_lecturer_id) if topic.receiving_lecturer_id else session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == topic.proposer_user_id))
        if proposer is None:
            fail(409, "Proposing lecturer profile is unavailable")
        members = session.scalars(select(m.RegistrationMember).where(
            m.RegistrationMember.registration_id == reg.id,
            m.RegistrationMember.active.is_(True),
        )).all()
        if not (1 <= len(members) <= topic.max_students <= 3):
            fail(409, "Group membership is invalid")
        now = datetime.now(timezone.utc)
        thesis = m.Thesis(
            id=uuid4(), round_id=reg.round_id, topic_id=topic.id, registration_id=reg.id,
            department_id=topic.department_id, current_title=topic.current_title, state="ACTIVE",
        )
        session.add(thesis)
        session.flush()
        for member in members:
            session.add(m.ThesisMember(
                id=uuid4(), thesis_id=thesis.id, student_id=member.student_id,
                is_coordinator=member.is_coordinator, active=True, joined_at=now,
            ))
        session.add(m.AdvisorAssignment(
            id=uuid4(), thesis_id=thesis.id, lecturer_id=proposer.id,
            assignment_type="PRIMARY", assigned_by=user.id, effective_from=now, state="ACTIVE",
        ))
        reg.state = "FINALIZED"
        topic.state = "LOCKED"
        reg.department_finalized_by = user.id
        reg.department_finalized_at = now
        reg.row_version += 1
        session.flush()
        result = registration_out(session, reg)
        session.commit()
        return result
    except IntegrityError:
        session.rollback()
        fail(409, "Topic or registration was finalized concurrently")
    except Exception:
        session.rollback()
        raise
