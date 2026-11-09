"""Group-consented thesis changes and scoped recording of an external extension."""
from calendar import monthrange
from datetime import datetime, time
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from backend.db.models import entities as m
from backend.services.advisor_capacity import require_capacity
from backend.services.faculty_pool import compatible
from backend.services import documents, workflow_notices as notices
from backend.services.registration import _is_department_head, confirmed_student_ids, profile, row_version
from backend.services.theses import EDITABLE, audit, effective, now, primary_advisor, resource_role, thesis_access
from backend.services.withdrawals import VN, deadline

OPEN = {"SUBMITTED","ADVISOR_REVIEWED"}


def manager(session,user,thesis):
    lecturer = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == user.id)) if user.base_role == "LECTURER" else None
    return bool(lecturer and (_is_department_head(session,lecturer.id,thesis.department_id) or
        resource_role(session,user.id,"KLTN_COORDINATOR",round_id=thesis.round_id)))


def head(session,user,thesis):
    lecturer = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == user.id)) if user.base_role == "LECTURER" else None
    return bool(lecturer and _is_department_head(session,lecturer.id,thesis.department_id))


def active_members(session,thesis):
    return session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.active.is_(True)).order_by(m.ThesisMember.student_id)).all()


def receiver(session,topic):
    lecturer = session.get(m.LecturerProfile,topic.receiving_lecturer_id) if topic.receiving_lecturer_id else (
        session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == topic.proposer_user_id))
        if topic.proposer_type == "LECTURER" else None)
    account = session.get(m.UserAccount,lecturer.user_id) if lecturer else None
    return lecturer if lecturer and account and account.status == "ACTIVE" and compatible(session, topic.department_id, lecturer.department_id) else None


def snapshot(session,thesis):
    advisor = primary_advisor(session,thesis.id)
    if not advisor:
        raise HTTPException(409,"Khóa luận chưa có GVHD chính thức")
    topic = session.get(m.Topic,thesis.topic_id)
    members = active_members(session,thesis)
    return {"topic_id":str(topic.id),"topic_version":topic.row_version,"title":thesis.current_title,
        "description":topic.description or "","advisor_assignment_id":str(advisor.id),
        "advisor_id":str(advisor.lecturer_id),"advisor_user_id":str(session.get(m.LecturerProfile,advisor.lecturer_id).user_id),
        "members":[{"student_id":str(member.student_id),"user_id":str(session.get(m.StudentProfile,member.student_id).user_id),
            "name":session.get(m.StudentProfile,member.student_id).display_name} for member in members]}


def mutable(session,thesis):
    round_ = session.get(m.ThesisRound,thesis.round_id)
    if thesis.state not in EDITABLE or round_.state == "ARCHIVED":
        raise HTTPException(409,"Hồ sơ đã khóa giai đoạn thực hiện")
    if session.scalar(select(m.DefenseSlot.id).where(m.DefenseSlot.thesis_id == thesis.id)):
        raise HTTPException(409,"Cần xử lý lịch bảo vệ trước khi đổi đề tài hoặc gia hạn")
    if session.scalar(select(m.ThesisWithdrawalRequest.id).where(
        m.ThesisWithdrawalRequest.thesis_id == thesis.id,
        m.ThesisWithdrawalRequest.state.in_(["SUBMITTED","ADVISOR_CONFIRMED"])).limit(1)):
        raise HTTPException(409,"Nhóm đang có yêu cầu xin thôi chờ xử lý")


def open_request(session,thesis):
    return session.scalar(select(m.ThesisChangeRequest).where(
        m.ThesisChangeRequest.thesis_id == thesis.id,m.ThesisChangeRequest.state.in_(OPEN)))


def accessible(session,user,item):
    thesis = session.get(m.Thesis,item.thesis_id)
    return bool(manager(session,user,thesis) or str(user.id) in {str(item.requested_by),
        item.snapshot["advisor_user_id"],item.snapshot.get("target_advisor_user_id")} or
        any(member["user_id"]==str(user.id) for member in item.snapshot["members"]))


