from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import func, select

from backend.db.models import entities as m
from backend.services import evaluation, workflow_notices as notices
from backend.services.registration import _is_department_head, row_version
from backend.services.theses import audit, now, primary_advisor, resource_role

VN = ZoneInfo("Asia/Ho_Chi_Minh")
CRITERIA = (
    ('1.1', 'Chuyên cần', '1.0'),
    ('1.2', 'Cấu trúc khóa luận/đồ án hợp lý, bố cục chặt chẽ, rõ ràng, trình bày theo đúng quy định. Đúng kỹ thuật soạn thảo văn bản, không có dấu hiệu đạo văn.', '0.5'),
    ('1.3', 'Trích dẫn và trình bày tài liệu tham khảo, hình vẽ, bảng biểu rõ ràng, đúng quy định, không có lỗi chính tả, không lỗi in ấn.', '0.5'),
    ('2.1', 'Nêu được tính cấp thiết của đề tài, làm rõ tổng quan các công trình nghiên cứu, xác định mục đích, nhiệm vụ, đối tượng, phạm vi, nghiên cứu rõ ràng, hợp lý.', '0.5'),
    ('2.2', 'Nội dung nghiên cứu: Khối lượng công việc hợp lí; tư liệu phong phú, chính xác, phù hợp mục đích nghiên cứu.', '0.5'),
    ('2.3', 'Phương pháp nghiên cứu: Biết vận dụng các phương pháp nghiên cứu phù hợp với nội dung nghiên cứu của đề tài; trình bày nội dung có hệ thống khoa học, logic.', '1.0'),
    ('2.4', 'Khả năng áp dụng các giải thuật hiệu quả, số liệu chính xác; Khả năng giải quyết vấn đề, đầy đủ minh chứng khoa học; Khả năng suy luận, phân tích, tổng hợp tốt; có khả năng sáng tạo.', '1.0'),
    ('2.5', 'Kết quả nghiên cứu: - Nêu được kết quả đạt được phù hợp với mục tiêu nghiên cứu của đề tài; - Kết quả có giá trị về mặt lý luận và thực tiễn khoa học; - Có đánh giá, nhận xét kết quả, dự đoán tương lai (nếu cần).', '0.5'),
    ('2.6', 'Kết luận, kiến nghị phù hợp với nội dung nghiên cứu.', '0.5'),
    ('3.1', 'Demo không có lỗi, không vi phạm luật an ninh mạng/luật sở hữu trí tuệ; Có quy trình sử dụng/hướng dẫn sử dụng rõ ràng; Có triển khai, có khả năng ứng dụng.', '1.0'),
    ('3.2', 'Giao diện thân thiện, hợp lý; Các chức năng đáp ứng được yêu cầu của đề tài; Độ tin cậy, độ tương thích; Tốc độ, bảo mật, chi phí hợp lý.', '2.0'),
    ('3.3', 'Thuyết trình lưu loát, slide trình chiếu rõ ràng, có sáng tạo; Trả lời đúng, đáp ứng được yêu cầu các câu hỏi đặt ra.', '1.0'),
)
ROLES = {"CHAIR":"Chủ tịch","SECRETARY":"Thư ký","REVIEWER":"Phản biện Hội đồng","MEMBER":"Ủy viên"}


def lecturer_for(session, user):
    return session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == user.id)) if user.base_role == "LECTURER" else None


def manages(session, user, lecturer, round_id, department_id):
    if not lecturer:
        return False
    if _is_department_head(session, lecturer.id, department_id):
        return True
    if not resource_role(session, user.id, "KLTN_COORDINATOR", round_id=round_id):
        return False
    home = session.get(m.Department, lecturer.department_id) if lecturer.department_id else None
    target = session.get(m.Department, department_id)
    round_ = session.get(m.ThesisRound, round_id)
    if not home or not target or not round_:
        return False
    if round_.code == "SYN-DEMO":
        return council_faculty_id(session, home) == council_faculty_id(session, target)
    return not demo_department(home.code) and home.faculty_id == target.faculty_id


def demo_department(code):
    return code == "SYN-DEMO-DEP"


def council_faculty_id(session, department):
    if demo_department(department.code):
        faculty_id = session.scalar(select(m.Faculty.id).where(m.Faculty.code == "KHOA-CNKT"))
        if faculty_id:
            return faculty_id
    return department.faculty_id


def valid_council_scope(round_, department):
    return round_.code == "SYN-DEMO" or not demo_department(department.code)


def supervising_ids(session, thesis_id):
    from backend.services.theses import effective
    return set(session.scalars(select(m.AdvisorAssignment.lecturer_id).where(
        m.AdvisorAssignment.thesis_id == thesis_id, effective(m.AdvisorAssignment))))


def check_supervision_conflict(session, thesis, lecturer_ids):
    if lecturer_ids & supervising_ids(session, thesis.id):
        raise HTTPException(409, f"GVHD không được chấm đề tài mình hướng dẫn: {thesis.current_title}")


def membership(council, lecturer):
    return next((member for member in council.members if lecturer and member["id"] == str(lecturer.id)), None)


def student_for(session, user):
    return session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == user.id)) if user.base_role == "STUDENT" else None


