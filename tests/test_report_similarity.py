from pathlib import Path
from time import monotonic

from docx import Document
from PIL import Image, ImageDraw, ImageFont
import pytest

from backend.services.report_similarity import extract, ocr_command, text_matches


def test_pdf_scan_matches_text_and_embedded_image_in_another_report(tmp_path):
    command = ocr_command()
    if not command:
        pytest.skip("Tesseract unavailable")
    font = None
    for family in ("arial.ttf","DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(family,44)
            break
        except OSError:
            pass
    if not font:
        pytest.skip("A font with Vietnamese characters is required")
    phrases = [
        "Hệ thống quản lý khóa luận tốt nghiệp",
        "Phân tích dữ liệu và đánh giá kết quả",
        "Sinh viên trình bày phương pháp nghiên cứu",
    ]
    image = Image.new("RGB",(1400,440),"white")
    drawer = ImageDraw.Draw(image)
    for i,phrase in enumerate(phrases):
        drawer.text((80,80+i*90),phrase,font=font,fill="black")
    picture = tmp_path/"embedded.png"
    scan = tmp_path/"scanned.pdf"
    image.save(picture)
    image.save(scan,"PDF",resolution=180)
    report = Document()
    report.add_paragraph(" ".join(phrases))
    report.add_picture(str(picture))
    other = tmp_path/"other.docx"
    report.save(other)

    left = extract(Path(scan),".pdf",command,monotonic()+20)
    right = extract(Path(other),".docx",command,monotonic()+20)
    assert left["images_ocr"]==1, left["warnings"]
    assert right["images_ocr"]==1, right["warnings"]
    matches = text_matches(left["text"],right["text"])
    assert {m["right_kind"] for m in matches if m["left_kind"]=="OCR"} == {"OCR","TEXT"}
    assert left["images"][0][1] is not None and right["images"][0][1] is not None
    assert (left["images"][0][1] ^ right["images"][0][1]).bit_count() <= 6