def get_request(session,user,identifier,expected=None):
    # Topic allocation lock precedes thesis and request row locks in every change operation.
    if expected is not None:
        session.execute(select(func.pg_advisory_xact_lock(66103)))
    item = session.get(m.ThesisChangeRequest,identifier)
    if not item or not accessible(session,user,item):
        raise HTTPException(404,"Không tìm thấy yêu cầu đổi đề tài trong phạm vi của bạn")
    if expected is not None:
        topic_ids={UUID(item.snapshot["topic_id"])}
        if item.target_topic_id:
            topic_ids.add(item.target_topic_id)
        session.scalars(select(m.Topic).where(m.Topic.id.in_(topic_ids)).order_by(m.Topic.id).with_for_update()).all()
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == item.thesis_id).with_for_update()) if expected is not None else session.get(m.Thesis,item.thesis_id)
    if expected is not None:
        session.refresh(item,with_for_update=True)
        row_version(expected,item.row_version)
        if item.state not in OPEN:
            raise HTTPException(409,"Yêu cầu đã kết thúc. Tải lại dữ liệu hiện hành")
    return item,thesis


def topic_available(session,topic,thesis,scope="GROUP"):
    if not topic or topic.id == thesis.topic_id or topic.round_id != thesis.round_id or (
        topic.department_id != thesis.department_id) or topic.state != "APPROVED" or topic.archived_at:
        raise HTTPException(409,"Đề tài mới phải đang được công bố trong cùng đợt và bộ môn")
    if (1 if scope=="INDIVIDUAL" else len(active_members(session,thesis))) > topic.max_students:
        raise HTTPException(409,"Số thành viên vượt sức chứa của đề tài mới")
    if session.scalar(select(m.Thesis.id).where(m.Thesis.topic_id == topic.id).limit(1)) or session.scalar(
        select(m.TopicRegistration.id).where(m.TopicRegistration.topic_id == topic.id,
            m.TopicRegistration.state.in_(["DRAFT","RETURNED","SUBMITTED","LECTURER_ACCEPTED","FINALIZED"])).limit(1)):
        raise HTTPException(409,"Đề tài mới đã có nhóm đăng ký. Hãy chọn đề tài khác")
    lecturer = receiver(session,topic)
    if not lecturer:
        raise HTTPException(409,"Đề tài mới chưa có giảng viên tiếp nhận đang hoạt động")
    require_capacity(session, lecturer.id, excluding_thesis_id=thesis.id if scope=="GROUP" else None)
    return lecturer


def fresh(session,item,thesis):
    current = snapshot(session,thesis)
    for key in ("topic_id","topic_version","title","advisor_assignment_id","members"):
        if current[key] != item.snapshot[key]:
            raise HTTPException(409,"Nhóm, đề tài hoặc GVHD đã thay đổi. Hủy yêu cầu cũ và lập lại theo hồ sơ hiện tại")
    if item.target_topic_id:
        topic = session.get(m.Topic,item.target_topic_id)
        lecturer = topic_available(session,topic,thesis,item.scope)
        if topic.row_version != item.snapshot["target_topic_version"] or str(lecturer.user_id)!=item.snapshot["target_advisor_user_id"]:
            raise HTTPException(409,"Thông tin đề tài mới đã thay đổi. Lập lại yêu cầu để các bên xác nhận đúng nội dung")
    ids = [UUID(member["student_id"]) for member in item.snapshot["members"]]
    if confirmed_student_ids(session,thesis.round_id,ids) != set(ids):
        raise HTTPException(409,"Có thành viên đã mất quyền tham gia đợt. Liên hệ Khoa trước khi xử lý")


def required_roles(item):
    roles = {"CURRENT_ADVISOR":item.snapshot["advisor_user_id"]}
    if item.snapshot.get("target_advisor_user_id") not in {None,item.snapshot["advisor_user_id"]}:
        roles["NEW_ADVISOR"]=item.snapshot["target_advisor_user_id"]
    return roles


def ready(item):
    return all(item.consents.get(member["user_id"],{}).get("decision")=="AGREE" for member in item.snapshot["members"]) and all(
        item.reviews.get(role,{}).get("decision")=="AGREE" for role in required_roles(item))


def announce(session,user,item,event,message):
    recipients = {UUID(member["user_id"]) for member in item.snapshot["members"]}
    recipients.update(UUID(value) for value in required_roles(item).values())
    thesis = session.get(m.Thesis,item.thesis_id)
    recipients.update(notices.department_heads(session,thesis.department_id))
    for recipient in recipients:
        notices.emit(session,user.id,{recipient},event,"account",recipient,message,f"/changes?focus={item.id}&thesis={item.thesis_id}")


def finish(session,user,item,event,reason):
    item.row_version += 1
    audit(session,user,event,"thesis_change_request",item.id,reason)
    announce(session,user,item,event,reason)
    session.commit()
    return {"id":item.id}


