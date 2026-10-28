"""Exact-version private drafts and atomic publication for documents and proposals."""
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from test_core_workspace import workspace, synthetic_pdf, version_headers
from test_progress_annotations import annotation, save_headers
from test_registration import hdr, scenario
from backend.db.models import entities as m


def test_review_access_explains_accepted_version_and_student_role(workspace):
    client, users, _, _, _, _ = workspace
    path, review, expected, _, _ = submitted_file(workspace, "document")
    pending = client.get(path, headers=hdr(users[3])).json()
    assert pending["can_edit"] and pending["read_only_reason"] is None
    student = client.get(path, headers=hdr(users[0])).json()
    assert not student["can_edit"] and "tài khoản sinh viên" in student["read_only_reason"]
    accepted = client.post(review, headers={**hdr(users[3]), "If-Match": str(expected)},
        json={"decision": "ACCEPT", "comment": "GVHD tiếp nhận bản đã kiểm tra"})
    assert accepted.status_code == 200, accepted.text
    readonly = client.get(path, headers=hdr(users[3])).json()
    assert not readonly["can_edit"] and "đã được GVHD tiếp nhận" in readonly["read_only_reason"]
    assert client.put(path + "/" + str(uuid4()), headers=save_headers(users[3]), json=annotation()).status_code == 409


def submitted_file(workspace, kind):
    client, users, _, _, session, base = workspace
    if kind == "document":
        doc = client.post(base + "/documents", headers=hdr(users[0]), json={"title": "Reviewable plan", "document_type": "PLAN"}).json()
        upload = base + f"/documents/{doc['id']}/versions"
        made = client.post(upload, headers={**hdr(users[0]), "If-Match": str(doc["row_version"]), "Content-Type": "application/octet-stream", "X-File-Name": "plan.pdf"}, content=synthetic_pdf())
        assert made.status_code == 201, made.text
        parent = made.json()
        version = parent["versions"][0]
        row = session.get(m.DocumentVersion, version["id"])
        path = upload + f"/{row.id}"
        review_path = path + "/review"
        expected = version["row_version"]
    else:
        upload = base + "/proposal/versions"
        made = client.post(upload, headers={**hdr(users[0]), "If-Match": "0", "Content-Type": "application/octet-stream", "X-File-Name": "proposal.pdf"}, content=synthetic_pdf())
        assert made.status_code == 201, made.text
        parent = made.json()
        row = session.get(m.ProposalVersion, parent["versions"][0]["id"])
        path = upload + f"/{row.id}"
        review_path = base + "/proposal/reviews"
        expected = parent["row_version"]
    session.get(m.StoredFile, row.stored_file_id).scan_state = "CLEAN"
    session.commit()
    return path + "/annotations", review_path, expected, upload, parent


@pytest.mark.parametrize("kind", ["document", "proposal"])
def test_file_annotations_private_scoped_and_published_with_review(workspace, kind):
    client, users, _, _, session, base = workspace
    path, review, expected, _, _ = submitted_file(workspace, kind)
    note = str(uuid4())
    assert client.put(path + "/" + note, headers=save_headers(users[0]), json=annotation()).status_code == 403
    assert client.get(path, headers=hdr(users[2])).status_code == 404
    assert client.put(path + "/" + note, headers=save_headers(users[3]), json=annotation()).status_code == 200
    assert client.get(path, headers=hdr(users[0])).json()["annotations"] == []
    assert client.get(path, headers=hdr(users[4])).json()["annotations"] == []
    assert client.post(review, headers={**hdr(users[3]), "If-Match": str(expected + 1)},
        json={"decision": "REVISION_REQUIRED", "comment": "Stale must fail"}).status_code == 409
    assert client.get(path, headers=hdr(users[0])).json()["annotations"] == []
    result = client.post(review, headers={**hdr(users[3]), "If-Match": str(expected)},
        json={"decision": "REVISION_REQUIRED", "comment": "Revise pinned section"})
    assert result.status_code == 200, result.text
    visible = client.get(path, headers=hdr(users[0])).json()
    assert not visible["can_edit"] and visible["annotations"][0]["state"] == "PUBLISHED"
    assert client.put(path + "/" + note, headers=save_headers(users[3], 2), json=annotation()).status_code == 409
    assert client.delete(path + "/" + note, headers=save_headers(users[3], 2)).status_code == 409
    session.expire_all()
    row = session.get(m.ProgressReviewAnnotation, note)
    assert row.progress_report_id is None
    assert (row.document_version_id is not None) == (kind == "document")
    assert (row.proposal_version_id is not None) == (kind == "proposal")


