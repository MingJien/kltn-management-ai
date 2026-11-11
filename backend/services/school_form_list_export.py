"""Export the current round roster using the faculty's Mẫu 4 layout."""
from copy import copy
from datetime import datetime
from io import BytesIO
from pathlib import Path
import textwrap
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from fastapi.responses import Response
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import documents, form_templates, school_forms
from backend.services.theses import audit, primary_advisor

HEADERS = ("Stt", "Mã số sinh viên", "Họ tên sinh viên", "Lớp", "Khoa", "Tên đề tài khóa luận", "Giảng viên hướng dẫn", "Ghi chú")


def template_path(session, round_id):
    item = session.scalar(select(m.OfficialForm).where(m.OfficialForm.round_id == round_id, m.OfficialForm.code == "mau-04"))
    if item:
        version = school_forms.current(session, item)
        if item.state != "ACTIVE" or item.document_kind != "FORM" or not version:
            raise HTTPException(409, "Mẫu 4 đang ngừng sử dụng hoặc chưa có bản phát hành.")
        stored = session.get(m.StoredFile, version.stored_file_id)
        if not stored or not stored.original_name.lower().endswith(".xlsx"):
            raise HTTPException(409, "Mẫu 4 đang áp dụng phải là tệp Excel .xlsx.")
        response = documents.stored_download(session, SimpleNamespace(stored_file_id=stored.id, content_sha256=stored.sha256))
        return Path(response.path)
    path = form_templates.OFFICIAL_DIR / "mau 4.Mau DS SV THUC HIEN KLTN.xlsx"
    if not path.is_file():
        raise HTTPException(409, "Chưa có Mẫu 4 của Khoa để xuất danh sách.")
    return path


def safe_value(cell, value):
    cell.value = value
    if isinstance(value, str):
        cell.data_type = "s"  # Text from accounts/topics must never become an Excel formula.


def render_nop_ds(path, year_code, records):
    """Populate a copy of Mẫu 4 while preserving the actual Nộp ds worksheet."""
    workbook = load_workbook(path, data_only=False, keep_links=False)
    try:
        if "Nộp ds" not in workbook.sheetnames:
            raise HTTPException(409, "Mẫu 4 không có trang tính 'Nộp ds'.")
        sheet = workbook["Nộp ds"]
        if sheet.max_row > 500 or sheet.max_column > 30:
            raise HTTPException(409, "Kích thước trang Mẫu 4 bất thường; cần kiểm tra mẫu trước khi xuất.")
        headers = tuple(str(sheet.cell(7, col).value or "").strip().casefold() for col in range(1, 9))
        if headers != tuple(value.casefold() for value in HEADERS):
            raise HTTPException(409, "Cấu trúc cột Mẫu 4 đã thay đổi; cần cập nhật cách xuất trước khi sử dụng.")
        for position in ("A1", "D1", "A2", "D2", "A4", "C30", "F30"):
            value = sheet[position].value
            if not isinstance(value, str) or value.startswith("="):
                raise HTTPException(409, "Bố cục Mẫu 4 đã thay đổi; cần kiểm tra mẫu trước khi xuất.")
        if sheet.protection.sheet:
            raise HTTPException(409, "Trang 'Nộp ds' đang được bảo vệ, không thể điền danh sách.")
        for other in tuple(workbook.worksheets):
            if other != sheet:
                workbook.remove(other)
        workbook.active = 0
        workbook.properties.creator = ""
        workbook.properties.lastModifiedBy = ""
        if sheet.sheet_view.pane is None:
            sheet.sheet_view.topLeftCell = "A1"
            for selection in sheet.sheet_view.selection:
                selection.activeCell = "A1"
                selection.sqref = "A1"
        sheet.sheet_view.zoomScale = 70
        sheet.sheet_view.zoomScaleNormal = 70

        # Only template labels and headings survive; sample names, signatures and
        # any old roster data must never be carried over into a fresh export.
        static = {"A1", "D1", "A2", "D2", "A4", "A5", "C30", "F30"}
        static.update(f"{get_column_letter(col)}7" for col in range(1, 9))
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell, MergedCell):
                    continue
                if cell.coordinate not in static:
                    cell.value = None
                cell.comment = None
                cell.hyperlink = None
        safe_value(sheet["A5"], f"NĂM HỌC {year_code}")
        safe_value(sheet["F29"], "Đồng Tháp, ngày ...... tháng ...... năm ........")

        # Insert above the last ruled row so its bottom border and the complete
        # signature block move together when there are more than 21 students.
        extra = max(0, len(records) - 21)
        if extra:
            moved_merges = []
            for merged in list(sheet.merged_cells.ranges):
                if merged.min_row < 28 <= merged.max_row:
                    raise HTTPException(409, "Mẫu 4 có ô gộp giao vùng danh sách; cần kiểm tra mẫu trước khi xuất.")
                if merged.min_row >= 28:
                    moved_merges.append(copy(merged))
                    sheet.unmerge_cells(str(merged))
            dimensions = {index: copy(dimension) for index, dimension in sheet.row_dimensions.items() if index >= 28}
            for index in dimensions:
                del sheet.row_dimensions[index]
            sheet.insert_rows(28, extra)
            for index, dimension in dimensions.items():
                dimension.index = index + extra
                sheet.row_dimensions[index + extra] = dimension
            for row in range(28, 28 + extra):
                sheet.row_dimensions[row].height = sheet.row_dimensions[27].height
                for col in range(1, 9):
                    sheet.cell(row, col)._style = copy(sheet.cell(27, col)._style)
            for merged in moved_merges:
                merged.shift(row_shift=extra)
                sheet.merge_cells(str(merged))

        for index, values in enumerate(records, 1):
            row = index + 7
            line_count = 1
            for col, value in enumerate(values, 1):
                cell = sheet.cell(row, col)
                safe_value(cell, value)
                if col >= 3 and isinstance(value, str) and value:
                    alignment = copy(cell.alignment)
                    alignment.wrap_text = True
                    if alignment.vertical is None:
                        alignment.vertical = "center"
                    cell.alignment = alignment
                    width = sheet.column_dimensions[get_column_letter(col)].width or 10
                    if len(value) > int(width * 1.25) or "\n" in value:
                        line_count = max(line_count, sum(max(1, len(textwrap.wrap(line, width=max(8, int(width)))))
                                                           for line in value.splitlines() or [""]))
            if line_count > 1:
                sheet.row_dimensions[row].height = max(sheet.row_dimensions[row].height or 0, line_count * 14 + 5)
        if sheet.sheet_properties.pageSetUpPr is None:
            sheet.sheet_properties.pageSetUpPr = PageSetupProperties()
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.print_title_rows = "1:7"
        sheet.print_area = f"A1:H{34 + extra}"
        result = BytesIO()
        workbook.save(result)
        return result.getvalue()
    finally:
        workbook.close()


