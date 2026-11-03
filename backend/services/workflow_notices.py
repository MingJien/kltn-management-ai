"""Transactional notices to the people concerned, never a broadcast of private submissions."""
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from backend.db.models import entities as m


def active_users(session, user_ids):
    return set(session.scalars(select(m.UserAccount.id).where(
        m.UserAccount.id.in_(set(user_ids)-{None}), m.UserAccount.status == "ACTIVE")))


def emit(session, actor_id, recipients, event, resource_type, resource_id, message, url, *, include_inactive=False):
    if not url.startswith("/") or url.startswith("//"):
        raise ValueError("Notices link only to local application routes")
    recipients = set(recipients)-{None} if include_inactive else active_users(session, recipients)
    for recipient in recipients-{actor_id}:
        session.add(m.UserNotification(id=uuid4(), recipient_user_id=recipient, actor_user_id=actor_id,
            kind="WORKFLOW_NOTICE", subject_type=resource_type,
            subject_id=resource_id, message=message[:1500], url=url))






def department_heads(session, department_id):
    from backend.services.theses import effective
    return set(session.scalars(select(m.LecturerProfile.user_id).join(m.PositionAssignment,
        m.PositionAssignment.lecturer_id == m.LecturerProfile.id).join(m.OrganizationalPosition,
        m.OrganizationalPosition.id == m.PositionAssignment.position_id).where(
        m.PositionAssignment.department_id == department_id,
        m.OrganizationalPosition.code == "DEPARTMENT_HEAD", effective(m.PositionAssignment))))


def actor_name(session, user_id):
    for cls in (m.StudentProfile, m.LecturerProfile):
        person = session.scalar(select(cls).where(cls.user_id == user_id))
        if person:
            return person.display_name
    return "Quản trị viên"










def topic_event(session, topic, actor_id, event):
    if event == "TOPIC_SUBMITTED" and topic.proposer_type == "LECTURER":
        recipients = department_heads(session, topic.department_id)
        label = "đã gửi đề tài chờ bộ môn duyệt"
    elif event in {"TOPIC_ARCHIVED", "TOPIC_RESTORED"}:
        recipients = {topic.proposer_user_id}
        if topic.receiving_lecturer_id:
            recipients.add(session.get(m.LecturerProfile, topic.receiving_lecturer_id).user_id)
        recipients |= set(session.scalars(select(m.StudentProfile.user_id).join(m.RegistrationMember,
            m.RegistrationMember.student_id == m.StudentProfile.id).join(m.TopicRegistration,
            m.TopicRegistration.id == m.RegistrationMember.registration_id).where(m.TopicRegistration.topic_id == topic.id)))
        label = "đã ngừng sử dụng đề tài cho đăng ký mới (hồ sơ đang làm được giữ nguyên)" if event == "TOPIC_ARCHIVED" else "đã khôi phục hiển thị đề tài"
    elif event in {"TOPIC_APPROVED", "TOPIC_RETURNED", "TOPIC_REJECTED"}:
        recipients = {topic.proposer_user_id}
        if topic.proposer_type == "STUDENT":
            recipients |= set(session.scalars(select(m.StudentProfile.user_id).join(m.RegistrationMember,
                m.RegistrationMember.student_id == m.StudentProfile.id).join(m.TopicRegistration,
                m.TopicRegistration.id == m.RegistrationMember.registration_id).where(m.TopicRegistration.topic_id == topic.id)))
            if event == "TOPIC_APPROVED":
                # Keep the existing approval notice for the proposer and receiving GV; notify other group members once.
                recipients.discard(topic.proposer_user_id)
                if topic.receiving_lecturer_id:recipients.discard(session.get(m.LecturerProfile, topic.receiving_lecturer_id).user_id)
        label = {"TOPIC_APPROVED": "đã duyệt đề tài", "TOPIC_RETURNED": "yêu cầu chỉnh sửa đề tài",
            "TOPIC_REJECTED": "đã từ chối đề tài"}[event]
    else:
        return
    emit(session, actor_id, recipients, event, "topic", topic.id,
        f"{actor_name(session, actor_id)} {label}: {topic.code} · {topic.current_title}.", f"/topics?focus={topic.id}")




