"""Versioned institutional forms/publications; business access stays round-scoped."""
from datetime import date, datetime
import io
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote
from uuid import uuid4
import zipfile

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from backend.db.models import entities as m
from backend.services import documents, file_scanner, form_templates
from backend.services.registration import profile, row_version
from backend.services.roster import assigned
from backend.services.theses import audit, effective, now

MAX_FORM_BYTES = 25*1024*1024

STAFF_ONLY = {f"mau-{number:02d}" for number in range(6,12)}


def manages(session, user, round_id):
    return user.base_role in {"ADMIN", "LECTURER"} and assigned(session,user,round_id,"FORM_MANAGER")


def round_row(session, round_id):
    row = session.get(m.ThesisRound,round_id)
    if not row:
        raise HTTPException(404,"Không tìm thấy đợt KLTN")
    return row


def require_manager(session,user,round_id):
    row=round_row(session,round_id)
    if not manages(session,user,round_id):
        raise HTTPException(403,"Cần được giao quyền Quản lý biểu mẫu cho đợt này")
    if row.state == "ARCHIVED":
        raise HTTPException(409,"Đợt đã lưu trữ, chỉ được xem lại")
    return row


def latest_eligibility():
    newer=aliased(m.EligibilitySnapshot)
    return m.EligibilitySnapshot.version==select(func.max(newer.version)).where(
        newer.student_id==m.EligibilitySnapshot.student_id,newer.round_id==m.EligibilitySnapshot.round_id).correlate(m.EligibilitySnapshot).scalar_subquery()


def belongs(session,user,round_id):
    if manages(session,user,round_id):
        return True
    if user.base_role == "STUDENT":
        student=profile(session,user,"STUDENT")
        return bool(session.scalar(select(m.EligibilitySnapshot.id).where(m.EligibilitySnapshot.student_id==student.id,
            m.EligibilitySnapshot.round_id==round_id,m.EligibilitySnapshot.state=="CONFIRMED",latest_eligibility()).limit(1)) or
            session.scalar(select(m.ThesisMember.id).join(m.Thesis,m.Thesis.id==m.ThesisMember.thesis_id).where(
                m.ThesisMember.student_id==student.id,m.ThesisMember.active.is_(True),m.Thesis.round_id==round_id).limit(1)))
    if user.base_role == "LECTURER":
        lecturer=profile(session,user,"LECTURER")
        return bool(session.scalar(select(m.ResourceAssignment.id).where(m.ResourceAssignment.user_id==user.id,
                m.ResourceAssignment.round_id==round_id,effective(m.ResourceAssignment)).limit(1)) or
            session.scalar(select(m.Topic.id).where(m.Topic.round_id==round_id,
                or_(m.Topic.proposer_user_id==user.id,m.Topic.receiving_lecturer_id==lecturer.id)).limit(1)) or
            session.scalar(select(m.AdvisorAssignment.id).join(m.Thesis,m.Thesis.id==m.AdvisorAssignment.thesis_id).where(
                m.AdvisorAssignment.lecturer_id==lecturer.id,m.Thesis.round_id==round_id,effective(m.AdvisorAssignment)).limit(1)) or
            session.scalar(select(m.EligibilitySnapshot.id).join(m.StudentProfile,m.StudentProfile.id==m.EligibilitySnapshot.student_id).where(
                m.EligibilitySnapshot.round_id==round_id,m.EligibilitySnapshot.state=="CONFIRMED",latest_eligibility(),
                m.StudentProfile.department_id==lecturer.department_id).limit(1)))
    return False


def visible(session,user,item):
    if manages(session,user,item.round_id):
        return True
    if user.base_role not in {"STUDENT","LECTURER"} or item.state!="ACTIVE":
        return False
    if user.base_role=="STUDENT" and (item.audience=="LECTURER" or item.code in STAFF_ONLY):
        return False
    return item.document_kind=="FORM" or belongs(session,user,item.round_id)


def access(session,user):
    rows=session.scalars(select(m.ThesisRound).order_by(m.ThesisRound.created_at.desc())).all()
    result=[]
    for row in rows:
        manage=manages(session,user,row.id)
        if not manage and (user.base_role not in {"STUDENT","LECTURER"} or (row.state=="DRAFT" and not belongs(session,user,row.id))):
            continue
        year=session.get(m.AcademicYear,row.academic_year_id)
        result.append(dict(id=row.id,label=f"{year.code} · {row.code}",state=row.state,
            can_manage=manage and row.state!="ARCHIVED",can_view_publications=belongs(session,user,row.id)))
    return result


