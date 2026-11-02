"""Published lecturer profiles, private edits, and independent academic approval."""
import hashlib
import io
import unicodedata
import warnings
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, or_, select

from backend.api.lecturer_profile_schemas import ProfileData
from backend.db.models import entities as m
from backend.services import documents, file_scanner, workflow_notices as notices
from backend.services.registration import profile, row_version
from backend.services.theses import audit, effective, is_faculty_dean, now

OPEN = {"DRAFT", "SUBMITTED"}


def fold(value):
    return "".join(c for c in unicodedata.normalize("NFD", value.lower().replace("đ","d")) if not unicodedata.combining(c))


ACCENTS = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
ASCII = "".join(fold(c) for c in ACCENTS)


def scopes(session, user):
    if user.base_role != "LECTURER":return set(),set()
    lecturer=profile(session,user,"LECTURER")
    records=session.execute(select(m.PositionAssignment.department_id,m.PositionAssignment.faculty_id)
        .join(m.OrganizationalPosition,m.OrganizationalPosition.id==m.PositionAssignment.position_id)
        .where(m.PositionAssignment.lecturer_id==lecturer.id,effective(m.PositionAssignment),
            or_(and_(m.OrganizationalPosition.code=="DEPARTMENT_HEAD",m.PositionAssignment.department_id.is_not(None)),
                and_(m.OrganizationalPosition.code=="FACULTY_DEAN",m.PositionAssignment.faculty_id.is_not(None))))).all()
    return {r.department_id for r in records if r.department_id},{r.faculty_id for r in records if r.faculty_id}


def can_review(session,user,lecturer):
    if user.id==lecturer.user_id:return False
    departments,faculties=scopes(session,user)
    department=session.get(m.Department,lecturer.department_id)
    return lecturer.department_id in departments or bool(department and department.faculty_id in faculties)


def lecturer_row(session,identifier,*,lock=False):
    query=select(m.LecturerProfile).where(m.LecturerProfile.id==identifier)
    if lock:query=query.with_for_update().execution_options(populate_existing=True)
    item=session.scalar(query)
    if not item:raise HTTPException(404,"Không tìm thấy hồ sơ giảng viên")
    return item


def own(session,user,*,lock=False):
    if user.base_role!="LECTURER":raise HTTPException(403,"Chỉ giảng viên cập nhật hồ sơ của chính mình")
    lecturer=profile(session,user,"LECTURER")
    return lecturer_row(session,lecturer.id,lock=lock)


def published_data(item):
    return ProfileData.model_validate({**(item.profile_data or {}),"display_name":item.display_name}).model_dump()


def avatar_url(item):
    return f"/api/v1/lecturer-profiles/{item.id}/avatar?v={item.row_version}" if item.avatar_file_id else None


def visible(session,user,item):
    account=session.get(m.UserAccount,item.user_id)
    return bool(user.id==item.user_id or user.base_role=="ADMIN" or can_review(session,user,item) or
        (account and account.status=="ACTIVE" and account.base_role=="LECTURER"))


def detail(session,user,identifier):
    item=lecturer_row(session,identifier)
    if not visible(session,user,item):raise HTTPException(404,"Không tìm thấy giảng viên đang được phép xem")
    account=session.get(m.UserAccount,item.user_id)
    department=session.get(m.Department,item.department_id)
    faculty=session.get(m.Faculty,department.faculty_id)
    private=user.id==item.user_id or user.base_role=="ADMIN" or can_review(session,user,item)
    data=published_data(item)
    if not private and not data["show_phone"]:data["contact_phone"]=None
    positions=session.execute(select(m.OrganizationalPosition.name).join(m.PositionAssignment,
        m.PositionAssignment.position_id==m.OrganizationalPosition.id).where(
        m.PositionAssignment.lecturer_id==item.id,effective(m.PositionAssignment))).scalars().all()
    return {"id":item.id,"user_id":item.user_id if private else None,"lecturer_code":item.lecturer_code,
        "display_name":item.display_name,"department_id":item.department_id,"department_code":department.code,
        "department_name":department.name,"faculty_name":faculty.name,"data":data,
        "avatar_url":avatar_url(item),"row_version":item.row_version,
        "verified_at":item.profile_verified_at,"positions":positions,
        "account_email":account.email if private else None,"account_status":account.status if private else None,
        "can_manage_identity":user.base_role=="ADMIN","is_owner":user.id==item.user_id}