def create(session,user,thesis_id,data,expected):
    session.execute(select(func.pg_advisory_xact_lock(66103)))
    visible=thesis_access(session,user,thesis_id,action="document:submit")
    topic_ids={visible.topic_id}
    if data.target_topic_id:
        topic_ids.add(data.target_topic_id)
    session.scalars(select(m.Topic).where(m.Topic.id.in_(topic_ids)).order_by(m.Topic.id).with_for_update()).all()
    thesis = thesis_access(session,user,thesis_id,lock=True,write=True,action="document:submit")
    row_version(expected,thesis.row_version)
    mutable(session,thesis)
    round_ = session.scalar(select(m.ThesisRound).where(m.ThesisRound.id==thesis.round_id).with_for_update())
    if not round_.execution_starts_on or not datetime.combine(round_.execution_starts_on,time.min,VN)<=now()<deadline(round_.execution_starts_on):
        raise HTTPException(409,"Đổi đề tài chỉ được gửi trong 14 ngày đầu kể từ mốc bắt đầu thực hiện")
    if open_request(session,thesis):
        raise HTTPException(409,"Nhóm đã có yêu cầu đổi đề tài chờ xử lý")
    from backend.services.thesis_extensions import pending as pending_extension
    if pending_extension(session,thesis.id):raise HTTPException(409,"Cần xử lý yêu cầu gia hạn trước khi đổi đề tài")
    before = snapshot(session,thesis)
    if data.scope=="INDIVIDUAL" and (data.kind!="REPLACEMENT" or len(before["members"])<2):
        raise HTTPException(422,"Tách cá nhân chỉ áp dụng cho nhóm từ hai người và phải chọn đề tài mới")
    if data.kind == "REPLACEMENT":
        if not data.target_topic_id or data.proposed_title or data.proposed_description:
            raise HTTPException(422,"Chọn đề tài đã công bố, không nhập tên hoặc nội dung thay thế")
        topic = session.get(m.Topic,data.target_topic_id)
        lecturer = topic_available(session,topic,thesis,data.scope)
        before.update(target_topic_version=topic.row_version,target_advisor_user_id=str(lecturer.user_id),
            target_advisor_name=lecturer.display_name)
        title,description=topic.current_title,topic.description or ""
    else:
        title,description=data.proposed_title,data.proposed_description
        if data.target_topic_id or len(title)<10 or len(description)<20 or (title==before["title"] and description==before["description"]):
            raise HTTPException(422,"Nhập tên từ 10 ký tự, phạm vi từ 20 ký tự và nội dung khác hồ sơ hiện tại")
    item = m.ThesisChangeRequest(thesis_id=thesis.id,requested_by=user.id,kind=data.kind,scope=data.scope,
        proposed_title=title,proposed_description=description,target_topic_id=data.target_topic_id,
        reason=data.reason,state="SUBMITTED",snapshot=before,submitted_at=now(),reviews={},
        consents={str(user.id):{"decision":"AGREE","at":now().isoformat()}})
    session.add(item)
    session.flush()
    audit(session,user,"THESIS_CHANGE_SUBMITTED","thesis_change_request",item.id,data.reason)
    announce(session,user,item,"THESIS_CHANGE_SUBMITTED","Nhóm đã gửi yêu cầu đổi đề tài. Các thành viên và GVHD cần xác nhận.")
    session.commit()
    return {"id":item.id}


def consent(session,user,identifier,data,expected):
    item,thesis=get_request(session,user,identifier,expected)
    mutable(session,thesis)
    fresh(session,item,thesis)
    if str(user.id) not in {row["user_id"] for row in item.snapshot["members"]}:
        raise HTTPException(403,"Chỉ thành viên nhóm xác nhận nguyện vọng của mình")
    if str(user.id) in item.consents:
        raise HTTPException(409,"Bạn đã trả lời yêu cầu này")
    item.consents={**item.consents,str(user.id):{"decision":data.decision,"at":now().isoformat()}}
    if data.decision=="DECLINE":
        item.state,item.decided_at,item.decided_by,item.decision_reason="REJECTED",now(),user.id,"Có thành viên không đồng ý"
    return finish(session,user,item,"THESIS_CHANGE_CONSENT","Thành viên đã "+("đồng ý" if data.decision=="AGREE" else "không đồng ý")+" đổi đề tài")