def current(session,item):
    return session.scalar(select(m.OfficialFormVersion).where(m.OfficialFormVersion.official_form_id==item.id,
        m.OfficialFormVersion.state=="PUBLISHED"))


def version_out(session,version):
    file=session.get(m.StoredFile,version.stored_file_id)
    actor=session.get(m.UserAccount,version.uploaded_by)
    lecturer=session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id==actor.id))
    return dict(id=version.id,version_no=version.version_no,row_version=version.row_version,state=version.state,
        file_name=file.original_name,byte_size=file.byte_size,scan_state=file.scan_state,uploaded_at=version.created_at,
        uploaded_by_name=lecturer.display_name if lecturer else actor.email,
        source_reference=version.source_reference,change_reason=version.change_reason,published_at=version.published_at)


def item_out(session,user,item):
    query=select(m.OfficialFormVersion).where(m.OfficialFormVersion.official_form_id==item.id)
    if not manages(session,user,item.round_id):
        query=query.where(m.OfficialFormVersion.state.in_(["PUBLISHED","SUPERSEDED"]))
    versions=session.scalars(query.order_by(m.OfficialFormVersion.version_no.desc())).all()
    return dict(id=item.id,round_id=item.round_id,code=item.code,title=item.title,document_kind=item.document_kind,
        audience=item.audience,state=item.state,row_version=item.row_version,versions=[version_out(session,row) for row in versions])


def listing(session,user,round_id):
    round_row(session,round_id)
    if not any(row["id"]==round_id for row in access(session,user)):
        raise HTTPException(403,"Bạn chưa được xem kho tài liệu của đợt này")
    rows=session.scalars(select(m.OfficialForm).where(m.OfficialForm.round_id==round_id).order_by(m.OfficialForm.code)).all()
    manage=manages(session,user,round_id)
    return [item_out(session,user,item) for item in rows if visible(session,user,item) and (manage or current(session,item))]


def catalog(session,form_id,lock=False):
    query=select(m.OfficialForm).where(m.OfficialForm.id==form_id)
    row=session.scalar(query.with_for_update() if lock else query)
    if not row:
        raise HTTPException(404,"Không tìm thấy biểu mẫu/tài liệu Khoa")
    return row


def validate_audience(code,audience):
    if code in STAFF_ONLY and audience!="LECTURER":
        raise HTTPException(422,"Mẫu 6–11 chỉ dành cho giảng viên; không công bố cho sinh viên")


def create(session,user,data):
    require_manager(session,user,data.round_id)
    session.scalar(select(m.ThesisRound).where(m.ThesisRound.id==data.round_id).with_for_update())
    validate_audience(data.code,data.audience)
    if session.scalar(select(m.OfficialForm.id).where(m.OfficialForm.round_id==data.round_id,m.OfficialForm.code==data.code)):
        raise HTTPException(409,"Mã tài liệu đã có trong đợt; hãy mở hồ sơ đó để thêm phiên bản")
    item=m.OfficialForm(id=uuid4(),round_id=data.round_id,code=data.code,title=data.title,
        document_kind=data.document_kind,audience=data.audience,created_by=user.id,state="ACTIVE")
    session.add(item);audit(session,user,"OFFICIAL_FORM_CREATED","official_form",item.id,data.reason)
    session.flush();result=item_out(session,user,item);session.commit();return result


def update(session,user,form_id,data,expected):
    item=catalog(session,form_id,True);require_manager(session,user,item.round_id);row_version(expected,item.row_version)
    validate_audience(item.code,data.audience)
    item.title=data.title;item.audience=data.audience;item.state=data.state;item.row_version+=1
    audit(session,user,"OFFICIAL_FORM_METADATA_UPDATED","official_form",item.id,data.reason)
    session.flush();result=item_out(session,user,item);session.commit();return result