def request_out(session,user,item,lecturer):
    file=session.get(m.StoredFile,item.avatar_file_id) if item.avatar_file_id else None
    return {"id":item.id,"lecturer_id":item.lecturer_id,"lecturer_name":lecturer.display_name,
        "lecturer_code":lecturer.lecturer_code,"department_name":session.get(m.Department,lecturer.department_id).name,
        "version_no":item.version_no,"row_version":item.row_version,"state":item.state,
        "base_profile_version":item.base_profile_version,"stale":item.state in OPEN and item.base_profile_version!=lecturer.row_version,
        "proposed_data":item.proposed_data,"original_data":item.original_data,
        "avatar_changed":item.avatar_file_id!=item.original_avatar_file_id,
        "avatar_url":f"/api/v1/lecturer-profile-changes/{item.id}/avatar?v={item.row_version}" if file else None,
        "avatar_name":file.original_name if file else None,"avatar_scan_state":file.scan_state if file else None,
        "original_avatar_url":f"/api/v1/lecturer-profile-changes/{item.id}/original-avatar" if item.original_avatar_file_id else None,
        "submission_note":item.submission_note,"submitted_at":item.submitted_at,"updated_at":item.updated_at,
        "reviewed_at":item.reviewed_at,"reviewed_by_name":notices.actor_name(session,item.reviewed_by) if item.reviewed_by else None,
        "decision_reason":item.decision_reason,"can_review":can_review(session,user,lecturer) and item.state=="SUBMITTED",
        "reviewer_count":len(reviewers(session,lecturer)) if item.state in OPEN else None}


def workspace(session,user):
    lecturer=own(session,user)
    changes=session.scalars(select(m.LecturerProfileChange).where(m.LecturerProfileChange.lecturer_id==lecturer.id)
        .order_by(m.LecturerProfileChange.version_no.desc())).all()
    return {"profile":detail(session,user,lecturer.id),"active_request":next((request_out(session,user,r,lecturer) for r in changes if r.state in OPEN),None),
        "history":[request_out(session,user,r,lecturer) for r in changes if r.state not in OPEN]}


def reviewers(session,lecturer):
    department=session.get(m.Department,lecturer.department_id)
    candidates=session.execute(select(m.LecturerProfile.user_id,m.OrganizationalPosition.code).join(m.PositionAssignment,
        m.PositionAssignment.lecturer_id==m.LecturerProfile.id).join(m.OrganizationalPosition,
        m.OrganizationalPosition.id==m.PositionAssignment.position_id).join(m.UserAccount,m.UserAccount.id==m.LecturerProfile.user_id)
        .where(effective(m.PositionAssignment),m.UserAccount.status=="ACTIVE",m.UserAccount.id!=lecturer.user_id,
            or_(and_(m.OrganizationalPosition.code=="DEPARTMENT_HEAD",m.PositionAssignment.department_id==lecturer.department_id),
                and_(m.OrganizationalPosition.code=="FACULTY_DEAN",m.PositionAssignment.faculty_id==department.faculty_id)))).all()
    heads={row.user_id for row in candidates if row.code=="DEPARTMENT_HEAD"}
    return heads or {row.user_id for row in candidates if row.code=="FACULTY_DEAN"}


