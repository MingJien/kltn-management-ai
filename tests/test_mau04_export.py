from io import BytesIO
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Border, Font, Side
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import form_templates
from backend.services.school_form_list_export import render_nop_ds
from backend.services.theses import now
from test_registration import hdr, scenario
from test_core_workspace import workspace
from test_school_forms import forms


def test_mau04_export_tracks_active_members_and_checks_permissions(forms, tmp_path, monkeypatch):
    client, users, students, lecturers, session, round_id = forms
    monkeypatch.setattr(form_templates, "OFFICIAL_DIR", tmp_path)
    template = Workbook()
    sheet = template.active
    sheet.title = "Nộp ds"
    template.create_sheet("Lịch báo cáo")
    for cell, value in {"A1":"TRƯỜNG ĐẠI HỌC ĐỒNG THÁP", "D1":"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
                        "A2":"KHOA CÔNG NGHỆ VÀ KỸ THUẬT", "D2":"Độc lập - Tự do - Hạnh phúc",
                        "A4":"DANH SÁCH SINH VIÊN VÀ GIẢNG VIÊN HƯỚNG DẪN KHÓA LUẬN TỐT NGHIỆP"}.items():
        sheet[cell] = value
    sheet.append([])
    for col, value in enumerate(("Stt", "Mã số sinh viên", "Họ tên sinh viên", "Lớp", "Khoa", "Tên đề tài khóa luận", "Giảng viên hướng dẫn", "Ghi chú"), 1):
        sheet.cell(7, col).value = value
    sheet["C30"] = "P. TRƯỞNG KHOA"
    sheet["F30"] = "NGƯỜI LẬP BẢNG"
    sheet["C34"] = "Tên người ký mẫu cũ"
    for area in ("D1:G1", "D2:G2", "A4:G4", "A5:G5", "F29:G29", "F30:G30", "F34:G34"):
        sheet.merge_cells(area)
    template.save(tmp_path / "mau 4.Mau DS SV THUC HIEN KLTN.xlsx")
    path = f"/api/v1/school-forms/rounds/{round_id}/mau-04"
    assert client.post(path, headers=hdr(users[0])).status_code == 403
    assert client.post(path, headers=hdr(users[3])).status_code == 403
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.round_id == round_id))
    thesis.current_title = "=đề tài giả lập"
    session.commit()
    preview = client.get(path + "/preview", headers=hdr(users[4]))
    assert preview.status_code == 200, preview.text
    assert preview.json()["students"] >= 1 and preview.json()["theses"] >= 1
    assert client.get(path + "/preview", headers=hdr(users[0])).status_code == 403
    response = client.post(path, headers=hdr(users[4]))
    assert response.status_code == 200, response.text
    result = load_workbook(BytesIO(response.content), data_only=False)
    assert result.sheetnames == ["Nộp ds"]
    result_sheet = result.active
    student_row = next(row for row in range(8, result_sheet.max_row + 1)
        if result_sheet.cell(row, 2).value == students[0].student_code)
    assert result_sheet.cell(student_row, 6).value == "=đề tài giả lập"
    assert result_sheet.cell(student_row, 6).data_type == "s"
    assert result_sheet.cell(student_row, 7).value == lecturers[0].display_name
    assert "Tên người ký mẫu cũ" not in str([c.value for row in result_sheet for c in row])
    member = session.scalar(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.student_id == students[0].id))
    member.active = False
    session.commit()
    refreshed = client.post(path, headers=hdr(users[4]))
    assert refreshed.status_code == 200
    refreshed_sheet = load_workbook(BytesIO(refreshed.content)).active
    codes = [refreshed_sheet.cell(row, 2).value for row in range(8, refreshed_sheet.max_row + 1)]
    assert students[0].student_code not in codes
    remaining = session.scalars(select(m.StudentProfile.student_code).join(m.ThesisMember,
        m.ThesisMember.student_id == m.StudentProfile.id).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.active.is_(True))).all()
    assert all(code in codes for code in remaining)
    admin = users[5]
    admin.base_role = "ADMIN"
    session.commit()
    assert client.post(path, headers=hdr(admin)).status_code == 200
    assignment = m.ResourceAssignment(id=uuid4(), user_id=admin.id, round_id=round_id,
        assignment_type="FORM_MANAGER", effective_from=now()-timedelta(minutes=1), state="ACTIVE")
    session.add(assignment)
    session.commit()
    assert client.post(path, headers=hdr(admin)).status_code == 200
    assignment.state = "REVOKED"
    session.commit()
    assert client.post(path, headers=hdr(admin)).status_code == 200
    for item in session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id)):
        item.active = False
    session.commit()
    assert client.get(path + "/preview", headers=hdr(users[4])).json()["students"] == 0
    empty = client.post(path, headers=hdr(users[4]))
    assert empty.status_code == 409
    assert "chưa có sinh viên" in empty.json()["detail"]


