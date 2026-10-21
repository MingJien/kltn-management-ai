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
               registration_id: UUID, kind: str) -> None:
    lecturer = session.get(m.LecturerProfile, topic.receiving_lecturer_id) if topic.receiving_lecturer_id else None
    if lecturer is None and topic.proposer_type == "LECTURER":
        lecturer = session.scalar(select(m.LecturerProfile).where(
            m.LecturerProfile.user_id == topic.proposer_user_id))
    if lecturer is None:
        raise ValueError("Notification recipient lecturer does not exist")
    session.add(m.UserNotification(
        id=uuid4(), recipient_user_id=lecturer.user_id, actor_user_id=actor_user_id,
        registration_id=registration_id, kind=kind,
    ))


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


def list_notices(session: Session, user_id: UUID, limit: int = 20) -> NotificationSummaryOut:
    base = (m.UserNotification.recipient_user_id == user_id,
            m.UserNotification.revoked_at.is_(None))
    unread = session.scalar(select(func.count()).select_from(m.UserNotification).where(
        *base, m.UserNotification.read_at.is_(None))) or 0
    notices = session.scalars(select(m.UserNotification).where(*base).order_by(
        m.UserNotification.created_at.desc(), m.UserNotification.id.desc()).limit(limit)).all()
    if not notices:
        return NotificationSummaryOut(unread_count=unread, items=[])
    registration_ids = {item.registration_id for item in notices}
    registrations = {row.id: row for row in session.scalars(select(m.TopicRegistration).where(
        m.TopicRegistration.id.in_(registration_ids))).all()}
    topics = {row.id: row for row in session.scalars(select(m.Topic).where(
        m.Topic.id.in_({row.topic_id for row in registrations.values()}))).all()}
    actors = {row.user_id: row.display_name for row in session.scalars(select(m.StudentProfile).where(
        m.StudentProfile.user_id.in_({item.actor_user_id for item in notices}))).all()}
    items = []
    for item in notices:
        reg = registrations[item.registration_id]
        topic = topics[reg.topic_id]
        student = actors.get(item.actor_user_id, "Sinh viên")
        if item.kind == "PROPOSAL_SUBMITTED":
            message = f"{student} đề xuất bạn hướng dẫn đề tài: {topic.current_title} (chờ bộ môn duyệt)."
        elif item.kind == "PROPOSAL_APPROVED":
            message = f"Bộ môn đã duyệt đề xuất của {student}: {topic.current_title}. Mời bạn xét đăng ký."
        elif item.kind == "REGISTRATION_JOINED":
            message = f"{student} vừa tham gia đăng ký đề tài: {topic.current_title}."
        else:
            message = f"{student} đã đăng ký đề tài: {topic.current_title}."
        items.append(NotificationOut(id=item.id, message=message, created_at=item.created_at,
            read_at=item.read_at, url=f"/registrations?focus={reg.id}"))
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
