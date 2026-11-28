"""Read-only access to the faculty-provided official templates.

The faculty files in ``docs/BieuMau`` are the only source of a blank form. This
module never generates, rewrites or stores a copy of them; when the file is not
present in the environment the caller must report that exporting is not
possible instead of inventing a look-alike form.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import os

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_DIR = Path(os.getenv("KLTN_OFFICIAL_TEMPLATE_DIR", str(ROOT / "docs" / "BieuMau"))).resolve()
PREVIEW_DIR = Path(os.getenv("KLTN_FORM_PREVIEW_DIR", str(ROOT / "local" / "school-form-previews"))).resolve()

TEMPLATES = {
    "plan": OFFICIAL_DIR / "mau 2.Ke hoach thuc hien cua SV.docx",
    "proposal": OFFICIAL_DIR / "mau 3.De cuong thuc hien de tai.docx",
}
UNAVAILABLE = ("Chưa có mẫu chính thức của Khoa trong môi trường này; "
               "hệ thống không tự dựng mẫu thay thế nên chưa thể xuất biểu mẫu.")

OFFICIAL_FORMS = [
    {
        "id": "mau-01a",
        "title": "Mẫu 1a - Đơn đăng ký làm KLTN cá nhân",
        "filename": "mau 1a.Don dang ky lam KLTN ca nhan.docx",
    },
    {
        "id": "mau-01b",
        "title": "Mẫu 1b - Đơn đăng ký làm KLTN theo nhóm",
        "filename": "mau 1b.Don dang ky lam KLTN theo nhom.docx",
    },
    {
        "id": "mau-02",
        "title": "Mẫu 2 - Kế hoạch thực hiện của SV",
        "filename": "mau 2.Ke hoach thuc hien cua SV.docx",
    },
    {
        "id": "mau-03",
        "title": "Mẫu 3 - Đề cương thực hiện đề tài",
        "filename": "mau 3.De cuong thuc hien de tai.docx",
    },
    {
        "id": "mau-04",
        "title": "Mẫu 4 - Danh sách sinh viên thực hiện KLTN",
        "filename": "mau 4.Mau DS SV THUC HIEN KLTN.xlsx",
    },
    {
        "id": "mau-05",
        "title": "Mẫu 5 - Quy định trình bày quyển báo cáo & bìa KLTN",
        "filename": "mau 5.Quy đinh trinh bay quyen bao cao & bia KLTN.docx",
    },
    {
        "id": "mau-06",
        "title": "Mẫu 6 - Phiếu đánh giá dành cho tất cả thành viên hội đồng",
        "filename": "mau 6.Phieu danh gia danh cho  tat ca thanh vien hoi dong.xlsx",
    },
    {
        "id": "mau-07",
        "title": "Mẫu 7 - Bản nhận xét KLTN dành cho GVHD",
        "filename": "mau 7.Ban nhan xet KLTN danh cho GVHD.docx",
    },
    {
        "id": "mau-08",
        "title": "Mẫu 8 - Bản nhận xét KLTN dành cho GVPB",
        "filename": "mau 8.Ban nhan xet KLTN danh cho GVPB.docx",
    },
    {
        "id": "mau-09",
        "title": "Mẫu 9 - Biên bản họp hội đồng chấm KLTN",
        "filename": "mau 9.Bien ban hop hoi dong cham KLTN.docx",
    },
    {
        "id": "mau-10",
        "title": "Mẫu 10 - Bảng điểm tổng hợp KLTN",
        "filename": "mau 10.Bang diem tong hop KLTN.docx",
    },
    {
        "id": "mau-11",
        "title": "Mẫu 11 - Bảng điểm chính thức",
        "filename": "mau 11.Bang diem chinh thuc.xlsx",
    },
]

STUDENT_FORM_IDS = {"mau-01a", "mau-01b", "mau-02", "mau-03", "mau-04", "mau-05"}

def list_sources() -> list[dict]:
    sources = []
    for meta in OFFICIAL_FORMS:
        path = OFFICIAL_DIR / meta["filename"]
        if path.is_file():
            sources.append({**meta, "byte_size": path.stat().st_size, "extension": path.suffix.lower()})
    return sources


def source_path(source_id: str) -> Path:
    for meta in OFFICIAL_FORMS:
        if meta["id"] == source_id:
            path = OFFICIAL_DIR / meta["filename"]
            if path.is_file():
                return path
            raise HTTPException(409, UNAVAILABLE)
    raise HTTPException(404, "Không tìm thấy tệp nguồn này")


def source_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def allowed_form(meta: dict, role: str) -> bool:
    if role == "LECTURER":
        return True
    if role == "STUDENT":
        return meta["id"] in STUDENT_FORM_IDS
    raise HTTPException(403, "Vai trò này không được tải biểu mẫu nghiệp vụ")


def list_official_templates(role: str) -> list[dict]:
    items = []
    if role not in {"STUDENT", "LECTURER"}:
        raise HTTPException(403, "Vai trò này không được tải biểu mẫu nghiệp vụ")
    if not OFFICIAL_DIR.is_dir():
        return items
    for meta in OFFICIAL_FORMS:
        path = OFFICIAL_DIR / meta["filename"]
        if allowed_form(meta, role) and path.is_file():
            items.append({
                "id": meta["id"],
                "title": meta["title"],
                "filename": meta["filename"],
                "byte_size": path.stat().st_size,
                "extension": path.suffix.lower(),
            })
    return items


def official_template_by_id(template_id: str, role: str) -> tuple[bytes, str, str]:
    if template_id == "plan":
        template_id = "mau-02"
    elif template_id == "proposal":
        template_id = "mau-03"
    meta = next((item for item in OFFICIAL_FORMS if item["id"] == template_id), None)
    if meta is None:
        raise HTTPException(404, "Không tìm thấy biểu mẫu này")
    if not allowed_form(meta, role):
        raise HTTPException(403, "Bạn không được tải biểu mẫu này")
    path = OFFICIAL_DIR / meta["filename"]
    if not path.is_file():
        raise HTTPException(409, UNAVAILABLE)
    suffix = path.suffix.lower()
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if suffix == ".docx"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return path.read_bytes(), meta["filename"], media_type


def official_template(kind: str) -> bytes:
    """Return the untouched bytes of an official template, or refuse to export."""
    path = TEMPLATES.get(kind)
    if path is None:
        raise HTTPException(404, "Không có biểu mẫu này")
    if not path.is_file():
        raise HTTPException(409, UNAVAILABLE)
    return path.read_bytes()


def template_available(kind: str) -> bool:
    path = TEMPLATES.get(kind)
    return bool(path and path.is_file())
