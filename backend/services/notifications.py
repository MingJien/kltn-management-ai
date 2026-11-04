"""Account-scoped in-web notices for academic and account actions.

One row per recipient. A notice either keeps the legacy registration link or carries
the thesis/subject/message/url of the exact action. Notifications are never sent by
email and only the addressed account can list them.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.api.schemas import NotificationOut, NotificationSummaryOut
from backend.db.models import entities as m

VN_TZ = timezone(timedelta(hours=7))
DOCUMENT_TYPE_LABELS = {
    "PROPOSAL": "Đề cương (Mẫu 3)",
    "PLAN": "Kế hoạch thực hiện (Mẫu 2)",
    "REPORT": "Cuốn báo cáo KLTN",
    "SUPPORTING": "Tài liệu hỗ trợ",
}


def format_due(value: datetime) -> str:
    return value.astimezone(VN_TZ).strftime("%H:%M ngày %d/%m/%Y")


def _advisor(session: Session, thesis: m.Thesis) -> m.LecturerProfile | None:
    from backend.services.theses import primary_advisor

    assignment = primary_advisor(session, thesis.id)
    return session.get(m.LecturerProfile, assignment.lecturer_id) if assignment else None


def _student_user_ids(session: Session, thesis_id: UUID) -> list[UUID]:
    return list(session.scalars(select(m.StudentProfile.user_id).join(
        m.ThesisMember, m.ThesisMember.student_id == m.StudentProfile.id).where(
        m.ThesisMember.thesis_id == thesis_id, m.ThesisMember.active.is_(True))).all())


def _department_head_ids(session: Session, department_id: UUID, actor_user_id: UUID) -> list[UUID]:
    now = datetime.now(timezone.utc)
    return [head_id for head_id in session.scalars(select(m.LecturerProfile.user_id)
        .join(m.PositionAssignment, m.PositionAssignment.lecturer_id == m.LecturerProfile.id)
        .join(m.OrganizationalPosition, m.OrganizationalPosition.id == m.PositionAssignment.position_id)
        .join(m.UserAccount, m.UserAccount.id == m.LecturerProfile.user_id)
        .where(m.LecturerProfile.department_id == department_id,
               m.OrganizationalPosition.code == "DEPARTMENT_HEAD",
               m.PositionAssignment.department_id == department_id,
               m.PositionAssignment.state == "ACTIVE",
               m.PositionAssignment.effective_from <= now,
               (m.PositionAssignment.effective_to.is_(None) | (m.PositionAssignment.effective_to > now)),
               m.UserAccount.status == "ACTIVE").distinct()).all()
        if head_id != actor_user_id]


def add_notice(session: Session, *, topic: m.Topic | None = None, thesis: m.Thesis | None = None,
               actor_user_id: UUID, kind: str, registration_id: UUID | None = None,
               recipient_user_id: UUID | None = None, message: str | None = None,
               url: str | None = None, subject_type: str | None = None,
               subject_id: UUID | None = None) -> None:
    if registration_id is None and thesis is not None:
        registration_id = thesis.registration_id
    if recipient_user_id is None:
        if thesis is not None:
            advisor = _advisor(session, thesis)
            if advisor is None:
                raise ValueError("Notification recipient advisor does not exist")
            recipient_user_id = advisor.user_id
        elif topic is not None:
            lecturer = session.get(m.LecturerProfile, topic.receiving_lecturer_id) if topic.receiving_lecturer_id else None
            if lecturer is None and topic.proposer_type == "LECTURER":
                lecturer = session.scalar(select(m.LecturerProfile).where(
                    m.LecturerProfile.user_id == topic.proposer_user_id))
            if lecturer is None:
                raise ValueError("Notification recipient lecturer does not exist")
            recipient_user_id = lecturer.user_id
        else:
            raise ValueError("Notification recipient is required")
    if thesis is not None and message:
        linked_topic=session.get(m.Topic,thesis.topic_id)
        if linked_topic.code not in message:message=f"{message} · {linked_topic.code} · {thesis.current_title}"
    session.add(m.UserNotification(
        id=uuid4(), recipient_user_id=recipient_user_id, actor_user_id=actor_user_id,
        registration_id=registration_id, thesis_id=thesis.id if thesis else None,
        kind=kind, message=message, url=url, subject_type=subject_type, subject_id=subject_id,
    ))


def notify_user(session: Session, *, recipient_user_id: UUID, actor_user_id: UUID,
                kind: str, message: str, url: str = "/account") -> None:
    session.add(m.UserNotification(
        id=uuid4(), recipient_user_id=recipient_user_id, actor_user_id=actor_user_id,
        kind=kind, message=message, url=url,
    ))


def notify_thesis_advisor(session: Session, *, thesis: m.Thesis, actor_user_id: UUID,
                          kind: str, message: str, section: str = "progress") -> None:
    advisor = _advisor(session, thesis)
    if advisor is not None and advisor.user_id != actor_user_id:
        add_notice(session, thesis=thesis, actor_user_id=actor_user_id, kind=kind,
                   recipient_user_id=advisor.user_id, message=message,
                   url=f"/theses/{thesis.id}?section={section}", subject_type="thesis",
                   subject_id=thesis.id)
    if kind in {"PROGRESS_SUBMITTED","DOCUMENT_SUBMITTED","PROPOSAL_SUBMITTED"}:
        notify_thesis_students(session,thesis=thesis,actor_user_id=actor_user_id,kind=kind,message=message,section=section)


def notify_thesis_students(session: Session, *, thesis: m.Thesis, actor_user_id: UUID,
                           kind: str, message: str, section: str = "progress",
                           include_advisor: bool = False) -> None:
    recipients = [user_id for user_id in _student_user_ids(session, thesis.id)
                  if user_id != actor_user_id]
    if include_advisor:
        advisor = _advisor(session, thesis)
        if advisor is not None and advisor.user_id != actor_user_id:
            recipients.append(advisor.user_id)
    for user_id in dict.fromkeys(recipients):
        add_notice(session, thesis=thesis, actor_user_id=actor_user_id, kind=kind,
                   recipient_user_id=user_id, message=message,
                   url=f"/theses/{thesis.id}?section={section}", subject_type="thesis",
                   subject_id=thesis.id)


def notify_round_participants(session: Session, *, round_id: UUID, actor_user_id: UUID,
                              kind: str, message: str, section: str = "progress") -> None:
    from backend.services.workflow_notices import round_announcement

    round_ = session.get(m.ThesisRound, round_id)
    round_announcement(session, actor_user_id, round_id, kind,
        f"Đợt {round_.code} · {message}", f"/{section}")


def notify_department_heads(session: Session, *, topic: m.Topic, actor_user_id: UUID,
                            registration_id: UUID, kind: str = "PROPOSAL_SUBMITTED",
                            message: str | None = None, url: str | None = None) -> None:
    for head_id in _department_head_ids(session, topic.department_id, actor_user_id):
        add_notice(session, topic=topic, actor_user_id=actor_user_id,
                   registration_id=registration_id, kind=kind,
                   recipient_user_id=head_id, message=message, url=url)


def notify_department_heads_of(session: Session, *, department_id: UUID, actor_user_id: UUID,
                               kind: str, message: str, thesis: m.Thesis | None = None,
                               section: str = "proposal") -> None:
    for head_id in _department_head_ids(session, department_id, actor_user_id):
        add_notice(session, thesis=thesis, actor_user_id=actor_user_id, kind=kind,
                   recipient_user_id=head_id, message=message,
                   url=(f"/theses/{thesis.id}?section={section}" if thesis is not None else None),
                   subject_type="thesis" if thesis is not None else None,
                   subject_id=thesis.id if thesis is not None else None)


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
    from backend.services.workflow_notices import can_view
    user=session.get(m.UserAccount,user_id)
    candidates=session.scalars(select(m.UserNotification).where(*base).order_by(m.UserNotification.created_at.desc(),m.UserNotification.id.desc())).all()
    cache={};visible=[]
    for item in candidates:
        key=(item.thesis_id,item.subject_type,item.subject_id,item.kind.split("_")[0])
        if key not in cache:cache[key]=can_view(session,user,item)
        if cache[key]:visible.append(item)
    unread=sum(item.read_at is None for item in visible)
    notices=[item for item in visible if not unread_only or item.read_at is None][offset:offset+limit]
    if not notices:
        return NotificationSummaryOut(unread_count=unread, items=[])
    registration_ids = {item.registration_id for item in notices if item.registration_id is not None}
    registrations = {row.id: row for row in session.scalars(select(m.TopicRegistration).where(
        m.TopicRegistration.id.in_(registration_ids))).all()} if registration_ids else {}
    topics = {row.id: row for row in session.scalars(select(m.Topic).where(
        m.Topic.id.in_({row.topic_id for row in registrations.values()}))).all()} if registrations else {}
    actors = {row.user_id: row.display_name for row in session.scalars(select(m.StudentProfile).where(
        m.StudentProfile.user_id.in_({item.actor_user_id for item in notices}))).all()}
    recipient = session.get(m.UserAccount, user_id)
    items = []
    for item in notices:
        reg = registrations.get(item.registration_id) if item.registration_id else None
        topic = topics.get(reg.topic_id) if reg else None
        student = actors.get(item.actor_user_id, "Sinh viên")
        if item.message:
            message = item.message
        elif topic is not None:
            message = _legacy_message(item, topic, student, recipient)
        else:
            message = "Thông báo mới từ hệ thống."
        if item.url:
            url = item.url
        elif topic is not None:
            url = ("/notifications" if recipient.base_role == "ADMIN" else
                   f"/topics?focus={topic.id}" if item.kind.startswith("PROPOSAL_") else
                   f"/registrations?focus={reg.id}")
        else:
            url = "/account" if item.kind.startswith("ACCOUNT_") else "/notifications"
        items.append(NotificationOut(id=item.id, message=message, created_at=item.created_at,
            read_at=item.read_at, url=url))
    return NotificationSummaryOut(unread_count=unread, items=items)


def _legacy_message(item: m.UserNotification, topic: m.Topic, student: str,
                    recipient: m.UserAccount) -> str:
    if item.kind == "PROPOSAL_SUBMITTED":
        return f"{student} đã gửi đề xuất đề tài: {topic.current_title} (chờ bộ môn duyệt)."
    if item.kind == "PROPOSAL_APPROVED":
        return (f"Bộ môn đã duyệt đề xuất đề tài: {topic.current_title}."
               if recipient.base_role == "STUDENT" else
               f"Bộ môn đã duyệt đề xuất của {student}: {topic.current_title}. Mời bạn xét đăng ký.")
    if item.kind == "REGISTRATION_JOINED":
        return f"{student} vừa tham gia đăng ký đề tài: {topic.current_title}."
    if item.kind == "REGISTRATION_ACCEPTED":
        return f"GV đã chấp nhận đăng ký đề tài: {topic.current_title}."
    if item.kind == "REGISTRATION_REJECTED":
        return f"GV đã từ chối đăng ký đề tài: {topic.current_title}. Xem chi tiết để biết lý do."
    return (f"Nhóm đã gửi đăng ký đề tài: {topic.current_title}. Đang chờ GV xét."
            if recipient.base_role == "STUDENT" else
            f"{student} đã đăng ký đề tài: {topic.current_title}.")


def mark_notice_read(session: Session, user_id: UUID, notification_id: UUID) -> None:
    notice = session.scalar(select(m.UserNotification).where(
        m.UserNotification.id == notification_id,
        m.UserNotification.recipient_user_id == user_id,
        m.UserNotification.revoked_at.is_(None),
    ).with_for_update())
    if notice is None:
        raise HTTPException(404, "Notification not found")
    from backend.services.workflow_notices import can_view
    if not can_view(session,session.get(m.UserAccount,user_id),notice):raise HTTPException(404,"Notification not found")
    if notice.read_at is None:
        notice.read_at = datetime.now(timezone.utc)
        session.commit()