def roster_records(session, user, round_id):
    round_ = school_forms.round_row(session, round_id)
    if not school_forms.can_export_list(session, user, round_id):
        raise HTTPException(403, "Cần quyền Điều phối KLTN hoặc Admin để xuất danh sách của đợt.")
    rows = session.execute(select(m.Thesis, m.StudentProfile, m.Faculty.name)
        .join(m.ThesisMember, m.ThesisMember.thesis_id == m.Thesis.id)
        .join(m.StudentProfile, m.StudentProfile.id == m.ThesisMember.student_id)
        .join(m.Department, m.Department.id == m.StudentProfile.department_id)
        .join(m.Faculty, m.Faculty.id == m.Department.faculty_id)
        .where(m.Thesis.round_id == round_id, m.Thesis.state != "WITHDRAWN", m.ThesisMember.active.is_(True))
        .order_by(m.StudentProfile.student_code, m.Thesis.id)).all()
    records = []
    for index, (thesis, student, faculty_name) in enumerate(rows, 1):
        assignment = primary_advisor(session, thesis.id)
        lecturer = session.get(m.LecturerProfile, assignment.lecturer_id) if assignment else None
        records.append((index, student.student_code, student.display_name, student.class_name or "", faculty_name,
                        thesis.current_title, lecturer.display_name if lecturer else "", "" if lecturer else "Chưa có GVHD chính thức"))
    return round_, rows, records


def preview_mau_04(session, user, round_id):
    round_, rows, records = roster_records(session, user, round_id)
    return {"round_id": str(round_.id), "round_code": round_.code, "students": len(records),
            "theses": len({thesis.id for thesis, _, _ in rows}),
            "missing_advisors": sum(1 for record in records if record[7])}


def export_mau_04(session, user, round_id):
    round_, rows, records = roster_records(session, user, round_id)
    if not records:
        raise HTTPException(409, "Đợt này chưa có sinh viên đang thực hiện khóa luận; hãy chọn đợt khác hoặc hoàn tất bước GV tiếp nhận.")
    year = session.get(m.AcademicYear, round_.academic_year_id)
    content = render_nop_ds(template_path(session, round_id), year.code, records)
    audit(session, user, "ROUND_MAU04_EXPORTED", "thesis_round", round_id,
          f"Xuất danh sách Mẫu 4: {len(records)} sinh viên; {datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat()}")
    session.commit()
    from backend.services.download_names import filename
    name=filename("Mau-04-Danh-sach-SV-GVHD",round_.code,extension=".xlsx")
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"',
                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