def review(session,user,identifier,data,expected):
    item,thesis=get_request(session,user,identifier,expected)
    mutable(session,thesis)
    fresh(session,item,thesis)
    if required_roles(item).get(data.role)!=str(user.id):
        raise HTTPException(403,"Cần đúng GVHD được ghi nhận trong yêu cầu")
    if not all(item.consents.get(member["user_id"],{}).get("decision")=="AGREE" for member in item.snapshot["members"]):
        raise HTTPException(409,"Chờ mọi thành viên nhóm đồng ý trước khi GVHD xem xét")
    if data.role in item.reviews:
        raise HTTPException(409,"Bạn đã ghi ý kiến cho vai trò này")
    item.reviews={**item.reviews,data.role:{"decision":data.decision,"reason":data.reason,"by":str(user.id),"at":now().isoformat()}}
    if data.decision=="REJECT":
        item.state,item.decided_at,item.decided_by,item.decision_reason="REJECTED",now(),user.id,data.reason
    elif ready(item):
        item.state="ADVISOR_REVIEWED"
    return finish(session,user,item,"THESIS_CHANGE_REVIEWED","GVHD đã "+("đồng ý" if data.decision=="AGREE" else "từ chối")+" đổi đề tài · "+data.reason)


def cancel(session,user,identifier,expected):
    item,_=get_request(session,user,identifier,expected)
    if item.requested_by!=user.id:
        raise HTTPException(403,"Chỉ người gửi được hủy yêu cầu còn chờ")
    item.state,item.decided_by,item.decided_at,item.decision_reason="CANCELLED",user.id,now(),"Người gửi hủy yêu cầu"
    return finish(session,user,item,"THESIS_CHANGE_CANCELLED",item.decision_reason)


def reset_evidence(session,user,thesis):
    proposal = session.scalar(select(m.Proposal).where(m.Proposal.thesis_id==thesis.id).with_for_update())
    if proposal:
        proposal.state,proposal.row_version="REVISION_REQUIRED",proposal.row_version+1
    progress_rows=session.scalars(select(m.ProgressReport).where(m.ProgressReport.thesis_id==thesis.id)
        .order_by(m.ProgressReport.milestone_id,m.ProgressReport.version_no.desc()).with_for_update()).all()
    seen=set()
    for report in progress_rows:
        if report.milestone_id not in seen:
            report.state,report.row_version="REVISION_REQUIRED",report.row_version+1
            seen.add(report.milestone_id)
    for member in active_members(session,thesis):
        work=session.scalar(select(m.MemberWorkAssignment).where(m.MemberWorkAssignment.thesis_member_id==member.id)
            .order_by(m.MemberWorkAssignment.version_no.desc()).limit(1).with_for_update())
        if work:
            work.state,work.row_version="REVISION_REQUIRED",work.row_version+1
    for document in session.scalars(select(m.Document).where(m.Document.thesis_id==thesis.id,
            m.Document.document_type.in_(["PLAN","REPORT"]),m.Document.state=="ACTIVE").with_for_update()):
        latest = session.scalar(select(m.DocumentVersion).where(m.DocumentVersion.document_id==document.id)
            .order_by(m.DocumentVersion.version_no.desc()).limit(1).with_for_update())
        if latest:
            latest.state,latest.row_version="REVISION_REQUESTED",latest.row_version+1
            document.row_version+=1
    for assignment in session.scalars(select(m.ReviewerAssignment).where(
        or_(m.ReviewerAssignment.thesis_id==thesis.id,
            m.ReviewerAssignment.proposal_id.in_(select(m.Proposal.id).where(m.Proposal.thesis_id==thesis.id))),
        m.ReviewerAssignment.state=="ACTIVE").with_for_update()):
        assignment.state,assignment.row_version="REVOKED",assignment.row_version+1
        lecturer=session.get(m.LecturerProfile,assignment.lecturer_id)
        notices.emit(session,user.id,{lecturer.user_id},"THESIS_CHANGE_ASSIGNMENT_ENDED","account",lecturer.user_id,
            "Phân công nhận xét đã kết thúc do đổi đề tài. Bộ môn sẽ phân công lại theo hồ sơ mới.","/evaluation")
        audit(session,user,"THESIS_CHANGE_ASSIGNMENT_ENDED","thesis",thesis.id,source_reference=str(assignment.id))
    for assignment in session.scalars(select(m.ResourceAssignment).where(m.ResourceAssignment.thesis_id==thesis.id,
        m.ResourceAssignment.assignment_type=="PROGRESS_REVIEWER",effective(m.ResourceAssignment)).with_for_update()):
        assignment.state,assignment.effective_to,assignment.row_version="REVOKED",now(),assignment.row_version+1
        notices.emit(session,user.id,{assignment.user_id},"THESIS_CHANGE_ASSIGNMENT_ENDED","account",assignment.user_id,
            "Phân công góp ý tiến độ đã kết thúc do đổi đề tài.","/theses")
    thesis.state="ACTIVE"
    thesis.row_version+=1


