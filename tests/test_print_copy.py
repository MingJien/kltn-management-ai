"""Pure local tests for footer generation; these tests do not connect to a database."""
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo
from zipfile import ZipFile

import pytest
from fastapi import HTTPException

from docx import Document
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, DecodedStreamObject, TextStringObject

from backend.services.proposal_export import _footer_lines, _print_bytes


def test_malformed_docx_returns_validation_error_instead_of_server_error():
    source = BytesIO()
    with ZipFile(source,"w") as archive:
        archive.writestr("[Content_Types].xml","broken XML")
        archive.writestr("word/document.xml","broken XML")
    with pytest.raises(HTTPException) as caught:
        _print_bytes(source.getvalue(),".docx",["Footer"])
    assert caught.value.status_code == 422


def test_pdf_print_copy_stamps_address_code_and_local_time_at_bottom_left():
    instant = datetime(2026, 10, 20, 10, 24, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    footer = _footer_lines("http://localhost:5173", "DC-2026-0001-V03", instant)
    assert footer == [
        "Xuất tại: http://localhost:5173",
        "Mã số: DC-2026-0001-V03",
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
    assert "Xuat tai:" in text and "Ma so:" in text and "Thoi diem xuat:" in text
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
    assert "Xuất tại: http://localhost:5173" in footer_text
    assert "Mã số: KH-2026-0001-V01" in footer_text
    assert "Thời điểm xuất: 10:24 20/10/2026" in footer_text


@pytest.mark.parametrize('rotation', [0, 90])
def test_pdf_footer_reserves_space_for_source_content_and_annotation(rotation):
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({
        NameObject('/F1'): DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 1 0 0 rg 1 0 0 1 30 22 Tm (ORIGINAL BOTTOM TEXT) Tj ET')
    page[NameObject('/Contents')] = stream
    page[NameObject('/Annots')] = ArrayObject([DictionaryObject({
        NameObject('/Type'): NameObject('/Annot'), NameObject('/Subtype'): NameObject('/Link'),
        NameObject('/Rect'): ArrayObject([FloatObject(x) for x in [30, 18, 200, 34]]),
        NameObject('/A'): DictionaryObject({NameObject('/S'): NameObject('/URI'), NameObject('/URI'): TextStringObject('https://example.test')})})])
    if rotation:
        page.rotate(rotation)
    source = BytesIO()
    writer.write(source)
    printed, _ = _print_bytes(source.getvalue(), '.pdf', ['Address', 'CODE-V01', '10:24 20/10/2026'])
    result = PdfReader(BytesIO(printed)).pages[0]
    assert 'ORIGINAL BOTTOM TEXT' in result.extract_text()
    assert 'CODE-V01' in result.extract_text()
    # Even an annotation at the old bottom edge must move above the footer band.
    assert float(result['/Annots'][0].get_object()['/Rect'][1]) >= 45
    assert list(result.mediabox) == ([0, 0, 842, 595] if rotation else [0, 0, 595, 842])
    assert b'1 1 1 rg' not in result.get_contents().get_data()
