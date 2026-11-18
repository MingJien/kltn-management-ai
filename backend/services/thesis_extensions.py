"""Student requests, per-member consent and an explicit external extension decision."""
from types import SimpleNamespace
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from backend.db.models import entities as m
from backend.services import thesis_changes as c
from backend.services.extension_policy import maximum_until, validate_defense_window

OPEN={"SUBMITTED","ADVISOR_REVIEWED"}


def pending(session,thesis_id):
    return session.scalar(select(m.ThesisExtensionRequest).where(m.ThesisExtensionRequest.thesis_id==thesis_id,
        m.ThesisExtensionRequest.state.in_(OPEN)))

def consents(session,item):
    return session.scalars(select(m.ThesisExtensionConsent).where(m.ThesisExtensionConsent.request_id==item.id)
        .order_by(m.ThesisExtensionConsent.student_id)).all()

def unanimous(session,item):
    rows=consents(session,item)
    return bool(rows) and all(row.decision=="AGREE" for row in rows)

def can_see(session,user,item):
    thesis=session.get(m.Thesis,item.thesis_id)
    return c.head(session,user,thesis) or c.manager(session,user,thesis) or str(user.id)==item.snapshot["advisor_user_id"] or any(
        member["user_id"]==str(user.id) for member in item.snapshot["members"])

def announce(session,actor,item,event,message,pending_only=False):
    ids={UUID(row["user_id"]) for row in item.snapshot["members"]}
    if pending_only:
        waiting={str(row.student_id) for row in consents(session,item) if row.decision=="PENDING"}
        ids={UUID(row["user_id"]) for row in item.snapshot["members"] if row["student_id"] in waiting}
    else:
        ids.add(UUID(item.snapshot["advisor_user_id"]))
        thesis=session.get(m.Thesis,item.thesis_id)
        ids |= c.notices.department_heads(session,thesis.department_id)
    for recipient in ids:
        c.notices.emit(session,actor.id or item.requested_by,{recipient},event,"account",recipient,message,
            f"/changes?thesis={item.thesis_id}&extension={item.id}",include_actor=actor.id is None)

def expire(session,item):
    if item.state=="SUBMITTED" and item.consent_due_at and item.consent_due_at<=c.now() and not unanimous(session,item):
        item.state,item.row_version="EXPIRED",item.row_version+1
        system=SimpleNamespace(id=None)
        c.audit(session,system,"THESIS_EXTENSION_EXPIRED","thesis_extension_request",item.id,
            "Hết hạn xác nhận đồng thuận; hồ sơ tham gia KLTN không thay đổi")
        announce(session,system,item,"THESIS_EXTENSION_EXPIRED","Yêu cầu gia hạn hết hạn xác nhận. Hồ sơ KLTN của các thành viên vẫn giữ nguyên.")
        return True
    return False

def defense_outcome(session, item):
    extension = session.get(m.ThesisExtension, item.extension_id) if item.extension_id else None
    if not extension:
        return {"status": "NOT_APPROVED", "message": "", "starts_at": None, "ends_at": None}
    thesis = session.get(m.Thesis, item.thesis_id)
    slots = session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.thesis_id == item.thesis_id)
        .order_by(m.DefenseSlot.starts_at.desc(), m.DefenseSlot.id)).all()
    valid_slots = [slot for slot in slots if slot.starts_at >= item.extension_starts_at and slot.ends_at <= extension.until_at]
    slot = next(iter(valid_slots or slots), None)
    info = {"starts_at": slot.starts_at if slot else None, "ends_at": slot.ends_at if slot else None}
    if thesis.state in {"DEFENDED", "COMPLETED"} or (slot and slot.finalized_at and all(s.finalized_at for s in slots)):
        return {**info, "status": "COMPLETED", "message": "Đã ghi nhận kết quả phiên bảo vệ."}
    if thesis.state == "WITHDRAWN":
        return {**info, "status": "WITHDRAWN", "message": "Khóa luận đã kết thúc theo thủ tục xin thôi."}
    valid = False
    if slot:
        try:
            validate_defense_window(item.extension_starts_at, extension.until_at, slot.starts_at, slot.ends_at)
            valid = True
        except HTTPException:
            pass
    if item.state == "EXPIRED" or (c.now() > extension.until_at and not valid):
        return {**info, "status": "NOT_PASSED", "message": "Không đạt: hết hạn gia hạn mà không có lịch bảo vệ hợp lệ trong thời hạn được duyệt."}
    if c.now() > extension.until_at:
        return {**info, "status": "PENDING_RESULT", "message": "Có lịch bảo vệ trong hạn. Chờ Thư ký/Chủ tịch đối chiếu và chốt kết quả thực tế; không tự kết luận không đạt do nhập kết quả muộn."}
    return {**info, "status": "SCHEDULED" if valid else "WAITING", "message":
        "Đã xếp lịch bảo vệ trong thời hạn gia hạn." if valid else "Đã có hạn gia hạn. Khoa chưa xếp lịch bảo vệ phù hợp; theo dõi thông báo xếp lịch trong thời hạn được duyệt."}


