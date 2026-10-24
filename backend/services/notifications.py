"""Small, account-scoped notices for the registration workflow."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.api.schemas import NotificationOut, NotificationSummaryOut
from backend.db.models import entities as m


def add_notice(session: Session, *, topic: m.Topic, actor_user_id: UUID,
               registration_id: UUID, kind: str, recipient_user_id: UUID | None = None) -> None:
    if recipient_user_id is None:
        lecturer = session.get(m.LecturerProfile, topic.receiving_lecturer_id) if topic.receiving_lecturer_id else None
        if lecturer is None and topic.proposer_type == "LECTURER":
            lecturer = session.scalar(select(m.LecturerProfile).where(
                m.LecturerProfile.user_id == topic.proposer_user_id))
        if lecturer is None:
            raise ValueError("Notification recipient lecturer does not exist")
        recipient_user_id = lecturer.user_id
    session.add(m.UserNotification(
        id=uuid4(), recipient_user_id=recipient_user_id, actor_user_id=actor_user_id,
        registration_id=registration_id, kind=kind,
    ))


def notify_department_heads(session: Session, *, topic: m.Topic, actor_user_id: UUID,
                            registration_id: UUID) -> None:
    now = datetime.now(timezone.utc)
    receiver = session.get(m.LecturerProfile, topic.receiving_lecturer_id) if topic.receiving_lecturer_id else None
    head_ids = session.scalars(select(m.LecturerProfile.user_id)
        .join(m.PositionAssignment, m.PositionAssignment.lecturer_id == m.LecturerProfile.id)
        .join(m.OrganizationalPosition, m.OrganizationalPosition.id == m.PositionAssignment.position_id)
        .join(m.UserAccount, m.UserAccount.id == m.LecturerProfile.user_id)
        .where(m.LecturerProfile.department_id == topic.department_id,
               m.OrganizationalPosition.code == "DEPARTMENT_HEAD",
               m.PositionAssignment.department_id == topic.department_id,
               m.PositionAssignment.state == "ACTIVE",
               m.PositionAssignment.effective_from <= now,
               (m.PositionAssignment.effective_to.is_(None) | (m.PositionAssignment.effective_to > now)),
               m.UserAccount.status == "ACTIVE").distinct()).all()
    for head_id in head_ids:
        if head_id not in {actor_user_id, receiver.user_id if receiver else None}:
            add_notice(session, topic=topic, actor_user_id=actor_user_id,
                       registration_id=registration_id, kind="PROPOSAL_SUBMITTED",
                       recipient_user_id=head_id)


def notify_admins(session: Session, *, topic: m.Topic, actor_user_id: UUID,
                  registration_id: UUID, kind: str) -> None:
    admin_ids = session.scalars(select(m.UserAccount.id).where(
        m.UserAccount.base_role == "ADMIN", m.UserAccount.status == "ACTIVE",
        m.UserAccount.id != actor_user_id)).all()
    for admin_id in admin_ids:
        add_notice(session, topic=topic, actor_user_id=actor_user_id,
                   registration_id=registration_id, kind=kind,
                   recipient_user_id=admin_id)


def revoke_proposal_notice(session: Session, *, registration_id: UUID,
                           lecturer_id: UUID | None, now: datetime) -> None:
    criteria = [m.UserNotification.registration_id == registration_id,
                m.UserNotification.kind == "PROPOSAL_SUBMITTED",
                m.UserNotification.revoked_at.is_(None)]
    if lecturer_id is not None:
        lecturer = session.get(m.LecturerProfile, lecturer_id)
        if lecturer is None:
            return
        criteria.append(m.UserNotification.recipient_user_id == lecturer.user_id)
    session.execute(update(m.UserNotification).where(*criteria).values(revoked_at=now))


def revoke_actor_notices(session: Session, *, registration_id: UUID,
                         actor_user_id: UUID, now: datetime) -> None:
    session.execute(update(m.UserNotification).where(
        m.UserNotification.registration_id == registration_id,
        m.UserNotification.actor_user_id == actor_user_id,
        m.UserNotification.revoked_at.is_(None),
    ).values(revoked_at=now))


def list_notices(session: Session, user_id: UUID, limit: int = 20, offset: int = 0,
                 unread_only: bool = False) -> NotificationSummaryOut:
    base = (m.UserNotification.recipient_user_id == user_id,
            m.UserNotification.revoked_at.is_(None))
    unread = session.scalar(select(func.count()).select_from(m.UserNotification).where(
        *base, m.UserNotification.read_at.is_(None))) or 0
    visible = (*base, m.UserNotification.read_at.is_(None)) if unread_only else base
    notices = session.scalars(select(m.UserNotification).where(*visible).order_by(
        m.UserNotification.created_at.desc(), m.UserNotification.id.desc()).offset(offset).limit(limit)).all()
    if not notices:
        return NotificationSummaryOut(unread_count=unread, items=[])
    registration_ids = {item.registration_id for item in notices}
    registrations = {row.id: row for row in session.scalars(select(m.TopicRegistration).where(
        m.TopicRegistration.id.in_(registration_ids))).all()}
    topics = {row.id: row for row in session.scalars(select(m.Topic).where(
        m.Topic.id.in_({row.topic_id for row in registrations.values()}))).all()}
    actors = {row.user_id: row.display_name for row in session.scalars(select(m.StudentProfile).where(
        m.StudentProfile.user_id.in_({item.actor_user_id for item in notices}))).all()}
    recipient = session.get(m.UserAccount, user_id)
    items = []
    for item in notices:
        reg = registrations[item.registration_id]
        topic = topics[reg.topic_id]
        student = actors.get(item.actor_user_id, "Sinh viên")
        if item.kind == "PROPOSAL_SUBMITTED":
            message = f"{student} đã gửi đề xuất đề tài: {topic.current_title} (chờ bộ môn duyệt)."
        elif item.kind == "PROPOSAL_APPROVED":
            message = (f"Bộ môn đã duyệt đề xuất đề tài: {topic.current_title}."
                       if recipient.base_role == "STUDENT" else
                       f"Bộ môn đã duyệt đề xuất của {student}: {topic.current_title}. Mời bạn xét đăng ký.")
        elif item.kind == "REGISTRATION_JOINED":
            message = f"{student} vừa tham gia đăng ký đề tài: {topic.current_title}."
        elif item.kind == "REGISTRATION_ACCEPTED":
            message = f"GV đã chấp nhận đăng ký đề tài: {topic.current_title}."
        elif item.kind == "REGISTRATION_REJECTED":
            message = f"GV đã từ chối đăng ký đề tài: {topic.current_title}. Xem chi tiết để biết lý do."
        else:
            message = (f"Nhóm đã gửi đăng ký đề tài: {topic.current_title}. Đang chờ GV xét."
                       if recipient.base_role == "STUDENT" else
                       f"{student} đã đăng ký đề tài: {topic.current_title}.")
        url = ("/notifications" if recipient.base_role == "ADMIN" else
               f"/topics?focus={topic.id}" if item.kind.startswith("PROPOSAL_") else
               f"/registrations?focus={reg.id}")
        items.append(NotificationOut(id=item.id, message=message, created_at=item.created_at,
            read_at=item.read_at, url=url))
    return NotificationSummaryOut(unread_count=unread, items=items)


def mark_notice_read(session: Session, user_id: UUID, notification_id: UUID) -> None:
    notice = session.scalar(select(m.UserNotification).where(
        m.UserNotification.id == notification_id,
        m.UserNotification.recipient_user_id == user_id,
        m.UserNotification.revoked_at.is_(None),
    ).with_for_update())
    if notice is None:
        raise HTTPException(404, "Notification not found")
    if notice.read_at is None:
        notice.read_at = datetime.now(timezone.utc)
        session.commit()
