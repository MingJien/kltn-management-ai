"""Compare two authorized reports, retaining the page or image behind every match."""
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
from itertools import islice
import os
from pathlib import Path
import re
import shutil
import subprocess
from time import monotonic
import unicodedata

from docx import Document
from fastapi import HTTPException
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import defense, documents, evaluation

MAX_PAGES = 60
MAX_IMAGES = 24
MAX_IMAGE_PIXELS = 20_000_000
WORDS = re.compile(r"\w+", re.UNICODE)
NGRAM = 5


def authorized_reports(session,user):
    lecturer = defense.lecturer_for(session,user)
    if not lecturer:
        raise HTTPException(403,"Chỉ giảng viên được phân quyền xử lý báo cáo")
    for thesis in session.scalars(select(m.Thesis).where(m.Thesis.state != "WITHDRAWN").order_by(m.Thesis.current_title)):
        if not defense.manages(session,user,lecturer,thesis.round_id,thesis.department_id):
            continue
        version = evaluation.report(session,thesis)
        file = session.get(m.StoredFile,version.stored_file_id) if version else None
        if version and file and file.scan_state=="CLEAN" and Path(file.original_name).suffix.lower() in {".pdf",".docx"}:
            yield thesis,version,file


def options(session,user):
    return [{"thesis_id":t.id,"title":t.current_title,"version_id":v.id,"version_no":v.version_no}
        for t,v,_ in authorized_reports(session,user)]


