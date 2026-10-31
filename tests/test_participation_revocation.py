from datetime import timedelta
from uuid import uuid4, UUID

from sqlalchemy import select

from test_registration import scenario, hdr
from test_registration_forms import forms, upload
from test_core_workspace import workspace, open_milestone
from backend.db.models import entities as m
from backend.services.theses import now
from backend.services.account_directory import build_account_directory
from backend.services.roster import RosterRow, import_roster
from fastapi import HTTPException
import pytest


def verifier(session, user, round_id):
    for kind in ("ELIGIBILITY_VERIFIER", "ELIGIBILITY_IMPORTER"):
        session.add(m.ResourceAssignment(id=uuid4(), user_id=user.id, round_id=round_id,
            assignment_type=kind, state="ACTIVE", effective_from=now()-timedelta(days=1)))
    session.commit()


def test_revoke_restores_only_with_explicit_decision_and_preserves_account(forms):
    client, users, students, topic, session, reg, path = forms
    verifier(session, users[4], topic.round_id)
    base = f"/api/v1/rounds/{topic.round_id}/roster"
    payload = {"student_id":str(students[0].id),"reason":"Synthetic decision", "basis_ref":"TEST-REVOKE"}
    assert client.post(base+"/revoke", headers=hdr(users[4]), json=payload).status_code == 200
    assert client.get(path, headers=hdr(users[0])).json()["can_submit"] is False
    assert upload(client,users[0],path).status_code == 409
    evidence=client.post(f"/api/v1/topic-registrations/{reg['id']}/evidence",headers={**hdr(users[0]),"X-File-Name":"test.pdf"},content=b"%PDF-test")
    assert evidence.status_code==403
    assert users[0].status == "ACTIVE"
    assert client.get("/api/v1/me/context", headers=hdr(users[0])).status_code == 200
    assert client.post(base+"/restore", headers=hdr(users[0]), json=payload).status_code == 403
    assert client.post(base+"/restore", headers=hdr(users[4]), json={**payload,"reason":" "}).status_code == 422
    assert client.post(base+"/restore", headers=hdr(users[4]), json=payload).status_code == 200
    assert client.get(path, headers=hdr(users[0])).json()["can_submit"] is True
    assert upload(client,users[0],path).status_code == 201
    assert client.post(base+"/restore", headers=hdr(users[4]), json=payload).status_code == 409
    snapshots=session.scalars(select(m.EligibilitySnapshot).where(m.EligibilitySnapshot.student_id==students[0].id).order_by(m.EligibilitySnapshot.version)).all()
    assert [s.state for s in snapshots] == ["CONFIRMED","REJECTED","CONFIRMED"]
    notices=session.scalars(select(m.UserNotification).where(m.UserNotification.recipient_user_id==users[0].id)).all()
    assert len(notices)==2 and all(n.kind=="WORKFLOW_NOTICE" for n in notices)
    assert not session.scalar(select(m.UserNotification.id).where(m.UserNotification.recipient_user_id==users[1].id))


def test_revoked_member_cannot_submit_but_teammate_can(workspace):
    client, users, students, lecturers, session, path = workspace
    thesis=session.get(m.Thesis, UUID(path.rsplit("/",1)[1]))
    verifier(session, users[4], thesis.round_id)
    milestone=open_milestone(client,users,path)
    payload={"milestone_id":milestone["id"],"summary":"Synthetic weekly results", "reported_ratio":20}
    decision={"student_id":str(students[0].id),"reason":"Synthetic revoke", "basis_ref":"TEST"}
    assert client.post(f"/api/v1/rounds/{thesis.round_id}/roster/revoke",headers=hdr(users[4]),json=decision).status_code==200
    data=client.get(path,headers=hdr(users[0])).json()
    assert "document:view" in data["actions"] and "document:submit" not in data["actions"]
    assert "proposal:submit" not in data["actions"] and "progress:submit" not in data["actions"]
    assert client.post(path+"/progress-reports",headers=hdr(users[0]),json=payload).status_code==403
    assert client.post(path+"/progress-reports",headers=hdr(users[1]),json=payload).status_code==201


def test_import_cannot_silently_restore_revoked_student(scenario):
    client, users, students, lecturers, topic, session = scenario
    verifier(session,users[4],topic.round_id)
    st=students[0];department=session.get(m.Department,st.department_id)
    st.class_name="TEST";st.major_code="7480201"
    session.add(m.DepartmentMajor(id=uuid4(), department_id=department.id,code="7480201",name="Test major",active=True))
    from backend.services.passwords import unusable_password
    users[0].email="revoked@example.invalid"
    users[0].password_hash=unusable_password()
    session.commit()
    client.post(f"/api/v1/rounds/{topic.round_id}/roster/revoke",headers=hdr(users[4]),json={"student_id":str(st.id),"reason":"Synthetic revoke", "basis_ref":"TEST"})
    row=RosterRow(2,st.student_code,st.display_name,users[0].email,department.code,"TEST","7480201")
    with pytest.raises(HTTPException) as exc:
        import_roster(session,users[4],topic.round_id,[row],"OLD-LIST")
    assert exc.value.status_code==409
    assert session.scalar(select(m.EligibilitySnapshot).where(m.EligibilitySnapshot.student_id==st.id).order_by(m.EligibilitySnapshot.version.desc())).state=="REJECTED"


def test_directory_filters_pending_separately_from_disabled(scenario):
    client, users, students, lecturers, topic, session=scenario
    users[0].status="DISABLED";users[0].email_verified_at=None
    users[1].status="DISABLED";users[1].email_verified_at=now()
    users[2].status="LOCKED"
    session.commit()
    def ids(state):
        return {row["id"] for row in build_account_directory(session,search="",category="STUDENT",additional_role="",offset=0,limit=100,account_status=state)["items"]}
    assert ids("PENDING")=={str(users[0].id)}
    assert ids("DISABLED")=={str(users[1].id)}
    assert ids("LOCKED")=={str(users[2].id)}
