"""Blank forms come only from the faculty files; the system never fabricates one."""
import pytest
from fastapi import HTTPException

from backend.services import form_templates


def test_official_plan_template_is_served_byte_for_byte():
    if not form_templates.template_available("plan"):
        pytest.skip("Official Mẫu 2 is not present in this environment")
    assert form_templates.official_template("plan") == form_templates.TEMPLATES["plan"].read_bytes()


def test_official_proposal_template_is_served_byte_for_byte():
    if not form_templates.template_available("proposal"):
        pytest.skip("Official Mẫu 3 is not present in this environment")
    assert form_templates.official_template("proposal") == form_templates.TEMPLATES["proposal"].read_bytes()


def test_missing_template_reports_it_cannot_export(monkeypatch, tmp_path):
    monkeypatch.setitem(form_templates.TEMPLATES, "plan", tmp_path / "missing.docx")
    with pytest.raises(HTTPException) as raised:
        form_templates.official_template("plan")
    assert raised.value.status_code == 409
    assert "mẫu chính thức" in raised.value.detail


def test_unknown_template_kind_is_not_invented():
    with pytest.raises(HTTPException) as raised:
        form_templates.official_template("unknown")
    assert raised.value.status_code == 404


def test_student_only_sees_forms_through_five_and_cannot_download_later_forms(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from backend.api.core import download_official_template

    monkeypatch.setattr(form_templates, "OFFICIAL_DIR", tmp_path)
    for meta in form_templates.OFFICIAL_FORMS:
        (tmp_path / meta["filename"]).write_bytes(meta["id"].encode())
    student = SimpleNamespace(base_role="STUDENT")
    lecturer = SimpleNamespace(base_role="LECTURER")
    admin = SimpleNamespace(base_role="ADMIN")
    assert [item["id"] for item in form_templates.list_official_templates("STUDENT")] == [
        "mau-01a", "mau-01b", "mau-02", "mau-03", "mau-04", "mau-05"]
    assert len(form_templates.list_official_templates("LECTURER")) == 12
    assert download_official_template("mau-05", user=student).body == b"mau-05"
    for template_id in ("mau-06", "mau-07", "mau-08", "mau-09", "mau-10", "mau-11"):
        with pytest.raises(HTTPException) as denied:
            download_official_template(template_id, user=student)
        assert denied.value.status_code == 403
        assert download_official_template(template_id, user=lecturer).body == template_id.encode()
    with pytest.raises(HTTPException) as denied:
        form_templates.list_official_templates(admin.base_role)
    assert denied.value.status_code == 403
