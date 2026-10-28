"""PostgreSQL: private summaries/files, exact version ownership and atomic publication."""
from uuid import uuid4
from pathlib import Path

import pytest
from sqlalchemy import func, select

from test_core_workspace import workspace, synthetic_pdf
from test_registration import hdr, scenario
from test_progress_annotations import report_with_file, save_headers
from test_file_annotations import submitted_file
from backend.db.models import entities as m


def target(workspace, kind):
    if kind == "progress":
        report, path, _ = report_with_file(workspace)
        return path, path.removesuffix("/annotations")+"/review", report["row_version"]
    path, review, expected, _, _ = submitted_file(workspace, kind)
    return path, review, expected


def upload(client, user, path, identifier=None, content=None):
    identifier = identifier or str(uuid4())
    response = client.post(path+f"/{identifier}/attachment", headers={**save_headers(user),
        "Content-Type":"application/octet-stream", "X-File-Name":"lecturer-feedback.pdf"},
        content=content or synthetic_pdf())
    return identifier, response


@pytest.mark.parametrize("kind", ["progress", "document", "proposal"])
def test_private_feedback_files_publish_only_with_official_review(workspace, kind):
    client, users, _, _, session, _ = workspace
    path, review, expected = target(workspace, kind)
    _, forbidden = upload(client, users[0], path)
    assert forbidden.status_code == 403
    identifier, made = upload(client, users[3], path)
    assert made.status_code == 201, made.text
    assert made.json()["annotation_kind"] == "ATTACHMENT"
    note = session.get(m.ProgressReviewAnnotation, identifier)
    file = session.get(m.StoredFile, note.attachment_file_id)
    assert file.scan_state == "QUARANTINED"
    assert note.stored_file_id != note.attachment_file_id
    endpoint = path+f"/{identifier}/attachment"
    assert client.get(path, headers=hdr(users[0])).json()["annotations"] == []
    assert client.get(endpoint, headers=hdr(users[0])).status_code == 404
    assert client.get(endpoint, headers=hdr(users[4])).status_code == (403 if kind == "progress" else 404)
    assert client.get(endpoint, headers=hdr(users[3])).status_code == 409
    rejected = client.post(review, headers={**hdr(users[3]),"If-Match":str(expected)},
        json={"decision":"REVISION_REQUIRED","comment":"Revise from my feedback file"})
    assert rejected.status_code == 409, rejected.text
    session.expire_all()
    assert session.get(m.ProgressReviewAnnotation, identifier).state == "DRAFT"
    assert client.get(path, headers=hdr(users[0])).json()["annotations"] == []
    file = session.get(m.StoredFile, note.attachment_file_id); file.scan_state = "CLEAN"; session.commit()
    assert client.get(endpoint, headers=hdr(users[3])).content == synthetic_pdf()
    # Lost-response retries return the same draft, never duplicate or overwrite its bytes.
    _, retry = upload(client, users[3], path, identifier)
    assert retry.status_code == 201 and retry.json()["id"] == identifier
    approved = client.post(review, headers={**hdr(users[3]),"If-Match":str(expected)},
        json={"decision":"REVISION_REQUIRED","comment":"Revise from my feedback file"})
    assert approved.status_code == 200, approved.text
    visible = client.get(path, headers=hdr(users[0])).json()["annotations"]
    assert visible[0]["state"] == "PUBLISHED"
    assert client.get(endpoint, headers=hdr(users[0])).content == synthetic_pdf()
    assert client.get(endpoint, headers=hdr(users[2])).status_code == 404
    assert client.delete(path+f"/{identifier}", headers=save_headers(users[3],2)).status_code == 409


@pytest.mark.parametrize("kind", ["progress", "document", "proposal"])
def test_summary_autosaved_on_server_private_and_single_per_reviewer(workspace, kind):
    client, users, _, _, _, _ = workspace
    path, review, expected = target(workspace, kind)
    identifier = str(uuid4())
    data = {"annotation_kind":"SUMMARY","comment":"Draft with https://example.org/reference"}
    made = client.put(path+f"/{identifier}", headers=save_headers(users[3]), json=data)
    assert made.status_code == 200, made.text
    assert client.get(path, headers=hdr(users[0])).json()["annotations"] == []
    restored = client.get(path, headers=hdr(users[3])).json()["annotations"]
    assert restored[0]["comment"] == data["comment"]
    assert client.put(path+f"/{uuid4()}", headers=save_headers(users[3]), json=data).status_code == 409
    assert client.put(path+f"/{identifier}", headers=save_headers(users[3]), json=data).status_code == 409
    assert client.put(path+f"/{uuid4()}", headers=save_headers(users[3]), json={"annotation_kind":"ATTACHMENT"}).status_code == 422
    sent = client.post(review, headers={**hdr(users[3]),"If-Match":str(expected)},
        json={"decision":"REVISION_REQUIRED","comment":"Final conclusion with https://example.org/reference"})
    assert sent.status_code == 200, sent.text
    published = client.get(path, headers=hdr(users[0])).json()["annotations"]
    assert published[0]["comment"] == "Final conclusion with https://example.org/reference"
    assert published[0]["state"] == "PUBLISHED"


def test_feedback_upload_failure_rolls_back_file_and_database(workspace, monkeypatch):
    client, users, _, _, session, _ = workspace
    path, _, _ = target(workspace,"document")
    from backend.services.documents import storage_root
    before = set(storage_root().iterdir())
    count = session.scalar(select(func.count()).select_from(m.StoredFile))
    identifier = str(uuid4())
    def fail():
        raise RuntimeError("Synthetic commit failure")
    monkeypatch.setattr(session,"commit",fail)
    with pytest.raises(RuntimeError,match="Synthetic commit failure"):
        upload(client,users[3],path,identifier)
    assert set(storage_root().iterdir()) == before
    assert session.get(m.ProgressReviewAnnotation,identifier) is None
    assert session.scalar(select(func.count()).select_from(m.StoredFile)) == count