def new_request(session,user,expected):
    lecturer=own(session,user,lock=True);row_version(expected,lecturer.row_version)
    if session.scalar(select(m.LecturerProfileChange.id).where(m.LecturerProfileChange.lecturer_id==lecturer.id,m.LecturerProfileChange.state.in_(OPEN))):
        raise HTTPException(409,"Đã có bản nháp hoặc hồ sơ đang chờ duyệt. Tiếp tục bản hiện có hoặc rút trước khi tạo mới")
    previous=session.scalar(select(m.LecturerProfileChange).where(m.LecturerProfileChange.lecturer_id==lecturer.id)
        .order_by(m.LecturerProfileChange.version_no.desc()).limit(1))
    reuse=previous and previous.state in {"RETURNED","WITHDRAWN"} and previous.base_profile_version==lecturer.row_version
    data=published_data(lecturer)
    item=m.LecturerProfileChange(id=uuid4(),lecturer_id=lecturer.id,base_profile_version=lecturer.row_version,
        version_no=previous.version_no+1 if previous else 1,original_data=data,
        proposed_data=previous.proposed_data if reuse else data,
        avatar_file_id=previous.avatar_file_id if reuse else lecturer.avatar_file_id,
        original_avatar_file_id=lecturer.avatar_file_id,state="DRAFT")
    session.add(item);session.flush();result=request_out(session,user,item,lecturer);session.commit();return result


def request_access(session,user,identifier,*,write=False):
    initial=session.get(m.LecturerProfileChange,identifier)
    if not initial:raise HTTPException(404,"Không tìm thấy yêu cầu cập nhật hồ sơ")
    lecturer=lecturer_row(session,initial.lecturer_id,lock=write)
    query=select(m.LecturerProfileChange).where(m.LecturerProfileChange.id==identifier)
    item=session.scalar(query.with_for_update().execution_options(populate_existing=True) if write else query)
    owner=user.id==lecturer.user_id
    if not owner and (item.state=="DRAFT" or not can_review(session,user,lecturer)):
        raise HTTPException(404,"Yêu cầu không thuộc phạm vi được xem hoặc duyệt")
    return lecturer,item


def editable(session,user,identifier,expected):
    lecturer,item=request_access(session,user,identifier,write=True)
    if user.id!=lecturer.user_id:raise HTTPException(403,"Chỉ chủ hồ sơ được sửa bản nháp")
    row_version(expected,item.row_version)
    if item.state!="DRAFT":raise HTTPException(409,"Bản đã gửi hoặc đã xử lý được giữ nguyên; rút hồ sơ hoặc tạo bản sửa để cập nhật")
    if item.base_profile_version!=lecturer.row_version:raise HTTPException(409,"Thông tin gốc đã đổi. Rút bản nháp và tạo bản mới theo dữ liệu hiện hành")
    return lecturer,item


def save(session,user,identifier,data,expected):
    lecturer,item=editable(session,user,identifier,expected)
    item.proposed_data=data.model_dump();item.row_version+=1
    session.flush();result=request_out(session,user,item,lecturer);session.commit();return result


def submit(session,user,identifier,data,expected):
    lecturer,item=editable(session,user,identifier,expected)
    ProfileData.model_validate(item.proposed_data)
    if item.proposed_data==published_data(lecturer) and item.avatar_file_id==lecturer.avatar_file_id:
        raise HTTPException(422,"Chưa có thay đổi so với hồ sơ đang hiển thị")
    if item.avatar_file_id:documents.require_clean(session.get(m.StoredFile,item.avatar_file_id),"gửi ảnh đại diện để duyệt")
    item.state="SUBMITTED";item.submission_note=data.note;item.submitted_at=now();item.row_version+=1
    audit(session,user,"LECTURER_PROFILE_SUBMITTED","lecturer_profile_change",item.id,data.note)
    notices.emit(session,user.id,reviewers(session,lecturer),"LECTURER_PROFILE_SUBMITTED","lecturer_profile_change",item.id,
        f"{lecturer.display_name} ({lecturer.lecturer_code}) gửi cập nhật hồ sơ giảng viên cần duyệt.",f"/lecturer-profile-reviews?request={item.id}")
    if not reviewers(session,lecturer):
        admins=session.scalars(select(m.UserAccount.id).where(m.UserAccount.base_role=="ADMIN",m.UserAccount.status=="ACTIVE")).all()
        for admin_id in admins:
            notices.emit(session,user.id,{admin_id},"LECTURER_PROFILE_MISSING_REVIEWER","account",admin_id,
                f"Hồ sơ {lecturer.lecturer_code} đang chờ nhưng chưa có TBM/Trưởng khoa khác đủ thẩm quyền duyệt. Cần kiểm tra phân công chức vụ.","/lecturers")
    session.flush();result=request_out(session,user,item,lecturer);session.commit();return result