def valid_file(name,content):
    if Path(name).suffix.lower()!=".xlsx":
        if Path(name).suffix.lower() not in {".pdf",".docx"}:
            raise HTTPException(422,"Chỉ nhận PDF, DOCX hoặc XLSX (không nhận tệp có macro)")
        return documents.valid_content(name,content)
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries=archive.infolist();names={entry.filename for entry in entries}
            if len(entries)>3000 or sum(entry.file_size for entry in entries)>50*1024*1024 or not {"[Content_Types].xml","xl/workbook.xml"}<=names or any(entry.flag_bits&1 or entry.filename.lower().endswith("vbaproject.bin") for entry in entries):
                raise ValueError()
        from openpyxl import load_workbook
        workbook=load_workbook(io.BytesIO(content),read_only=True,data_only=True,keep_links=False);workbook.close()
    except Exception as exc:
        raise HTTPException(422,"Tệp XLSX không hợp lệ, có macro hoặc vượt giới hạn giải nén") from exc
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def read_file(request,upload):
    from backend.api.auth import _same_app_origin
    if not _same_app_origin(request):
        raise HTTPException(403,"Nguồn yêu cầu không được phép")
    name=(upload.filename or "").replace("\\","/").split("/")[-1].strip()
    if not name or len(name)>180 or any(ord(c)<32 for c in name):
        raise HTTPException(422,"Tên tệp không hợp lệ")
    chunks=[];size=0
    while chunk:=await upload.read(1024*1024):
        size+=len(chunk)
        if size>MAX_FORM_BYTES:raise HTTPException(413,"Tệp biểu mẫu Khoa tối đa 25 MB")
        chunks.append(chunk)
    content=b"".join(chunks)
    if not content:raise HTTPException(422,"Tệp rỗng")
    return name,content,valid_file(name,content)


async def upload(session,user,form_id,request,expected,source_reference,reason,file_upload):
    path=None
    try:
        item=catalog(session,form_id,True);require_manager(session,user,item.round_id);row_version(expected,item.row_version)
        if item.state!="ACTIVE":raise HTTPException(409,"Hồ sơ đã ngừng sử dụng")
        name,content,mime=await read_file(request,file_upload)
        file,_,path=documents.persist_upload(session,name,content,mime);file_scanner.scan(file,path);session.flush()
        latest=session.scalar(select(func.max(m.OfficialFormVersion.version_no)).where(m.OfficialFormVersion.official_form_id==item.id)) or 0
        version=m.OfficialFormVersion(id=uuid4(),official_form_id=item.id,version_no=latest+1,stored_file_id=file.id,
            uploaded_by=user.id,source_reference=source_reference,change_reason=reason,state="DRAFT")
        session.add(version);item.row_version+=1
        audit(session,user,"OFFICIAL_FORM_VERSION_UPLOADED","official_form",item.id,f"v{latest+1}: {reason}",after_hash=file.sha256)
        session.flush();result=item_out(session,user,item);session.commit();return result
    except Exception:
        session.rollback()
        if path and path.is_file():
            try:path.unlink()
            except OSError:pass
        raise


def version_row(session,item,version_id):
    version=session.scalar(select(m.OfficialFormVersion).where(m.OfficialFormVersion.id==version_id,
        m.OfficialFormVersion.official_form_id==item.id).with_for_update())
    if not version:raise HTTPException(404,"Không tìm thấy phiên bản")
    return version


def publish(session,user,form_id,version_id,data,expected):
    item=catalog(session,form_id,True);require_manager(session,user,item.round_id)
    version=version_row(session,item,version_id);row_version(expected,version.row_version)
    if item.state!="ACTIVE" or version.state!="DRAFT":raise HTTPException(409,"Chỉ phát hành bản nháp của hồ sơ đang dùng")
    latest=session.scalar(select(func.max(m.OfficialFormVersion.version_no)).where(m.OfficialFormVersion.official_form_id==item.id,m.OfficialFormVersion.state!="WITHDRAWN"))
    prior_published=session.scalar(select(func.max(m.OfficialFormVersion.version_no)).where(m.OfficialFormVersion.official_form_id==item.id,m.OfficialFormVersion.published_at.is_not(None))) or 0
    if latest!=version.version_no or version.version_no<=prior_published:raise HTTPException(409,"Chỉ phát hành bản mới nhất; không ghi đè bằng bản cũ")
    file=session.get(m.StoredFile,version.stored_file_id)
    documents.stored_download(session,SimpleNamespace(stored_file_id=file.id,content_sha256=file.sha256))
    old=current(session,item)
    if old:old.state="SUPERSEDED";old.row_version+=1;session.flush()
    version.state="PUBLISHED";version.published_by=user.id;version.published_at=now();version.row_version+=1;item.row_version+=1
    audit(session,user,"OFFICIAL_FORM_PUBLISHED","official_form",item.id,f"v{version.version_no}: {data.reason}",after_hash=file.sha256)
    session.flush();result=item_out(session,user,item);session.commit();return result


