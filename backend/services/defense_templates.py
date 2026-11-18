"""Fill faculty originals without rebuilding their page furniture or table styles."""
from copy import copy, deepcopy
from hashlib import sha256
from math import ceil
from textwrap import wrap
from pathlib import Path
from typing import Annotated, Literal

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt
from fastapi import HTTPException
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import form_templates, school_forms


NarrativeKey=Literal["objectives","functions","achievements","discussion","conclusion","recommendations","note","reviewer_comments","member_comments"]
LineBreaks=dict[NarrativeKey,Annotated[list[Annotated[int,Field(ge=0,le=100000,strict=True)]],Field(max_length=20)]]


class FieldStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bold: bool | None = None
    italic: bool | None = None
    font_size: int | None = Field(default=None,ge=10,le=14)
    line_spacing: float | None = Field(default=None,ge=1,le=1.5)
    alignment: Literal['left','center','right','justify'] | None = None
    space_after: int | None = Field(default=None,ge=0,le=8)


class PrintLayout(BaseModel):
    """Presentation only. No document text, scores or roster accepted from a client."""
    model_config = ConfigDict(extra="forbid")
    font_size: int | None = Field(default=None, ge=11, le=14)
    line_spacing: float | None = Field(default=None, ge=1, le=1.5)
    paragraph_space: int | None = Field(default=None, ge=0, le=8)
    break_recommendations: bool = False
    narrative_bold: bool | None = None
    narrative_italic: bool | None = None
    line_breaks: LineBreaks = Field(default_factory=dict)
    tabs: LineBreaks = Field(default_factory=dict)
    field_styles: dict[NarrativeKey,FieldStyle] = Field(default_factory=dict)

    @field_validator("line_breaks")
    @classmethod
    def normalize_breaks(cls,value):
        return {key:sorted(set(positions)) for key,positions in sorted(value.items()) if positions}

    def code(self):
        return sha256(self.model_dump_json().encode()).hexdigest()[:8]


def narrative_text(text, key, layout):
    """Add line breaks only; preserve every character of the source content."""
    positions=layout.line_breaks.get(key,[])
    tabs=layout.tabs.get(key,[])
    for pos in [*positions,*tabs]:
        if pos>len(text) or not text or (0<pos<len(text) and not (text[pos-1].isspace() or text[pos].isspace())):
            raise HTTPException(422,"Chỉ ngắt dòng giữa các từ của nội dung đã lưu. Tải lại nội dung nếu hồ sơ đã thay đổi")
    for pos,character in sorted([(p,"\n") for p in positions]+[(p,"\t") for p in tabs],reverse=True):text=text[:pos]+character+text[pos:]
    return text


def narrative_style(paragraph,layout,key=None):
    style=layout.field_styles.get(key) if key else None
    for run in paragraph.runs:
        if layout.narrative_bold is not None:run.bold=layout.narrative_bold
        if layout.narrative_italic is not None:run.italic=layout.narrative_italic
        if style:
            if style.bold is not None:run.bold=style.bold
            if style.italic is not None:run.italic=style.italic
            if style.font_size:run.font.size=Pt(style.font_size)
    if style and style.line_spacing:paragraph.paragraph_format.line_spacing=style.line_spacing
    if style and style.space_after is not None:paragraph.paragraph_format.space_after=Pt(style.space_after)
    if style and style.alignment:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        paragraph.alignment={'left':WD_ALIGN_PARAGRAPH.LEFT,'center':WD_ALIGN_PARAGRAPH.CENTER,'right':WD_ALIGN_PARAGRAPH.RIGHT,'justify':WD_ALIGN_PARAGRAPH.JUSTIFY}[style.alignment]


def source(session, user, round_id, number):
    key = f"mau-{number:02}"
    managed = school_forms.compatibility_download(session, user, key, round_id)
    local = form_templates.OFFICIAL_DIR / next(
        item["filename"] for item in form_templates.OFFICIAL_FORMS if item["id"] == key)
    path = local if local.is_file() else Path(managed.path) if managed else local
    minutes_reference=form_templates.OFFICIAL_DIR / "Mẫu nd họp của 9.Bien ban hop hoi dong cham KLTN.docx"
    if number==9 and minutes_reference.is_file():path=minutes_reference
    if not path.is_file():
        raise HTTPException(409, f"Chưa có Mẫu {number} gốc của Khoa trong môi trường này")
    if path.suffix.lower() != (".xlsx" if number in {6,11} else ".docx"):
        raise HTTPException(409,f"Mẫu {number} đang phát hành không đúng định dạng để điền tự động. Cần tệp gốc {'Excel' if number in {6,11} else 'Word'}")
    return path


