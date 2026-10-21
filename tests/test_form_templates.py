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
