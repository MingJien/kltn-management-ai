"""Versioned exports from faculty originals; academic values are server-owned."""
from io import BytesIO
from hashlib import sha256
from types import SimpleNamespace

from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import defense, defense_templates as templates
from backend.services.download_names import filename

MIME = {"docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def response(file, name, extension):
    return Response(file.getvalue(),media_type=MIME[extension],headers={
        "Content-Disposition":f'attachment; filename="{name}.{extension}"',"Cache-Control":"private, no-store"})


def stamp(identifier, version, instant, base_url):
    return f"{identifier} · {version} · {instant.astimezone(defense.VN):%d/%m/%Y %H:%M}"


def preview_sheet(result):
    """Read-only preview of the very same generated workbook, including merges."""
    book=load_workbook(BytesIO(result.body),data_only=True)
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
                cells.append({"text":str(value) if value is not None else "","rowspan":span[0],"colspan":span[1],
                    "color":"#"+rgb[-6:] if isinstance(rgb,str) and len(rgb)==8 else "#000000",
                    "bold":bool(c.font.bold),"italic":bool(c.font.italic),"size":c.font.sz or 12,
                    "align":c.alignment.horizontal if c.alignment.horizontal in {"left","center","right"} else "left"})
            rows.append(cells)
        sheets.append({"name":sheet.title,"rows":rows,"truncated":sheet.max_row>1000 or sheet.max_column>30,
            "widths":[min(120,sheet.column_dimensions[get_column_letter(i)].width or 13)*7 for i in range(1,min(sheet.max_column,30)+1)]})
    return JSONResponse({"sheets":sheets},headers={"Cache-Control":"private, no-store"})


def notes(slot, council, roster):
    result = {"REVIEWER":[], "OTHER":[]}
    for student in roster:
        for person in council.members:
            mark = slot.marks.get(student["id"],{}).get(person["id"])
            if mark and mark.get("note","").strip():
                result["REVIEWER" if person["role"]=="REVIEWER" else "OTHER"].append(
                    f"{student['name']} ({student['code']}) — {person['name']} ({defense.ROLES[person['role']]}):\n{mark['note']}")
    return {key:"\n\n".join(value) for key,value in result.items()}


def council_with_units(session, council):
    members=[]
    for person in council.members:
        lecturer=session.get(m.LecturerProfile,person["id"])
        department=session.get(m.Department,lecturer.department_id) if lecturer else None
        members.append({**person,"unit":department.name if department else ""})
    return SimpleNamespace(name=council.name,reference=council.reference,members=members)


def export_slot(session,user,identifier,form,base_url,student_id=None,lecturer_id=None,*,blank=False,layout=None,layout_fields=False):
    layout=layout or templates.PrintLayout()
    slot,council,member,own,manager=defense.load_slot(session,user,identifier)
    if own or not (member or manager):raise HTTPException(403,"Chỉ hội đồng và người phụ trách được tải mẫu")
    allowed={"note"} if form==6 else {"objectives","functions","achievements","discussion","conclusion","recommendations","reviewer_comments","member_comments"}
    if set(layout.line_breaks)-allowed:raise HTTPException(422,"Chỉ định dạng các phần diễn giải có trong biểu mẫu này")
    blank=blank and form==6
    if not slot.finalized_at and not blank and form!=6:raise HTTPException(409,"Chỉ xuất bản dùng để ký sau khi chốt kết quả")
    title=slot.minutes.get("title") or session.get(m.Thesis,slot.thesis_id).current_title
    roster=templates.academic_roster(session,slot)
    stamp_id=f"M{form}-{slot.id}"
    if form==6:stamp_id=f"M6-{str(slot.id).replace('-','')[:12]}-{str(student_id).replace('-','')[:8]}-{str(lecturer_id).replace('-','')[:8]}"
    footer=stamp(stamp_id,f"v{slot.row_version}",slot.finalized_at or defense.now(),base_url)
    footer+=f" · DL:{templates.metadata_code(roster)} · BT:{layout.code()}"
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
        footer+=f" · BM:{sha256(path.read_bytes()).hexdigest()[:10]}"
        book=templates.score_sheet(path,student,evaluator,
            defense.ROLES[evaluator["role"]],title,advisor_name,mark,attendance.get("bonus","0"),
            None if blank else defense.total(mark,attendance),blank,status+footer,layout,slot.starts_at.astimezone(defense.VN))
        book.save(out)
        lecturer=session.get(m.LecturerProfile,lecturer_id)
        return response(out,filename("Mau-06-Phieu-trong" if blank else "Mau-06-Phieu-cham",student["code"]+"-"+lecturer.lecturer_code,slot.row_version),"xlsx")
    templates.require_metadata(roster,["class_name"])
    if layout_fields:
        comments=notes(slot,council,roster)
        values={**slot.minutes,"reviewer_comments":comments["REVIEWER"],"member_comments":comments["OTHER"]}
        labels={"objectives":"Mục tiêu","functions":"Chức năng","achievements":"Kết quả đạt được","discussion":"Nội dung họp","reviewer_comments":"Ý kiến phản biện","member_comments":"Ý kiến thành viên khác","conclusion":"Kết luận","recommendations":"Kiến nghị"}
        return JSONResponse({"fields":[{"key":key,"label":label,"text":values.get(key) or ""} for key,label in labels.items()]},headers={"Cache-Control":"private, no-store"})
    path=templates.source(session,user,council.round_id,9)
    footer+=f" · BM:{sha256(path.read_bytes()).hexdigest()[:10]}"
    doc=templates.minutes_document(path,slot,
        council_with_units(session,council),roster,defense.results(slot,council),notes(slot,council,roster),footer,
        layout,slot.starts_at.astimezone(defense.VN))
    doc.save(out)
    return response(out,filename("Mau-09-Bien-ban",council.name,slot.row_version)+f"-{slot.starts_at.astimezone(defense.VN):%Y%m%d-%H%M}","docx")


def export_council(session,user,identifier,form,base_url,*,layout=None):
    layout=layout or templates.PrintLayout()
    council=session.get(m.DefenseCouncil,identifier)
    lecturer=defense.lecturer_for(session,user)
    member=defense.membership(council,lecturer) if council else None
    if not council or not (defense.manages(session,user,lecturer,council.round_id,council.department_id) or (
            member and member["role"] in {"CHAIR","SECRETARY"})):
        raise HTTPException(404,"Không tìm thấy bảng điểm trong phạm vi của bạn")
    if not council.closed_at:raise HTTPException(409,"Khóa bảng điểm hội đồng trước khi xuất bản dùng để ký")
    slots=session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.council_id==identifier)
        .order_by(m.DefenseSlot.starts_at,m.DefenseSlot.id)).all()
    latest={}
    for slot in slots:
        totals=defense.results(slot,council)
        for student in templates.academic_roster(session,slot):
            if totals[student["id"]]["average"] is None:
                decision=session.scalar(select(m.DefenseAbsenceDecision).where(m.DefenseAbsenceDecision.slot_id==slot.id,
                    m.DefenseAbsenceDecision.thesis_member_id==student["id"]))
                if decision:
                    student["outcome_label"]=("Không đạt do vắng" if decision.outcome=="NOT_PASSED" else "Chờ bảo vệ bổ sung")+" · "+decision.reference
            latest[student["student_id"]]=(student,totals[student["id"]]["average"])
    rows=list(latest.values())
    templates.require_metadata([s for s,_ in rows],["class_name"] if form==10 else ["birth_date"])
    footer=stamp(f"M{form}-{council.id}","v1",council.closed_at,base_url)
    footer+=f" · DL:{templates.metadata_code([s for s,_ in rows],include_birth=form==11)} · BT:{layout.code()}"
    out=BytesIO()
    path=templates.source(session,user,council.round_id,form)
    footer+=f" · BM:{sha256(path.read_bytes()).hexdigest()[:10]}"
    if form==10:
        templates.summary_document(path,council,rows,footer,layout,council.closed_at.astimezone(defense.VN)).save(out)
        return response(out,filename("Mau-10-Bang-diem-tong-hop",council.name,1),"docx")
    round_=session.get(m.ThesisRound,council.round_id)
    templates.official_sheet(path,council,round_,rows,footer,layout).save(out)
    return response(out,filename("Mau-11-Bang-diem-chinh-thuc",council.name,1),"xlsx")
