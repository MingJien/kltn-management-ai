"""Content, source fidelity and pagination contracts for the four faculty forms."""
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from docx.oxml.ns import qn
from openpyxl import load_workbook
from pydantic import ValidationError

from backend.services import defense_templates as t
from backend.services.defense_export import notes, preview_sheet, response


def source(number):
    paths=list(t.form_templates.OFFICIAL_DIR.glob(f"mau {number}.*"))
    if not paths:pytest.skip("Faculty original not installed in this environment")
    return paths[0]


def data():
    people=[dict(id=str(i),name=f"Giảng viên {i}",role=role,unit="Công nghệ thông tin")
            for i,role in enumerate(["CHAIR","REVIEWER","REVIEWER","MEMBER","SECRETARY"])]
    council=NS(members=people,name="Hội đồng kiểm thử",reference="QĐ-TEST-2026")
    roster=[dict(id=str(i),student_id=str(i),name=f"Nguyễn Văn {'An' if i==0 else 'Bình'}",code="002341262"+str(i),
        class_name="ĐHCNTT22A",major="Công nghệ thông tin",birth_date="2004-03-15") for i in range(2)]
    slot=NS(minutes=dict(title="Đề tài kiểm thử",advisor="Giảng viên hướng dẫn",objectives="Mục tiêu nghiên cứu",
        functions="Các chức năng",achievements="Kết quả nghiên cứu",discussion="Câu hỏi và trả lời",
        conclusion="Kết luận của chủ tịch",recommendations="Kiến nghị hoàn thiện",classifications={"0":"Giỏi","1":"Khá"}),
        room="Phòng 201",attendance={"_council":{"present_ids":[p["id"] for p in people]}},
        marks={s["id"]:{p["id"]:{"note":f"Nhận xét {p['id']} cho {s['code']}"} for p in people} for s in roster})
    totals={s["id"]:dict(average="8.0",scores=["8.0"]*5,attendance={"status":"PRESENT"}) for s in roster}
    return council,roster,slot,totals


def test_minutes_preserve_source_sections_and_aggregate_every_signed_ballot():
    council,roster,slot,totals=data()
    doc=t.minutes_document(source(9),slot,council,roster,totals,notes(slot,council,roster),"v1",t.PrintLayout(),datetime.now(timezone.utc))
    text="\n".join(p.text for p in doc.paragraphs)
    for value in ["IV. NỘI DUNG HỌP","Mục tiêu:","Chức năng:","Kết quả đạt được:","V. KIẾN NGHỊ CỦA HỘI ĐỒNG","Xếp loại: Giỏi","Xếp loại: Khá"]:
        assert value in text
    for student in roster:
        for person in council.members:
            assert slot.marks[student["id"]][person["id"]]["note"] in text
    assert doc.sections[0].page_width==t.Document(source(9)).sections[0].page_width
    assert doc.tables[5].rows[0]._tr.trPr.find(qn("w:cantSplit")) is not None
    assert next(p for p in doc.paragraphs if p.text=="Kiến nghị hoàn thiện").paragraph_format.keep_with_next
    assert "ĐHCNTT22A" in doc.tables[2].cell(0,1).text


def test_score_sheet_preserves_merges_and_writes_literal_student_data():
    council,roster,slot,_=data()
    student={**roster[0],"name":"=NOT_A_FORMULA"}
    book=t.score_sheet(source(6),student,council.members[1],"Phản biện",slot.minutes["title"],"GVHD",
        {"scores":["0"]*12,"note":"Nội dung\nxuống dòng"},"1","1.0",False,"v1",t.PrintLayout(),datetime.now(timezone.utc))
    s=book.active
    assert str(s.merged_cells)==str(load_workbook(source(6)).active.merged_cells)
    assert "ĐHCNTT22A" in s["A7"].value and "Công nghệ thông tin" in s["A7"].value
    assert s["A6"].data_type=="s"
    assert s["F29"].value==1 and s["F29"].number_format=="0.0" and s.row_dimensions[31].height>=100
    out=BytesIO();book.save(out)
    result=preview_sheet(response(out,"test","xlsx"))
    assert b"rowspan" in result.body


def test_summary_grows_from_original_row_and_keeps_zero_grade():
    council,roster,_,_=data()
    rows=[({**roster[i%2],"code":str(i)},"0.0" if i==0 else "8.0") for i in range(36)]
    doc=t.summary_document(source(10),council,rows,"v1",t.PrintLayout(),datetime.now(timezone.utc))
    assert len(doc.tables[1].rows)==37
    assert doc.tables[1].cell(1,4).text=="0.0"
    assert all(r.cells[3].text=="ĐHCNTT22A" for r in doc.tables[1].rows[1:])
    assert doc.tables[1].rows[0]._tr.trPr.find(qn("w:tblHeader")) is not None


def test_official_sheet_expands_and_preserves_date_and_signature():
    council,roster,_,_=data()
    rows=[({**deepcopy(roster[i%2]),"code":"00"+str(i)},"8.5") for i in range(36)]
    s=t.official_sheet(source(11),council,NS(code="TEST"),rows,"v1",t.PrintLayout()).active
    assert s["B11"].value=="000" and s["E11"].value.year==2004
    assert s["F46"].value==8.5 and s["F46"].number_format=="0.0" and s["F53"].value=="Giảng viên 4"
    original=load_workbook(source(11)).active
    assert s["A7"].value==original["A7"].value and s["G7"].value==original["G7"].value
    assert "F48:G48" in str(s.merged_cells) and "F53:G53" in str(s.merged_cells)
    assert s.page_setup.fitToHeight==0


def test_layout_accepts_presentation_only_and_rejects_tiny_type_or_text_edits():
    for value in [{"font_size":4},{"line_spacing":.5},{"paragraph_space":50},{"scores":[10]},{"conclusion":"altered"}]:
        with pytest.raises(ValidationError):t.PrintLayout(**value)


def test_line_breaks_preserve_source_characters_and_reject_replacement_or_word_splitting():
    text="Kết quả 🧪 được kiểm chứng"
    layout=t.PrintLayout(line_breaks={"discussion":[0,7,7]})
    rendered=t.narrative_text(text,"discussion",layout)
    assert rendered.replace("\n","")==text
    assert layout.line_breaks["discussion"]==[0,7]
    from fastapi import HTTPException
    with pytest.raises(HTTPException):t.narrative_text(text,"discussion",t.PrintLayout(line_breaks={"discussion":[1]}))
    for value in [{"average":[1]},{"discussion":"new content"},{"discussion":[True]},{"discussion":[-1]},{"discussion":list(range(21))}]:
        with pytest.raises(ValidationError):t.PrintLayout(line_breaks=value)
