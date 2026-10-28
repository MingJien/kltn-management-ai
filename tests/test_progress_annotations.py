"""Real PostgreSQL checks for private drafts, version isolation and atomic publication."""
import json
from uuid import uuid4

from sqlalchemy import select

from test_core_workspace import workspace, open_milestone, synthetic_pdf, version_headers
from test_registration import hdr, scenario
from backend.db.models import entities as m


def report_with_file(workspace):
    client, users, _, _, session, path = workspace
    milestone = open_milestone(client, users, path)
    payload = {"milestone_id": milestone["id"], "summary": "Synthetic annotation test", "reported_ratio": 40}
    made = client.post(path + "/progress-submissions", headers=hdr(users[0]),
        data={"report": json.dumps(payload)}, files={"file": ("review.pdf", synthetic_pdf(), "application/pdf")})
    assert made.status_code == 201, made.text
    # Scanner behaviour is tested separately; this fixture explicitly models a cleared file.
    row = session.get(m.ProgressReport, made.json()["id"])
    session.get(m.StoredFile, row.evidence_file_id).scan_state = "CLEAN"
    session.commit()
    report = client.get(path + "/progress-reports", headers=hdr(users[3])).json()[0]
    return report, path + f"/progress-reports/{report['id']}/annotations", payload


def annotation(comment="Clarify this result"):
    return {"page_number": 1, "x": .3, "y": .4, "comment": comment, "quoted_text": "result", "location_label": ""}


def save_headers(user, expected=0):
    return {**hdr(user), "If-Match": str(expected)}


def test_private_drafts_publish_with_exact_review_and_cannot_be_overwritten(workspace):
    client, users, _, _, session, _ = workspace
    report, path, _ = report_with_file(workspace)
    note_id = str(uuid4())
    assert client.put(path + "/" + note_id, headers=save_headers(users[0]), json=annotation()).status_code == 403
    assert client.get(path, headers=hdr(users[2])).status_code == 404
    made = client.put(path + "/" + note_id, headers=save_headers(users[3]), json=annotation())
    assert made.status_code == 200, made.text
    note = made.json()
    assert note["state"] == "DRAFT" and note["row_version"] == 1
    assert client.get(path, headers=hdr(users[0])).json()["annotations"] == []
    assert client.get(path, headers=hdr(users[4])).status_code == 403
    assert client.put(path + "/" + note_id, headers=save_headers(users[3]), json=annotation("stale write")).status_code == 409
    sent = client.post(path.removesuffix("/annotations") + "/review", headers=version_headers(users[3], report),
        json={"decision": "REVISION_REQUIRED", "comment": "Please revise the pinned result"})
    assert sent.status_code == 200, sent.text
    visible = client.get(path, headers=hdr(users[1])).json()
    assert not visible["can_edit"] and len(visible["annotations"]) == 1
    assert visible["annotations"][0]["state"] == "PUBLISHED" and visible["annotations"][0]["published_at"]
    assert client.delete(path + "/" + note_id, headers=save_headers(users[3], 2)).status_code == 409
    session.expire_all()
    assert session.get(m.ProgressReviewAnnotation, note_id).comment == "Clarify this result"


def test_blank_pin_rolls_back_decision_and_draft_can_be_removed(workspace):
    client, users, _, _, session, _ = workspace
    report, path, _ = report_with_file(workspace)
    note_id = str(uuid4())
    assert client.put(path + "/" + note_id, headers=save_headers(users[3]), json=annotation("")).status_code == 200
    rejected = client.post(path.removesuffix("/annotations") + "/review", headers=version_headers(users[3], report),
        json={"decision": "CONFIRM", "comment": "Complete"})
    assert rejected.status_code == 409
    session.expire_all()
    assert session.get(m.ProgressReport, report["id"]).state == "SUBMITTED"
    assert session.get(m.ProgressReviewAnnotation, note_id).state == "DRAFT"
    assert not session.scalar(select(m.ProgressReview.id).where(m.ProgressReview.progress_report_id == report["id"]))
    assert client.delete(path + "/" + note_id, headers=save_headers(users[3], 1)).status_code == 204
    assert client.get(path, headers=hdr(users[3])).json()["annotations"] == []


def test_new_submission_never_inherits_or_repositions_old_drafts(workspace):
    client, users, _, _, _, thesis_path = workspace
    report, path, payload = report_with_file(workspace)
    note_id = str(uuid4())
    assert client.put(path + "/" + note_id, headers=save_headers(users[3]), json=annotation()).status_code == 200
    newer = client.post(thesis_path + "/progress-reports", headers=hdr(users[0]), json=payload)
    assert newer.status_code == 201, newer.text
    assert newer.json()["version_no"] == 2
    assert client.put(path + "/" + note_id, headers=save_headers(users[3], 1), json=annotation("old version")).status_code == 409
    assert client.get(path, headers=hdr(users[0])).json()["annotations"] == []
    fresh_path = thesis_path + f"/progress-reports/{newer.json()['id']}/annotations"
    assert client.get(fresh_path, headers=hdr(users[3])).json()["annotations"] == []


def test_unrelated_peer_cannot_read_or_comment_even_with_legacy_assignment(workspace):
    from backend.services.theses import now
    client, users, _, lecturers, session, thesis_path = workspace
    report, path, _ = report_with_file(workspace)
    thesis = client.get(thesis_path, headers=hdr(users[4])).json()
    assert client.post(thesis_path+"/progress-reviewers",headers=version_headers(users[4],thesis),
        json={"lecturer_id":str(lecturers[2].id),"reason":"Retired cross review"}).status_code==403
    session.add(m.ResourceAssignment(id=uuid4(),user_id=users[5].id,thesis_id=thesis["id"],
        assignment_type="PROGRESS_REVIEWER",state="ACTIVE",effective_from=now()))
    session.commit()
    assert client.get(path,headers=hdr(users[5])).status_code==404
    assert client.put(path+"/"+str(uuid4()),headers=save_headers(users[5]),json=annotation()).status_code==404
    endpoint=path.removesuffix("/annotations")+"/review"
    assert client.post(endpoint,headers=version_headers(users[5],report),json={"decision":"COMMENT_ONLY","comment":"Not allowed"}).status_code==404


def test_invalid_coordinates_and_uncleared_files_are_rejected(workspace):
    client, users, _, _, session, _ = workspace
    report, path, _ = report_with_file(workspace)
    for values in ({"x": 1.1}, {"y": None}, {"page_number": None}, {"page_number": 0}):
        assert client.put(path + "/" + str(uuid4()), headers=save_headers(users[3]), json={**annotation(), **values}).status_code == 422
    row = session.get(m.ProgressReport, report["id"])
    session.get(m.StoredFile, row.evidence_file_id).scan_state = "QUARANTINED"
    session.commit()
    assert client.put(path + "/" + str(uuid4()), headers=save_headers(users[3]), json=annotation()).status_code == 409