def manage_council(session, user, data, identifier=None, signature=None):
    lecturer = lecturer_for(session, user)
    if not manages(session, user, lecturer, data.round_id, data.department_id):
        raise HTTPException(403, "Chỉ TBM hoặc điều phối được giao mới được lập hội đồng")
    round_ = session.get(m.ThesisRound, data.round_id)
    department = session.get(m.Department, data.department_id)
    if not round_ or round_.state == "ARCHIVED" or not department or not department.active:
        raise HTTPException(409, "Đợt hoặc bộ môn không còn khả dụng")
    if not valid_council_scope(round_, department):
        raise HTTPException(422, "Bộ môn giả lập chỉ dùng trong đợt SYN-DEMO")
    roles = [member.role for member in data.members]
    ids = {member.lecturer_id for member in data.members}
    if len(ids) != 5 or sorted(roles) != sorted(["CHAIR","SECRETARY","REVIEWER","REVIEWER","MEMBER"]):
        raise HTTPException(422, "Hội đồng gồm 5 người khác nhau: chủ tịch, thư ký, hai phản biện và một ủy viên")
    found = {row.id: (row.display_name, faculty_id, code) for row, faculty_id, code in session.execute(
        select(m.LecturerProfile, m.Department.faculty_id, m.Department.code)
        .join(m.UserAccount, m.UserAccount.id == m.LecturerProfile.user_id)
        .outerjoin(m.Department, m.Department.id == m.LecturerProfile.department_id)
        .where(m.LecturerProfile.id.in_(ids), m.UserAccount.status == "ACTIVE", m.UserAccount.base_role == "LECTURER"))}
    if ids != found.keys():
        raise HTTPException(422, "Có tài khoản giảng viên không hoạt động")
    if round_.code != "SYN-DEMO" and any(demo_department(code) for _, _, code in found.values()):
        raise HTTPException(422, "Tài khoản thuộc bộ môn giả lập chỉ tham gia hội đồng demo")
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    existing=session.get(m.DefenseCouncil,identifier) if identifier else None
    slots=[]
    if identifier:
        if not existing or (existing.round_id,existing.department_id)!=(data.round_id,data.department_id):
            raise HTTPException(404,"Không tìm thấy hội đồng trong phạm vi này")
        if signature!=council_signature(existing):
            raise HTTPException(409,"Hội đồng đã được cập nhật. Làm mới để đối chiếu trước khi sửa")
        slots=session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.council_id==identifier).order_by(m.DefenseSlot.id).with_for_update()).all()
        if existing.closed_at or any(s.finalized_at or s.marks or meeting_started(s) or s.minutes for s in slots):
            raise HTTPException(409,"Chỉ sửa thành phần trước khi nhập dữ liệu buổi bảo vệ")
    if data.thesis_ids and not data.confirmed_no_conflict:
        raise HTTPException(422, "Cần xác nhận đã đối chiếu quan hệ thân nhân trước khi lập hội đồng")
    if len(set(data.thesis_ids)) != len(data.thesis_ids):
        raise HTTPException(422, "Danh sách đề tài đối chiếu có mục trùng")
    for thesis_id in sorted(data.thesis_ids):
        thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == thesis_id).with_for_update())
        if not thesis or (thesis.round_id, thesis.department_id) != (data.round_id, data.department_id) or thesis.state == "WITHDRAWN":
            raise HTTPException(422, "Đề tài đối chiếu phải còn hiệu lực trong đúng đợt và bộ môn")
        check_supervision_conflict(session, thesis, ids)
    reference_faculty_id = council_faculty_id(session, department)
    guests = {member_id for member_id, (_, faculty_id, code) in found.items()
        if faculty_id != reference_faculty_id and not (round_.code == "SYN-DEMO" and demo_department(code))}
    if guests and not data.confirmed_guests:
        raise HTTPException(422, "Cần xác nhận quyết định có ghi các thành viên được mời ngoài Khoa")
    member_records = []
    for member in data.members:
        record = {"id":str(member.lecturer_id), "name":found[member.lecturer_id][0], "role":member.role}
        if member.lecturer_id in guests:
            record["invitation_reference"] = data.reference
        member_records.append(record)
    if session.scalar(select(m.DefenseCouncil.id).where(m.DefenseCouncil.round_id == data.round_id,
            m.DefenseCouncil.department_id == data.department_id, m.DefenseCouncil.name == data.name,
            m.DefenseCouncil.id != identifier if identifier else True)):
        raise HTTPException(409, "Tên hội đồng đã tồn tại trong đợt và bộ môn")
    council = existing or m.DefenseCouncil(round_id=data.round_id, department_id=data.department_id, name=data.name,
        reference=data.reference, created_by=user.id, members=member_records)
    if existing:
        removed = {row["id"] for row in existing.members} - {row["id"] for row in member_records}
        audit(session,user,"DEFENSE_COUNCIL_BEFORE_REVISION","defense_council",existing.id,json.dumps(council_out(existing),default=str,ensure_ascii=False))
        council.name,council.reference=data.name,data.reference
        council.members=member_records
        for slot in slots:
            validate_ready(session,session.get(m.Thesis,slot.thesis_id),council,{r["id"] for r in slot.roster} if slot.prior_slot_id else None)
            for other,other_council in session.execute(select(m.DefenseSlot,m.DefenseCouncil).join(m.DefenseCouncil,m.DefenseSlot.council_id==m.DefenseCouncil.id).where(
                m.DefenseSlot.council_id!=council.id,m.DefenseSlot.starts_at<slot.ends_at,m.DefenseSlot.ends_at>slot.starts_at)):
                if ids.intersection(UUID(p["id"]) for p in other_council.members):
                    raise HTTPException(409,"Thành viên mới bị trùng lịch ở hội đồng khác")
            slot.row_version+=1
            notify(session,user,slot,council,"DEFENSE_COUNCIL_REVISED","Đã cập nhật hội đồng bảo vệ")
            notify_removed(session, user, lecturer_accounts(session, removed), "Bạn đã được rút khỏi hội đồng của lịch này")
    session.add(council)
    session.flush()
    detail = f"Đã đối chiếu {len(data.thesis_ids)} đề tài. Xác nhận quan hệ thân nhân: {'Có' if data.confirmed_no_conflict else 'Chưa ghi nhận'}."
    audit(session, user, "DEFENSE_COUNCIL_REVISED" if existing else "DEFENSE_COUNCIL_CREATED", "defense_council", council.id, detail, source_reference=data.reference)
    session.commit()
    return {"id":council.id}


def meeting_started(slot):
    return bool(slot.attendance.get("_council") or any(
        isinstance(value, dict) and value.get("status") for value in slot.attendance.values()))


def load_slot(session, user, identifier, *, write=False):
    query = select(m.DefenseSlot).where(m.DefenseSlot.id == identifier)
    slot = session.scalar(query.with_for_update().execution_options(populate_existing=True) if write else query)
    if not slot:
        raise HTTPException(404, "Không tìm thấy lịch bảo vệ")
    council = session.get(m.DefenseCouncil, slot.council_id)
    lecturer, student = lecturer_for(session, user), student_for(session, user)
    member = membership(council, lecturer)
    own = next((row for row in slot.roster if student and row["student_id"] == str(student.id)), None)
    manager = manages(session, user, lecturer, council.round_id, council.department_id)
    if not (member or own or manager):
        raise HTTPException(404, "Không tìm thấy lịch bảo vệ trong phạm vi của bạn")
    return slot, council, member, own, manager


def thesis_state_allows_schedule(thesis, extension):
    return thesis.state == "READY_FOR_DEFENSE" or (thesis.state == "EXTENDED" and extension is not None)


def validate_ready(session, thesis, council, member_ids=None):
    if (thesis.round_id, thesis.department_id) != (council.round_id, council.department_id):
        raise HTTPException(422, "Đề tài và hội đồng phải cùng đợt và bộ môn")
    round_ = session.get(m.ThesisRound, council.round_id)
    department = session.get(m.Department, council.department_id)
    if not department.active or round_.state == "ARCHIVED" or not valid_council_scope(round_, department):
        raise HTTPException(409, "Đợt hoặc bộ môn của hội đồng không còn phù hợp để bảo vệ")
    active = evaluation.members(session, thesis)
    if member_ids is not None:
        active=[row for row in active if str(row.id) in member_ids]
    report = evaluation.report(session, thesis)
    extension = session.scalar(select(m.ThesisExtension).where(m.ThesisExtension.thesis_id == thesis.id))
    if not active or not report or not (thesis_state_allows_schedule(thesis, extension) or (member_ids is not None and thesis.state=="DEFENDED")) or any(
        evaluation.eligibility_out(session, thesis, row, report)["state"] != "ELIGIBLE" for row in active):
        raise HTTPException(409, "Đề tài cần được chốt đủ điều kiện trên phiên bản báo cáo hiện tại")
    check_supervision_conflict(session, thesis, {UUID(row["id"]) for row in council.members})
    if evaluation.pending_reviewer_forms(session,thesis,report):
        raise HTTPException(409,"Cần đủ Mẫu 8 của tất cả giảng viên phản biện đang được phân công cho từng SV trên bản báo cáo hiện tại")
    return active, report


def validate_extension_window(extension, request, starts_at, ends_at):
    if not extension:
        return
    from backend.services.extension_policy import validate_defense_window
    validate_defense_window(request.extension_starts_at if request else None,
        extension.until_at, starts_at, ends_at)