def split_member(session,user,item,thesis,topic,lecturer,reason):
    student=session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id==item.requested_by))
    member=session.scalar(select(m.ThesisMember).where(m.ThesisMember.thesis_id==thesis.id,
        m.ThesisMember.student_id==student.id,m.ThesisMember.active.is_(True)).with_for_update())
    remaining=[row for row in active_members(session,thesis) if row.student_id!=student.id]
    if not member or not remaining:raise HTTPException(409,"Thành viên đã thay đổi; không thể tách theo yêu cầu cũ")
    # The old thesis remains active, so the new thesis consumes a new supervision slot.
    require_capacity(session,lecturer.id,lock=True)
    old_reg=session.scalar(select(m.TopicRegistration).where(m.TopicRegistration.id==thesis.registration_id).with_for_update())
    reg_member=session.scalar(select(m.RegistrationMember).where(m.RegistrationMember.registration_id==old_reg.id,
        m.RegistrationMember.student_id==student.id).with_for_update())
    member.active,member.is_coordinator,member.left_at=False,False,now()
    reg_member.active,reg_member.is_coordinator=False,False
    session.flush()
    if not any(row.is_coordinator for row in remaining):
        remaining[0].is_coordinator=True
        successor=session.scalar(select(m.RegistrationMember).where(m.RegistrationMember.registration_id==old_reg.id,
            m.RegistrationMember.student_id==remaining[0].student_id))
        successor.is_coordinator=True
    old_reg.expected_member_count=len(remaining)
    old_reg.row_version+=1
    from uuid import uuid4
    reg=m.TopicRegistration(id=uuid4(),round_id=thesis.round_id,topic_id=topic.id,created_by=student.id,
        expected_member_count=1,state="FINALIZED",submitted_at=now(),lecturer_decided_by=lecturer.id,
        lecturer_decided_at=now(),lecturer_reason=reason,department_finalized_by=user.id,department_finalized_at=now())
    session.add(reg);session.flush()
    session.add(m.RegistrationMember(registration_id=reg.id,round_id=reg.round_id,student_id=student.id,
        active=True,is_coordinator=True,consent_status="ACCEPTED",responded_by_user_id=student.user_id,responded_at=now()))
    new=m.Thesis(id=uuid4(),round_id=thesis.round_id,topic_id=topic.id,registration_id=reg.id,
        department_id=thesis.department_id,current_title=topic.current_title,state="ACTIVE")
    session.add(new);session.flush()
    session.add(m.ThesisMember(thesis_id=new.id,student_id=student.id,active=True,is_coordinator=True,joined_at=now()))
    session.add(m.AdvisorAssignment(thesis_id=new.id,lecturer_id=lecturer.id,assigned_by=user.id,effective_from=now(),state="ACTIVE"))
    topic.state,topic.row_version="LOCKED",topic.row_version+1
    reset_evidence(session,user,thesis)
    # Source identity stays intact; add only the resulting resource link.
    item.snapshot={**item.snapshot,"result_thesis_id":str(new.id)}
    audit(session,user,"THESIS_CREATED_FROM_TOPIC_CHANGE","thesis",new.id,reason,source_reference=str(item.id))
    notices.emit(session,user.id,{student.user_id},"THESIS_CREATED_FROM_TOPIC_CHANGE","account",student.user_id,
        "Đổi đề tài đã được duyệt. Hồ sơ mới đã được tạo; bạn cần nộp Mẫu 1–3 theo đề tài mới.",f"/theses/{new.id}")


