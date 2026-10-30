"""Fill the faculty's retained Mẫu 7/8 without rebuilding its DOCX package."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import re
import zipfile

from lxml import etree as E

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}


def fill_review_form(source, kind, values, sections, *, completed, allow, code, instant):
    """Patch only documented form slots and the export footer; reject an unknown template."""
    try:
        with zipfile.ZipFile(io.BytesIO(source)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(i.file_size for i in entries) > 50*1024*1024:
                raise ValueError("Oversized template package")
            parts = {i.filename: archive.read(i.filename) for i in entries}
        parser = E.XMLParser(resolve_entities=False, no_network=True)
        root = E.fromstring(parts["word/document.xml"], parser)
        body = root.find(f"{{{W}}}body")
        paragraphs = list(body.findall(f"{{{W}}}p"))

        def text(p):
            return "".join(p.xpath(".//w:t/text()", namespaces=NS)).strip()

        def find(prefix):
            matches = [p for p in paragraphs if text(p).startswith(prefix)]
            if len(matches) != 1:
                raise ValueError("Faculty template fields have changed")
            return matches[0]

        def replace(p, value):
            original = p.find(f"{{{W}}}r/{{{W}}}rPr")
            for child in list(p):
                if child.tag in {f"{{{W}}}r", f"{{{W}}}hyperlink"}:
                    p.remove(child)
            run = E.SubElement(p, f"{{{W}}}r")
            if original is not None:
                run.append(deepcopy(original))
            for index, line in enumerate(value.split("\n")):
                if index:
                    E.SubElement(run, f"{{{W}}}br")
                node = E.SubElement(run, f"{{{W}}}t")
                node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                node.text = line

        def slot(prefix, value):
            p = find(prefix)
            original_font = p.find(f"{{{W}}}r/{{{W}}}rPr")
            original_font = deepcopy(original_font) if original_font is not None else E.Element(f"{{{W}}}rPr")
            for tag in ("b", "i", "u"):
                for mark in original_font.findall(f"{{{W}}}{tag}"):
                    original_font.remove(mark)
            fonts = original_font.find(f"{{{W}}}rFonts")
            if fonts is None:
                fonts = E.SubElement(original_font, f"{{{W}}}rFonts")
                fonts.set(f"{{{W}}}ascii", "Times New Roman"); fonts.set(f"{{{W}}}hAnsi", "Times New Roman")
            if original_font.find(f"{{{W}}}sz") is None:
                E.SubElement(original_font, f"{{{W}}}sz").set(f"{{{W}}}val", "28")
            lines = value.split("\n")
            replace(p, lines[0])
            following = p.getnext()
            while following is not None and following.tag == f"{{{W}}}p" and re.fullmatch(r"[.\s…]+", text(following)):
                next_node = following.getnext()
                body.remove(following)
                following = next_node
            cursor = p
            for line in lines[1:]:
                response = E.Element(f"{{{W}}}p")
                original_props = p.find(f"{{{W}}}pPr")
                props = deepcopy(original_props) if original_props is not None else E.Element(f"{{{W}}}pPr")
                for keep in props.findall(f"{{{W}}}keepNext"):
                    props.remove(keep)
                alignment = props.find(f"{{{W}}}jc")
                if alignment is not None:
                    props.remove(alignment)
                alignment = E.SubElement(props, f"{{{W}}}jc"); alignment.set(f"{{{W}}}val", "left")
                response.append(props)
                replace(response, line)
                response.find(f"{{{W}}}r").insert(0, deepcopy(original_font))
                cursor.addnext(response)
                cursor = response
            if len(lines) > 1:
                props = p.find(f"{{{W}}}pPr")
                if props is None:
                    props = E.Element(f"{{{W}}}pPr"); p.insert(0, props)
                if props.find(f"{{{W}}}keepNext") is None:
                    E.SubElement(props, f"{{{W}}}keepNext")

        for p in root.xpath(".//w:tbl//w:p", namespaces=NS):
            if re.fullmatch(r"KHOA\s*[.\s…]+", text(p)):
                faculty_name = values["faculty"]
                replace(p, faculty_name.upper() if faculty_name.lower().startswith("khoa") else "KHOA " + faculty_name.upper())

        slot("Họ và tên sinh viên:", "Họ và tên sinh viên: " + values["student"])
        slot("Lớp:", f"Lớp: {values['class_name']}    Mã sinh viên: {values['student_code']}")
        slot("Tên đề tài:", "Tên đề tài: " + values["title"])
        if kind == "ADVISOR":
            slot("Họ và tên (học hàm, học vị)", "Họ và tên (học hàm, học vị) giảng viên hướng dẫn: " + values["lecturer"])
            slot("Đơn vị:", "Đơn vị: " + values["unit"])
            fields = [("1. Về tinh thần", "attitude"), ("2. Sự đáp ứng", "content"), ("3. Hình thức", "presentation")]
            for prefix, key in fields:
                label = text(find(prefix)).split(":")[0] + ":"
                slot(prefix, label + "\n" + sections[key])
            slot("Đề nghị của giảng viên hướng dẫn:", "Đề nghị của giảng viên hướng dẫn: " +
                ("Đồng ý cho bảo vệ." if allow else "Không đồng ý cho bảo vệ.") + "\n" +
                ("Xác nhận KLTN đã hoàn thành." if completed else "KLTN chưa hoàn thành."))
        else:
            slot("Người hướng dẫn khoa học:", "Người hướng dẫn khoa học: " + values["advisor"])
            fields = [("1. Đánh giá", "presentation"), ("2. Tính cấp thiết", "research"),
                ("4. Những kết quả", "contribution"), ("5. Những điểm", "discussion"), ("6. Đánh giá chung", "overall")]
            for prefix, key in fields:
                slot(prefix, text(find(prefix)) + "\n" + sections[key])
        signature = find("(Ký, ghi rõ")
        name_p = E.Element(f"{{{W}}}p")
        name_props = deepcopy(signature.find(f"{{{W}}}pPr"))
        if name_props is not None:
            name_p.append(name_props)
        replace(name_p, values["lecturer"])
        signature_font = signature.find(f"{{{W}}}r/{{{W}}}rPr")
        if signature_font is not None:
            name_p.find(f"{{{W}}}r").insert(0, deepcopy(signature_font))
        # Reserve signing space without manual line breaks that stretch justified text.
        if name_props is None:
            name_props = E.SubElement(name_p, f"{{{W}}}pPr")
            name_p.insert(0, name_props)
        spacing = name_props.find(f"{{{W}}}spacing")
        if spacing is None:
            spacing = E.SubElement(name_props, f"{{{W}}}spacing")
        spacing.set(f"{{{W}}}before", "480")
        signature.addnext(name_p)
        for p in paragraphs:
            if text(p).startswith(("Đồng Tháp,", "Giảng viên hướng dẫn", "Người phản biện", "(Ký, ghi rõ")):
                props = p.find(f"{{{W}}}pPr")
                if props is None:
                    props = E.Element(f"{{{W}}}pPr"); p.insert(0, props)
                if props.find(f"{{{W}}}keepNext") is None:
                    E.SubElement(props, f"{{{W}}}keepNext")
        # Blank writing-space paragraphs at the end of the blank template are filled by the response above.
        for candidate in list(body)[::-1]:
            if candidate.tag == f"{{{W}}}sectPr":
                continue
            if candidate.tag == f"{{{W}}}p" and not text(candidate):
                body.remove(candidate)
            else:
                break

        # Add an ordinary Word footer without changing the reference's styles, section geometry or headers.
        rel_path = "word/_rels/document.xml.rels"
        rel_root = E.fromstring(parts[rel_path], parser)
        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        content_root = E.fromstring(parts["[Content_Types].xml"], parser)
        content_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
        sect = body.find(f"{{{W}}}sectPr")
        if sect is None:
            raise ValueError("Template has no section settings")
        refs = sect.findall(f"{{{W}}}footerReference")
        if refs:
            # An altered faculty template with footer rules needs an explicit mapping, not a guessed rewrite.
            raise ValueError("Faculty template now has its own footer")
        rid = "rIdNv6ReviewFooter"
        if any(node.get("Id") == rid for node in rel_root):
            raise ValueError("Footer relationship collision")
        E.SubElement(rel_root, f"{{{rel_ns}}}Relationship", Id=rid,
            Type=R+"/footer", Target="footerNv6Review.xml")
        E.SubElement(content_root, f"{{{content_ns}}}Override", PartName="/word/footerNv6Review.xml",
            ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml")
        reference = E.Element(f"{{{W}}}footerReference")
        reference.set(f"{{{W}}}type", "default")
        reference.set(f"{{{R}}}id", rid)
        sect.insert(0, reference)
        footer = E.Element(f"{{{W}}}ftr", nsmap={"w": W})
        p = E.SubElement(footer, f"{{{W}}}p")
        r = E.SubElement(p, f"{{{W}}}r")
        props = E.SubElement(r, f"{{{W}}}rPr")
        font = E.SubElement(props, f"{{{W}}}rFonts")
        font.set(f"{{{W}}}ascii", "Times New Roman"); font.set(f"{{{W}}}hAnsi", "Times New Roman")
        size = E.SubElement(props, f"{{{W}}}sz"); size.set(f"{{{W}}}val", "16")
        t = E.SubElement(r, f"{{{W}}}t")
        local = instant.astimezone(timezone(timedelta(hours=7)))
        t.text = f"{code} · Báo cáo v{values['report_version']} · {local:%H:%M %d/%m/%Y} (GMT+7) · Bản để ký, chưa xác nhận chữ ký"
        serialize = lambda node: E.tostring(node, xml_declaration=True, encoding="UTF-8", standalone=True)
        parts["word/document.xml"] = serialize(root)
        parts[rel_path] = serialize(rel_root)
        parts["[Content_Types].xml"] = serialize(content_root)
        parts["word/footerNv6Review.xml"] = serialize(footer)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, value in parts.items():
                archive.writestr(name, value)
        return output.getvalue()
    except (ValueError, KeyError, zipfile.BadZipFile, E.XMLSyntaxError, AttributeError) as exc:
        from fastapi import HTTPException
        raise HTTPException(409, "Mẫu DOCX của Khoa không khớp cấu trúc Mẫu 7/8 đang hỗ trợ. Tải mẫu chính thức để điền và ký; cần cập nhật ánh xạ trước khi xuất tự động.") from exc


def export_review(session, user, thesis_id, review_id, expected):
    import hashlib
    from fastapi import HTTPException
    from pathlib import Path
    from backend.db.models import entities as m
    from backend.services import evaluation as service, form_templates, school_forms
    from backend.services.proposal_export import _print_response
    from backend.services.theses import audit, now, primary_advisor
    thesis, item = service.editable_review(session, user, thesis_id, review_id, expected)
    if any(not item.sections.get(f["key"]) for f in service.FORM_FIELDS[item.kind]) or (
        item.kind == "ADVISOR" and (item.allow_defense is None or item.thesis_completed is None)):
        raise HTTPException(422, "Lưu đầy đủ nội dung phiếu và đề nghị trước khi xuất để ký")
    template_id = "mau-07" if item.kind == "ADVISOR" else "mau-08"
    managed = school_forms.compatibility_download(session, user, template_id, thesis.round_id)
    if managed is not None:
        source = Path(managed.path).read_bytes()
    else:
        source, _, _ = form_templates.official_template_by_id(template_id, user.base_role)
    member = session.get(m.ThesisMember, item.thesis_member_id)
    student = session.get(m.StudentProfile, member.student_id)
    lecturer = session.get(m.LecturerProfile, item.lecturer_id)
    department = session.get(m.Department, thesis.department_id)
    faculty = session.get(m.Faculty, department.faculty_id)
    advisor = primary_advisor(session, thesis.id)
    instant = now()
    report = session.get(m.DocumentVersion, item.report_version_id)
    code = f"M{'7' if item.kind == 'ADVISOR' else '8'}-{item.id.hex[:12].upper()}-V{item.version_no}-R{item.row_version}"
    content = fill_review_form(source, item.kind, {"student": student.display_name, "student_code": student.student_code,
        "class_name": student.class_name or "Chưa cập nhật", "title": thesis.current_title,
        "faculty": faculty.name,
        "lecturer": lecturer.display_name, "unit": department.name+" · "+faculty.name,
        "advisor": session.get(m.LecturerProfile, advisor.lecturer_id).display_name if advisor else "Chưa ghi nhận",
        "report_version": report.version_no}, item.sections, completed=item.thesis_completed,
        allow=item.allow_defense, code=code, instant=instant)
    audit(session, user, "THESIS_REVIEW_EXPORTED", "thesis_review", item.id, "Xuất phiếu đã điền để ký ngoài hệ thống",
        before_hash=hashlib.sha256(source).hexdigest(), after_hash=hashlib.sha256(content).hexdigest(), source_reference=code)
    session.commit()
    return _print_response(content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", code, ".docx", instant)