def schedule(session, user, data, identifier=None, expected=None, *, commit=True):
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    slot = None
    old_council = None
    thesis_ids = {data.thesis_id}
    if identifier:
        original, _, _, _, old_manager = load_slot(session, user, identifier)
        if not old_manager:
            raise HTTPException(403, "Bạn không quản lý lịch này")
        thesis_ids.add(original.thesis_id)
    locked_theses = {t.id: t for t in session.scalars(select(m.Thesis)
        .where(m.Thesis.id.in_(thesis_ids)).order_by(m.Thesis.id).with_for_update())}
    if identifier:
        slot, old_council, _, _, old_manager = load_slot(session, user, identifier, write=True)
        if not old_manager:
            raise HTTPException(403, "Bạn không quản lý lịch này")
        row_version(expected, slot.row_version)
        if not schedule_editable(slot, old_council):
            raise HTTPException(409, "Chỉ đổi lịch trước khi ghi nhận buổi bảo vệ và khi hội đồng còn mở")
        if slot.prior_slot_id and slot.thesis_id != data.thesis_id:
            raise HTTPException(422, "Phiên bảo vệ bổ sung phải giữ nguyên đề tài và sinh viên đã được Khoa cho phép")
    council = session.get(m.DefenseCouncil, data.council_id)
    thesis = locked_theses.get(data.thesis_id)
    if not council or not thesis or not manages(session,user,lecturer_for(session,user),council.round_id,council.department_id):
        raise HTTPException(404, "Không tìm thấy hội đồng hoặc đề tài trong phạm vi quản lý")
    if council.closed_at:
        raise HTTPException(409, "Hội đồng đã khóa bảng điểm")
    if (not slot or slot.thesis_id!=thesis.id or slot.council_id!=council.id) and not data.confirmed_no_conflict:
        raise HTTPException(422,"Cần đối chiếu quan hệ thân nhân giữa thành viên hội đồng và SV trong đề tài trước khi xếp lịch")
    if data.ends_at <= data.starts_at:
        raise HTTPException(422, "Giờ kết thúc phải sau giờ bắt đầu")
    if data.arrival_at and (data.arrival_at>data.starts_at or data.arrival_at.astimezone(VN).date()!=data.starts_at.astimezone(VN).date()):
        raise HTTPException(422,"Giờ tập trung phải cùng ngày và không muộn hơn giờ bảo vệ dự kiến")
    if not (slot.prior_slot_id if slot else data.prior_slot_id) and session.scalar(select(m.DefenseSlot.id).where(
            m.DefenseSlot.thesis_id == thesis.id, m.DefenseSlot.id != slot.id if slot else True).limit(1)):
        raise HTTPException(409, "Đề tài đã có lịch bảo vệ")
    prior_id=slot.prior_slot_id if slot else data.prior_slot_id
    chosen={str(row) for row in data.thesis_member_ids}
    if slot and prior_id:
        chosen={row["id"] for row in slot.roster}
    if prior_id:
        prior=session.get(m.DefenseSlot,prior_id)
        if not prior or prior.thesis_id!=thesis.id or not prior.finalized_at or not chosen or data.starts_at<prior.ends_at:
            raise HTTPException(422,"Chọn phiên đã chốt và SV được Khoa cho bảo vệ bổ sung; lịch phải sau phiên cũ")
        allowed={str(d.thesis_member_id) for d in session.scalars(select(m.DefenseAbsenceDecision).where(
            m.DefenseAbsenceDecision.slot_id==prior_id,m.DefenseAbsenceDecision.outcome=="SUPPLEMENTARY"))}
        if not chosen<=allowed or any(prior.attendance.get(key,{}).get("status")!="ABSENT" for key in chosen):
            raise HTTPException(409,"Chỉ xếp bổ sung cho SV vắng có quyết định cho phép của Khoa")
        for previous in session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.thesis_id==thesis.id)):
            if slot and previous.id==slot.id:continue
            if not previous.finalized_at or (previous.prior_slot_id==prior_id and chosen.intersection(r["id"] for r in previous.roster)):
                raise HTTPException(409,"Sinh viên đã có lịch bổ sung hoặc đề tài còn phiên chưa chốt")
    elif chosen:
        raise HTTPException(422,"Danh sách SV riêng chỉ dùng cho phiên bảo vệ bổ sung")
    active, report = validate_ready(session, thesis, council,chosen if prior_id else None)
    if prior_id and {str(row.id) for row in active}!=chosen:
        raise HTTPException(409,"Thành viên đã thay đổi, Khoa cần đối chiếu lại hồ sơ")
    extension=session.scalar(select(m.ThesisExtension).where(m.ThesisExtension.thesis_id==thesis.id))
    extension_request=session.scalar(select(m.ThesisExtensionRequest).where(
        m.ThesisExtensionRequest.extension_id==extension.id)) if extension else None
    validate_extension_window(extension,extension_request,data.starts_at,data.ends_at)
    lecturer_ids = {item["id"] for item in council.members}
    overlaps = session.execute(select(m.DefenseSlot, m.DefenseCouncil)
        .join(m.DefenseCouncil, m.DefenseCouncil.id == m.DefenseSlot.council_id)
        .where(m.DefenseSlot.starts_at < data.ends_at, m.DefenseSlot.ends_at > data.starts_at)).all()
    for other, other_council in overlaps:
        if slot and other.id == slot.id:
            continue
        if " ".join(other.room.casefold().split()) == " ".join(data.room.casefold().split()) or lecturer_ids.intersection(
                item["id"] for item in other_council.members):
            raise HTTPException(409, "Lịch trùng phòng hoặc trùng thành viên hội đồng")
    roster = []
    for member in active:
        student = session.get(m.StudentProfile, member.student_id)
        roster.append({"id":str(member.id),"student_id":str(student.id),"name":student.display_name,
            "code":student.student_code,"class_name":student.class_name or "", "major":student.major_code or ""})
    old_recipients = set()
    if slot:
        old_recipients = schedule_recipients(session, slot, old_council)
        old_title = locked_theses[slot.thesis_id].current_title
        audit(session, user, "DEFENSE_SCHEDULE_BEFORE_REVISION", "defense_slot", slot.id,
            json.dumps({"thesis_id": slot.thesis_id, "council_id": slot.council_id, "room": slot.room,
                "starts_at": slot.starts_at, "ends_at": slot.ends_at}, default=str, ensure_ascii=False))
        if slot.thesis_id != thesis.id:
            slot.attendance = {}
    if not slot:
        slot = m.DefenseSlot(thesis_id=thesis.id, prior_slot_id=prior_id, marks={}, attendance={}, minutes={})
        session.add(slot)
    else:
        slot.row_version += 1
    slot.thesis_id, slot.council_id, slot.report_version_id = thesis.id, council.id, report.id
    slot.starts_at, slot.ends_at, slot.room, slot.roster = data.starts_at, data.ends_at, data.room, roster
    slot.arrival_at=data.arrival_at
    session.flush()
    from backend.services.publications import sync_slot
    sync_slot(session, slot)
    event = "DEFENSE_RESCHEDULED" if identifier else "DEFENSE_SCHEDULED"
    audit(session,user,event,"defense_slot",slot.id,data.room)
    notify(session,user,slot,council,event,"Lịch bảo vệ đã thay đổi" if identifier else "Đã xếp lịch bảo vệ")
    if identifier:
        notify_removed(session, user, old_recipients - schedule_recipients(session, slot, council),
            f"Bạn không còn được xếp trong lịch bảo vệ đã thay đổi · {old_title}")
    if commit:
        session.commit()
    return {"id":slot.id}


def schedule_batch(session, user, data):
    if len({item.council_id for item in data.slots}) != 1 or any(item.prior_slot_id for item in data.slots):
        raise HTTPException(422, "Xếp liên tiếp dành cho một hội đồng và các phiên bảo vệ chính")
    if len({item.thesis_id for item in data.slots}) != len(data.slots):
        raise HTTPException(422, "Danh sách xếp lịch có đề tài trùng")
    try:
        result = [schedule(session,user,item,commit=False) for item in data.slots]
        session.commit()
        return {"slots": result}
    except Exception:
        session.rollback()
        raise


