"""Versioned exports from faculty originals; academic values are server-owned."""
from io import BytesIO
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from sqlalchemy import func, select

from backend.db.models import entities as m
from backend.services import defense, defense_register, defense_templates as templates, workflow_notices
from backend.services.download_names import filename
from backend.services.theses import audit

MIME = {"docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def response(file, name, extension):
    return Response(file.getvalue(),media_type=MIME[extension],headers={
        "Content-Disposition":f'attachment; filename="{name}.{extension}"',"Cache-Control":"private, no-store"})


def stamp(identifier, version, instant, base_url):
    return f"{identifier} · {version} · {instant.astimezone(defense.VN):%d/%m/%Y %H:%M}"


def next_print_number(session,round_id,slot_id,form,student_id=None,lecturer_id=None,course_code=None):
    query=select(m.DefensePrintRecord).where(m.DefensePrintRecord.form==form,m.DefensePrintRecord.slot_id==slot_id) if slot_id else select(m.DefensePrintRecord).where(m.DefensePrintRecord.form==form,m.DefensePrintRecord.round_id==round_id,m.DefensePrintRecord.slot_id.is_(None))
    return 1+sum(all(row.source.get(k)==v for k,v in {'student_id':str(student_id) if student_id else None,'lecturer_id':str(lecturer_id) if lecturer_id else None,'course_code':course_code}.items()) for row in session.scalars(query))


def preview_sheet(result):
    """Read-only preview of the very same generated workbook, including merges."""
    book=load_workbook(BytesIO(result.body),data_only=True,rich_text=True)
    sheets=[]
    for sheet in book:
        merged={}
        for region in sheet.merged_cells.ranges:
            for row in range(region.min_row,region.max_row+1):
                for col in range(region.min_col,region.max_col+1):
                    merged[row,col]=(region.max_row-region.min_row+1,region.max_col-region.min_col+1) if (row,col)==(region.min_row,region.min_col) else None
        rows=[]
        for row in sheet.iter_rows(max_row=min(sheet.max_row,1000),max_col=min(sheet.max_column,30)):
            cells=[]
            for c in row:
                if (c.row,c.column) in merged and merged[c.row,c.column] is None:continue
                span=merged.get((c.row,c.column),(1,1))
                value=c.value
                if (c.coordinate=="A7" and value=="[ASCIMP]") or (c.coordinate=="G7" and value=="GhiChu"):
                    value=""  # internal import markers remain intact in the XLSX
                if hasattr(value,"strftime"):value=value.strftime("%d/%m/%Y")
                elif isinstance(value,(int,float)) and c.number_format in {"0.0","0.00"}:
                    value=f"{value:.{len(c.number_format)-2}f}"
                color=c.font.color
                rgb=color.rgb if color and color.type=="rgb" else None
                from openpyxl.cell.rich_text import CellRichText,TextBlock
                segments=[{"text":part.text if isinstance(part,TextBlock) else str(part),"bold":bool(part.font.b) if isinstance(part,TextBlock) else bool(c.font.b),"italic":bool(part.font.i) if isinstance(part,TextBlock) else bool(c.font.i)} for part in value] if isinstance(value,CellRichText) else None
                cells.append({"text":str(value) if value is not None else "","segments":segments,"rowspan":span[0],"colspan":span[1],
                    "color":"#"+rgb[-6:] if isinstance(rgb,str) and len(rgb)==8 else "#000000",
                    "bold":bool(c.font.bold),"italic":bool(c.font.italic),"size":c.font.sz or 12,
                    "rule_below":sheet['A2'].value=='PHIẾU ĐÁNH GIÁ' and c.row==1 and c.column in {1,3},
                    "align":c.alignment.horizontal if c.alignment.horizontal in {"left","center","right"} else "left"})
            rows.append(cells)
        sheets.append({"name":sheet.title,"rows":rows,"truncated":sheet.max_row>1000 or sheet.max_column>30,
            "row_heights":[sheet.row_dimensions[i].height for i in range(1,len(rows)+1)],
            "widths":[min(120,sheet.column_dimensions[get_column_letter(i)].width or 13)*7 for i in range(1,min(sheet.max_column,30)+1)]})
    return JSONResponse({"sheets":sheets},headers={"Cache-Control":"private, no-store"})


def notes(slot, council, roster):
    result = {"REVIEWER":[], "OTHER":[]}
    oral_comments = slot.minutes.get("oral_comments", {})
    for student in roster:
        for person in council.members:
            mark = slot.marks.get(student["id"],{}).get(person["id"], {})
            written = mark.get("note", "").strip()
            oral = oral_comments.get(student["id"], {}).get(person["id"], "").strip()
            comment = "\n".join(filter(None, [written, f"Ý kiến tại buổi họp: {oral}" if oral else ""]))
            if comment:
                result["REVIEWER" if person["role"]=="REVIEWER" else "OTHER"].append(
                    (f"{student['name']} — " if len(roster)>1 else '')+f"{person['name']} ({defense.ROLES[person['role']]}):\n{comment}")
    return {key:"\n".join(value) for key,value in result.items()}


def council_with_units(session, council):
    members=[]
    for person in council.members:
        lecturer=session.get(m.LecturerProfile,person["id"])
        department=session.get(m.Department,lecturer.department_id) if lecturer else None
        members.append({**person,"unit":department.name if department else ""})
    return SimpleNamespace(name=council.name,reference=council.reference,members=members,advisor_unit='')


def export_slot(session,user,identifier,form,base_url,student_id=None,lecturer_id=None,*,blank=False,layout=None,layout_fields=False,record=False,expected_revision=None):
    layout=layout or templates.PrintLayout()
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    slot,council,member,own,manager=defense.load_slot(session,user,identifier,write=record)
    if own or not (member or manager):raise HTTPException(403,"Chỉ hội đồng và người phụ trách được tải mẫu")
    allowed={"note"} if form==6 else {"objectives","functions","achievements","discussion","conclusion","recommendations","reviewer_comments","member_comments"}
    if (set(layout.line_breaks)|set(layout.tabs)|set(layout.field_styles))-allowed:raise HTTPException(422,"Chỉ định dạng các phần diễn giải có trong biểu mẫu này")
    if (layout_fields or layout.line_breaks or layout.tabs or layout.field_styles or layout.font_size or layout.narrative_bold is not None or layout.narrative_italic is not None) and (not member or member["role"]!="SECRETARY"):
        raise HTTPException(403,"Chỉ thư ký hội đồng được chỉnh trình bày bản xuất")
    blank=blank and form==6
    if record and (blank or not slot.finalized_at or layout_fields):
        raise HTTPException(409, "Chỉ lưu bản dùng để ký khi đã chốt phiên bảo vệ")
    if record and form==9 and defense.minutes_blockers(slot):
        raise HTTPException(409,'Biên bản lịch sử còn thiếu nội dung: '+'. '.join(defense.minutes_blockers(slot))+'. Lập đề nghị đính chính có căn cứ trước khi phát hành')
    if not slot.finalized_at and not blank and form!=6:raise HTTPException(409,"Chỉ xuất bản dùng để ký sau khi chốt kết quả")
    title=slot.minutes.get("title") or session.get(m.Thesis,slot.thesis_id).current_title
    roster=templates.academic_roster(session,slot)
    stamp_id=f"M{form}-{slot.id}"
    if form==6:stamp_id=f"M6-{str(slot.id).replace('-','')[:12]}-{str(student_id).replace('-','')[:8]}-{str(lecturer_id).replace('-','')[:8]}"
    record_id = uuid4() if record else None
    print_number=next_print_number(session,council.round_id,slot.id,form,student_id,lecturer_id)
    footer=f"Mẫu {form} · "+(f"Mã tra cứu: {record_id.hex[:12]} · Bản {print_number}" if record_id else "Bản xem trước")+f" · {defense.now().astimezone(defense.VN):%d/%m/%Y}"
    out=BytesIO()
    if form==6:
        student=next((r for r in roster if r["id"]==str(student_id)),None)
        evaluator=next((r for r in council.members if r["id"]==str(lecturer_id)),None)
        if not student or not evaluator or not (manager or (member and (
                member["id"]==evaluator["id"] or member["role"] in {"CHAIR","SECRETARY"}))):
            raise HTTPException(404,"Không tìm thấy phiếu chấm trong phạm vi của bạn")
        templates.require_metadata([student],["class_name","major","training_cohort"])
        mark={"scores":[None]*12,"note":""} if blank else slot.marks.get(student["id"],{}).get(evaluator["id"])
        if not mark:raise HTTPException(404,"Sinh viên không có phiếu chấm")
        if layout_fields:
            return JSONResponse({"fields":[{"key":"note","label":"Đề nghị / nhận xét","text":mark.get("note","")}]},headers={"Cache-Control":"private, no-store"})
        from backend.services.theses import primary_advisor
        advisor=primary_advisor(session,slot.thesis_id)
        advisor_name=slot.minutes.get("advisor") or (session.get(m.LecturerProfile,advisor.lecturer_id).display_name if advisor else "Chưa cập nhật")
        attendance=slot.attendance.get(student["id"],{})
        status="PHIẾU TRỐNG · CHƯA CÓ KẾT QUẢ · " if blank else "CHƯA CHỐT · " if not slot.finalized_at else ""
        path=templates.source(session,user,council.round_id,6)
        book=templates.score_sheet(path,student,evaluator,
            defense.ROLES[evaluator["role"]],title,advisor_name,mark,attendance.get("bonus","0"),
            None if blank else defense.total(mark,attendance),blank,status+footer,layout,slot.starts_at.astimezone(defense.VN))
        book.save(out)
        templates.restore_template_drawings(out,path)
        lecturer=session.get(m.LecturerProfile,lecturer_id)
        name = filename("Mau-06-Phieu-trong" if blank else "Mau-06-Phieu-cham",student["code"]+"-"+lecturer.lecturer_code,print_number)
        return print_response(session, user, out, name, "xlsx", record_id, council.round_id, form, path, layout,
            slot=slot, student_id=student_id, lecturer_id=lecturer_id,expected_revision=expected_revision)
    templates.require_metadata(roster,["class_name"])
    if layout_fields:
        comments=notes(slot,council,roster)
        values={**slot.minutes,"reviewer_comments":comments["REVIEWER"],"member_comments":comments["OTHER"]}
        labels={"objectives":"Mục tiêu","functions":"Chức năng","achievements":"Kết quả đạt được","discussion":"Nội dung họp","reviewer_comments":"Ý kiến phản biện","member_comments":"Ý kiến thành viên khác","conclusion":"Kết luận","recommendations":"Kiến nghị"}
        return JSONResponse({"fields":[{"key":key,"label":label,"text":values.get(key) or ""} for key,label in labels.items()]},headers={"Cache-Control":"private, no-store"})
    path=templates.source(session,user,council.round_id,9)
    council_data=council_with_units(session,council)
    from backend.services.theses import primary_advisor
    advisor=primary_advisor(session,slot.thesis_id)
    lecturer=session.get(m.LecturerProfile,advisor.lecturer_id) if advisor else None
    unit=session.get(m.Department,lecturer.department_id) if lecturer else None
    council_data.advisor_unit=unit.name if unit else ''
    doc=templates.minutes_document(path,slot,
        council_data,roster,defense.results(slot,council),notes(slot,council,roster),footer,
        layout,slot.starts_at.astimezone(defense.VN))
    doc.save(out)
    thesis=session.get(m.Thesis,slot.thesis_id);topic=session.get(m.Topic,thesis.topic_id);round_=session.get(m.ThesisRound,council.round_id)
    name=f"Bien-ban_{filename(round_.code)}_{filename(topic.code)}_{slot.starts_at.astimezone(defense.VN):%Y%m%d}_v{print_number}"
    return print_response(session, user, out, name, "docx", record_id, council.round_id, form, path, layout, slot=slot,expected_revision=expected_revision)


def export_round(session, user, identifier, form, base_url, *, layout=None, course_code=None, record=False,expected_revision=None):
    layout=layout or templates.PrintLayout()
    if record:
        session.execute(select(func.pg_advisory_xact_lock(66102)))
    round_, sessions = defense_register.require_round_access(session, user, identifier)
    data = defense_register.rows_for_sessions(session, sessions)
    problems = defense_register.export_readiness(data, sessions)
    if problems:
        raise HTTPException(409, ". ".join(problems))
    templates.require_metadata(data, ["class_name"] if form == 10 else ["birth_date"])
    if form == 11 and not course_code:
        raise HTTPException(422, "Chọn hoặc nhập mã học phần trước khi xuất Mẫu 11")
    rows = [(row, row["grade"]) for row in data]
    instant = defense.now()
    record_id = uuid4() if record else None
    print_number=next_print_number(session,identifier,None,form,course_code=course_code)
    footer=f"Mẫu {form} · "+(f"Mã tra cứu: {record_id.hex[:12]} · Bản {print_number}" if record_id else "Bản xem trước")+f" · {round_.code} · {instant.astimezone(defense.VN):%d/%m/%Y}"
    result_hash = sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    out=BytesIO()
    path=templates.source(session,user,identifier,form)
    scope = SimpleNamespace(name="Toàn đợt", reference=round_.code, summary_label=f"Đợt: {round_.code}",
                            members=[{"role": "SECRETARY", "name": ""}])
    if form == 10:
        extension = "docx"
        templates.summary_document(path,scope,rows,footer,layout,instant.astimezone(defense.VN)).save(out)
    else:
        extension = "xlsx"
        templates.official_sheet(path,scope,round_,rows,footer,layout,course_code=course_code).save(out)
    prefix = "Tong-hop-diem" if form == 10 else "Diem-hoc-phan"
    name = f"{prefix}_{filename(round_.code)}"+(f"_{course_code}" if form==11 else '')+f"_{instant.astimezone(defense.VN):%Y%m%d}_v{print_number}"
    return print_response(session,user,out,name,extension,record_id,identifier,form,path,layout,
        course_code=course_code, result_hash=result_hash,expected_revision=expected_revision)


def print_response(session, user, out, name, extension, record_id, round_id, form, path, layout, *,
                   slot=None, student_id=None, lecturer_id=None, course_code=None, result_hash=None,expected_revision=None):
    council=session.get(m.DefenseCouncil,slot.council_id) if slot else None
    fingerprint={'form':form,'slot':str(slot.id) if slot else None,'revision':slot.row_version if slot else None,
        'council':defense.council_signature(council) if council else None,'layout':layout.model_dump(mode='json'),
        'template':sha256(path.read_bytes()).hexdigest(),'student':str(student_id),'lecturer':str(lecturer_id),
        'course':course_code,'results':result_hash}
    revision=sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()
    if expected_revision is not None and expected_revision!=revision:
        raise HTTPException(409,'Dữ liệu hoặc định dạng đã đổi. Cập nhật bản xem trước rồi lưu lại bản dùng để ký')
    if record_id:
        if expected_revision is None:
            raise HTTPException(409,'Xem trước hồ sơ trước khi lưu bản dùng để ký')
        affected=select(m.DefenseCorrection.id).join(m.DefenseSlot,m.DefenseSlot.id==m.DefenseCorrection.slot_id)
        affected=affected.where(m.DefenseCorrection.state=='PENDING',m.DefenseSlot.id==slot.id) if slot else affected.join(
            m.DefenseCouncil,m.DefenseCouncil.id==m.DefenseSlot.council_id).where(m.DefenseCorrection.state=='PENDING',m.DefenseCouncil.round_id==round_id)
        if session.scalar(affected.limit(1)):
            raise HTTPException(409,'Có đề nghị đính chính chờ xử lý; giải quyết trước khi phát hành bản mới')
        content = out.getvalue()
        if len(content) > 30 * 1024 * 1024:
            raise HTTPException(409, "Bản xuất vượt 30 MB. Cần kiểm tra tệp mẫu của Khoa trước khi lưu")
        digest = sha256(content).hexdigest()
        source = {"template_sha256": sha256(path.read_bytes()).hexdigest(), "layout": layout.model_dump(mode="json"),
                  "slot_revision": slot.row_version if slot else None, "student_id": str(student_id) if student_id else None,
                  "lecturer_id": str(lecturer_id) if lecturer_id else None, "course_code": course_code,
                  "result_sha256": result_hash}
        source['print_number']=next_print_number(session,round_id,slot.id if slot else None,form,student_id,lecturer_id,course_code)
        family=select(m.DefensePrintRecord).where(m.DefensePrintRecord.slot_id==slot.id) if slot else select(m.DefensePrintRecord).where(m.DefensePrintRecord.round_id==round_id,m.DefensePrintRecord.slot_id.is_(None))
        for previous in session.scalars(family.where(m.DefensePrintRecord.form==form)):
            if all(previous.source.get(key)==source.get(key) for key in ('student_id','lecturer_id','course_code')) and not previous.source.get('superseded_by'):
                previous.source={**previous.source,'superseded_by':record_id.hex[:12],'superseded_at':defense.now().isoformat()}
        session.add(m.DefensePrintRecord(id=record_id, round_id=round_id, slot_id=slot.id if slot else None,
            created_by=user.id, created_at=defense.now(), form=form, filename=f"{name}.{extension}", sha256=digest,
            content=content, source=source))
        audit(session,user,"DEFENSE_PRINT_SAVED","defense_slot" if slot else "thesis_round",slot.id if slot else round_id,
              f"Mẫu {form} · {record_id.hex[:12]}",after_hash=digest)
        session.commit()
    result=response(out, name, extension)
    result.headers['X-Preview-Revision']=revision
    return result


def print_access(session, user, item):
    if item.slot_id is None:
        defense_register.require_round_access(session, user, item.round_id)
        return
    _, _, member, own, manager = defense.load_slot(session, user, item.slot_id)
    if own or not (member or manager):
        raise HTTPException(404, "Không tìm thấy bản in trong phạm vi của bạn")
    if item.form == 6 and not manager and (member["role"] not in {"CHAIR", "SECRETARY"} and member["id"] != item.source.get("lecturer_id")):
        raise HTTPException(404, "Không tìm thấy bản in trong phạm vi của bạn")


def print_history(session, user, *, round_id=None, slot_id=None):
    current_revision=None
    current_hash=None
    if slot_id:
        slot, _, member, own, manager = defense.load_slot(session, user, slot_id)
        current_revision=slot.row_version
        if own or not (member or manager):
            raise HTTPException(404, "Không tìm thấy bản in trong phạm vi của bạn")
        query = select(m.DefensePrintRecord).where(m.DefensePrintRecord.slot_id == slot_id)
    else:
        defense_register.require_round_access(session, user, round_id)
        current_hash=sha256(json.dumps(defense_register.rows_for_sessions(session,
            defense_register.council_sessions(session,round_id)),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        query = select(m.DefensePrintRecord).where(m.DefensePrintRecord.round_id == round_id, m.DefensePrintRecord.slot_id.is_(None))
    pending_query=select(m.DefenseCorrection.id).join(m.DefenseSlot,m.DefenseSlot.id==m.DefenseCorrection.slot_id).where(m.DefenseCorrection.state=='PENDING')
    pending_query=pending_query.where(m.DefenseSlot.id==slot_id) if slot_id else pending_query.join(m.DefenseCouncil,m.DefenseCouncil.id==m.DefenseSlot.council_id).where(m.DefenseCouncil.round_id==round_id)
    pending=bool(session.scalar(pending_query.limit(1)))
    rows = []
    latest_family={}
    for item in session.scalars(query.order_by(m.DefensePrintRecord.created_at.desc(), m.DefensePrintRecord.id.desc())):
        if slot_id and item.form == 6 and not manager and member["role"] not in {"CHAIR", "SECRETARY"} and member["id"] != item.source.get("lecturer_id"):
            continue
        family=(item.form,item.source.get('student_id'),item.source.get('lecturer_id'),item.source.get('course_code'))
        superseded=item.source.get('superseded_by') or latest_family.get(family)
        latest_family.setdefault(family,item.id.hex[:12])
        rows.append({"id": item.id, "form": item.form, "filename": item.filename, "created_at": item.created_at,
                     "actor": workflow_notices.actor_name(session, item.created_by),
                     "course_code": item.source.get("course_code"), "code": item.id.hex[:12],
                     'print_number':item.source.get('print_number'),
                     'can_withdraw':bool(manager or (member and member['role'] in {'CHAIR','SECRETARY'})) if slot_id else True,
                     'pending_correction':pending,'superseded_by':superseded,'withdrawn_reason':item.source.get('withdrawn_reason'),
                     "current": not superseded and not item.source.get('withdrawn_reason') and (item.source.get('slot_revision')==current_revision and bool(slot.finalized_at) if item.slot_id else item.source.get('result_sha256')==current_hash)})
        if len(rows) == 50:
            break
    return rows


def lookup_print(session,user,code):
    from sqlalchemy import cast,String
    if len(code)!=12 or any(c not in '0123456789abcdef' for c in code.lower()):raise HTTPException(422,'Nhập mã tra cứu 12 ký tự trên footer')
    matches=session.scalars(select(m.DefensePrintRecord).where(func.replace(cast(m.DefensePrintRecord.id,String),'-','').like(code.lower()+'%'))).all()
    if len(matches)!=1:raise HTTPException(404,'Không tìm thấy mã bản in')
    item=matches[0];print_access(session,user,item)
    history=print_history(session,user,slot_id=item.slot_id) if item.slot_id else print_history(session,user,round_id=item.round_id)
    return next((row for row in history if row['id']==item.id),{'id':item.id,'code':item.id.hex[:12],'filename':item.filename,'form':item.form,'current':False,'actor':workflow_notices.actor_name(session,item.created_by),'created_at':item.created_at})


def withdraw_print(session,user,identifier,reason):
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    item=session.get(m.DefensePrintRecord,identifier)
    if not item:raise HTTPException(404,'Không tìm thấy bản in')
    print_access(session,user,item)
    if item.slot_id:
        _,_,member,_,manager=defense.load_slot(session,user,item.slot_id)
        if not manager and (not member or member['role'] not in {'CHAIR','SECRETARY'}):raise HTTPException(403,'Chỉ thư ký, chủ tịch hoặc người quản lý được thu hồi bản in')
    if item.source.get('withdrawn_reason') or item.source.get('superseded_by'):raise HTTPException(409,'Bản in đã được thu hồi hoặc thay thế')
    item.source={**item.source,'withdrawn_reason':reason,'withdrawn_by':str(user.id),'withdrawn_at':defense.now().isoformat()}
    audit(session,user,'DEFENSE_PRINT_WITHDRAWN','defense_slot' if item.slot_id else 'thesis_round',item.slot_id or item.round_id,reason,source_reference=item.id.hex[:12])
    session.commit()


def download_print(session, user, identifier):
    item = session.get(m.DefensePrintRecord, identifier)
    if not item:
        raise HTTPException(404, "Không tìm thấy bản in đã lưu")
    print_access(session,user,item)
    if sha256(item.content).hexdigest() != item.sha256:
        raise HTTPException(409, "Bản in lưu trữ không khớp mã đối chiếu")
    name, extension = item.filename.rsplit(".", 1)
    return response(BytesIO(item.content), name, extension)