def decide(session,user,identifier,data,expected):
    item,thesis=get_request(session,user,identifier,expected)
    if not head(session,user,thesis):
        raise HTTPException(403,"Chỉ trưởng bộ môn đúng phạm vi được quyết định đổi đề tài")
    mutable(session,thesis)
    if data.decision=="APPROVE":
        fresh(session,item,thesis)
        if not ready(item):
            raise HTTPException(409,"Cần đủ đồng ý của nhóm, GVHD cũ và GVHD mới nếu thay đổi")
        if item.scope=="INDIVIDUAL":
            topic=session.get(m.Topic,item.target_topic_id)
            lecturer=topic_available(session,topic,thesis,item.scope)
            split_member(session,user,item,thesis,topic,lecturer,data.reason)
            item.state,item.decided_at,item.decided_by,item.decision_reason="APPROVED",now(),user.id,data.reason
            return finish(session,user,item,"THESIS_CHANGE_APPROVED","Bộ môn duyệt tách thành viên sang đề tài mới; nhóm còn lại tiếp tục đề tài cũ và cập nhật Mẫu 1–3")
        reg = session.get(m.TopicRegistration,thesis.registration_id)
        old_topic=session.get(m.Topic,thesis.topic_id)
        if item.target_topic_id:
            topic=session.scalar(select(m.Topic).where(m.Topic.id==item.target_topic_id).with_for_update())
            lecturer=topic_available(session,topic,thesis)
            advisor=primary_advisor(session,thesis.id)
            if advisor.lecturer_id!=lecturer.id:
                require_capacity(session, lecturer.id, excluding_thesis_id=thesis.id, lock=True)
                advisor.state,advisor.effective_to,advisor.row_version="ENDED",now(),advisor.row_version+1
                session.flush()
                session.add(m.AdvisorAssignment(thesis_id=thesis.id,lecturer_id=lecturer.id,
                    assigned_by=user.id,effective_from=now(),state="ACTIVE"))
            reg.topic_id,reg.lecturer_decided_by,reg.lecturer_decided_at=topic.id,lecturer.id,now()
            reg.lecturer_reason="Đổi đề tài được bộ môn phê duyệt · "+data.reason
            thesis.topic_id,topic.state=topic.id,"LOCKED"
            topic.row_version+=1
            # The released topic remains locked for this round, retaining its used-topic history.
            audit(session,user,"THESIS_TOPIC_REPLACED","thesis",thesis.id,
                f"{old_topic.code} → {topic.code}; {data.reason}")
        else:
            from backend.services.topics import _title_version
            old_topic.current_title,old_topic.description=item.proposed_title,item.proposed_description
            old_topic.row_version+=1
            _title_version(session,old_topic,user.id,item.proposed_title,data.reason)
        thesis.current_title=item.proposed_title
        reg.expected_member_count=len(active_members(session,thesis))
        reg.department_finalized_by,reg.department_finalized_at=user.id,now()
        reg.row_version+=1
        reset_evidence(session,user,thesis)
        item.state="APPROVED"
    else:
        item.state="REJECTED"
    item.decided_at,item.decided_by,item.decision_reason=now(),user.id,data.reason
    return finish(session,user,item,"THESIS_CHANGE_"+item.state,
        ("Bộ môn đã duyệt đổi đề tài. Nhóm cần cập nhật Mẫu 1–3 và báo cáo." if item.state=="APPROVED" else "Bộ môn từ chối đổi đề tài.")+" · "+data.reason)


def extension_for(session,thesis):
    return session.scalar(select(m.ThesisExtension).where(m.ThesisExtension.thesis_id==thesis.id))


def historical_identity(session,thesis,instant):
    change=session.scalar(select(m.ThesisChangeRequest).where(m.ThesisChangeRequest.thesis_id==thesis.id,
        m.ThesisChangeRequest.state=="APPROVED",m.ThesisChangeRequest.decided_at>instant)
        .order_by(m.ThesisChangeRequest.decided_at).limit(1))
    advisor_id=UUID(change.snapshot["advisor_id"]) if change else (
        primary_advisor(session,thesis.id).lecturer_id if primary_advisor(session,thesis.id) else None)
    lecturer=session.get(m.LecturerProfile,advisor_id) if advisor_id else None
    return {"title":change.snapshot["title"] if change else thesis.current_title,
        "advisor":lecturer.display_name if lecturer else "Chưa ghi nhận"}


def add_months(value,count):
    month=value.month-1+count
    year=value.year+month//12
    month=month%12+1
    return value.replace(year=year,month=month,day=min(value.day,monthrange(year,month)[1]))


def extension_out(session,item):
    if not item:
        return None
    file=session.get(m.StoredFile,item.evidence_file_id) if item.evidence_file_id else None
    request=session.scalar(select(m.ThesisExtensionRequest).where(m.ThesisExtensionRequest.extension_id==item.id))
    return {"extension_starts_at":request.extension_starts_at if request else None,"id":item.id,"original_due_at":item.original_due_at,"until_at":item.until_at,"decision_on":item.decision_on,
        "reference":item.reference,"reason":item.reason,"recorded_at":item.recorded_at,
        "recorded_by":notices.actor_name(session,item.recorded_by),"interim_grade":"I",
        "file":{"id":file.id,"name":file.original_name,"scan_state":file.scan_state} if file else None}


def record_extension(session,user,thesis_id,data,expected):
    thesis=thesis_access(session,user,thesis_id)
    if not manager(session,user,thesis):raise HTTPException(403,"Chỉ người quản lý đúng phạm vi xử lý gia hạn")
    raise HTTPException(409,"Cần SV gửi yêu cầu gia hạn, đủ đồng thuận nhóm và ý kiến GVHD trước khi TBM ghi nhận quyết định")


