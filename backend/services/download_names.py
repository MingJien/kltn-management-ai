"""Readable attachment names, independent of storage keys and original uploads."""
from pathlib import Path
import re
import unicodedata

from backend.db.models import entities as m


def filename(label, identity="", version=None, extension=""):
    def part(value, limit):
        value = unicodedata.normalize("NFD", str(value)).replace("đ", "d").replace("Đ", "D")
        value = "".join(char for char in value if not unicodedata.combining(char))
        return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_")[:limit].rstrip("-_")
    parts = [part(label, 55), part(identity, 40)]
    if version is not None:
        parts.append(f"v{version}")
    return ("-".join(value for value in parts if value) or "Tai-lieu") + extension.lower()


def thesis_identity(session, thesis_id):
    thesis = session.get(m.Thesis, thesis_id)
    return thesis.current_title if thesis else "KLTN"


def document_filename(session, version, original_name):
    extension = Path(original_name).suffix
    if getattr(version, "download_label", None):
        return filename(version.download_label, getattr(version, "download_identity", ""), extension=extension)
    if isinstance(version, m.DocumentVersion):
        document = session.get(m.Document, version.document_id)
        label = {"PLAN":"Mau-02-Ke-hoach", "REPORT":"Cuon-bao-cao-KLTN", "SUPPORTING":"Tai-lieu-ho-tro"}.get(document.document_type, "Tai-lieu")
        if document.document_type == "SUPPORTING":
            label = document.title
        return filename(label, thesis_identity(session, document.thesis_id), version.version_no, extension)
    if isinstance(version, m.RegistrationFormVersion):
        registration = session.get(m.TopicRegistration, version.registration_id)
        topic = session.get(m.Topic, registration.topic_id)
        return filename(f"Mau-{version.form_code}-Don-dang-ky", topic.current_title, version.version_no, extension)
    return filename(Path(original_name).stem, extension=extension)