def expire_without_council(session,item):
    if item.state != "APPROVED" or not item.extension_id:
        return False
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == item.thesis_id).with_for_update())
    item = session.scalar(select(m.ThesisExtensionRequest).where(m.ThesisExtensionRequest.id == item.id)
        .with_for_update().execution_options(populate_existing=True))
    if item.state != "APPROVED" or defense_outcome(session, item)["status"] != "NOT_PASSED":
        return False
    extension = session.get(m.ThesisExtension, item.extension_id)
    message = defense_outcome(session, item)["message"]
    # Preserve the official approval, actor, date and reason; the expiry is a separate audit event.
    item.state = "EXPIRED"
    item.row_version += 1
    thesis.state, thesis.row_version = "ARCHIVED", thesis.row_version + 1
    system = SimpleNamespace(id=None)
    c.audit(session, system, "THESIS_EXTENSION_NOT_PASSED", "thesis", thesis.id, message,
        source_reference=extension.reference)
    announce(session, system, item, "THESIS_EXTENSION_NOT_PASSED", message)
    return True

def locked(session,user,identifier,expected):
    visible=session.get(m.ThesisExtensionRequest,identifier)
    if not visible or not can_see(session,user,visible):raise HTTPException(404,"Không tìm thấy yêu cầu gia hạn trong phạm vi của bạn")
    thesis=session.scalar(select(m.Thesis).where(m.Thesis.id==visible.thesis_id).with_for_update())
    item=session.scalar(select(m.ThesisExtensionRequest).where(m.ThesisExtensionRequest.id==identifier).with_for_update())
    if expire(session,item):
        session.commit()
        raise HTTPException(409,"Yêu cầu đã hết hạn lấy ý kiến; hồ sơ KLTN không bị hủy")
    c.row_version(expected,item.row_version)
    if item.state not in OPEN:raise HTTPException(409,"Yêu cầu gia hạn đã kết thúc. Hãy làm mới dữ liệu")
    return item,thesis

def fresh(session,item,thesis):
    c.mutable(session,thesis,allow_ready=True)
    before=item.snapshot
    current=c.snapshot(session,thesis)
    for key in ("topic_id","title","advisor_assignment_id","members"):
        if before[key]!=current[key]:raise HTTPException(409,"Nhóm, đề tài hoặc GVHD đã thay đổi; hủy yêu cầu cũ và lập lại")
    ids=[UUID(row["student_id"]) for row in before["members"]]
    if c.confirmed_student_ids(session,thesis.round_id,ids)!=set(ids):
        raise HTTPException(409,"Có thành viên không còn quyền tham gia đợt; cần Khoa đối chiếu")
    if c.open_request(session,thesis):raise HTTPException(409,"Đang có yêu cầu đổi đề tài chờ xử lý")
    if c.extension_for(session,thesis):raise HTTPException(409,"Khóa luận đã được gia hạn một lần")

def finish(session,user,item,event,message):
    item.row_version+=1
    c.audit(session,user,event,"thesis_extension_request",item.id,message)
    announce(session,user,item,event,message)
    session.commit()
    return output(session,user,item)

