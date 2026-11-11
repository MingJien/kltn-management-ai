from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from fastapi import HTTPException, Response
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import defense
from backend.services.download_names import filename

MIME = {
    "docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def response(file, name, extension):
    return Response(file.getvalue(),media_type=MIME[extension],headers={
        "Content-Disposition":f'attachment; filename="{name}.{extension}"',
        "Cache-Control":"private, no-store",
    })


def word(title, footer):
    doc = Document()
    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(12)
    banner = doc.add_table(rows=1, cols=2)
    banner.cell(0,0).text = "TRƯỜNG ĐẠI HỌC ĐỒNG THÁP\nKHOA CÔNG NGHỆ VÀ KỸ THUẬT"
    banner.cell(0,1).text = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(title).bold = True
    doc.sections[0].footer.paragraphs[0].add_run(footer).font.size = Pt(9)
    return doc


def table(doc, headings, rows):
    tab = doc.add_table(rows=1,cols=len(headings))
    tab.style = "Table Grid"
    for cell,text in zip(tab.rows[0].cells,headings):
        cell.text = text
    for row in rows:
        for cell,text in zip(tab.add_row().cells,row):
            cell.text = str(text)


def signature(doc,council,first):
    people = {member["role"]:member["name"] for member in council.members}
    tab = doc.add_table(rows=1,cols=2)
    tab.cell(0,0).text = f"{first}\n(Ký, ghi rõ họ tên)\n\n\n" + (people["CHAIR"] if first.startswith("CHỦ TỊCH") else "")
    tab.cell(0,1).text = "THƯ KÝ\n(Ký, ghi rõ họ tên)\n\n\n" + people["SECRETARY"]


def spreadsheet(title, footer):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    sheet.oddFooter.left.text = footer
    sheet.print_options.horizontalCentered = True
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    return workbook,sheet


def write_row(sheet, values):
    row = sheet.max_row + 1 if sheet["A1"].value is not None else 1
    for col,value in enumerate(values,1):
        cell = sheet.cell(row,col,value)
        # User-supplied names and notes stay literal even when they start with "=".
        if isinstance(value,str):
            cell.data_type = "s"
    return row


def format_sheet(sheet,header,widths):
    sheet.freeze_panes = f"A{header+1}"
    sheet.print_title_rows = f"1:{header}"
    for col,width in enumerate(widths,1):
        sheet.column_dimensions[get_column_letter(col)].width = width
        sheet.cell(header,col).font = Font(bold=True)
        sheet.cell(header,col).alignment = Alignment(wrap_text=True)


def stamp(identifier, version, instant, base_url):
    url = base_url.split("?")[0]
    return f"{identifier} · {version} · {instant.astimezone(defense.VN):%d/%m/%Y %H:%M} · {url}"


def export_slot(session,user,identifier,form,base_url,student_id=None,lecturer_id=None,*,blank=False):
    slot,council,member,own,manager = defense.load_slot(session,user,identifier)
    if own or not (member or manager):
        raise HTTPException(403,"Chỉ hội đồng và người phụ trách được tải mẫu")
    blank=blank and form==6
    if not slot.finalized_at and not blank and form != 6:
        raise HTTPException(409,"Chỉ xuất bản dùng để ký sau khi chốt kết quả")
    title = slot.minutes.get("title") or session.get(m.Thesis,slot.thesis_id).current_title
    stamp_id = f"M{form}-{slot.id}"
    if form == 6:
        stamp_id += f"-{student_id}-{lecturer_id}"
    footer = stamp(stamp_id,f"v{slot.row_version}",slot.finalized_at or defense.now(),base_url)
    if blank:
        footer="PHIẾU CHẤM TRỐNG · CHƯA CÓ KẾT QUẢ · "+footer
    out = BytesIO()
    if form == 6:
        student = next((row for row in slot.roster if row["id"]==str(student_id)),None)
        evaluator = next((row for row in council.members if row["id"]==str(lecturer_id)),None)
        if not student or not evaluator or not (manager or (member and (
            member["id"] == evaluator["id"] or member["role"] in {"CHAIR","SECRETARY"}))):
            raise HTTPException(404,"Không tìm thấy phiếu chấm trong phạm vi của bạn")
        mark = {"scores":[None]*12,"note":""} if blank else slot.marks.get(student["id"],{}).get(evaluator["id"])
        if not mark:
            raise HTTPException(404,"Sinh viên không có phiếu chấm")
        attendance = slot.attendance.get(student["id"],{})
        from backend.services import form_templates, school_forms
        managed = school_forms.compatibility_download(session,user,"mau-06",council.round_id)
        source = Path(managed.path) if managed else form_templates.OFFICIAL_DIR / next(
            item["filename"] for item in form_templates.OFFICIAL_FORMS if item["id"] == "mau-06")
        if not source.is_file():
            raise HTTPException(409,"Chưa có biểu mẫu Mẫu 6 của Khoa để xuất")
        book = load_workbook(source)
        sheet = book.active
        from backend.services.theses import primary_advisor
        advisor = primary_advisor(session,slot.thesis_id)
        advisor_name = session.get(m.LecturerProfile,advisor.lecturer_id).display_name if advisor else "Chưa cập nhật"
        fields = {"A5":f"Họ và tên (học hàm, học vị) người đánh giá: {evaluator['name']}    Nhiệm vụ trong hội đồng: {defense.ROLES[evaluator['role']]}",
            "A6":f"Họ và tên sinh viên: {student['name']}    Mã sinh viên: {student['code']}",
            "A7":f"Lớp: {student['class_name']}    Ngành: {student['major']}", "A8":f"Tên đề tài: {title}",
            "A9":"", "A10":f"Người hướng dẫn khoa học: {advisor_name}", "A30":f"III. Đề nghị (nếu có): {mark.get('note','')}"}
        for address,value in fields.items():
            sheet[address] = value
            sheet[address].data_type = "s"
            sheet[address].alignment = Alignment(horizontal="left",vertical="center",wrap_text=True)
        for row,score in zip([14,15,16,18,19,20,21,22,23,25,26,27],mark["scores"]):
            sheet[f"F{row}"] = None if blank else float(score)
        sheet["F28"] = None if blank else float(attendance.get("bonus","0"))
        for address in ("F13","F17","F24","F29"):
            sheet[address] = None
        if not blank:
            scores = [float(score) for score in mark["scores"]]
            sheet["F13"],sheet["F17"],sheet["F24"] = sum(scores[:3]),sum(scores[3:9]),sum(scores[9:])
            sheet["F29"] = float(defense.total(mark,attendance,".1"))
        sheet.oddFooter.left.text = ("CHUA CHOT · " if not slot.finalized_at else "") + footer
        book.save(out)
        lecturer = session.get(m.LecturerProfile, lecturer_id)
        name = filename("Mau-06-Phieu-trong" if blank else "Mau-06-Phieu-cham", student["code"]+"-"+lecturer.lecturer_code, slot.row_version)
        return response(out,name,"xlsx")

    doc = word("BIÊN BẢN HỌP HỘI ĐỒNG\nCHẤM KHÓA LUẬN TỐT NGHIỆP",footer)
    doc.add_heading("I. THÔNG TIN VỀ KHÓA LUẬN",2)
    doc.add_paragraph(f"Đề tài: {title}")
    if slot.minutes["advisor"]:
        doc.add_paragraph("Giảng viên hướng dẫn: " + slot.minutes["advisor"])
    table(doc,["Họ và tên","Mã sinh viên","Lớp"],[(r["name"],r["code"],r["class_name"]) for r in slot.roster])
    doc.add_heading("II. DANH SÁCH THÀNH VIÊN HỘI ĐỒNG",2)
    doc.add_paragraph(f"{council.name} · {council.reference}")
    table(doc,["STT","Họ và tên","Chức trách"],[(i,m["name"],defense.ROLES[m["role"]]) for i,m in enumerate(council.members,1)])
    present=slot.attendance.get("_council",{}).get("present_ids")
    if present is not None:
        doc.add_paragraph("Có mặt: "+", ".join(m["name"] for m in council.members if m["id"] in present))
        absent=[m["name"] for m in council.members if m["id"] not in present]
        if absent:
            doc.add_paragraph("Vắng: "+", ".join(absent))
    doc.add_heading("III. THỜI GIAN VÀ ĐỊA ĐIỂM HỌP",2)
    doc.add_paragraph(f"{slot.starts_at.astimezone(defense.VN):%d/%m/%Y %H:%M} – {slot.ends_at.astimezone(defense.VN):%d/%m/%Y %H:%M} · {slot.room}")
    doc.add_heading("IV. NỘI DUNG HỌP",2)
    doc.add_paragraph(slot.minutes["discussion"])
    totals = defense.results(slot,council)
    table(doc,["Sinh viên","Điểm KLTN","Ghi chú"],[(r["name"],totals[r["id"]]["average"] or "—",
        "Vắng: "+totals[r["id"]]["attendance"]["reason"] if totals[r["id"]]["average"] is None else "") for r in slot.roster])
    doc.add_heading("Kết luận",2)
    doc.add_paragraph(slot.minutes["conclusion"])
    signature(doc,council,"CHỦ TỊCH HỘI ĐỒNG")
    doc.save(out)
    return response(out,filename("Mau-09-Bien-ban",council.name,slot.row_version)+f"-{slot.starts_at.astimezone(defense.VN):%Y%m%d-%H%M}","docx")


def export_council(session,user,identifier,form,base_url):
    council = session.get(m.DefenseCouncil,identifier)
    lecturer = defense.lecturer_for(session,user)
    member = defense.membership(council,lecturer) if council else None
    if not council or not (defense.manages(session,user,lecturer,council.round_id,council.department_id) or (
        member and member["role"] in {"CHAIR","SECRETARY"})):
        raise HTTPException(404,"Không tìm thấy bảng điểm trong phạm vi của bạn")
    if not council.closed_at:
        raise HTTPException(409,"Khóa bảng điểm hội đồng trước khi xuất bản dùng để ký")
    slots = session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.council_id == identifier)
        .order_by(m.DefenseSlot.starts_at,m.DefenseSlot.id)).all()
    latest = {}
    for slot in slots:
        totals = defense.results(slot,council)
        for student in slot.roster:
            latest[student["student_id"]]=(student,totals[student["id"]]["average"])
    rows=list(latest.values())
    footer = stamp(f"M{form}-{council.id}","v1",council.closed_at,base_url)
    round_ = session.get(m.ThesisRound,council.round_id)
    out = BytesIO()
    if form == 10:
        doc = word("BẢNG ĐIỂM TỔNG HỢP KHÓA LUẬN TỐT NGHIỆP",footer)
        doc.add_paragraph(f"{council.name} · {round_.code} · {council.reference}")
        table(doc,["STT","Họ và tên","Mã sinh viên","Lớp","Điểm KLTN"],[
            (i,s["name"],s["code"],s["class_name"],score or "Vắng")
            for i,(s,score) in enumerate(rows,1)])
        signature(doc,council,"TRƯỞNG KHOA")
        doc.save(out)
        return response(out,filename("Mau-10-Bang-diem-tong-hop",council.name,1),"docx")
    book,sheet = spreadsheet("Mẫu 11",footer)
    write_row(sheet,["BẢNG GHI ĐIỂM CỦA HỌC PHẦN"])
    write_row(sheet,["Học phần","Khóa luận tốt nghiệp"])
    write_row(sheet,["Đợt",round_.code,"Hội đồng",council.name])
    write_row(sheet,["Giảng viên",next(m["name"] for m in council.members if m["role"]=="CHAIR"),"Bậc đào tạo","Đại học"])
    header = write_row(sheet,["STT","Mã sinh viên","Họ đệm","Tên","Ngày sinh","Cuối kỳ 100%","Ghi chú"])
    for i,(s,score) in enumerate(rows,1):
        parts = s["name"].rsplit(maxsplit=1)
        write_row(sheet,[i,s["code"],parts[0] if len(parts)==2 else "",parts[-1] if parts else "",
            None,float(score) if score is not None else None,"Vắng" if score is None else ""])
    write_row(sheet,["","Trưởng khoa (Ký, ghi rõ họ tên)","","","Thư ký (Ký, ghi rõ họ tên)"])
    format_sheet(sheet,header,[9,20,26,17,17,20,28])
    book.save(out)
    return response(out,filename("Mau-11-Bang-diem-chinh-thuc",council.name,1),"xlsx")