def academic_roster(session, slot):
    """Keep populated frozen data; repair only missing legacy profile metadata."""
    out = []
    for original in slot.roster:
        row = dict(original)
        student = session.get(m.StudentProfile, row["student_id"])
        if student and not slot.finalized_at:
            # Scheduling is a draft snapshot. Take verified profile corrections
            # up to finalization; afterwards keep populated historical values.
            row.update(name=student.display_name,code=student.student_code,class_name=student.class_name or "",
                major_code=student.major_code or "",major=student.major_code or "",
                birth_date=student.birth_date.isoformat() if student.birth_date else "",training_cohort=student.training_cohort or "")
        major_code = row.get("major_code") or (student.major_code if student else None)
        major = session.scalar(select(m.DepartmentMajor).where(
            m.DepartmentMajor.department_id == student.department_id,
            m.DepartmentMajor.code == major_code)) if student and major_code else None
        row["class_name"] = row.get("class_name") or (student.class_name if student else None) or ""
        row["major_code"] = major_code or ""
        row["major"] = (major.name if major and row.get("major") in {None, "", major_code} else row.get("major")) or major_code or ""
        if row["major"].startswith("Chưa xác minh"):row["major"]=""
        row["birth_date"] = row.get("birth_date") or (student.birth_date.isoformat() if student and student.birth_date else "")
        row["training_cohort"] = row.get("training_cohort") or (student.training_cohort if student else None) or ""
        row["department_id"] = str(student.department_id) if student else row.get("department_id", "")
        out.append(row)
    return out


def require_metadata(roster, fields):
    labels={"class_name":"lớp","major":"ngành","birth_date":"ngày sinh","training_cohort":"khóa học"}
    missing=[f"{s['code']}: {', '.join(labels[key] for key in fields if not str(s.get(key) or '').strip())}"
        for s in roster if any(not str(s.get(key) or '').strip() for key in fields)]
    if missing:
        raise HTTPException(409,"Chưa đủ thông tin để xuất bản ký. "+"; ".join(missing)+
            ". TBM/điều phối bổ sung tại Kết quả & xuất → Thông tin học vụ sinh viên, có căn cứ đính chính.")