def request_out(session,user,item):
    thesis=session.get(m.Thesis,item.thesis_id)
    roles=required_roles(item)
    pending=item.state in OPEN
    return {"id":item.id,"code":"DOI-"+item.id.hex[:12].upper(),"thesis_id":item.thesis_id,
        "kind":item.kind,"requested_by":item.requested_by,"scope":item.scope,"result_thesis_id":item.snapshot.get("result_thesis_id"),"state":item.state,"reason":item.reason,"proposed_title":item.proposed_title,
        "proposed_description":item.proposed_description,"snapshot":item.snapshot,"consents":item.consents,
        "reviews":item.reviews,"submitted_at":item.submitted_at,"decided_at":item.decided_at,
        "decision_reason":item.decision_reason,"decided_by":notices.actor_name(session,item.decided_by) if item.decided_by else None,
        "row_version":item.row_version,
        "can_consent":pending and str(user.id) not in item.consents and any(row["user_id"]==str(user.id) for row in item.snapshot["members"]),
        "can_cancel":pending and item.requested_by==user.id,
        "review_roles":[role for role,identifier in roles.items() if identifier==str(user.id) and role not in item.reviews] if pending else [],
        "can_decide":pending and head(session,user,thesis),"ready":ready(item)}


def extension_download(session,user,thesis_id):
    thesis=thesis_access(session,user,thesis_id)
    advisor=primary_advisor(session,thesis.id)
    own=any(session.get(m.StudentProfile,row.student_id).user_id==user.id for row in active_members(session,thesis))
    advising=bool(advisor and session.get(m.LecturerProfile,advisor.lecturer_id).user_id==user.id)
    if not (manager(session,user,thesis) or own or advising):
        raise HTTPException(404,"Không tìm thấy minh chứng")
    item=extension_for(session,thesis)
    file=session.get(m.StoredFile,item.evidence_file_id) if item and item.evidence_file_id else None
    return documents.stored_download(session,SimpleNamespace(stored_file_id=file.id,content_sha256=file.sha256) if file else None)


