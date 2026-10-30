"""Audited print exports are readable by the same actors as their exact source version."""
from uuid import uuid4

from test_core_workspace import workspace, synthetic_pdf, upload, version_headers
from test_registration import scenario, hdr
from test_registration_forms import forms, upload as upload_form
from backend.db.models import entities as m


def cleared_document(workspace, kind, title):
    client, users, _, _, session, path = workspace
    doc = client.post(path + "/documents", headers=hdr(users[0]), json={"title": title, "document_type": kind}).json()
    made = upload(client, users[0], path, doc, synthetic_pdf(), "submission.pdf")
    assert made.status_code == 201, made.text
    doc = made.json(); version = doc["versions"][0]
    stored = session.get(m.StoredFile, session.get(m.DocumentVersion, version["id"]).stored_file_id)
    stored.scan_state = "CLEAN"  # Explicit API fixture state; UI tests use the real scanner.
    session.commit()
    return doc, version, path + f"/documents/{doc['id']}/versions/{version['id']}"


def test_export_history_is_version_specific_private_and_does_not_change_original(workspace):
    client, users, _, _, _, path = workspace
    doc, version, endpoint = cleared_document(workspace, "PLAN", "Synthetic plan")
    assert client.get(path, headers=hdr(users[0])).json()["registration_id"]
    assert client.get(endpoint + "/print-history", headers=hdr(users[0])).json() == []
    assert client.post(endpoint + "/print-copy", headers=hdr(users[0])).status_code == 409
    accepted = client.post(endpoint + "/review", headers=version_headers(users[3], version), json={"decision": "ACCEPT", "comment": "Plan accepted"})
    assert accepted.status_code == 200, accepted.text
    for actor in (users[0], users[3]):
        exported = client.post(endpoint + "/print-copy", headers=hdr(actor))
        assert exported.status_code == 200, exported.text
    history = client.get(endpoint + "/print-history", headers=hdr(users[1]))
    assert history.status_code == 200 and len(history.json()) == 2
    assert all(row["copy_status"] == "APPROVED" and row["version_no"] == 1 and row["document_code"] == exported.headers["x-document-code"] for row in history.json())
    assert client.get(endpoint + "/print-history", headers=hdr(users[2])).status_code == 404
    _, _, same_bytes_other_document = cleared_document(workspace, "SUPPORTING", "Same bytes, different document")
    assert client.get(same_bytes_other_document + "/print-history", headers=hdr(users[0])).json() == []
    assert client.get(endpoint + "/download", headers=hdr(users[0])).content == synthetic_pdf()
    assert client.get(path + f"/documents/{doc['id']}/versions/{uuid4()}/print-history", headers=hdr(users[0])).status_code == 404


def test_registration_receipt_history_is_not_reported_as_faculty_approval(forms):
    client, users, _, _, session, reg, path = forms
    made = upload_form(client, users[0], path)
    assert made.status_code == 201, made.text
    version = made.json()["versions"][0]
    file = session.get(m.StoredFile, session.get(m.RegistrationFormVersion, version["id"]).stored_file_id)
    file.scan_state = "CLEAN"; session.commit()
    endpoint = path + "/" + version["id"]
    result = client.post(endpoint + "/print-copy", headers=hdr(users[0]))
    assert result.status_code == 200, result.text
    history = client.get(endpoint + "/print-history", headers=hdr(users[0])).json()
    assert len(history) == 1 and history[0]["copy_status"] == "SUBMITTED"
    assert client.get(endpoint + "/print-history", headers=hdr(users[2])).status_code == 404
    sent = client.post(path.removesuffix("/forms") + "/submit", headers=hdr(users[0])).json()
    accepted = client.post(path.removesuffix("/forms") + "/lecturer-decision", headers=version_headers(users[3], sent), json={"decision": "ACCEPT"})
    assert accepted.status_code == 200, accepted.text
    assert client.get(endpoint + "/print-history", headers=hdr(users[0])).json()[0]["copy_status"] == "SUBMITTED"