def withdraw(session,user,form_id,version_id,data,expected):
    item=catalog(session,form_id,True);require_manager(session,user,item.round_id)
    version=version_row(session,item,version_id);row_version(expected,version.row_version)
    if version.state=="WITHDRAWN":raise HTTPException(409,"Bản này đã thu hồi")
    version.state="WITHDRAWN";version.row_version+=1;item.row_version+=1
    audit(session,user,"OFFICIAL_FORM_WITHDRAWN","official_form",item.id,f"v{version.version_no}: {data.reason}")
    session.flush();result=item_out(session,user,item);session.commit();return result


def rescan(session,user,form_id,version_id,expected):
    item=catalog(session,form_id,True);require_manager(session,user,item.round_id)
    version=version_row(session,item,version_id);row_version(expected,version.row_version)
    if version.state!="DRAFT":raise HTTPException(409,"Chỉ quét lại bản nháp")
    file=session.get(m.StoredFile,version.stored_file_id)
    if file.scan_state=="INFECTED":raise HTTPException(409,"Tệp có mã độc; hãy tải bản sạch mới")
    file_scanner.require_available();file_scanner.scan(file,documents.storage_root()/Path(file.storage_key).name);version.row_version+=1
    session.flush();result=item_out(session,user,item);session.commit();return result


def downloadable(session,user,form_id,version_id):
    item=catalog(session,form_id)
    if not visible(session,user,item):raise HTTPException(404,"Không tìm thấy tài liệu trong phạm vi của bạn")
    version=session.scalar(select(m.OfficialFormVersion).where(m.OfficialFormVersion.id==version_id,m.OfficialFormVersion.official_form_id==item.id))
    if not version:raise HTTPException(404,"Không tìm thấy phiên bản")
    if not manages(session,user,item.round_id) and (version.state not in {"PUBLISHED","SUPERSEDED"} or not current(session,item)):
        raise HTTPException(404,"Phiên bản chưa phát hành hoặc đã thu hồi")
    file=session.get(m.StoredFile,version.stored_file_id)
    response=documents.stored_download(session,SimpleNamespace(stored_file_id=file.id,content_sha256=file.sha256))
    response.media_type=file.media_type
    response.headers["content-type"]=file.media_type
    return item,version,file,response


def spreadsheet(session,user,form_id,version_id):
    _,_,file,response=downloadable(session,user,form_id,version_id)
    if not file.original_name.lower().endswith(".xlsx"):raise HTTPException(422,"Không phải tệp Excel")
    from openpyxl import load_workbook
    workbook=load_workbook(response.path,read_only=True,data_only=True,keep_links=False)
    sheets=[]
    try:
        for sheet in workbook.worksheets[:8]:
            rows=[]
            for cells in sheet.iter_rows(max_row=min(sheet.max_row or 0,200),max_col=min(sheet.max_column or 0,30)):
                row=[]
                for cell in cells:
                    value=cell.value
                    if isinstance(value,(date,datetime)):value=value.isoformat()
                    elif isinstance(value,int) and len(cell.number_format)>1 and set(cell.number_format)=={"0"}:value=str(value).zfill(min(len(cell.number_format),30))
                    row.append("" if value is None else str(value)[:2000])
                rows.append(row)
            sheets.append(dict(name=sheet.title,rows=rows,truncated=(sheet.max_row or 0)>200 or (sheet.max_column or 0)>30))
        return dict(sheets=sheets,truncated=len(workbook.worksheets)>8)
    finally:workbook.close()


def default_round(session,user):
    rows=access(session,user)
    return rows[0]["id"] if rows else None


