"""Activity history must enforce resource boundaries before filtering and paging."""
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from backend.db.models import entities as m
from backend.services.theses import now
from test_core_workspace import workspace
from test_registration import hdr, scenario


def add_event(session, actor, resource_type, resource_id, action, reason, **extra):
    item = m.AuditEvent(id=uuid4(), actor_id=actor.id, action=action,
        resource_type=resource_type, resource_id=resource_id, reason=reason,
        occurred_at=now(), correlation_id=uuid4(), **extra)
    session.add(item)
    session.flush()
    return item


def test_activity_scopes_admin_student_advisor_head_and_comment_only(workspace):
    client, users, students, lecturers, session, path = workspace
    thesis_id = UUID(path.rsplit("/", 1)[1])
    admin = m.UserAccount(id=uuid4(), external_subject=uuid4().hex, base_role="ADMIN", status="ACTIVE")
    session.add(admin)
    session.flush()
    own = add_event(session, admin, "user_account", users[0].id, "ACCOUNT_EMAIL_CORRECTED", "Own account correction", source_reference="CV-TEST-28")
    other = add_event(session, admin, "user_account", users[2].id, "ACCOUNT_EMAIL_CORRECTED", "Unrelated personal account")
    progress = add_event(session, users[3], "thesis", thesis_id, "PROGRESS_CONFIRM", "Progress visible to reviewer")
    document = add_event(session, users[3], "thesis", thesis_id, "DOCUMENT_REVIEWED", "Document not for cross reviewer")
    evidence = add_event(session, admin, "registration", session.get(m.Thesis, thesis_id).registration_id,
        "REGISTRATION_EVIDENCE_UPLOADED", "Legacy registration resource name")
    unrelated = add_event(session, admin, "thesis", uuid4(), "DOCUMENT_REVIEWED", "Unrelated private thesis")
    session.add(m.ResourceAssignment(id=uuid4(), user_id=users[5].id, thesis_id=thesis_id,
        assignment_type="PROGRESS_REVIEWER", state="ACTIVE", effective_from=now()-timedelta(days=1)))
    session.commit()

    def ids(user, query=""):
        response = client.get("/api/v1/activity?limit=100" + query, headers=hdr(user))
        assert response.status_code == 200, response.text
        return {item["id"] for item in response.json()["items"]}

    assert {str(own.id), str(other.id)} <= ids(admin)
    assert str(document.id) not in ids(admin) and str(unrelated.id) not in ids(admin)
    assert str(progress.id) not in ids(admin)
    assert {str(own.id), str(progress.id), str(document.id)} <= ids(users[0])
    assert str(evidence.id) in ids(users[0]) and str(evidence.id) in ids(users[3])
    assert str(evidence.id) not in ids(users[2])
    assert str(other.id) not in ids(users[0]) and str(unrelated.id) not in ids(users[0])
    assert str(own.id) not in ids(users[1])
    assert str(progress.id) not in ids(users[2])
    assert {str(progress.id), str(document.id)} <= ids(users[3])
    assert str(document.id) not in ids(users[4]) and str(progress.id) not in ids(users[4])
    assert str(progress.id) not in ids(users[5]) and str(document.id) not in ids(users[5])
    assert ids(users[0], f"&resource_type=user_account&resource_id={users[2].id}") == set()
    topic = session.get(m.Topic, session.get(m.Thesis, thesis_id).topic_id)
    search = client.get("/api/v1/activity", headers=hdr(users[0]), params={"search":topic.code}).json()
    assert str(progress.id) in {event["id"] for event in search["items"]}
    assert client.get("/api/v1/activity").status_code == 401


def test_activity_search_reference_legacy_dates_and_pagination(scenario):
    client, users, _, _, _, session = scenario
    new = add_event(session, users[0], "user_account", users[0].id, "ACCOUNT_EMAIL_CORRECTED",
        "Correction justification", source_reference="CV/2026-TEST")
    old = add_event(session, users[0], "user_account", users[0].id, "ACCOUNT_EMAIL_CORRECTED",
        "Legacy correction; reference=OLD-REF-26")
    session.commit()
    result = client.get("/api/v1/activity?search=CV%2F2026-TEST", headers=hdr(users[0])).json()
    assert result["total"] == 1 and result["items"][0]["id"] == str(new.id)
    legacy = client.get("/api/v1/activity?search=OLD-REF-26", headers=hdr(users[0])).json()
    assert legacy["items"][0]["source_reference"] == "OLD-REF-26"
    assert legacy["items"][0]["reason"] == "Legacy correction"
    first = client.get("/api/v1/activity?limit=1&offset=0", headers=hdr(users[0])).json()
    second = client.get("/api/v1/activity?limit=1&offset=1", headers=hdr(users[0])).json()
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get("/api/v1/activity?date_from=2026-12-01&date_to=2026-01-01", headers=hdr(users[0])).status_code == 422
    assert client.get("/api/v1/activity?search=%25", headers=hdr(users[0])).json()["total"] == 0
    assert client.get("/api/v1/activity?limit=101", headers=hdr(users[0])).status_code == 422


def test_account_reason_is_retrievable_after_admin_action(scenario):
    client, users, _, _, _, session = scenario
    admin = m.UserAccount(id=uuid4(), external_subject=uuid4().hex, base_role="ADMIN", status="ACTIVE")
    session.add(admin)
    session.commit()
    response = client.post(f"/api/v1/admin/users/{users[0].id}/lock", headers=hdr(admin),
        json={"locked": True, "reason": "Faculty confirmed temporary suspension"})
    assert response.status_code == 204, response.text
    history = client.get(f"/api/v1/activity?resource_type=user_account&resource_id={users[0].id}", headers=hdr(admin)).json()
    assert history["items"][0]["action"] == "ACCOUNT_LOCKED"
    assert history["items"][0]["reason"] == "Faculty confirmed temporary suspension"
    assert session.scalar(select(m.AuditEvent.id).where(m.AuditEvent.action == "ACCOUNT_LOCKED"))