def assignment_event(session, actor_id, target_id, round_id, role, *, revoked=False):
    from backend.services.account_directory import RESOURCE_ROLE_LABELS
    round_ = session.get(m.ThesisRound, round_id)
    label = RESOURCE_ROLE_LABELS.get(role, role)
    emit(session, actor_id, {target_id}, "ROUND_PERMISSION_REVOKED" if revoked else "ROUND_PERMISSION_GRANTED",
        "account", target_id, f"Khoa {'thu hồi nhiệm vụ' if revoked else 'giao nhiệm vụ'} {label} · đợt {round_.code}. Tải lại trang để cập nhật menu và quyền.", "/account")




def can_view(session, user, notice):
    """A saved notice is not an access grant; re-check current membership/assignment."""
    from backend.services.theses import rights, resource_role
    kind, identifier = notice.subject_type, notice.subject_id
    if notice.thesis_id:
        kind,identifier="thesis",notice.thesis_id
    if not kind:
        return True
    if kind == "thesis_withdrawal_request":
        from backend.services.withdrawals import can_view
        item = session.get(m.ThesisWithdrawalRequest, identifier)
        return bool(item and can_view(session, user, item))
    if kind == "account":
        return user.id == identifier or user.base_role == "ADMIN"
    if kind == "lecturer_profile_change":
        from backend.services.lecturer_profiles import request_access
        try:
            request_access(session,user,identifier)
            return True
        except HTTPException:
            return False
    if kind == "defense":
        from backend.services.evaluation import permissions
        thesis = session.get(m.Thesis, identifier)
        return bool(thesis and "evaluation:view" in permissions(session, user, thesis))
    if kind == "thesis":
        thesis = session.get(m.Thesis, identifier)
        if thesis is None:
            return False
        action = "progress:view" if notice.kind.startswith("PROGRESS_") else (
            "document:view" if notice.kind.startswith("DOCUMENT_") else
            "proposal:view" if notice.kind.startswith("PROPOSAL_") else "work:view" if notice.kind.startswith("WORK_") else "view")
        return action in rights(session, user, thesis)
    if kind == "official_form":
        from backend.services.school_forms import visible
        item=session.get(m.OfficialForm,identifier)
        return bool(item and visible(session,user,item))
    if kind == "round":
        from backend.services.school_forms import belongs
        return belongs(session, user, identifier)
    if kind == "topic":
        from backend.services.topics import get_visible_topic
        try:
            get_visible_topic(session, user, identifier)
            return True
        except HTTPException:
            return False
    if kind == "registration":
        from backend.services.registration import get_registration
        try:
            get_registration(session, user, identifier)
            return True
        except HTTPException:
            return False
    return False


def registration_event(session,reg,actor_id,event):
    labels={"REGISTRATION_MEMBER_CONFIRMED":"đã xác nhận tham gia nhóm","REGISTRATION_MEMBER_DECLINED":"đã từ chối tham gia nhóm","REGISTRATION_CANCELLED":"đã hủy đăng ký","REGISTRATION_MEMBER_WITHDREW":"đã rút khỏi nhóm","REGISTRATION_REJECT":"đã từ chối đề xuất","PROPOSAL_RETURNED_AFTER_LECTURER_REJECTION":"đã trả hồ sơ để nhóm chỉnh sửa","PROPOSAL_REASSIGNED_AFTER_LECTURER_REJECTION":"đã chuyển hồ sơ sang GV tiếp nhận khác"}
    if event not in labels:return
    session.flush()
    topic=session.get(m.Topic,reg.topic_id)
    recipients=set(session.scalars(select(m.StudentProfile.user_id).join(m.RegistrationMember,m.RegistrationMember.student_id==m.StudentProfile.id).where(m.RegistrationMember.registration_id==reg.id)))
    if event=="REGISTRATION_REJECT":
        if topic.proposer_type!="STUDENT":return
        recipients=department_heads(session,topic.department_id)
    elif topic.receiving_lecturer_id and event!="PROPOSAL_REASSIGNED_AFTER_LECTURER_REJECTION":
        recipients.add(session.get(m.LecturerProfile,topic.receiving_lecturer_id).user_id)
    emit(session,actor_id,recipients,event,"registration",reg.id,f"{actor_name(session,actor_id)} {labels[event]}: {topic.code} · {topic.current_title}.",f"/registrations?focus={reg.id}")