@pytest.mark.parametrize("kind", ["document", "proposal"])
def test_blank_pin_rolls_back_and_new_file_cannot_inherit_notes(workspace, kind):
    client, users, _, _, _, _ = workspace
    path, review, expected, upload, parent = submitted_file(workspace, kind)
    note = str(uuid4())
    assert client.put(path + "/" + note, headers=save_headers(users[3]), json=annotation("")).status_code == 200
    rejected = client.post(review, headers={**hdr(users[3]), "If-Match": str(expected)},
        json={"decision": "REVISION_REQUIRED", "comment": "Blank pin must abort decision"})
    assert rejected.status_code == 409, rejected.text
    assert client.get(path, headers=hdr(users[3])).json()["annotations"][0]["state"] == "DRAFT"
    newer = client.post(upload, headers={**hdr(users[0]), "If-Match": str(parent["row_version"]), "Content-Type": "application/octet-stream", "X-File-Name": "updated.pdf"}, content=synthetic_pdf())
    assert newer.status_code == 201, newer.text
    fresh_path = upload + f"/{newer.json()['versions'][0]['id']}/annotations"
    assert client.get(fresh_path, headers=hdr(users[3])).json()["annotations"] == []
    assert client.put(path + "/" + note, headers=save_headers(users[3], 1), json=annotation("old draft")).status_code == 409


def test_annotation_requires_exactly_one_target_in_postgresql(workspace):
    client, users, _, _, session, _ = workspace
    path, _, _, _, _ = submitted_file(workspace, "document")
    note = str(uuid4())
    assert client.put(path + "/" + note, headers=save_headers(users[3]), json=annotation()).status_code == 200
    row = session.get(m.ProgressReviewAnnotation, note)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            row.document_version_id = None
            session.flush()
    session.expire_all()
    assert session.get(m.ProgressReviewAnnotation, note).document_version_id is not None


def test_proposal_peer_cannot_confirm_or_read_other_lecturer_drafts(workspace):
    client, users, _, lecturers, _, base = workspace
    path, review, _, _, proposal = submitted_file(workspace, "proposal")
    assert client.get(path, headers=hdr(users[5])).status_code == 404
    assigned = client.post(base + "/proposal/reviewers", headers=version_headers(users[4], proposal),
        json={"lecturer_id": str(lecturers[2].id), "reason": "Peer review synthetic assignment"})
    assert assigned.status_code == 200, assigned.text
    proposal = assigned.json()
    own, peer = str(uuid4()), str(uuid4())
    assert client.put(path + "/" + own, headers=save_headers(users[3]), json=annotation()).status_code == 200
    assert client.get(path, headers=hdr(users[5])).json()["annotations"] == []
    assert client.put(path + "/" + peer, headers=save_headers(users[5]), json=annotation()).status_code == 200
    assert client.post(review, headers=version_headers(users[5], proposal), json={"decision": "CONFIRM", "comment": "Forbidden"}).status_code == 403
    result = client.post(review, headers=version_headers(users[5], proposal), json={"decision": "COMMENT", "comment": "Peer comment with pin"})
    assert result.status_code == 200, result.text
    visible = client.get(path, headers=hdr(users[0])).json()["annotations"]
    assert [note["id"] for note in visible] == [peer]