def apply_shared_arrival(session,user,council_id,data):
    from backend.api.defense_schemas import SlotInput
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    if len({row.id for row in data.slots})!=len(data.slots):raise HTTPException(422,'Danh sách lịch bị trùng')
    try:
        for row in data.slots:
            slot=session.get(m.DefenseSlot,row.id)
            if not slot or slot.council_id!=council_id:raise HTTPException(404,'Lịch không thuộc hội đồng đã chọn')
            item=SlotInput(council_id=council_id,thesis_id=slot.thesis_id,starts_at=slot.starts_at,ends_at=slot.ends_at,room=data.room or slot.room,arrival_at=data.arrival_at,confirmed_no_conflict=True,prior_slot_id=slot.prior_slot_id)
            schedule(session,user,item,slot.id,row.version,commit=False)
        session.commit()
    except Exception:
        session.rollback();raise


def lecturer_accounts(session, ids):
    return set(session.scalars(select(m.LecturerProfile.user_id).where(
        m.LecturerProfile.id.in_([UUID(value) for value in ids]))))


def schedule_recipients(session, slot, council):
    recipients = set(session.scalars(select(m.StudentProfile.user_id).where(
        m.StudentProfile.id.in_([UUID(row["student_id"]) for row in slot.roster]))))
    recipients |= lecturer_accounts(session, {row["id"] for row in council.members})
    recipients |= lecturer_accounts(session, {str(identifier) for identifier in supervising_ids(session, slot.thesis_id)})
    return recipients | notices.department_heads(session, council.department_id)


def notify(session, user, slot, council, event, message):
    thesis = session.get(m.Thesis, slot.thesis_id)
    starts = slot.starts_at.astimezone(VN)
    ends = slot.ends_at.astimezone(VN)
    council_accounts = lecturer_accounts(session, {row["id"] for row in council.members})
    student_accounts = set(session.scalars(select(m.StudentProfile.user_id).where(
        m.StudentProfile.id.in_([UUID(row["student_id"]) for row in slot.roster]))))
    participants = council_accounts | student_accounts
    schedule_event = event in {"DEFENSE_SCHEDULED", "DEFENSE_RESCHEDULED", "DEFENSE_CANCELLED", "DEFENSE_COUNCIL_REVISED"}
    recipients = schedule_recipients(session, slot, council) if schedule_event else participants
    correction_event = event.startswith("DEFENSE_CORRECTION_")
    if correction_event:
        recipients |= notices.department_heads(session, council.department_id)
    for recipient in recipients:
        url = "/defense" if event == "DEFENSE_CANCELLED" else (
            f"/defense?slot={slot.id}" if correction_event or recipient in participants else f"/theses/{thesis.id}")
        notices.emit(session,user.id,{recipient},event,"account",recipient,
            f"{message} · {thesis.current_title} · {council.name} · Tập trung {(slot.arrival_at or slot.starts_at).astimezone(VN):%d/%m/%Y %H:%M}; bảo vệ dự kiến {starts:%H:%M} → {ends:%H:%M} · {slot.room}",
            url)


def notify_removed(session, user, recipients, message):
    for recipient in recipients:
        notices.emit(session, user.id, {recipient}, "DEFENSE_ASSIGNMENT_REMOVED", "account", recipient,
            message, "/defense")


def schedule_editable(slot, council):
    return not (council.closed_at or slot.finalized_at or slot.marks or meeting_started(slot) or slot.minutes)


def cancel_schedule(session,user,identifier,expected,reason):
    slot,council,_,_,manager = load_slot(session,user,identifier,write=True)
    row_version(expected,slot.row_version)
    if not manager:
        raise HTTPException(403,"Bạn không quản lý lịch này")
    if not schedule_editable(slot, council):
        raise HTTPException(409,"Lịch đã có dữ liệu bảo vệ hoặc hội đồng đã khóa")
    audit(session,user,"DEFENSE_CANCELLED","defense_slot",slot.id,reason)
    notify(session,user,slot,council,"DEFENSE_CANCELLED","Đã hủy lịch bảo vệ")
    session.delete(slot)
    session.commit()


def edit(session, user, identifier, expected, *, secretary=False, independent=False):
    slot,council,member,_,_ = load_slot(session,user,identifier,write=True)
    if not independent:
        row_version(expected,slot.row_version)
    if not member or (secretary and member["role"] != "SECRETARY"):
        raise HTTPException(403,"Thao tác cần đúng vai trò được phân công trong hội đồng")
    if slot.finalized_at or council.closed_at:
        raise HTTPException(409,"Hồ sơ đã chốt")
    return slot,council,member


def student_id(slot, identifier):
    key = str(identifier)
    if not any(row["id"] == key for row in slot.roster):
        raise HTTPException(404,"Sinh viên không thuộc lịch bảo vệ này")
    return key


def save_marks(session,user,identifier,expected,data):
    independent=data.ballot_revision is not None
    slot,council,member = edit(session,user,identifier,expected,independent=independent)
    check_supervision_conflict(session, session.get(m.Thesis, slot.thesis_id),
        {UUID(row["id"]) for row in council.members})
    ensure_quorum(slot,council)
    from backend.services.publications import rows
    if any(r.state in {"SUBMITTED", "ADVISOR_CONFIRMED"} for r in rows(session, slot.thesis_id)):
        raise HTTPException(409,"Cần GVHD và TBM xử lý xong hồ sơ điểm thưởng trước khi chấm")
    if invalid_bonus(session, slot):
        raise HTTPException(409,"Cần đối chiếu mức thưởng đã được TBM duyệt trước khi chấm")
    student = student_id(slot,data.thesis_member_id)
    lecturer = str(data.lecturer_id)
    old=slot.marks.get(student,{}).get(lecturer,{})
    if independent and (data.context_token != context_token(slot,council) or data.ballot_revision != old.get("revision",0)):
        raise HTTPException(409,"Phiếu hoặc thành phần/điểm thưởng đã thay đổi. Nội dung đang nhập được giữ lại; hãy đối chiếu trước khi lưu lại.")
    if lecturer not in {row["id"] for row in council.members}:
        raise HTTPException(422,"Giảng viên không thuộc hội đồng")
    if lecturer not in slot.attendance["_council"]["present_ids"]:
        raise HTTPException(409,"Giảng viên vắng không được lập phiếu chấm")
    if lecturer != member["id"] and (member["role"] != "SECRETARY" or len(data.paper_entry_reason) < 5):
        raise HTTPException(403,"Chỉ thư ký được nhập hộ từ phiếu giấy và phải ghi căn cứ")
    if slot.attendance.get(student,{}).get("status") != "PRESENT":
        raise HTTPException(409,"Thư ký cần xác nhận sinh viên có mặt trước khi chấm")
    for score, (key,_,maximum) in zip(data.scores,CRITERIA):
        if not score.is_finite() or score < 0 or score > Decimal(maximum) or score != score.quantize(Decimal(".01")):
            raise HTTPException(422,f"Tiêu chí {key} cần điểm từ 0 đến {maximum}, tối đa 2 chữ số thập phân")
    marks = dict(slot.marks.get(student,{}))
    if old:
        audit(session,user,"DEFENSE_MARK_REVISED","defense_slot",slot.id,json.dumps({"student":student,"lecturer":lecturer,"previous":old},ensure_ascii=False))
    marks[lecturer] = {"scores":[str(value) for value in data.scores],"note":data.note,"revision":old.get("revision",0)+1,
        "recorded_at":now().isoformat(),"recorded_by":str(user.id),"paper_entry_reason":data.paper_entry_reason}
    slot.marks = {**slot.marks, student:marks}
    finish_edit(session,user,slot,"DEFENSE_MARK_SUBMITTED",f"{student} · {lecturer} · {data.paper_entry_reason}")