def withdraw(session,user,identifier,data,expected):
    lecturer,item=request_access(session,user,identifier,write=True)
    if user.id!=lecturer.user_id:raise HTTPException(403,"Chỉ chủ hồ sơ được rút yêu cầu")
    row_version(expected,item.row_version)
    if item.state not in OPEN:raise HTTPException(409,"Yêu cầu đã được xử lý, không thể rút")
    item.state="WITHDRAWN";item.decision_reason=data.reason;item.row_version+=1
    audit(session,user,"LECTURER_PROFILE_WITHDRAWN","lecturer_profile_change",item.id,data.reason)
    session.flush();result=request_out(session,user,item,lecturer);session.commit();return result


def decide(session,user,identifier,data,expected):
    lecturer,item=request_access(session,user,identifier,write=True)
    if not can_review(session,user,lecturer):raise HTTPException(403,"Không được tự duyệt hồ sơ; cần TBM cùng bộ môn hoặc Trưởng khoa đúng phạm vi")
    row_version(expected,item.row_version)
    if item.state!="SUBMITTED":raise HTTPException(409,"Yêu cầu đã được xử lý hoặc đã rút")
    if data.decision=="APPROVE":
        if not data.confirm_verified:raise HTTPException(422,"Cần xác nhận đã đối chiếu thông tin trước khi duyệt")
        account=session.get(m.UserAccount,lecturer.user_id)
        if account.status!="ACTIVE":raise HTTPException(409,"Tài khoản GV đang khóa hoặc ngừng hoạt động; chưa thể duyệt công bố")
        if lecturer.row_version!=item.base_profile_version:raise HTTPException(409,"Hồ sơ gốc đã đổi. Trả lại để GV gửi bản mới, không ghi đè dữ liệu hiện hành")
        checked=ProfileData.model_validate(item.proposed_data).model_dump()
        if item.avatar_file_id:documents.require_clean(session.get(m.StoredFile,item.avatar_file_id),"duyệt công bố ảnh đại diện")
        lecturer.display_name=checked.pop("display_name");lecturer.profile_data=checked;lecturer.avatar_file_id=item.avatar_file_id
        lecturer.profile_verified_at=now();lecturer.profile_verified_by=user.id;lecturer.row_version+=1
        item.state="APPROVED"
    else:item.state="RETURNED"
    item.reviewed_by=user.id;item.reviewed_at=now();item.decision_reason=data.reason;item.row_version+=1
    audit(session,user,"LECTURER_PROFILE_APPROVED" if data.decision=="APPROVE" else "LECTURER_PROFILE_RETURNED",
        "lecturer_profile_change",item.id,data.reason)
    notices.emit(session,user.id,{lecturer.user_id},"LECTURER_PROFILE_DECIDED","lecturer_profile_change",item.id,
        f"Hồ sơ giảng viên lần {item.version_no} {'đã được duyệt và cập nhật công khai' if item.state=='APPROVED' else 'cần bổ sung, chỉnh sửa'}. Lý do: {data.reason}","/account?section=lecturer-profile")
    session.flush();result=request_out(session,user,item,lecturer);session.commit();return result