def metadata_code(rows, *, include_birth=False):
    import json
    fields={"name","code","class_name","major","training_cohort"}
    if include_birth:fields.add("birth_date")
    public=[{key:value for key,value in r.items() if key in fields} for r in rows]
    return sha256(json.dumps(public, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]


def put(paragraph, value):
    """Retain paragraph and first run properties instead of assigning .text."""
    runs = paragraph.runs
    if not runs:
        paragraph.add_run(str(value))
    else:
        runs[0].text = str(value)
        for run in runs[1:]:
            run.text = ""
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(13)


def cell(cell_, value):
    put(cell_.paragraphs[0], value)
    for p in cell_.paragraphs[1:]:
        p._element.getparent().remove(p._element)


def after(paragraph, value, layout=None, key=None):
    element = deepcopy(paragraph._p)
    paragraph._p.addnext(element)
    from docx.text.paragraph import Paragraph
    result = Paragraph(element, paragraph._parent)
    put(result, value)
    result.paragraph_format.keep_with_next = False
    result.paragraph_format.keep_together = False
    result.paragraph_format.line_spacing = 1.15
    result.paragraph_format.space_before = Pt(0)
    result.paragraph_format.space_after = Pt(3)
    # Content inherits the template family and size, not a heading's emphasis.
    for run in result.runs:
        run.bold = False
        run.italic = False
    if layout:narrative_style(result,layout,key)
    return result


def paragraphs(doc):
    yield from doc.paragraphs
    for table in doc.tables:
        for row in table.rows:
            seen = set()
            for c in row.cells:
                if id(c._tc) not in seen:
                    seen.add(id(c._tc))
                    yield from c.paragraphs


def layout_word(doc, layout, footer, signature, anchor):
    compat=doc.settings.element.find(qn("w:compat"))
    if compat is None:
        compat=OxmlElement("w:compat");doc.settings.element.append(compat)
    compat.append(OxmlElement("w:doNotExpandShiftReturn"))
    for p in paragraphs(doc):
        p.paragraph_format.widow_control = True
        if layout.line_spacing is not None:
            p.paragraph_format.line_spacing = layout.line_spacing
        if layout.paragraph_space is not None:
            p.paragraph_format.space_after = Pt(layout.paragraph_space)
        if layout.font_size:
            for run in p.runs:
                run.font.size = Pt(layout.font_size)
    # An indivisible signature row travels with real preceding content.
    anchor.paragraph_format.keep_with_next = True
    anchor.paragraph_format.keep_together = True
    if layout.break_recommendations:
        anchor.paragraph_format.page_break_before = True
    tr = signature.rows[0]
    tr.height = Mm(45)
    from docx.enum.table import WD_ROW_HEIGHT_RULE
    tr.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    tr._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    for c in tr.cells:
        for p in c.paragraphs:
            p.paragraph_format.keep_together = True
            p.paragraph_format.keep_with_next = True
    tr.cells[-1].paragraphs[-1].paragraph_format.keep_with_next = False
    for table in doc.tables:
        positioning=table._tbl.tblPr.find(qn("w:tblpPr"))
        if positioning is not None:table._tbl.tblPr.remove(positioning)
        for row in table.rows:
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            if row.height is not None:row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST
    for section in doc.sections:
        for target in (section.footer,section.first_page_footer,section.even_page_footer):
            p = target.paragraphs[0]
            put(p, footer)
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:run.font.size = Pt(7)
    # Remove source placeholder whitespace immediately before signatures. Otherwise
    # keep-with-next joins only an empty line and allows an orphan signature page.
    node = signature._tbl.getprevious()
    while node is not None and node.tag == qn("w:p") and not "".join(node.itertext()).strip():
        prior = node.getprevious()
        node.getparent().remove(node)
        node = prior
    # Empty paragraphs inherited after a table can create a footer-only page.
    node=signature._tbl.getnext()
    while node is not None and node.tag==qn("w:p"):
        next_=node.getnext()
        from docx.text.paragraph import Paragraph
        if not Paragraph(node,doc._body).text.strip():node.getparent().remove(node)
        node=next_
    # Word requires a terminal paragraph after a table. Give its paragraph mark
    # 1pt instead of letting Word insert a full-height line on a new blank page.
    terminal=doc.add_paragraph()
    terminal.paragraph_format.space_before=Pt(0)
    terminal.paragraph_format.space_after=Pt(0)
    terminal.paragraph_format.line_spacing=Pt(1)
    mark=OxmlElement("w:rPr")
    size=OxmlElement("w:sz");size.set(qn("w:val"),"2");mark.append(size)
    terminal._p.get_or_add_pPr().append(mark)


def signature_names(table, chair, secretary, date, *, dean=False):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    for index,(heading,name) in enumerate([("Trưởng khoa" if dean else "CHỦ TỊCH HỘI ĐỒNG","" if dean else chair),("THƯ KÝ",secretary)]):
        c=table.cell(0,index)
        cell(c, "" if index==0 else f"Đồng Tháp, ngày {date.day:02} tháng {date.month:02} năm {date.year}")
        blocks=[c.paragraphs[0],c.add_paragraph(heading),c.add_paragraph("(Ký, ghi rõ họ tên)"),c.add_paragraph(name)]
        for p in blocks:
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after=Pt(0)
            p.paragraph_format.space_before=Pt(0)
            for r in p.runs:r.font.name="Times New Roman";r.font.size=Pt(13);r.italic=False
        blocks[1].runs[0].bold=True
        blocks[2].runs[0].italic=True
        blocks[2].paragraph_format.space_after=Mm(24)


def score_sheet(path, student, evaluator, role, title, advisor, mark, bonus, total, blank, footer, layout, date):
    book = load_workbook(path,rich_text=True)
    sheet = book.active
    if "PHIẾU ĐÁNH GIÁ" not in str(sheet["A2"].value):
        raise HTTPException(409,"Cấu trúc Mẫu 6 đang phát hành chưa được hỗ trợ. Kiểm tra lại tệp gốc của Khoa")
    if any(str(sheet[f'A{row}'].value).strip()!=code for row,code in zip([14,15,16,18,19,20,21,22,23,25,26,27],['1.1','1.2','1.3','2.1','2.2','2.3','2.4','2.5','2.6','3.1','3.2','3.3'])):
        raise HTTPException(409,'Vị trí tiêu chí Mẫu 6 đã đổi. Cần cập nhật ánh xạ trước khi điền điểm')
    fields = {
        "A5": f"Họ và tên (học hàm, học vị) người đánh giá: {evaluator['name']}\nNhiệm vụ trong hội đồng: {role}",
        "A6": f"Họ và tên sinh viên: {student['name']}     Mã sinh viên: {student['code']}",
        "A7": f"Lớp: {student['class_name'] or 'Chưa cập nhật'}     Ngành: {student['major'] or 'Chưa cập nhật'}     Khóa học: {student.get('training_cohort') or 'Chưa cập nhật'}",
        "A8": f"Tên đề tài: {title}", "A9": "", "A10": f"Người hướng dẫn khoa học: {advisor}",
        "A30": "III. Đề nghị (nếu có): " + narrative_text(mark.get("note", ""),"note",layout),
        "D31": f"Đồng Tháp, ngày {date.day:02} tháng {date.month:02} năm {date.year}\nNgười đánh giá\n(Ký, ghi rõ họ tên)\n\n\n\n\n\n{evaluator['name']}",
    }
    for address, value in fields.items():
        sheet[address] = value
        sheet[address].data_type = "s"
        sheet[address].alignment = Alignment(horizontal="center" if address == "D31" else "left", vertical="top", wrap_text=True)
    for index, row in enumerate([14,15,16,18,19,20,21,22,23,25,26,27]):
        sheet[f"F{row}"] = None if blank else float(mark["scores"][index])
    sheet["F28"] = float(bonus)
    for address in ("F13", "F17", "F24", "F29"):
        sheet[address] = None
    if not blank:
        values = [float(v) for v in mark["scores"]]
        sheet["F13"], sheet["F17"], sheet["F24"] = sum(values[:3]), sum(values[3:9]), sum(values[9:])
        sheet["F29"] = float(total)
    sheet["F29"].number_format="0.0"
    for row in [5,6,7,8,10,30]:
        value = str(sheet[f"A{row}"].value or "")
        note_style=layout.field_styles.get("note") if row==30 else None
        size=note_style.font_size if note_style and note_style.font_size else sheet[f"A{row}"].font.sz or 10
        lines = sum(max(1, ceil(len(line)/max(40,88*10/size))) for line in value.split("\n"))
        sheet.row_dimensions[row].height = max(sheet.row_dimensions[row].height or 15, lines * max(17,size*1.3) + 5)
    for row in range(12,30):
        text=str(sheet[f"B{row}"].value or "")
        size=layout.font_size or sheet[f"B{row}"].font.sz or 10
        lines=sum(max(1,len(wrap(part,width=max(40,int(76*10/size))))) for part in text.split("\n"))
        sheet.row_dimensions[row].height=max(sheet.row_dimensions[row].height or 15,lines*size*1.22+4)
    if layout.font_size:
        for address in ("E12", "F12"):
            sheet[address].alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
        sheet.row_dimensions[12].height=max(sheet.row_dimensions[12].height,layout.font_size*2.6)
    sheet.row_dimensions[31].height = 150
    if layout.narrative_bold is not None or layout.narrative_italic is not None:
        font=copy(sheet["A30"].font)
        if layout.narrative_bold is not None:font.b=layout.narrative_bold
        if layout.narrative_italic is not None:font.i=layout.narrative_italic
        sheet["A30"].font=font
    # Preserve rich formatting of fixed criteria; style only the inserted narrative.
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    style=layout.field_styles.get("note")
    sheet["A30"]=CellRichText(TextBlock(InlineFont(rFont="Times New Roman",sz=sheet["A30"].font.sz,b=True),"III. Đề nghị (nếu có): "),
        TextBlock(InlineFont(rFont="Times New Roman",sz=style.font_size if style and style.font_size else sheet["A30"].font.sz,
            b=style.bold if style and style.bold is not None else bool(layout.narrative_bold),
            i=style.italic if style and style.italic is not None else bool(layout.narrative_italic)),narrative_text(mark.get("note", ""),"note",layout)))
    sheet.page_setup.paperSize=sheet.PAPERSIZE_A4
    # The source uses zero top/bottom/footer margins, which clips signatures on
    # physical printers and even Excel PDF. Retain its grid, add print clearance.
    sheet.page_margins.top=.3
    sheet.page_margins.bottom=.5
    sheet.page_margins.footer=.2
    layout_sheet(sheet, layout, footer, "A1:F31")
    # M6 is a single complete signed sheet, including long comments. Very long
    # comments get their own continuation, rather than shrinking everything.
    if len(mark.get("note", "")) > 650:
        note = book.create_sheet("Nhận xét tiếp theo")
        note.column_dimensions["A"].width = 100
        note["A1"] = f"Nhận xét kèm phiếu · {student['code']} · {evaluator['name']}"
        formatted_note=narrative_text(mark["note"],"note",layout)
        chunks = []
        while len(formatted_note)>500:
            boundary=max(formatted_note.rfind(" ",0,500),formatted_note.rfind("\n",0,500))
            split=boundary+1 if boundary>0 else 500
            chunks.append(formatted_note[:split])
            formatted_note=formatted_note[split:]
        chunks.append(formatted_note)
        for i, text in enumerate(chunks, 2):
            note.cell(i,1,text).data_type = "s"
            note.cell(i,1).alignment = Alignment(wrap_text=True, vertical="top")
            from openpyxl.styles import Font
            note_size=style.font_size if style and style.font_size else layout.font_size or 11
            note.cell(i,1).font=Font(name="Times New Roman",size=note_size,b=style.bold if style and style.bold is not None else bool(layout.narrative_bold),i=style.italic if style and style.italic is not None else bool(layout.narrative_italic))
            note_lines=sum(max(1,len(wrap(part,width=max(45,int(100*11/note_size))))) for part in text.split("\n"))
            note.row_dimensions[i].height = max(100,note_lines*note_size*1.3+8)
        sheet["A30"] = "III. Đề nghị (nếu có): Xem trang Nhận xét tiếp theo kèm cùng mã bản xuất."
        sheet.row_dimensions[30].height = 34
        layout_sheet(note, layout, footer, f"A1:A{len(chunks)+1}")
        note.print_title_rows="1:1"
    return book


def layout_sheet(sheet, layout, footer, area):
    sheet.print_area = area
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1 if sheet.title != "Nhận xét tiếp theo" else 0
    sheet.print_options.horizontalCentered = True
    sheet.oddFooter.left.text = footer.replace("&", "&&")
    sheet.oddFooter.left.size = 7
    for row in sheet:
        for c in row:
            if c.value is not None and layout.font_size:
                font = copy(c.font)
                font.sz = layout.font_size
                c.font = font


def minutes_document(path, slot, council, roster, totals, notes, footer, layout, date):
    doc = Document(path)
    p, tables = doc.paragraphs, doc.tables
    if len(tables)==3 and len(p)>=37 and p[16].text.startswith('IV.'):
        return minutes_from_reference(doc,slot,council,roster,totals,notes,footer,layout,date)
    if len(tables)<6 or len(p)<26 or "IV." not in p[13].text:
        raise HTTPException(409,"Cấu trúc Mẫu 9 đã thay đổi. Cần cập nhật ánh xạ từ tệp gốc của Khoa trước khi xuất")
    cell(tables[1].cell(0,1), slot.minutes["title"])
    cell(tables[1].cell(1,2), "\n".join(r["name"] for r in roster))
    cell(tables[2].cell(0,1), "\n".join(r["class_name"] or "Chưa cập nhật" for r in roster))
    cell(tables[2].cell(0,3), "\n".join(r["code"] for r in roster))
    cell(tables[3].cell(0,1), slot.minutes.get("advisor", ""))
    order = {"CHAIR":0, "REVIEWER":1, "MEMBER":2, "SECRETARY":3}
    members = sorted(council.members, key=lambda r: order[r["role"]])
    roles = {"CHAIR":"Chủ tịch hội đồng", "SECRETARY":"Thư ký", "REVIEWER":"Phản biện", "MEMBER":"Ủy viên"}
    for index, person in enumerate(members,1):
        for col, value in enumerate([index, person["name"], person.get("unit", ""), roles[person["role"]]]):
            cell(tables[4].cell(index,col), str(value))
    present = slot.attendance.get("_council",{}).get("present_ids",[])
    put(p[7], f"(Theo Quyết định: {council.reference})")
    put(p[8], f"Tổng số: {len(members)}          Số có mặt: {len(present)}          Số vắng mặt: {len(members)-len(present)}")
    put(p[10], f"1. Thời gian: {date:%H:%M}, ngày {date:%d/%m/%Y}")
    put(p[11], f"2. Địa điểm: {slot.room}")
    for index, key, label in [(15,"objectives","Mục tiêu"),(16,"functions","Chức năng"),(17,"achievements","Kết quả đạt được")]:
        put(p[index], f"{label}: {narrative_text(slot.minutes.get(key) or '',key,layout) or 'Chưa ghi nhận riêng; xem nội dung họp bên dưới.'}")
        narrative_style(p[index],layout,key)
    after(p[17], narrative_text(slot.minutes["discussion"],"discussion",layout),layout,"discussion")
    after(p[18], narrative_text(notes["REVIEWER"],"reviewer_comments",layout) or "Không có nhận xét bổ sung trên phiếu chấm đã lưu.",layout,"reviewer_comments")
    after(p[19], narrative_text(notes["OTHER"],"member_comments",layout) or "Không có nhận xét bổ sung trên phiếu chấm đã lưu.",layout,"member_comments")
    after(p[20], narrative_text(slot.minutes["conclusion"],"conclusion",layout),layout,"conclusion")
    counts = []
    for row in roster:
        result = totals[row["id"]]
        marks = slot.marks.get(row["id"],{})
        valid = len([person for person in present if person in marks])
        issued=len(present) if result["attendance"].get("status")=="PRESENT" else 0
        counts.append(f"{row['name']} ({row['code']}): phát ra {issued}; thu về {valid}; hợp lệ {valid}.")
    put(p[22], "- Số phiếu phát ra / thu về / hợp lệ theo từng sinh viên:")
    put(p[23], "\n".join(counts))
    result_lines=[]
    for row in roster:
        r=totals[row["id"]]
        average=r.get("average")
        text = f"{row['name']} ({row['code']}): "
        text += f"Kết quả các phiếu: {', '.join(r['scores'])} điểm. Trung bình: {average} điểm. Xếp loại: {slot.minutes.get('classifications',{}).get(row['id']) or 'Chưa ghi nhận'}." if average is not None else "Vắng bảo vệ; chưa có điểm. " + r["attendance"].get("reason", "")
        result_lines.append(text)
    put(p[24], "\n".join(result_lines))
    p[24].paragraph_format.keep_with_next=True
    p[24].paragraph_format.keep_together=True
    for index in [13,14,18,19,20,21]:p[index].paragraph_format.keep_with_next=True
    recommendation_status = "Hội đồng xác nhận không có kiến nghị." if slot.minutes.get("no_recommendations") else "Chưa ghi nhận kiến nghị."
    anchor = after(p[25], narrative_text(slot.minutes.get("recommendations") or "","recommendations",layout) or recommendation_status,layout,"recommendations")
    p[25].paragraph_format.keep_with_next = True
    p[22].paragraph_format.keep_with_next = True
    p[23].paragraph_format.keep_with_next = True
    if layout.break_recommendations:
        p[21].paragraph_format.page_break_before = True
    people={r["role"]:r["name"] for r in members}
    signature_names(tables[5], people["CHAIR"], people["SECRETARY"], date)
    layout_word(doc, layout.model_copy(update={"break_recommendations":False}), footer, tables[5], anchor)
    return doc


def minutes_from_reference(doc,slot,council,roster,totals,notes,footer,layout,date):
    """Fill the newly supplied worked example without retaining any sample personal data."""
    from decimal import Decimal
    p=doc.paragraphs
    anchors={4:'1. Tên đề tài:',5:'2. Sinh viên thực hiện:',10:'II.',13:'III.',16:'IV.',21:'2. Ý kiến',24:'3. Ý kiến',26:'4. Kết luận',29:'5. Kết quả',33:'V.'}
    if any(not p[index].text.strip().startswith(text) for index,text in anchors.items()):
        raise HTTPException(409,'Bố trí mẫu nội dung họp Mẫu 9 đã đổi; cần cập nhật ánh xạ trước khi xuất')
    put(p[4],'1. Tên đề tài: '+slot.minutes['title'])
    put(p[5],'2. Sinh viên thực hiện: '+'; '.join(r['name'] for r in roster))
    put(p[6],'\n'.join(f"Lớp: {r['class_name']}     Mã sinh viên: {r['code']}" for r in roster))
    put(p[8],'Họ và tên (học hàm, học vị): '+slot.minutes.get('advisor',''))
    put(p[9],'Đơn vị: '+getattr(council,'advisor_unit',''))
    put(p[11],f'(Theo Quyết định: {council.reference})')
    present=slot.attendance.get('_council',{}).get('present_ids',[])
    put(p[12],f'Tổng số: 05          Số có mặt: {len(present):02}          Số vắng mặt: {5-len(present):02}')
    put(p[14],f'1. Thời gian: {date:%H:%M}, ngày {date:%d/%m/%Y}');put(p[15],'2. Địa điểm: '+slot.room)
    for index,key,label in [(18,'objectives','Mục tiêu'),(19,'functions','Chức năng'),(20,'achievements','Kết quả đạt được')]:
        put(p[index],f'{label}: '+narrative_text(slot.minutes.get(key) or '',key,layout));narrative_style(p[index],layout,key)
    if slot.minutes.get('discussion'):after(p[20],narrative_text(slot.minutes['discussion'],'discussion',layout),layout,'discussion')
    for index,key,value in [(22,'reviewer_comments',notes['REVIEWER']),(25,'member_comments',notes['OTHER']),(27,'conclusion',slot.minutes['conclusion']),(34,'recommendations',slot.minutes.get('recommendations') or 'Hội đồng xác nhận không có kiến nghị.')]:
        put(p[index],narrative_text(value,key,layout));narrative_style(p[index],layout,key)
    for index in [23,28,35,36]:p[index]._element.getparent().remove(p[index]._element)
    anchor=p[32]
    for i,row in enumerate(roster):
        result=totals[row['id']];scores=[Decimal(v) for v in result.get('scores',[]) if v is not None]
        count=len(scores);issued=len(present) if result['attendance'].get('status')=='PRESENT' else 0
        prefix=(row['name']+': ') if len(roster)>1 else ''
        lines=[f'{prefix}- Số phiếu phát ra: {issued:02}     - Số phiếu thu về: {count:02}',f'- Số phiếu hợp lệ: {count:02}']
        lines.append(f"- Kết quả: {sum(scores):.1f} điểm. Trung bình: {result['average']}     Xếp loại: {slot.minutes.get('classifications',{}).get(row['id'],'')}" if result.get('average') is not None else '- Vắng bảo vệ; chưa có điểm. '+result['attendance'].get('reason',''))
        if i==0:
            for index,value in zip([30,31,32],lines):put(p[index],value)
        else:
            for line in lines:anchor=after(anchor,line)
    order={'CHAIR':0,'REVIEWER':1,'MEMBER':2,'SECRETARY':3}
    for index,person in enumerate(sorted(council.members,key=lambda r:order[r['role']]),1):
        for column,value in enumerate([index,person['name'],person.get('unit',''),{'CHAIR':'Chủ tịch hội đồng','SECRETARY':'Thư ký','REVIEWER':'Phản biện','MEMBER':'Ủy viên'}[person['role']]]):cell(doc.tables[1].cell(index,column),str(value))
    people={person['role']:person['name'] for person in council.members}
    signature_names(doc.tables[2],people['CHAIR'],people['SECRETARY'],date)
    for index in [16,17,21,24,26,29,30,31,33]:p[index].paragraph_format.keep_with_next=True
    layout_word(doc,layout,footer,doc.tables[2],p[34])
    return doc


def restore_template_drawings(out,path):
    """openpyxl drops connector shapes. Retain the original drawing package for M6 rules."""
    from io import BytesIO
    from zipfile import ZipFile,ZIP_DEFLATED
    from lxml import etree
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    relns='http://schemas.openxmlformats.org/package/2006/relationships'
    with ZipFile(path) as original,ZipFile(BytesIO(out.getvalue())) as generated:
        parts={name:generated.read(name) for name in generated.namelist()}
        sheet=etree.fromstring(parts['xl/worksheets/sheet1.xml']);source=etree.fromstring(original.read('xl/worksheets/sheet1.xml'))
        drawing=source.find('s:drawing',ns)
        if drawing is None:return
        for old in sheet.findall('s:drawing',ns):sheet.remove(old)
        drawing=deepcopy(drawing);drawing.set('{'+ns['r']+'}id','rIdTemplateRules');sheet.append(drawing)
        relpath='xl/worksheets/_rels/sheet1.xml.rels'
        rels=etree.fromstring(parts[relpath]) if relpath in parts else etree.Element('{'+relns+'}Relationships',nsmap={None:relns})
        for old in list(rels):
            if old.get('Type','').endswith('/drawing'):rels.remove(old)
        etree.SubElement(rels,'{'+relns+'}Relationship',Id='rIdTemplateRules',Type=ns['r']+'/drawing',Target='../drawings/drawing1.xml')
        parts[relpath]=etree.tostring(rels);parts['xl/worksheets/sheet1.xml']=etree.tostring(sheet)
        for name in original.namelist():
            if name.startswith(('xl/drawings/','xl/media/')) and not name.endswith('/'):parts[name]=original.read(name)
        types=etree.fromstring(parts['[Content_Types].xml']);src_types=etree.fromstring(original.read('[Content_Types].xml'))
        known={(x.tag,x.get('PartName') or x.get('Extension')) for x in types}
        for node in src_types:
            if node.get('PartName') and node.get('PartName').lstrip('/') not in parts:continue
            if (node.tag,node.get('PartName') or node.get('Extension')) not in known:types.append(deepcopy(node))
        parts['[Content_Types].xml']=etree.tostring(types)
    result=BytesIO()
    with ZipFile(result,'w',ZIP_DEFLATED) as archive:
        for name,content in parts.items():archive.writestr(name,content)
    out.seek(0);out.truncate();out.write(result.getvalue());out.seek(0)


def summary_document(path, council, rows, footer, layout, date):
    if layout.break_recommendations:
        raise HTTPException(422,"Mẫu 10 tự giữ các hàng kết quả đi cùng vùng ký; không tách riêng trang ký")
    doc = Document(path)
    if len(doc.tables)<3 or len(doc.tables[1].columns)!=5:
        raise HTTPException(409,"Cấu trúc Mẫu 10 đã thay đổi. Kiểm tra tệp gốc của Khoa trước khi xuất")
    tab = doc.tables[1]
    template = deepcopy(tab.rows[1]._tr)
    for row in list(tab.rows)[1:]:
        tab._tbl.remove(row._tr)
    for index, (student, score) in enumerate(rows,1):
        tab._tbl.append(deepcopy(template))
        for c, value in zip(tab.rows[-1].cells, [index,student["name"],student["code"],student["class_name"] or "Chưa cập nhật",score if score is not None else student.get("outcome_label","Vắng")]):
            cell(c, str(value))
            margins=OxmlElement("w:tcMar")
            for edge, amount in (("top",50),("bottom",50),("left",80),("right",80)):
                side=OxmlElement(f"w:{edge}")
                side.set(qn("w:w"),str(amount));side.set(qn("w:type"),"dxa")
                margins.append(side)
            properties=c._tc.get_or_add_tcPr()
            for old in list(properties.findall(qn("w:tcMar"))):properties.remove(old)
            properties.append(margins)
    for row in list(tab.rows)[-min(2,len(rows)):]:
        for c in row.cells:
            for p in c.paragraphs:p.paragraph_format.keep_with_next=True
    tab.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    anchor = doc.paragraphs[5]
    separator = doc.paragraphs[4]
    separator.paragraph_format.keep_with_next = True
    separator.paragraph_format.line_spacing = Pt(1)
    scope = getattr(council, "summary_label", f"Hội đồng: {council.name} · {council.reference}")
    put(anchor, f"Danh sách có {len(rows)} sinh viên · {scope}")
    people={r["role"]:r["name"] for r in council.members}
    signature_names(doc.tables[2], "", people["SECRETARY"], date, dean=True)
    layout_word(doc, layout, footer, doc.tables[2], anchor)
    return doc


def official_sheet(path, council, round_, rows, footer, layout, *, course_code=None):
    book=load_workbook(path)
    s=book.active
    if course_code:
        s["B5"] = f"Học phần: [{course_code}] - Khóa luận tốt nghiệp"
    # Preserve the import markers from the original.
    s["B6"]=f"Đợt: {round_.code} · {council.name}"
    s["B7"]="Giảng viên: "+next((r["name"] for r in council.members if r["role"]=="CHAIR"), "")
    if len(rows)>7:
        extra=len(rows)-7
        # openpyxl does not translate merged ranges when inserting rows.
        merges=[str(r) for r in s.merged_cells.ranges if r.min_row>=18]
        for r in merges:s.unmerge_cells(r)
        s.insert_rows(18,extra)
        from openpyxl.worksheet.cell_range import CellRange
        for r in merges:
            region=CellRange(r);region.shift(row_shift=extra);s.merge_cells(str(region))
    count=max(7,len(rows))
    for index in range(count):
        r=11+index
        for col in range(1,8):
            s.cell(r,col)._style=copy(s.cell(11,col)._style)
            s.cell(r,col).value=None
        if index>=len(rows):continue
        student,score=rows[index]
        parts=student["name"].rsplit(maxsplit=1)
        from datetime import date
        dob=date.fromisoformat(student["birth_date"]) if student.get("birth_date") else "Chưa cập nhật"
        for col,value in enumerate([index+1,student["code"],parts[0] if len(parts)==2 else "",parts[-1],dob,float(score) if score is not None else None,student.get("outcome_label","Vắng") if score is None else ""],1):
            c=s.cell(r,col,value)
            if isinstance(value,str):c.data_type="s"
            c.alignment=Alignment(horizontal="left" if col in {3,4,7} else "center",vertical="center",wrap_text=True)
        s.cell(r,5).number_format="dd/mm/yyyy"
        s.cell(r,6).number_format="0.0"
        # Names and absence decisions wrap in their actual columns, not across
        # the combined full-name width. Excel does not auto-fit exported rows.
        height=25
        for col in (2,3,4,7):
            c=s.cell(r,col)
            size=layout.font_size or c.font.sz or 14
            width=s.column_dimensions[c.column_letter].width or 13
            capacity=max(3,int(width*11/(size*.9)))
            lines=sum(max(1,len(wrap(part,width=capacity))) for part in str(c.value or "").split("\n"))
            height=max(height,lines*size*1.35+6)
        s.row_dimensions[r].height=height
    s.cell(11+count,1,f"Danh sách có {sum(score is not None for _,score in rows)} sinh viên có điểm / {len(rows)} sinh viên")
    secretary=next(r["name"] for r in council.members if r["role"]=="SECRETARY")
    s.cell(17+count,6,secretary)
    s.print_title_rows="4:10"
    layout_sheet(s,layout,footer,f"A1:G{17+count}")
    # Preserve readable print size on a large council rather than one tiny page.
    heights=[s.row_dimensions[11+i].height or 25 for i in range(count)]
    if sum(heights)>500:
        from openpyxl.worksheet.pagebreak import Break
        s.page_setup.fitToHeight=0
        stops=[]
        first=0
        while sum(heights[first:])+110>500:
            stop=first
            used=0
            while stop<count and used+heights[stop]<=500:
                used+=heights[stop]
                stop+=1
            stop=min(stop,count-3)
            if stop<=first:break
            stops.append(stop)
            first=stop
        for stop in stops:s.row_breaks.append(Break(id=10+stop))
    return book
