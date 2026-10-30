"""The one-line print footer is present in a real PDF without replacing its pages."""
import io

from pypdf import PdfReader, PdfWriter

from backend.services.proposal_export import _stamp_pdf


def test_pdf_print_footer_is_readable_and_page_count_is_preserved():
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=595, height=842)
    source = io.BytesIO()
    writer.write(source)
    stamped = _stamp_pdf(source.getvalue(),
        "https://kltn.example.test, mã số DC-2026-001-V01, 10:24 20/10/2026")
    pages = PdfReader(io.BytesIO(stamped)).pages
    assert len(pages) == 2
    for page in pages:
        text = page.extract_text()
        assert "DC-2026-001-V01" in text
        assert "https://kltn.example.test" in text
        assert "10:24 20/10/2026" in text
        assert "ma so" in text and "Xuat tai" not in text