def save_attendance(session,user,identifier,expected,member_id,data):
    slot,council,_ = edit(session,user,identifier,expected,secretary=True)
    if now() < slot.starts_at:
        raise HTTPException(409,"Chưa đến giờ bảo vệ. Có thể đổi lịch trước khi mở phiên")
    ensure_quorum(slot,council)
    student = student_id(slot,member_id)
    if data.status == "ABSENT" and (len(data.reason) < 5 or slot.marks.get(student)):
        raise HTTPException(409,"Cần lý do vắng và sinh viên chưa được nhập điểm")
    old = slot.attendance.get(student,{})
    slot.attendance = {**slot.attendance,student:{**old,"status":data.status,"reason":data.reason}}
    finish_edit(session,user,slot,"DEFENSE_ATTENDANCE_RECORDED",f"{student} · {data.status} · {data.reason}")


def ensure_quorum(slot,council):
    attendance=slot.attendance.get("_council",{})
    present=set(attendance.get("present_ids",[]))
    required={p["id"] for p in council.members if p["role"] in {"CHAIR","SECRETARY"}}
    if len(council.members)!=5 or len(present)<3 or not required<=present:
        raise HTTPException(409,"Cần điểm danh hội đồng: ít nhất 3/5 người, gồm chủ tịch và thư ký")


def save_council_attendance(session,user,identifier,expected,data):
    slot,council,_=edit(session,user,identifier,expected,secretary=True)
    present={str(value) for value in data.present_ids}
    ids={p["id"] for p in council.members}
    required={p["id"] for p in council.members if p["role"] in {"CHAIR","SECRETARY"}}
    if len(present)!=len(data.present_ids) or not present<=ids or not required<=present:
        raise HTTPException(422,"Danh sách có mặt phải gồm chủ tịch, thư ký và không trùng người")
    if now()<slot.starts_at:
        raise HTTPException(409,"Chưa đến giờ bảo vệ để xác nhận mở phiên")
    if any(set(marks)-present for marks in slot.marks.values()):
        raise HTTPException(409,"Người đã chấm không thể chuyển thành vắng")
    slot.attendance={**slot.attendance,"_council":{"present_ids":sorted(present),"reason":data.reason,
        "by":str(user.id),"at":now().isoformat()}}
    finish_edit(session,user,slot,"DEFENSE_COUNCIL_ATTENDANCE",data.reason)


def reopen_unsigned(session,user,identifier,expected,data):
    import json
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    slot,council,member,_,_=load_slot(session,user,identifier,write=True)
    row_version(expected,slot.row_version)
    if not member or member["role"] not in {"CHAIR","SECRETARY"}:
        raise HTTPException(403,"Chỉ chủ tịch hoặc thư ký được sửa bản chưa ký")
    if not slot.finalized_at or council.closed_at:
        raise HTTPException(409,"Chỉ mở bản đã chốt trước khi khóa bảng điểm hội đồng")
    thesis=session.scalar(select(m.Thesis).where(m.Thesis.id==slot.thesis_id).with_for_update())
    audit(session,user,"DEFENSE_UNSIGNED_REVISION","defense_slot",slot.id,json.dumps({
        "reason":data.reason,"previous_version":slot.row_version,"marks":slot.marks,
        "attendance":slot.attendance,"minutes":slot.minutes,"finalized_at":slot.finalized_at.isoformat(),
        "finalized_by":str(slot.finalized_by)},ensure_ascii=False))
    if session.scalar(select(m.DefenseAbsenceDecision.id).where(m.DefenseAbsenceDecision.slot_id==slot.id)):
        raise HTTPException(409,"Phiên đã được Khoa dùng làm căn cứ xử lý SV vắng; giữ nguyên hồ sơ gốc")
    slot.finalized_at,slot.finalized_by=None,None
    slot.minutes={key:value for key,value in slot.minutes.items() if key!="results_snapshot"}
    slot.attendance={**slot.attendance,"_revision_epoch":slot.row_version+1}
    other_completed=any(any(r["average"] is not None for r in results(other,session.get(m.DefenseCouncil,other.council_id)).values())
        for other in session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.thesis_id==thesis.id,m.DefenseSlot.id!=slot.id,m.DefenseSlot.finalized_at.is_not(None))))
    thesis.state,thesis.row_version=("DEFENDED" if other_completed else "READY_FOR_DEFENSE"),thesis.row_version+1
    notify(session,user,slot,council,"DEFENSE_REOPENED","Kết quả đang điều chỉnh trước ký; bản xuất trước đó đã hết hiệu lực")
    finish_edit(session,user,slot,"DEFENSE_REOPENED",data.reason)


def blockers(slot,council):
    pending=[]
    try:
        ensure_quorum(slot,council)
    except HTTPException as error:
        pending.append(error.detail)
    if not slot.minutes:
        pending.append("Thư ký cần lưu nội dung họp và kết luận")
    else:
        pending.extend(minutes_blockers(slot))
    present=slot.attendance.get("_council",{}).get("present_ids",[])
    for row in slot.roster:
        status=slot.attendance.get(row["id"],{}).get("status")
        if not status:
            pending.append(f"Cần điểm danh {row['name']}")
        if status=="PRESENT":
            missing=[p["name"] for p in council.members if p["id"] in present and p["id"] not in slot.marks.get(row["id"],{})]
            if missing:
                pending.append(f"{row['name']} còn thiếu phiếu của "+", ".join(missing))
    if now()<slot.starts_at:
        pending.append("Chưa đến giờ bảo vệ")
    return pending


def minutes_blockers(slot):
    if not slot.minutes:
        return ["Thư ký cần lưu nội dung họp và kết luận"]
    missing = []
    for key, label in (("objectives", "Mục tiêu"), ("functions", "Chức năng"), ("achievements", "Kết quả đạt được")):
        if not slot.minutes.get(key):
            missing.append(f"Bổ sung mục {label} trong biên bản")
    if not (slot.minutes.get("recommendations") or slot.minutes.get("no_recommendations")):
        missing.append("Nhập kiến nghị hoặc xác nhận hội đồng không có kiến nghị")
    classifications = slot.minutes.get("classifications", {})
    for student in slot.roster:
        if slot.attendance.get(student["id"], {}).get("status") == "PRESENT" and classifications.get(student["id"]) in {None, "Chờ xác nhận"}:
            missing.append(f"Ghi xếp loại được hội đồng xác nhận cho {student['name']}")
    return missing


def invalid_bonus(session,slot):
    from backend.services.publications import approved_for
    for row in slot.roster:
        current = slot.attendance.get(row["id"], {})
        try:
            approved = approved_for(session, slot.thesis_id, row["student_id"])
        except HTTPException:
            return True
        if Decimal(current.get("bonus", "0")) != Decimal(approved["bonus"]):
            return True
        if Decimal(approved["bonus"]) > 0 and current.get("bonus_claim_id") != approved.get("bonus_claim_id"):
            return True
    return False