def review_query(session,user):
    departments,faculties=scopes(session,user)
    if not departments and not faculties:raise HTTPException(403,"Chỉ TBM hoặc Trưởng khoa đang được phân công xem danh sách duyệt")
    return (select(m.LecturerProfileChange).join(m.LecturerProfile,m.LecturerProfile.id==m.LecturerProfileChange.lecturer_id)
        .join(m.Department,m.Department.id==m.LecturerProfile.department_id).where(
            m.LecturerProfile.user_id!=user.id,
            or_(m.LecturerProfile.department_id.in_(departments),m.Department.faculty_id.in_(faculties))))


def queue(session,user,state,q,limit,offset):
    query=review_query(session,user).where(m.LecturerProfileChange.state==state)
    if q:query=query.where(or_(m.LecturerProfile.display_name.ilike(f"%{q}%"),m.LecturerProfile.lecturer_code.ilike(f"%{q}%")))
    total=session.scalar(select(func.count()).select_from(query.subquery()))
    items=session.scalars(query.order_by(m.LecturerProfileChange.updated_at.desc(),m.LecturerProfileChange.id).offset(offset).limit(limit)).all()
    return {"total":total,"items":[request_out(session,user,item,session.get(m.LecturerProfile,item.lecturer_id)) for item in items]}


def directory(session,user,q,department_id,status,limit,offset):
    query=select(m.LecturerProfile).join(m.UserAccount,m.UserAccount.id==m.LecturerProfile.user_id).where(m.UserAccount.base_role=="LECTURER")
    if user.base_role!="ADMIN":query=query.where(m.UserAccount.status=="ACTIVE")
    elif status:query=query.where(m.UserAccount.status==status)
    if department_id:query=query.where(m.LecturerProfile.department_id==department_id)
    if q:
        name=func.translate(func.lower(m.LecturerProfile.display_name),ACCENTS,ASCII)
        filters=[name.contains(fold(q),autoescape=True),func.lower(m.LecturerProfile.lecturer_code).contains(q.lower(),autoescape=True)]
        if user.base_role=="ADMIN":filters.append(m.UserAccount.email.ilike(f"%{q}%"))
        query=query.where(or_(*filters))
    total=session.scalar(select(func.count()).select_from(query.subquery()))
    rows=session.scalars(query.order_by(m.LecturerProfile.display_name,m.LecturerProfile.id).offset(offset).limit(limit)).all()
    items=[]
    for row in rows:
        data=detail(session,user,row.id)
        items.append({key:data[key] for key in ("id","user_id","display_name","lecturer_code","department_id","department_name","faculty_name","avatar_url","data","verified_at","account_email","account_status","row_version")})
    departments=session.scalars(select(m.Department).where(m.Department.active.is_(True)).order_by(m.Department.name)).all()
    return {"items":items,"total":total,"departments":[{"id":d.id,"code":d.code,"name":d.name} for d in departments]}


def image_response(session,file_id):
    stored=session.get(m.StoredFile,file_id) if file_id else None
    documents.require_clean(stored,"xem ảnh đại diện")
    root=documents.storage_root();path=(root/Path(stored.storage_key).name).resolve()
    if path.parent!=root or not stored.storage_key.startswith("documents/") or not path.is_file():raise HTTPException(404,"Ảnh không khả dụng")
    if hashlib.sha256(path.read_bytes()).hexdigest()!=stored.sha256:raise HTTPException(409,"Ảnh không khớp bản lưu, cần kiểm tra tệp")
    return FileResponse(path,media_type=stored.media_type,headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})