def test_nop_ds_preserves_template_and_moves_footer_for_large_group(tmp_path):
    template = Workbook()
    sheet = template.active
    sheet.title = "Nộp ds"
    template.create_sheet("Không xuất lịch")
    for cell, value in {"A1":"TRƯỜNG ĐẠI HỌC ĐỒNG THÁP", "D1":"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
                        "A2":"KHOA CÔNG NGHỆ VÀ KỸ THUẬT", "D2":"Độc lập - Tự do - Hạnh phúc",
                        "A4":"DANH SÁCH SINH VIÊN VÀ GIẢNG VIÊN HƯỚNG DẪN KHÓA LUẬN TỐT NGHIỆP",
                        "C30":"P. TRƯỞNG KHOA", "F30":"NGƯỜI LẬP BẢNG", "C34":"Tên ví dụ cũ"}.items():
        sheet[cell] = value
    for col, value in enumerate(("Stt", "Mã số sinh viên", "Họ tên sinh viên", "Lớp", "Khoa", "Tên đề tài khóa luận", "Giảng viên hướng dẫn", "Ghi chú"), 1):
        sheet.cell(7, col).value = value
    for area in ("D1:G1", "D2:G2", "A4:G4", "A5:G5", "F29:G29", "F30:G30", "F34:G34"):
        sheet.merge_cells(area)
    sheet.row_dimensions[8].height = 24.5
    sheet.row_dimensions[27].height = 24.5
    sheet.row_dimensions[28].height = 24.5
    sheet.row_dimensions[29].height = 26.5
    sheet.column_dimensions["F"].width = 64
    sheet.page_setup.orientation = "landscape"
    sheet["A4"].font = Font(name="Times New Roman", size=14, bold=True)
    sheet["C27"].border = Border(bottom=Side(style="thin"))
    sheet["C28"].border = Border(bottom=Side(style="medium"))
    path = tmp_path / "mau-04.xlsx"
    template.save(path)
    records = [(i, f"{i:011}", f"Sinh viên DEMO {i}", "Lớp giả lập", "Khoa giả lập", "Đề tài giả lập", "GV giả lập", "") for i in range(1, 26)]
    output = load_workbook(BytesIO(render_nop_ds(path, "2026-2027", records)))
    assert output.sheetnames == ["Nộp ds"]
    result = output.active
    assert result["A5"].value == "NĂM HỌC 2026-2027"
    assert result["B32"].value == "00000000025"
    assert result["C30"].value == "Sinh viên DEMO 23"
    assert result["C34"].value == "P. TRƯỞNG KHOA"
    assert result["F34"].value == "NGƯỜI LẬP BẢNG"
    assert result["C38"].value is None
    assert "F33:G33" in {str(area) for area in result.merged_cells.ranges}
    assert "F34:G34" in {str(area) for area in result.merged_cells.ranges}
    assert result.row_dimensions[33].height == 26.5
    assert result.column_dimensions["F"].width == 64
    assert result.page_setup.orientation == "landscape"
    assert result["A4"].font.name == "Times New Roman" and result["A4"].font.bold
    assert result["C28"].border.bottom.style == "thin"
    assert result["C32"].border.bottom.style == "medium"
    assert result.page_setup.fitToWidth == 1
    assert result.page_setup.fitToHeight == 0
    assert result.print_title_rows == "$1:$7"
    assert "$H$38" in str(result.print_area)


def test_nop_ds_rejects_a_template_without_the_expected_sheet(tmp_path):
    template = Workbook()
    path = tmp_path / "wrong.xlsx"
    template.save(path)
    with pytest.raises(HTTPException) as exc:
        render_nop_ds(path, "2026-2027", [])
    assert exc.value.status_code == 409