def create(session,user,thesis_id,data,expected):
    thesis=c.thesis_access(session,user,thesis_id,action="extension:request",lock=True,write=True)
    c.row_version(expected,thesis.row_version)
    c.mutable(session,thesis,allow_ready=True)
    if pending(session,thesis.id) or c.open_request(session,thesis):raise HTTPException(409,"Nhóm đang có yêu cầu gia hạn hoặc đổi đề tài chờ xử lý")
    if c.extension_for(session,thesis):raise HTTPException(409,"Khóa luận đã được gia hạn một lần")
    baseline=session.scalar(select(m.DocumentDeadline).where(m.DocumentDeadline.round_id==thesis.round_id,
        m.DocumentDeadline.document_type=="REPORT").with_for_update())
    if not baseline:raise HTTPException(409,"Khoa chưa thiết lập hạn hoàn thành báo cáo của đợt")
    if data.until_at and (data.until_at<=baseline.due_at or data.until_at<=c.now()):raise HTTPException(422,"Hạn đề nghị phải sau hạn báo cáo và sau thời điểm hiện tại")
    before=c.snapshot(session,thesis)
    ids=[UUID(row["student_id"]) for row in before["members"]]
    if c.confirmed_student_ids(session,thesis.round_id,ids)!=set(ids):raise HTTPException(409,"Các thành viên cần có quyền tham gia đợt còn hiệu lực")
    item=m.ThesisExtensionRequest(thesis_id=thesis.id,requested_by=user.id,original_due_at=baseline.due_at,
        requested_until_at=data.until_at,reason=data.reason,snapshot=before,state="SUBMITTED",submitted_at=c.now())
    session.add(item);session.flush()
    for row in before["members"]:
        own=row["user_id"]==str(user.id)
        session.add(m.ThesisExtensionConsent(request_id=item.id,student_id=UUID(row["student_id"]),
            decision="AGREE" if own else "PENDING",responded_by=user.id if own else None,responded_at=c.now() if own else None))
    session.flush()
    return finish(session,user,item,"THESIS_EXTENSION_SUBMITTED","Đã gửi yêu cầu gia hạn. Các thành viên cần tự xác nhận; hồ sơ KLTN hiện tại vẫn giữ nguyên.")

def consent(session,user,identifier,data,expected):
    item,thesis=locked(session,user,identifier,expected);fresh(session,item,thesis)
    student=c.profile(session,user,"STUDENT")
    row=session.scalar(select(m.ThesisExtensionConsent).where(m.ThesisExtensionConsent.request_id==item.id,
        m.ThesisExtensionConsent.student_id==student.id).with_for_update())
    if not row:raise HTTPException(403,"Chỉ thành viên của nhóm tại thời điểm gửi tự xác nhận")
    if row.decision!="PENDING":raise HTTPException(409,"Bạn đã xác nhận yêu cầu này")
    row.decision,row.responded_by,row.responded_at=data.decision,user.id,c.now()
    if data.decision=="DECLINE":
        item.state,item.decided_by,item.decided_at,item.decision_reason="REJECTED",user.id,c.now(),"Có thành viên không đồng ý gia hạn nhóm"
    session.flush()
    return finish(session,user,item,"THESIS_EXTENSION_CONSENT","Thành viên đã "+("đồng ý gia hạn." if data.decision=="AGREE" else "không đồng ý; yêu cầu nhóm kết thúc, hồ sơ KLTN không bị hủy."))

def review(session,user,identifier,data,expected):
    item,thesis=locked(session,user,identifier,expected);fresh(session,item,thesis)
    if str(user.id)!=item.snapshot["advisor_user_id"]:raise HTTPException(403,"Chỉ GVHD hiện tại cho ý kiến gia hạn")
    if not unanimous(session,item):raise HTTPException(409,"Cần tất cả thành viên đồng ý trước khi GVHD xem xét")
    if item.advisor_reviewed_at:raise HTTPException(409,"GVHD đã ghi ý kiến")
    item.advisor_reviewed_by,item.advisor_reviewed_at,item.advisor_reason=user.id,c.now(),data.reason
    item.state="ADVISOR_REVIEWED" if data.decision=="AGREE" else "REJECTED"
    if data.decision!="AGREE":item.decided_by,item.decided_at,item.decision_reason=user.id,c.now(),data.reason
    return finish(session,user,item,"THESIS_EXTENSION_REVIEWED","GVHD "+("đồng ý, chuyển TBM xét. " if data.decision=="AGREE" else "không đồng ý. ")+data.reason)