async def upload_avatar(session,user,identifier,request,expected):
    from PIL import Image, ImageOps, UnidentifiedImageError
    from backend.api.auth import _same_app_origin
    lecturer,item=editable(session,user,identifier,expected)
    if not _same_app_origin(request):raise HTTPException(403,"Nguồn yêu cầu không được phép")
    content=bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content)>5*1024*1024:raise HTTPException(413,"Ảnh đại diện tối đa 5 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error",Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in {"JPEG","PNG","WEBP"} or getattr(source,"is_animated",False):raise ValueError()
                if min(source.size)<32 or max(source.size)>10000 or source.width*source.height>20_000_000:raise ValueError()
                image=ImageOps.exif_transpose(source).convert("RGB")
                image=ImageOps.fit(image,(512,512),method=Image.Resampling.LANCZOS)
                output=io.BytesIO();image.save(output,format="PNG")
    except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise HTTPException(422,"Chọn ảnh JPEG, PNG hoặc WebP tĩnh, tối thiểu 32×32 và tối đa 20 megapixel")
    path=None
    try:
        stored,_,path=documents.persist_upload(session,"avatar.png",output.getvalue(),"image/png")
        session.flush();file_scanner.scan(stored,path);item.avatar_file_id=stored.id;item.row_version+=1
        session.flush();result=request_out(session,user,item,lecturer);session.commit();return result
    except Exception:
        session.rollback()
        if path and path.is_file():path.unlink()
        raise


def remove_avatar(session,user,identifier,expected):
    lecturer,item=editable(session,user,identifier,expected);item.avatar_file_id=None;item.row_version+=1
    session.flush();result=request_out(session,user,item,lecturer);session.commit();return result


def rescan_avatar(session,user,identifier,expected):
    lecturer,item=editable(session,user,identifier,expected)
    file=session.get(m.StoredFile,item.avatar_file_id) if item.avatar_file_id else None
    if not file:raise HTTPException(404,"Chưa tải ảnh đại diện")
    file_scanner.scan(file,documents.storage_root()/Path(file.storage_key).name);item.row_version+=1
    session.flush();result=request_out(session,user,item,lecturer);session.commit();return result


def update_identity(session,user,identifier,data,expected):
    if user.base_role!="ADMIN":raise HTTPException(403,"Chỉ quản trị sửa định danh theo nguồn chính thức")
    lecturer=lecturer_row(session,identifier,lock=True);row_version(expected,lecturer.row_version)
    department=session.get(m.Department,data.department_id)
    if not department or not department.active:raise HTTPException(422,"Chọn bộ môn đang hoạt động")
    duplicate=session.scalar(select(m.LecturerProfile.id).where(func.lower(m.LecturerProfile.lecturer_code)==data.lecturer_code.lower(),m.LecturerProfile.id!=lecturer.id))
    if duplicate:raise HTTPException(409,"Mã giảng viên đã được sử dụng")
    if lecturer.department_id!=data.department_id:
        related=[(m.Topic,or_(m.Topic.proposer_user_id==lecturer.user_id,m.Topic.receiving_lecturer_id==lecturer.id)),
            (m.AdvisorAssignment,m.AdvisorAssignment.lecturer_id==lecturer.id),(m.ReviewerAssignment,m.ReviewerAssignment.lecturer_id==lecturer.id),
            (m.PositionAssignment,m.PositionAssignment.lecturer_id==lecturer.id),(m.ResourceAssignment,m.ResourceAssignment.user_id==lecturer.user_id)]
        if any(session.scalar(select(cls.id).where(condition).limit(1)) for cls,condition in related):
            raise HTTPException(409,"GV đã có hồ sơ hoặc phân công nghiệp vụ. Việc chuyển bộ môn cần quy trình điều chuyển, không sửa trực tiếp để tránh đổi quyền của hồ sơ đang dùng")
    lecturer.display_name=data.display_name;lecturer.lecturer_code=data.lecturer_code;lecturer.department_id=data.department_id;lecturer.row_version+=1
    audit(session,user,"LECTURER_IDENTITY_CORRECTED","lecturer_profile",lecturer.id,data.reason,source_reference=data.source_reference)
    notices.emit(session,user.id,{lecturer.user_id},"LECTURER_IDENTITY_CORRECTED","account",lecturer.user_id,"Định danh giảng viên của bạn đã được quản trị đối chiếu và cập nhật.","/account")
    session.commit();return detail(session,user,identifier)