def workspace(session,user):
    if user.base_role not in {"STUDENT","LECTURER"}:
        raise HTTPException(403,"Chức năng dành cho sinh viên và giảng viên được giao")
    theses=[]
    if user.base_role=="STUDENT":
        student=profile(session,user,"STUDENT")
        scope=select(m.ThesisMember.thesis_id).where(m.ThesisMember.student_id==student.id,m.ThesisMember.active.is_(True))
        query=select(m.Thesis).where(m.Thesis.id.in_(scope))
    else:
        lecturer=profile(session,user,"LECTURER")
        managed_rounds=select(m.ResourceAssignment.round_id).where(m.ResourceAssignment.user_id==user.id,
            m.ResourceAssignment.assignment_type=="KLTN_COORDINATOR",effective(m.ResourceAssignment))
        departments=[identifier for identifier in session.scalars(select(m.Department.id))
            if _is_department_head(session,lecturer.id,identifier)]
        advised=select(m.AdvisorAssignment.thesis_id).where(m.AdvisorAssignment.lecturer_id==lecturer.id,effective(m.AdvisorAssignment))
        query=select(m.Thesis).where(or_(m.Thesis.id.in_(advised),m.Thesis.round_id.in_(managed_rounds),
            m.Thesis.department_id.in_(departments)))
    visible_theses=list(session.scalars(query.order_by(m.Thesis.created_at.desc())))
    from backend.services.thesis_extensions import listing as extension_listing
    extension_items=extension_listing(session,user,[thesis.id for thesis in visible_theses])
    for thesis in visible_theses:
        try:
            thesis_access(session,user,thesis.id)
        except HTTPException:
            continue
        own = next((row for row in active_members(session,thesis)
            if session.get(m.StudentProfile,row.student_id).user_id==user.id),None)
        advisor=primary_advisor(session,thesis.id)
        if not (own or manager(session,user,thesis) or (advisor and session.get(m.LecturerProfile,advisor.lecturer_id).user_id==user.id)):
            continue
        round_=session.get(m.ThesisRound,thesis.round_id)
        cutoff=deadline(round_.execution_starts_on) if round_.execution_starts_on else None
        pending=open_request(session,thesis)
        extension=extension_for(session,thesis)
        from backend.services.thesis_extensions import pending as pending_extension
        extension_request=pending_extension(session,thesis.id)
        baseline=session.scalar(select(m.DocumentDeadline).where(m.DocumentDeadline.round_id==thesis.round_id,m.DocumentDeadline.document_type=="REPORT"))
        block=""
        try:
            mutable(session,thesis)
        except HTTPException as error:
            block=error.detail
        in_window=bool(cutoff and datetime.combine(round_.execution_starts_on,time.min,VN)<=now()<cutoff)
        candidates=[]
        if own and not block and in_window and not pending:
            for topic in session.scalars(select(m.Topic).where(m.Topic.round_id==thesis.round_id,
                    m.Topic.department_id==thesis.department_id,m.Topic.state=="APPROVED").order_by(m.Topic.code)):
                allowed={}
                for scope in ("GROUP","INDIVIDUAL"):
                    try:
                        lecturer=topic_available(session,topic,thesis,scope)
                        allowed[scope]=True
                    except HTTPException:
                        allowed[scope]=False
                if not any(allowed.values()):continue
                lecturer=receiver(session,topic)
                candidates.append({"id":topic.id,"code":topic.code,"title":topic.current_title,
                    "description":topic.description or "","advisor":lecturer.display_name,"capacity":topic.max_students,
                    "group_available":allowed["GROUP"],"individual_available":allowed["INDIVIDUAL"]})
        current_topic=session.get(m.Topic,thesis.topic_id)
        eligible=bool(own and own.student_id in confirmed_student_ids(session,thesis.round_id,[own.student_id]))
        can_request=bool(eligible and not block and in_window and not pending and not extension_request)
        evidence=[]
        if manager(session,user,thesis):
            evidence=[{"id":file.id,"name":file.original_name,"scan_state":file.scan_state} for file in session.scalars(
                select(m.StoredFile).join(m.DocumentVersion,m.DocumentVersion.stored_file_id==m.StoredFile.id)
                .join(m.Document,m.Document.id==m.DocumentVersion.document_id)
                .where(m.Document.thesis_id==thesis.id,m.StoredFile.scan_state=="CLEAN").distinct())]
        theses.append({"id":thesis.id,"title":thesis.current_title,"description":current_topic.description or "",
            "round_label":round_.code,"round_id":round_.id,"round_version":round_.row_version,"state":thesis.state,"row_version":thesis.row_version,
            "registration_id":thesis.registration_id,"member_count":len(active_members(session,thesis)),"starts_on":round_.execution_starts_on,"cutoff":cutoff,
            "can_request":can_request,"message":block or ("Nhóm đang có yêu cầu chờ xử lý" if pending or extension_request else
                "Quyền tham gia đợt đã bị thu hồi. Liên hệ Khoa để đối chiếu." if own and not eligible else
                "Chưa có ngày bắt đầu thực hiện" if not cutoff else "Ngoài thời hạn đổi đề tài" if not in_window else ""),
            "can_extend":False,
            "can_request_extension":bool(eligible and not block and not pending and not extension_request and not extension and baseline),
            "extension_request_blocker":block or ("Có yêu cầu đang chờ xử lý" if pending or extension_request else "Đã gia hạn một lần" if extension else "Khoa chưa thiết lập hạn báo cáo" if not baseline else ""),
            "extension_blocker":block or ("Đã gia hạn một lần" if extension else "Nhóm đang có yêu cầu đổi đề tài" if pending else
                "Chưa thiết lập hạn báo cáo của đợt" if not baseline else ""),
            "can_set_start":manager(session,user,thesis) and bool(resource_role(session,user.id,"KLTN_COORDINATOR",round_id=thesis.round_id)),
            "baseline_due":baseline.due_at if baseline else None,"extension_max":None,
            "extension":extension_out(session,extension),"candidates":candidates,"evidence":evidence})
    # Filter request access in SQL before reading free text or exposing group information.
    ids=[row["id"] for row in theses]
    user_key=str(user.id)
    query=select(m.ThesisChangeRequest).where(or_(m.ThesisChangeRequest.thesis_id.in_(ids),
        m.ThesisChangeRequest.requested_by==user.id,m.ThesisChangeRequest.snapshot["advisor_user_id"].astext==user_key,
        m.ThesisChangeRequest.snapshot["target_advisor_user_id"].astext==user_key,
        m.ThesisChangeRequest.snapshot["members"].contains([{"user_id":user_key}])))
    items=[request_out(session,user,item) for item in session.scalars(query.order_by(m.ThesisChangeRequest.submitted_at.desc()))
        if accessible(session,user,item)]
    return {"theses":theses,"requests":items,"extension_requests":extension_items}