def save_bonus(session,user,identifier,expected,member_id,data):
    from backend.services.publications import approved_for
    slot,council,member = edit(session,user,identifier,expected)
    if member["role"] != "CHAIR":
        raise HTTPException(403,"Chủ tịch hội đồng đối chiếu mức thưởng đã được TBM duyệt")
    student = student_id(slot,member_id)
    row = next(r for r in slot.roster if r["id"] == student)
    approved = approved_for(session, slot.thesis_id, row["student_id"])
    if data.points != Decimal(approved["bonus"]) or (data.points and str(data.evidence_version_id) != approved.get("bonus_evidence_version_id")):
        raise HTTPException(422,"Chỉ được sử dụng đúng mức thưởng và minh chứng đã được TBM duyệt cho sinh viên này")
    slot.attendance = {**slot.attendance, student: {**slot.attendance.get(student,{}), **approved,
        "bonus_confirmed_by":str(user.id), "bonus_confirmed_at":now().isoformat()}}
    finish_edit(session,user,slot,"DEFENSE_BONUS_CONFIRMED",approved.get("bonus_reference"))


def save_minutes(session,user,identifier,expected,data):
    slot,council,_ = edit(session,user,identifier,expected,secretary=True)
    student_ids = {r["id"] for r in slot.roster}
    if not set(map(str,data.classifications)) <= student_ids:
        raise HTTPException(422,"Xếp loại chỉ dành cho sinh viên trong phiên bảo vệ")
    if data.no_recommendations and data.recommendations:
        raise HTTPException(422,"Chọn một cách ghi: nhập kiến nghị hoặc xác nhận không có kiến nghị")
    present = set(slot.attendance.get("_council", {}).get("present_ids", []))
    members = {person["id"] for person in council.members} & present
    if any(str(student) not in student_ids or not set(map(str, comments)) <= members
            for student, comments in data.oral_comments.items()):
        raise HTTPException(422,"Ý kiến chỉ được ghi cho sinh viên trong phiên và thành viên hội đồng có mặt")
    slot.minutes = {**data.model_dump(mode="json"), "revision_epoch": slot.minutes.get("revision_epoch", 0)}
    finish_edit(session,user,slot,"DEFENSE_MINUTES_SAVED")


def correct_academic_profile(session,user,identifier,expected,member_id,data):
    """Correct identity metadata with a basis; never reopen or alter grading."""
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    slot,council,_,_,manager=load_slot(session,user,identifier,write=True)
    if not manager:raise HTTPException(403,"Chỉ TBM hoặc điều phối được đính chính thông tin học vụ")
    row_version(expected,slot.row_version)
    key=student_id(slot,member_id)
    original=next(r for r in slot.roster if r["id"]==key)
    student=session.scalar(select(m.StudentProfile).where(m.StudentProfile.id==UUID(original["student_id"])).with_for_update())
    major = validate_academic_profile(session,student,data)
    updated={**original,"name":student.display_name,"code":student.student_code,"class_name":data.class_name,"major_code":major.code,"major":major.name,
        "birth_date":data.birth_date.isoformat() if data.birth_date else "","training_cohort":data.training_cohort,
        "department_id":str(student.department_id)}
    if updated==original:raise HTTPException(422,"Thông tin học vụ chưa thay đổi")
    digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    session.add(m.AuditEvent(id=uuid4(),actor_id=user.id,action="DEFENSE_ACADEMIC_PROFILE_CORRECTED",
        resource_type="defense_slot",resource_id=slot.id,reason=f"{student.student_code} · {data.reason}",
        source_reference=data.source_reference,before_hash=digest(original),after_hash=digest(updated),occurred_at=now(),correlation_id=uuid4()))
    student.class_name,student.major_code,student.birth_date,student.training_cohort=data.class_name,data.major_code,data.birth_date,data.training_cohort or None
    slot.roster=[updated if r["id"]==key else r for r in slot.roster]
    slot.row_version+=1
    notify(session,user,slot,council,"DEFENSE_ACADEMIC_PROFILE_CORRECTED","Đã đính chính thông tin học vụ. Hãy xuất bản mới nếu cần ký lại")
    session.commit()


def validate_academic_profile(session, student, data):
    major=session.scalar(select(m.DepartmentMajor).where(m.DepartmentMajor.department_id==student.department_id,
        m.DepartmentMajor.code==data.major_code))
    if not major or (not major.active and data.major_code!=student.major_code):
        raise HTTPException(422,"Chọn ngành thuộc đúng bộ môn của sinh viên trong danh mục")
    if major.name.startswith("Chưa xác minh"):
        raise HTTPException(422,"Mã ngành cũ chưa được xác minh. Cần đối chiếu danh mục Khoa trước khi đính chính")
    if data.birth_date and (data.birth_date>now().astimezone(VN).date() or data.birth_date.year<1900):
        raise HTTPException(422,"Ngày sinh phải từ năm 1900 đến hiện tại")
    return major


def finish_edit(session,user,slot,event,reason=None):
    slot.row_version += 1
    audit(session,user,event,"defense_slot",slot.id,reason)
    session.commit()


def total(mark, attendance, precision=".1"):
    return min(Decimal(10),sum((Decimal(value) for value in mark["scores"]),Decimal(0)) +
        Decimal(attendance.get("bonus","0"))).quantize(Decimal(precision),rounding=ROUND_HALF_UP)


def results(slot, council):
    if slot.finalized_at and slot.minutes.get("results_snapshot"):
        return slot.minutes["results_snapshot"]
    out = {}
    for row in slot.roster:
        key = row["id"]
        attendance = slot.attendance.get(key,{})
        marks = slot.marks.get(key,{})
        voters = slot.attendance.get("_council",{}).get("present_ids",[p["id"] for p in council.members])
        precision=".01" if slot.finalized_at else ".1"
        values = [total(marks[person["id"]],attendance,precision) if person["id"] in marks else None for person in council.members if person["id"] in voters]
        average = None
        if attendance.get("status") == "PRESENT" and values and all(value is not None for value in values):
            average = str((sum(values)/len(values)).quantize(Decimal(".01" if slot.finalized_at else ".1"),rounding=ROUND_HALF_UP))
        out[key] = {"attendance":attendance,"scores":[str(value) if value is not None else None for value in values],"average":average}
    return out


def finalize(session,user,identifier,expected):
    slot,council,member = edit(session,user,identifier,expected)
    if member["role"] not in {"CHAIR","SECRETARY"}:
        raise HTTPException(403,"Chỉ chủ tịch hoặc thư ký được chốt")
    ensure_quorum(slot,council)
    if invalid_bonus(session,slot):
        raise HTTPException(409,"Cần đối chiếu lại minh chứng điểm thưởng còn an toàn và đúng hồ sơ trước khi chốt")
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == slot.thesis_id).with_for_update())
    active,report = validate_ready(session,thesis,council,{row["id"] for row in slot.roster} if slot.prior_slot_id else None)
    if {str(row.id) for row in active} != {row["id"] for row in slot.roster}:
        raise HTTPException(409,"Thành viên đã thay đổi. Cần đối chiếu lại lịch bảo vệ")
    if report.id != slot.report_version_id:
        raise HTTPException(409,"Phiên bản báo cáo đã thay đổi")
    if now() < slot.starts_at:
        raise HTTPException(409,"Chưa đến giờ bảo vệ")
    if not slot.minutes or any(row["attendance"].get("status") != "ABSENT" and row["average"] is None
        for row in results(slot,council).values()):
        raise HTTPException(409,"Cần có biên bản, điểm đầy đủ của sinh viên có mặt và lý do của sinh viên vắng")
    pending = minutes_blockers(slot)
    if pending:
        raise HTTPException(409, ". ".join(pending))
    frozen_results=results(slot,council)
    from backend.services.defense_templates import academic_roster
    slot.roster = academic_roster(session,slot)
    slot.finalized_at,slot.finalized_by = now(),user.id
    advisor = primary_advisor(session,thesis.id)
    slot.minutes = {**slot.minutes,"title":thesis.current_title,"results_snapshot":frozen_results,
        "advisor":session.get(m.LecturerProfile,advisor.lecturer_id).display_name if advisor else ""}
    if any(row["average"] is not None for row in results(slot,council).values()):
        thesis.state = "DEFENDED"
        thesis.row_version += 1
    notify(session,user,slot,council,"DEFENSE_FINALIZED","Đã chốt kết quả bảo vệ")
    finish_edit(session,user,slot,"DEFENSE_FINALIZED")


