"""Fill the supplied provisional template without changing the source file."""
from io import BytesIO
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo

from docx import Document
from fastapi import HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services.theses import audit, now


def fields(session, item):
    student = session.get(m.StudentProfile, item.student_id)
    thesis = session.get(m.Thesis, item.thesis_id)
    topic = session.get(m.Topic, thesis.topic_id)
    members = session.scalars(select(m.StudentProfile).join(m.ThesisMember,
        m.ThesisMember.student_id == m.StudentProfile.id).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.active.is_(True)).order_by(m.StudentProfile.student_code)).all()
    return {**item.application_data, "student_name": item.application_data["student_name"],
        "major": student.major_code or "", "email": session.get(m.UserAccount, student.user_id).email,
        "topic_code": topic.code or "", "members": "; ".join(f"{s.display_name} ({s.student_code})" for s in members),
        "group": len(members) > 1, "starts_on": item.execution_starts_on.strftime("%d/%m/%Y")}


def export(session, user, item):
    from backend.services.form_templates import OFFICIAL_DIR
    from backend.services.proposal_export import _public_url, _stamp_docx
    from backend.services.withdrawals import code
    path = OFFICIAL_DIR / "Don_xin_thoi_thuc_hien_KLTN.docx"
    if not path.is_file():
        raise HTTPException(503, "Chưa có DOCX đơn xin thôi trong kho mẫu của máy chủ")
    doc = Document(BytesIO(path.read_bytes()))
    if len(doc.tables) != 5 or len(doc.tables[1].rows) != 3 or len(doc.tables[2].rows) != 5:
        raise HTTPException(409, "Cấu trúc mẫu đã thay đổi; cần cập nhật ánh xạ trước khi xuất")
    data = fields(session, item)
    def fill(cell, text):
        paragraph = cell.paragraphs[0]
        for run in paragraph.runs:
            run.text = ""
        paragraph.add_run(text)
    table = doc.tables[1]
    for row, col, value in [(0,1,data["student_name"]),(0,3,data["student_code"]),
        (1,1,data["class_name"]),(1,3,data["major"]),(2,3,data["email"])]:
        fill(table.cell(row,col), value)
    table = doc.tables[2]
    for row,col,value in [(0,2,data["round_code"]),(0,6,data["topic_code"]),(1,1,data["title"]),
        (2,3,data["advisor_name"]),(3,2,data["starts_on"]),
        (3,5,"Hình thức: " + ("Theo nhóm" if data["group"] else "Cá nhân")),(4,4,data["members"])]:
        fill(table.cell(row,col),value)
    fill(doc.tables[3].cell(0,0), item.reason)
    doc.paragraphs[0].insert_paragraph_before("MẪU TẠM CHƯA ĐƯỢC KHOA DUYỆT — KIỂM TRA TRƯỚC KHI IN KÝ")
    buffer = BytesIO()
    doc.save(buffer)
    instant = now()
    content = _stamp_docx(buffer.getvalue(), [f"Xuất tại: {_public_url()}",f"Mã đơn: {code(item)} | Mẫu tạm",
        instant.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M %d/%m/%Y")])
    audit(session, user, "WITHDRAWAL_PRINT_EXPORTED", "thesis_withdrawal_request", item.id,
        "Mẫu tạm; template_sha256=" + hashlib.sha256(path.read_bytes()).hexdigest(),
        after_hash=hashlib.sha256(content).hexdigest())
    session.commit()
    return Response(content,media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition":f'attachment; filename="{code(item)}.docx"'})