def compatibility_list(session,user,round_id=None):
    if user.base_role not in {"STUDENT","LECTURER"}:raise HTTPException(403,"Vai trò này không tải biểu mẫu nghiệp vụ")
    round_id=round_id or default_round(session,user)
    result={item["id"]:item for item in form_templates.list_official_templates(user.base_role)}
    if not round_id:return list(result.values())
    for item in session.scalars(select(m.OfficialForm).where(m.OfficialForm.round_id==round_id,m.OfficialForm.document_kind=="FORM")):
        result.pop(item.code,None)
        if not visible(session,user,item):continue
        version=current(session,item)
        if version:
            file=session.get(m.StoredFile,version.stored_file_id)
            if file.scan_state=="CLEAN":result[item.code]=dict(id=item.code,title=item.title,filename=file.original_name,byte_size=file.byte_size,extension=Path(file.original_name).suffix.lower(),version_no=version.version_no)
    return list(result.values())


def compatibility_download(session,user,code,round_id=None):
    code={"plan":"mau-02","proposal":"mau-03"}.get(code,code)
    if user.base_role not in {"STUDENT","LECTURER"}:raise HTTPException(403,"Vai trò này không tải biểu mẫu nghiệp vụ")
    round_id=round_id or default_round(session,user)
    item=session.scalar(select(m.OfficialForm).where(m.OfficialForm.round_id==round_id,m.OfficialForm.code==code)) if round_id else None
    if item:
        if not visible(session,user,item) or item.document_kind!="FORM":raise HTTPException(403,"Không được tải biểu mẫu này")
        version=current(session,item)
        if version:return downloadable(session,user,item.id,version.id)[3]
        raise HTTPException(409,"Khoa chưa phát hành hoặc đã tạm ngừng biểu mẫu này")
    return None


def bootstrap(session,user,round_id,*,batch_limit=None):
    require_manager(session,user,round_id);paths=[];created=published=0;missing=[]
    try:
        # Serialize batch initialization for this round.
        session.scalar(select(m.ThesisRound).where(m.ThesisRound.id==round_id).with_for_update())
        for meta in form_templates.OFFICIAL_FORMS:
            if batch_limit is not None and created>=batch_limit:break
            if session.scalar(select(m.OfficialForm.id).where(m.OfficialForm.round_id==round_id,m.OfficialForm.code==meta["id"])):continue
            source=form_templates.OFFICIAL_DIR/meta["filename"]
            if not source.is_file():missing.append(meta["filename"]);continue
            content=source.read_bytes()
            if len(content)>MAX_FORM_BYTES:raise HTTPException(413,"Biểu mẫu nguồn vượt quá 25 MB")
            mime=valid_file(source.name,content)
            item=m.OfficialForm(id=uuid4(),round_id=round_id,code=meta["id"],title=meta["title"],document_kind="FORM",
                audience="STUDENT_AND_LECTURER" if meta["id"] in form_templates.STUDENT_FORM_IDS else "LECTURER",created_by=user.id,state="ACTIVE")
            session.add(item);session.flush()
            file,_,path=documents.persist_upload(session,source.name,content,mime);paths.append(path);file_scanner.scan(file,path);session.flush()
            clean=file.scan_state=="CLEAN"
            version=m.OfficialFormVersion(id=uuid4(),official_form_id=item.id,version_no=1,stored_file_id=file.id,uploaded_by=user.id,
                source_reference="docs/BieuMau/"+source.name,change_reason="Chuyển nguyên bản bộ mẫu Khoa đang phát hành vào kho quản lý phiên bản",
                state="PUBLISHED" if clean else "DRAFT",published_by=user.id if clean else None,published_at=now() if clean else None)
            session.add(version);created+=1;published+=int(clean)
            audit(session,user,"OFFICIAL_FORM_BOOTSTRAPPED","official_form",item.id,version.change_reason,after_hash=file.sha256)
        if not created and missing:raise HTTPException(409,"Chưa có tệp mẫu nguồn trong môi trường này; không tạo mẫu thay thế")
        remaining=sum(1 for meta in form_templates.OFFICIAL_FORMS if (form_templates.OFFICIAL_DIR/meta["filename"]).is_file() and not session.scalar(select(m.OfficialForm.id).where(m.OfficialForm.round_id==round_id,m.OfficialForm.code==meta["id"])))
        session.commit();return dict(created=created,published=published,drafts=created-published,missing=missing,remaining=remaining)
    except Exception:
        session.rollback()
        for path in paths:
            try:path.unlink(missing_ok=True)
            except OSError:pass
        raise