def ocr_command():
    override = os.getenv("KLTN_TESSERACT")
    path = shutil.which(override or "tesseract")
    if not path and not override and os.name == "nt":
        installed = Path(os.getenv("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe"
        if installed.is_file():
            path = str(installed)
    if not path:
        return None
    command = [path,"stdin","stdout","-l",os.getenv("KLTN_OCR_LANG","vie+eng")]
    local_models = Path(__file__).resolve().parents[2] / "local" / "ocr-tessdata"
    models = os.getenv("KLTN_OCR_DATA_DIR") or (str(local_models) if local_models.is_dir() else None)
    return command + ["--tessdata-dir",models] if models else command


def image_hash(image):
    resized = image.convert("L").resize((9,8),Image.Resampling.LANCZOS)
    pixels = resized.tobytes()
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value<<1) | (pixels[y*9+x]>pixels[y*9+x+1])
    return value


def image_section(raw, label, output, command, deadline):
    if output["images_seen"] >= MAX_IMAGES:
        output["warnings"].add(f"Giới hạn {MAX_IMAGES} ảnh mỗi báo cáo")
        return
    output["images_seen"] += 1
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.width*image.height > MAX_IMAGE_PIXELS:
                output["warnings"].add("Có ảnh vượt giới hạn độ phân giải")
                return
            if min(image.size) < 40:
                return
            fingerprint = image_hash(image)
            output["images"].append((label,fingerprint if 6 <= fingerprint.bit_count() <= 58 else None,sha256(raw).digest()))
            if not command:
                output["warnings"].add("Máy chủ chưa cấu hình Tesseract, chưa đọc chữ trong ảnh")
                return
            remaining = deadline-monotonic()
            if remaining <= 0:
                output["warnings"].add("Đã hết thời gian nhận dạng chữ")
                return
            image = image.convert("RGB")
            image.thumbnail((2400,3200),Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer,format="PNG")
            result = subprocess.run(command,input=buffer.getvalue(),capture_output=True,check=True,
                timeout=min(5,remaining),creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            text = result.stdout.decode("utf-8",errors="replace").strip()
            output["images_ocr"] += 1
            if text:
                output["text"].append((label,text,"OCR"))
    except (OSError,ValueError,Image.DecompressionBombError,subprocess.SubprocessError):
        output["warnings"].add("Có ảnh không đọc được hoặc OCR thiếu ngôn ngữ/đã hết thời gian")


def extract(path,suffix,command,deadline):
    out = {"text":[],"images":[],"warnings":set(),"images_seen":0,"images_ocr":0}
    if suffix==".pdf":
        reader = PdfReader(path)
        if len(reader.pages)>MAX_PAGES:
            out["warnings"].add(f"Chỉ kiểm tra {MAX_PAGES} trang PDF đầu")
        for number,page in enumerate(islice(reader.pages,MAX_PAGES),1):
            try:
                text = page.extract_text() or ""
                if text.strip():
                    out["text"].append((f"Trang {number}",text,"TEXT"))
                for position,embedded in enumerate(page.images,1):
                    if out["images_seen"] >= MAX_IMAGES:
                        out["warnings"].add(f"Giới hạn {MAX_IMAGES} ảnh mỗi báo cáo")
                        break
                    image_section(embedded.data,f"Trang {number}, ảnh {position}",out,command,deadline)
                if not text.strip() and not len(page.images):
                    out["warnings"].add(f"Trang {number} không có lớp chữ hoặc ảnh có thể tách")
            except Exception:
                out["warnings"].add(f"Không đọc hết nội dung trang {number}")
    else:
        doc = Document(path)
        for number,paragraph in enumerate(doc.paragraphs,1):
            if paragraph.text.strip():
                out["text"].append((f"Đoạn {number}",paragraph.text,"TEXT"))
        for number,table in enumerate(doc.tables,1):
            for position,row in enumerate(table.rows,1):
                out["text"].append((f"Bảng {number}, dòng {position}"," ".join(c.text for c in row.cells),"TEXT"))
        images = (part for part in doc.part.package.parts
            if part.content_type.startswith("image/") and str(part.partname).startswith("/word/media/"))
        for number,part in enumerate(images,1):
            if number>MAX_IMAGES:
                out["warnings"].add(f"Giới hạn {MAX_IMAGES} ảnh mỗi báo cáo")
                break
            image_section(part.blob,f"Ảnh chèn {number}",out,command,deadline)
    return out


def grams(text):
    words = WORDS.findall(unicodedata.normalize("NFC",text.casefold()))
    return set(zip(*(words[offset:] for offset in range(NGRAM))))


def text_matches(left,right):
    # Cross-source comparisons: a native paragraph can match OCR and vice versa.
    lookup = defaultdict(list)
    for index,(_,text,_) in enumerate(right):
        for gram in grams(text):
            if len(lookup[gram])<15:
                lookup[gram].append(index)
    matches = []
    for left_label,text,left_kind in left:
        left_grams = grams(text)
        if not left_grams:
            continue
        overlaps = defaultdict(int)
        for gram in left_grams:
            for index in lookup.get(gram,()):
                overlaps[index] += 1
        for index,count in overlaps.items():
            if count>=3:
                right_label,other,right_kind = right[index]
                example = " ".join(min(left_grams & grams(other)))
                matches.append({"left":left_label,"right":right_label,"left_kind":left_kind,"right_kind":right_kind,
                    "common_phrases":count,"example":example,
                    "left_excerpt":" ".join(text.split())[:220],"right_excerpt":" ".join(other.split())[:220]})
    return sorted(matches,key=lambda match:(-match["common_phrases"],match["left"],match["right"]))[:20]


def compare(session,user,left_id,right_id):
    if left_id==right_id:
        raise HTTPException(422,"Chọn báo cáo của hai đề tài khác nhau")
    reports = {version.id:(thesis,version,file) for thesis,version,file in authorized_reports(session,user)
        if version.id in {left_id,right_id}}
    if len(reports)!=2:
        raise HTTPException(404,"Báo cáo đã đổi phiên bản hoặc nằm ngoài phạm vi của bạn")
    if reports[left_id][0].id==reports[right_id][0].id:
        raise HTTPException(422,"Chọn báo cáo của hai đề tài khác nhau")
    command = ocr_command()
    parts = []
    for identifier in (left_id,right_id):
        _,version,file = reports[identifier]
        stored = documents.stored_download(session,version)
        try:
            parts.append(extract(stored.path,Path(file.original_name).suffix.lower(),command,monotonic()+24))
        except Exception as error:
            raise HTTPException(422,"Không thể đọc báo cáo. Kiểm tra tệp có bị khóa hoặc hỏng không.") from error
    left,right = parts
    images = []
    for a,x,digest in left["images"]:
        for b,y,other_digest in right["images"]:
            distance = 0 if digest == other_digest else (x^y).bit_count() if x is not None and y is not None else 64
            if distance <= 6:
                images.append({"left":a,"right":b,"distance":distance,"exact":digest == other_digest})
    return {"text_matches":text_matches(left["text"],right["text"]),
        "image_matches":sorted(images,key=lambda x:x["distance"])[:20],
        "coverage":[{"images_seen":part["images_seen"],"images_ocr":part["images_ocr"],"warnings":sorted(part["warnings"])}
            for part in parts]}