def decision(session,user,identifier,data,expected):
    item,thesis=locked(session,user,identifier,expected)
    if not c.head(session,user,thesis):raise HTTPException(403,"Chỉ Trưởng bộ môn đúng phạm vi quyết định yêu cầu gia hạn")
    if data.decision=="APPROVE":
        fresh(session,item,thesis)
        if not unanimous(session,item) or item.state!="ADVISOR_REVIEWED":raise HTTPException(409,"Chưa đủ đồng thuận nhóm và ý kiến đồng ý của GVHD")
        if not (data.confirm_decision and data.extension_starts_at and data.until_at and data.decision_on and data.reference):
            raise HTTPException(422,"Cần ngày bắt đầu gia hạn, hạn mới, ngày quyết định, căn cứ và xác nhận đã đối chiếu quyết định")
        start,until=data.extension_starts_at.astimezone(c.VN),data.until_at.astimezone(c.VN)
        if start<thesis.created_at or until<=start or until<=item.original_due_at or until<=c.now() or until>maximum_until(start):
            raise HTTPException(422,"Hạn mới phải sau hạn cũ và hiện tại, nằm trong thời hạn tối đa 5 tháng theo quyết định")
        if not thesis.created_at.astimezone(c.VN).date()<=data.decision_on<=c.now().astimezone(c.VN).date():raise HTTPException(422,"Ngày quyết định phải từ ngày lập khóa luận đến hôm nay")
        if session.scalar(select(m.DefenseSlot.id).where(m.DefenseSlot.thesis_id == thesis.id)):
            raise HTTPException(409, "Đề tài đã có lịch bảo vệ. Cần hủy lịch chưa diễn ra hoặc đối chiếu phiên đã có dữ liệu trước khi ghi nhận gia hạn")
        record=m.ThesisExtension(thesis_id=thesis.id,original_due_at=item.original_due_at,until_at=until,
            decision_on=data.decision_on,reference=data.reference,reason=data.reason,recorded_by=user.id,recorded_at=c.now())
        session.add(record);session.flush()
        item.extension_id,item.extension_starts_at=record.id,start
        thesis.state,thesis.row_version="EXTENDED",thesis.row_version+1
        item.state="APPROVED"
        c.audit(session,user,"THESIS_EXTENSION_RECORDED","thesis",thesis.id,
            f"Bắt đầu theo quyết định {start.isoformat()}; hạn cũ {item.original_due_at.isoformat()} → {until.isoformat()}",source_reference=data.reference)
    else:item.state="REJECTED"
    item.decided_by,item.decided_at,item.decision_reason=user.id,c.now(),data.reason
    return finish(session,user,item,"THESIS_EXTENSION_"+item.state,
        ("TBM đồng ý và ghi nhận quyết định gia hạn. " if item.state=="APPROVED" else "TBM không đồng ý gia hạn. ")+data.reason)

def cancel(session,user,identifier,expected):
    item,_=locked(session,user,identifier,expected)
    if item.requested_by!=user.id:raise HTTPException(403,"Chỉ người gửi hủy yêu cầu còn chờ")
    item.state="CANCELLED"
    return finish(session,user,item,"THESIS_EXTENSION_CANCELLED","Người gửi đã hủy yêu cầu gia hạn; hồ sơ KLTN vẫn giữ nguyên.")

def manage_consent(session,user,identifier,data,expected):
    item,thesis=locked(session,user,identifier,expected)
    if not c.manager(session,user,thesis):raise HTTPException(403,"Chỉ TBM hoặc điều phối của đợt quản lý hạn lấy ý kiến")
    if unanimous(session,item):raise HTTPException(409,"Các thành viên đã đồng thuận; chuyển GVHD xem xét")
    if data.due_at:
        if data.due_at<=c.now():raise HTTPException(422,"Hạn xác nhận phải ở tương lai")
        item.consent_due_at=data.due_at
    item.row_version+=1
    c.audit(session,user,"THESIS_EXTENSION_CONSENT_DEADLINE","thesis_extension_request",item.id,data.reason)
    announce(session,user,item,"THESIS_EXTENSION_REMINDER","Nhóm đang chờ bạn xác nhận yêu cầu gia hạn KLTN."+
        (f" Hạn xác nhận: {item.consent_due_at.astimezone(c.VN):%d/%m/%Y %H:%M}." if item.consent_due_at else ""),pending_only=True)
    session.commit()
    return output(session,user,item)

