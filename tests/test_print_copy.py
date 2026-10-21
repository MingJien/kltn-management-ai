"""Pure local tests for footer generation; these tests do not connect to a database."""
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from docx import Document
from pypdf import PdfReader, PdfWriter

from backend.services.proposal_export import _footer_lines, _print_bytes


def test_pdf_print_copy_stamps_address_code_and_local_time_at_bottom_left():
    instant = datetime(2026, 10, 20, 10, 24, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    footer = _footer_lines("http://localhost:5173", "DC-2026-0001-V03", instant)
    assert footer == [
        "Xuất từ: http://localhost:5173",
        "Mã: DC-2026-0001-V03",
        "Thời điểm xuất: 10:24 20/10/2026",
    ]

    source = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.write(source)

    printed, media_type = _print_bytes(source.getvalue(), ".pdf", footer)
    assert media_type == "application/pdf"
    page = PdfReader(BytesIO(printed)).pages[0]
    text = page.extract_text()
    assert "http://localhost:5173" in text
    assert "DC-2026-0001-V03" in text
    assert "10:24 20/10/2026" in text
    assert "Xuat tu:" in text and "Ma:" in text and "Thoi diem xuat:" in text
    assert PdfReader(BytesIO(source.getvalue())).pages[0].extract_text() in (None, "")


def test_docx_print_copy_stamps_vietnamese_footer_and_preserves_body():
    instant = datetime(2026, 10, 20, 10, 24, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    footer = _footer_lines("http://localhost:5173", "KH-2026-0001-V01", instant)
    source = BytesIO()
    original = Document()
    original.add_paragraph("Noi dung ban nop")
    original.save(source)

    printed, media_type = _print_bytes(source.getvalue(), ".docx", footer)
    assert media_type == (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    )
    result = Document(BytesIO(printed))
    assert [p.text for p in result.paragraphs] == ["Noi dung ban nop"]
    footer_text = "\n".join(
        p.text for section in result.sections for p in section.footer.paragraphs
    )
    assert "Xuất từ: http://localhost:5173" in footer_text
    assert "Mã: KH-2026-0001-V01" in footer_text
    assert "Thời điểm xuất: 10:24 20/10/2026" in footer_text