def workspace(session,user):
    lecturer, student = lecturer_for(session,user), student_for(session,user)
    if not lecturer and not student:
        raise HTTPException(403,"Chỉ giảng viên và sinh viên được xem lịch bảo vệ")
    councils = session.scalars(select(m.DefenseCouncil).order_by(m.DefenseCouncil.name)).all()
    managed = {c.id for c in councils if manages(session,user,lecturer,c.round_id,c.department_id)}
    visible = {c.id:c for c in councils if c.id in managed or membership(c,lecturer)}
    slots = []
    for slot in session.scalars(select(m.DefenseSlot).order_by(m.DefenseSlot.starts_at)):
        own = next((row for row in slot.roster if student and row["student_id"] == str(student.id)),None)
        if not own and slot.council_id not in visible:
            continue
        council = visible.get(slot.council_id) or session.get(m.DefenseCouncil,slot.council_id)
        member = membership(council,lecturer)
        thesis = session.get(m.Thesis,slot.thesis_id)
        assignment = primary_advisor(session, thesis.id)
        advisor = session.get(m.LecturerProfile, assignment.lecturer_id) if assignment else None
        privileged = slot.council_id in managed or (member and member["role"] in {"CHAIR","SECRETARY"})
        totals = results(slot,council)
        if own:
            totals = {own["id"]:{"attendance":totals[own["id"]]["attendance"],"average":totals[own["id"]]["average"] if slot.finalized_at else None}}
        elif not privileged and not slot.finalized_at:
            totals = {k:{"attendance":v["attendance"]} for k,v in totals.items()}
        marks = {} if own else slot.marks if privileged else {
            key:{lecturer_id:mark for lecturer_id,mark in values.items() if member and lecturer_id == member["id"]}
            for key,values in slot.marks.items()}
        slots.append({"id":slot.id,"prior_slot_id":slot.prior_slot_id,"absence_decisions":absence_out(session,slot,own),"thesis_id":thesis.id,"title":thesis.current_title,"council":council_out(council),
            "advisor_name":slot.minutes.get("advisor") or (advisor.display_name if advisor else None),
            "report_filename":session.get(m.StoredFile,session.get(m.DocumentVersion,slot.report_version_id).stored_file_id).original_name,
            "starts_at":slot.starts_at,"ends_at":slot.ends_at,"arrival_at":slot.arrival_at,"room":slot.room,"version":slot.row_version,
            "roster":visible_academic_roster(session,slot,own,privileged),"results":totals,"marks":marks,
            "context_token":context_token(slot,council),"bonus_evidence":evidence_options(session,slot.thesis_id),
            "minutes":slot.minutes if privileged else {}, "finalized_at":slot.finalized_at,
            "council_attendance":slot.attendance.get("_council",{}) if not own else {},
            "blockers":(blockers(slot,council)+(["Chủ tịch cần đối chiếu lại minh chứng điểm thưởng"] if invalid_bonus(session,slot) else [])) if privileged and not slot.finalized_at else [],
            "role":member["role"] if member else None,"lecturer_id":member["id"] if member else None,
            "can_manage":slot.council_id in managed,"schedule_editable":schedule_editable(slot,council)})
    scopes = []
    catalog = []
    eligible = []
    planning_theses = []
    if lecturer:
        departments = session.scalars(select(m.Department).where(m.Department.active.is_(True)).order_by(m.Department.code)).all()
        rounds = session.scalars(select(m.ThesisRound).where(m.ThesisRound.state != "ARCHIVED")).all()
        home = session.get(m.Department, lecturer.department_id) if lecturer.department_id else None
        for round_ in rounds:
            for department in departments:
                if not valid_council_scope(round_, department):
                    continue
                can_manage = manages(session, user, lecturer, round_.id, department.id)
                same_faculty = home and council_faculty_id(session, home) == council_faculty_id(session, department)
                if not (can_manage or same_faculty):
                    continue
                row = {"round_id": round_.id, "round_code": round_.code, "department_id": department.id,
                    "department_name": department.name, "department_code": department.code,
                    "faculty_id": council_faculty_id(session, department), "can_manage": can_manage}
                catalog.append(row)
                if can_manage:
                    scopes.append(row)
        allowed = {(row["round_id"],row["department_id"]) for row in scopes}
        for t in session.scalars(select(m.Thesis).where(m.Thesis.state.in_([
            "ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "READY_FOR_DEFENSE", "EXTENDED", "DEFENDED"])).order_by(m.Thesis.current_title)):
            if (t.round_id, t.department_id) not in allowed:
                continue
            row = {"id":t.id,"title":t.current_title,"round_id":t.round_id,"department_id":t.department_id,
                "advisor_ids":sorted(supervising_ids(session,t.id))}
            extension = session.scalar(select(m.ThesisExtension).where(m.ThesisExtension.thesis_id == t.id))
            report = evaluation.report(session, t)
            members = evaluation.members(session, t)
            member_states = [evaluation.eligibility_out(session, t, member, report)["state"] for member in members]
            if not report:
                reason = "Chưa có cuốn báo cáo."
            elif not members:
                reason = "Chưa có thành viên đang thực hiện."
            elif any(state == "STALE" for state in member_states):
                reason = "Kết quả xét đã cũ. TBM cần xét và lưu lại điều kiện của sinh viên."
            elif any(state != "ELIGIBLE" for state in member_states):
                reason = "Còn sinh viên chưa được chốt đủ điều kiện bảo vệ."
            elif extension and extension.until_at < now():
                reason = "Thời hạn gia hạn đã hết."
            elif t.state not in {"READY_FOR_DEFENSE", "EXTENDED"}:
                reason = "Hồ sơ chưa ở trạng thái sẵn sàng bảo vệ."
            elif evaluation.pending_reviewer_forms(session,t,report):
                reason = "Chưa nhận đủ Mẫu 8 từ tất cả phản biện đang được phân công cho từng SV."
            else:
                reason = None
            planning_theses.append({**row, "schedule_reason": reason,
                "can_review_eligibility": "evaluation:eligibility" in evaluation.permissions(session,user,t)})
            if reason:
                continue
            request = session.scalar(select(m.ThesisExtensionRequest).where(m.ThesisExtensionRequest.extension_id == extension.id)) if extension else None
            eligible.append({**row,
                "extension_starts_at":request.extension_starts_at if request else None,
                "extension_until_at":extension.until_at if extension else None})
    can_plan_demo = any(scope["round_code"] == "SYN-DEMO" for scope in scopes)
    candidates = [{"id":l.id,"name":l.display_name,"code":l.lecturer_code,"faculty_id":d.faculty_id if d else None,
        "department_code":d.code if d else None,
        "specializations":l.profile_data.get("specializations",[]) if l.profile_verified_at else []}
        for l,d in session.execute(select(m.LecturerProfile,m.Department)
        .join(m.UserAccount,m.UserAccount.id==m.LecturerProfile.user_id)
        .outerjoin(m.Department,m.Department.id==m.LecturerProfile.department_id)
        .where(m.UserAccount.status=="ACTIVE",m.UserAccount.base_role=="LECTURER")
        .order_by(m.LecturerProfile.display_name)) if can_plan_demo or not demo_department(d.code if d else None)] if scopes else []
    from backend.services.defense_register import rounds_for_export
    return {"councils":[council_out(c, c.id in managed) for c in visible.values()],"slots":slots,"scopes":scopes,"scope_catalog":catalog,
        "export_rounds": [{"id": round_.id, "code": round_.code} for round_ in rounds_for_export(session,user)],
        "eligible":eligible,"planning_theses":planning_theses,"candidates":candidates,"criteria":CRITERIA,"roles":ROLES,
        "academic_majors":[{"department_id":str(r.department_id),"code":r.code,"name":r.name} for r in session.scalars(select(m.DepartmentMajor).where(m.DepartmentMajor.active.is_(True)))]}


def visible_academic_roster(session,slot,own,privileged):
    from backend.services.defense_templates import academic_roster
    rows=academic_roster(session,slot)
    if own:return [r for r in rows if r["id"]==own["id"]]
    return rows if privileged else [{k:v for k,v in r.items() if k!="birth_date"} for r in rows]


def council_out(council, can_manage=False):
    return {"id":council.id,"round_id":council.round_id,"department_id":council.department_id,
        "name":council.name,"reference":council.reference,"members":council.members,
        "can_manage":can_manage,"closed_at":council.closed_at,"signature":council_signature(council)}


def council_signature(council):
    return hashlib.sha256(json.dumps([council.name,council.reference,council.members],sort_keys=True).encode()).hexdigest()


def close_council(session,user,identifier):
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    council = session.get(m.DefenseCouncil,identifier)
    if not council or not manages(session,user,lecturer_for(session,user),council.round_id,council.department_id):
        raise HTTPException(404,"Không tìm thấy hội đồng trong phạm vi quản lý")
    if council.closed_at:
        return
    slots = session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.council_id == identifier)
        .order_by(m.DefenseSlot.id).with_for_update()).all()
    if not slots or any(not slot.finalized_at for slot in slots):
        raise HTTPException(409,"Cần chốt toàn bộ lịch của hội đồng trước khi khóa bảng điểm")
    council.closed_at = now()
    audit(session,user,"DEFENSE_COUNCIL_CLOSED","defense_council",identifier)
    session.commit()


def context_token(slot,council):
    # Independent ballots may merge only while the common scoring context is unchanged.
    return hashlib.sha256(json.dumps([slot.attendance,council.members,str(slot.report_version_id),
        slot.minutes.get("revision_epoch",0)],sort_keys=True,default=str).encode()).hexdigest()


def evidence_options(session,thesis_id):
    rows=session.execute(select(m.DocumentVersion,m.Document,m.StoredFile)
        .join(m.Document,m.Document.id==m.DocumentVersion.document_id)
        .join(m.StoredFile,m.StoredFile.id==m.DocumentVersion.stored_file_id)
        .where(m.Document.thesis_id==thesis_id,m.Document.document_type.in_(["SUPPORTING"]),m.StoredFile.scan_state=="CLEAN",
            m.DocumentVersion.id.in_(select(m.PublicationClaim.evidence_version_id).where(m.PublicationClaim.thesis_id==thesis_id,m.PublicationClaim.state=="APPROVED")))
        .order_by(m.DocumentVersion.created_at.desc())).all()
    return [{"id":v.id,"name":f"{d.title} · {f.original_name} · v{v.version_no}","filename":f.original_name} for v,d,f in rows]


def report_download(session,user,identifier):
    from backend.services import documents
    slot,_,_,_,_=load_slot(session,user,identifier)
    version=session.get(m.DocumentVersion,slot.report_version_id)
    return documents.stored_download(session,version)


def clear_mark(session,user,identifier,expected,student,lecturer,reason):
    slot,_,member=edit(session,user,identifier,expected)
    if member["role"] not in {"CHAIR","SECRETARY"}:
        raise HTTPException(403,"Chỉ chủ tịch hoặc thư ký hủy phiếu nhập nhầm trước khi chốt")
    key=student_id(slot,student)
    marks=dict(slot.marks.get(key,{}))
    old=marks.pop(str(lecturer),None)
    if not old:
        raise HTTPException(404,"Phiếu không còn tồn tại; hãy làm mới dữ liệu")
    audit(session,user,"DEFENSE_MARK_VOIDED","defense_slot",slot.id,json.dumps({"student":key,
        "lecturer":str(lecturer),"reason":reason,"previous":old},ensure_ascii=False))
    slot.marks={**slot.marks,key:marks}
    # Change the context to reject drafts started before a ballot was voided.
    slot.attendance={**slot.attendance,"_revision_epoch":slot.row_version+1}
    finish_edit(session,user,slot,"DEFENSE_MARK_CLEARED",reason)


def absence_out(session,slot,own=None):
    return {str(d.thesis_member_id):{"outcome":d.outcome,"reference":d.reference,"reason":d.reason,
        "recorded_at":d.recorded_at,"recorded_by":notices.actor_name(session,d.recorded_by),"revision":d.row_version}
        for d in session.scalars(select(m.DefenseAbsenceDecision).where(m.DefenseAbsenceDecision.slot_id==slot.id))
        if own is None or own["id"]==str(d.thesis_member_id)}


def decide_absence(session,user,identifier,student,data):
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    slot,council,_,_,manager=load_slot(session,user,identifier,write=True)
    if not manager:
        raise HTTPException(403,"Chỉ TBM hoặc người quản lý KLTN được Khoa phân công ghi nhận quyết định")
    key=student_id(slot,student)
    if not slot.finalized_at or slot.attendance.get(key,{}).get("status")!="ABSENT":
        raise HTTPException(409,"Chỉ xử lý SV được ghi nhận vắng trong phiên đã chốt")
    if any(key in {r["id"] for r in child.roster} for child in session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.prior_slot_id==slot.id))):
        raise HTTPException(409,"Đã dùng quyết định để xếp lịch bổ sung; không được thay đổi căn cứ")
    row=session.scalar(select(m.DefenseAbsenceDecision).where(m.DefenseAbsenceDecision.slot_id==slot.id,m.DefenseAbsenceDecision.thesis_member_id==student))
    row_version(data.revision,row.row_version if row else 0)
    if row:
        audit(session,user,"DEFENSE_ABSENCE_BEFORE_REVISION","defense_slot",slot.id,json.dumps(absence_out(session,slot),default=str,ensure_ascii=False))
        row.row_version+=1
    else:
        row=m.DefenseAbsenceDecision(slot_id=slot.id,thesis_member_id=student)
        session.add(row)
    row.outcome,row.reference,row.reason=data.outcome,data.reference,data.reason
    row.recorded_at,row.recorded_by=now(),user.id
    audit(session,user,"DEFENSE_ABSENCE_DECIDED","defense_slot",slot.id,f"{key} · {data.outcome} · {data.reason}",source_reference=data.reference)
    notify(session,user,slot,council,"DEFENSE_ABSENCE_DECIDED","Khoa đã ghi nhận quyết định xử lý SV vắng; xem chi tiết theo từng sinh viên")
    session.commit()