def output(session,user,item):
    thesis=session.get(m.Thesis,item.thesis_id)
    rows={str(row.student_id):row for row in consents(session,item)}
    everyone=unanimous(session,item);opened=item.state in OPEN
    return {"id":item.id,"thesis_id":item.thesis_id,"title":item.snapshot["title"],"state":item.state,"row_version":item.row_version,
        "advisor_name":c.request_advisor_name(session,item.snapshot),
        "reason":item.reason,"submitted_at":item.submitted_at,"original_due_at":item.original_due_at,
        "requested_until_at":item.requested_until_at,"consent_due_at":item.consent_due_at,
        "advisor_reason":item.advisor_reason,"decision_reason":item.decision_reason,"decided_at":item.decided_at,
        "extension_starts_at":item.extension_starts_at,"extension_until_at":session.get(m.ThesisExtension,item.extension_id).until_at if item.extension_id else None,
        "all_agreed":everyone,"defense":defense_outcome(session,item),"reference":session.get(m.ThesisExtension,item.extension_id).reference if item.extension_id else None,
        "members":[{"student_id":row["student_id"],"name":row["name"],"user_id":row["user_id"],
            "decision":rows[row["student_id"]].decision,"responded_at":rows[row["student_id"]].responded_at} for row in item.snapshot["members"]],
        "can_consent":opened and any(row["user_id"]==str(user.id) and rows[row["student_id"]].decision=="PENDING" for row in item.snapshot["members"]),
        "can_review":opened and everyone and not item.advisor_reviewed_at and str(user.id)==item.snapshot["advisor_user_id"],
        "can_decide":opened and c.head(session,user,thesis),"can_cancel":opened and item.requested_by==user.id,
        "can_manage_consent":opened and not everyone and c.manager(session,user,thesis)}

def listing(session,user,thesis_ids):
    key=str(user.id)
    query=select(m.ThesisExtensionRequest).where((m.ThesisExtensionRequest.thesis_id.in_(thesis_ids)) |
        (m.ThesisExtensionRequest.requested_by==user.id) |
        (m.ThesisExtensionRequest.snapshot['members'].contains([{'user_id':key}])))
    items=[];changed=False
    for item in session.scalars(query.order_by(m.ThesisExtensionRequest.submitted_at.desc()).execution_options(populate_existing=True)):
        if not can_see(session,user,item):continue
        session.scalar(select(m.Thesis.id).where(m.Thesis.id == item.thesis_id).with_for_update())
        item=session.scalar(select(m.ThesisExtensionRequest).where(m.ThesisExtensionRequest.id == item.id)
            .with_for_update().execution_options(populate_existing=True))
        changed=expire(session,item) or changed
        changed=expire_without_council(session,item) or changed
        items.append(output(session,user,item))
    if changed:session.commit()
    return items


def process_expired(session):
    rows=session.scalars(select(m.ThesisExtensionRequest).where(m.ThesisExtensionRequest.state=="SUBMITTED",
        m.ThesisExtensionRequest.consent_due_at.is_not(None),m.ThesisExtensionRequest.consent_due_at<=c.now())
        .order_by(m.ThesisExtensionRequest.consent_due_at).limit(100).with_for_update(skip_locked=True)).all()
    for item in rows:expire(session,item)
    # Valid scheduled sessions await reconciliation, not repeated failure jobs.
    protected_session = select(m.DefenseSlot.id).where(
        m.DefenseSlot.thesis_id == m.ThesisExtensionRequest.thesis_id,
        or_(m.DefenseSlot.finalized_at.is_not(None), and_(
            m.DefenseSlot.starts_at >= m.ThesisExtensionRequest.extension_starts_at,
            m.DefenseSlot.ends_at <= m.ThesisExtension.until_at))).exists()
    approved=session.scalars(select(m.ThesisExtensionRequest)
        .join(m.ThesisExtension, m.ThesisExtension.id == m.ThesisExtensionRequest.extension_id)
        .join(m.Thesis, m.Thesis.id == m.ThesisExtensionRequest.thesis_id)
        .where(m.ThesisExtensionRequest.state == "APPROVED", m.ThesisExtension.until_at < c.now(),
            m.Thesis.state.not_in(["DEFENDED", "COMPLETED", "WITHDRAWN"]), ~protected_session)
        .order_by(m.ThesisExtension.until_at, m.ThesisExtensionRequest.id).limit(100)).all()
    for item in approved:expire_without_council(session,item)


def sweep_expired():
    from sqlalchemy.orm import Session
    from backend.api.dependencies import get_engine
    with Session(get_engine()) as session:
        process_expired(session)
        session.commit()
