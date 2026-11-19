"""Exercise retained archive metadata and the lifecycle upgrade on PostgreSQL."""
from datetime import timedelta
from importlib import import_module
from unicodedata import normalize
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from backend.db.models import entities as m
from backend.services.theses import now
from test_registration import hdr, scenario


def test_legacy_catalog_ranking_and_completion_migration(scenario):
    client, users, students, lecturers, topic, session = scenario
    instant = now()
    records = []
    for index, code in enumerate(("KLTN-01", "KLTN-010")):
        if index:
            topic = m.Topic(id=uuid4(), round_id=topic.round_id, department_id=topic.department_id,
                proposer_user_id=users[3].id, proposer_type="LECTURER", current_title="Hồ sơ thứ hai",
                code=code, max_students=1, state="LOCKED")
            session.add(topic)
        else:
            topic.code = code
        session.flush()
        registration = m.TopicRegistration(id=uuid4(), topic_id=topic.id, round_id=topic.round_id,
            created_by=students[index].id, expected_member_count=1, state="FINALIZED")
        session.add(registration)
        session.flush()
        thesis = m.Thesis(topic_id=topic.id, registration_id=registration.id, department_id=topic.department_id,
                          round_id=topic.round_id, current_title=topic.current_title, state="DEFENDED")
        stored = m.StoredFile(storage_key="documents/"+uuid4().hex, original_name="kiem-thu.pdf",
            media_type="application/pdf", byte_size=1, sha256="a"*64, scan_state="CLEAN")
        session.add_all([thesis,stored])
        session.flush()
        title = normalize("NFD", "  Đồ   án") if not index else "Đồ án ứng dụng 0012345678"
        snapshot = {"title":title, "advisor": normalize("NFD", "  Trần   Bình  "),
                    "students":[{"name":" Nguyễn  An ", "code": ("0012345678","0012345679")[index]}]}
        accepted = m.ThesisArchiveVersion(thesis_id=thesis.id, file_id=stored.id, submitted_by=users[index].id,
            version_no=1, state="ACCEPTED", snapshot=snapshot, decided_by=users[4].id,
            decided_at=instant+timedelta(seconds=index), decision_note="Đã đối chiếu")
        session.add(accepted)
        records.append((thesis,accepted))
    session.commit()

    def search(**params):
        response = client.get("/api/v1/thesis-archive/search", headers=hdr(users[4]), params=params)
        assert response.status_code == 200, response.text
        return response.json()

    for exact in ("kltn-01", "0012345678", "do an"):
        page = search(q=exact, limit=1)
        assert page["total"] == 2 and page["items"][0]["id"] == str(records[0][0].id)
        assert search(q=exact, limit=1, page=2)["items"][0]["id"] == str(records[1][0].id)
    assert search(q="tran binh")["total"] == 2
    for literal in ("%", "_"):
        assert search(q=literal)["total"] == 0
    first, original = records[0]
    shown = search(q="0012345678")["items"][0]["snapshot"]
    assert shown == {"title":"Đồ án","advisor":"Trần Bình","students":[{"name":"Nguyễn An","code":"0012345678"}]}
    assert original.snapshot["title"] != shown["title"]

    second, withdrawn = records[1]
    withdrawn.state = "REOPENED"
    session.add(m.ThesisArchiveVersion(thesis_id=second.id, file_id=withdrawn.file_id, submitted_by=users[1].id,
        version_no=2, state="SUBMITTED", snapshot=withdrawn.snapshot))
    session.flush()
    migration = import_module("backend.migrations_official.versions.20261119_0034_archive_completion")
    with Operations.context(MigrationContext.configure(session.connection())):
        migration.upgrade()
        migration.upgrade()
    session.expire_all()
    assert (first.state, first.row_version) == ("COMPLETED", 2)
    assert (second.state, second.row_version) == ("DEFENDED", 1)
    assert search()["total"] == 1 and original.snapshot["title"] != shown["title"]
