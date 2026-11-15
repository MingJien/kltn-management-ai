from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from test_registration import scenario, hdr
from backend.db.models import entities as m
from backend.services.account_tokens import make_token, token_account
from backend.services.passwords import unusable_password


def test_student_activation_requires_admin_and_confirmed_roster_and_preserves_self_link(scenario, monkeypatch):
    client, users, students, _, topic, session = scenario
    monkeypatch.setenv('AUTH_SESSION_SECRET', 'synthetic-student-activation-secret-at-least-32-characters')
    monkeypatch.setattr('backend.services.account_mail.mail_delivery_ready', lambda: True)
    monkeypatch.setattr('backend.services.account_mail.delivery_mode', lambda: 'smtp')
    instant = datetime.now(timezone.utc)

    class FixedMailClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

    monkeypatch.setattr('backend.api.roster.datetime', FixedMailClock)
    sent = []
    monkeypatch.setattr('backend.api.account._mail_link', lambda account, purpose: sent.append((account.id, purpose, account.identifier)))
    admin = m.UserAccount(id=uuid4(), external_subject='synthetic-admin-'+uuid4().hex, base_role='ADMIN', status='ACTIVE')
    session.add(admin)
    for idx in (0, 1):
        users[idx].password_hash = unusable_password()
        users[idx].status = 'DISABLED'
        users[idx].email = f'synthetic-{uuid4().hex}@example.invalid'
    session.flush()
    old_version = users[0].row_version
    self_link = make_token(users[0], 'activate')
    path = f'/api/v1/rounds/{topic.round_id}/roster/{students[0].id}/activation-link'
    assert client.post(path, headers=hdr(users[3])).status_code == 403
    assert client.post(path, headers=hdr(admin)).status_code == 403
    session.add(m.ResourceAssignment(id=uuid4(), user_id=admin.id, round_id=topic.round_id,
        assignment_type='ELIGIBILITY_IMPORTER', state='ACTIVE', effective_from=datetime.now(timezone.utc)-timedelta(days=1)))
    session.flush()
    result = client.post(path, headers=hdr(admin))
    assert result.status_code == 200, result.text
    assert result.json() == {'sent': True, 'delivery_mode': 'smtp'}
    assert sent == [(users[0].id, 'activate', students[0].student_code)]
    assert users[0].row_version == old_version
    assert token_account(self_link, 'activate') == (users[0].id, users[0].email, old_version)
    assert client.post(path, headers=hdr(admin)).status_code == 429
    roster = client.get(f'/api/v1/rounds/{topic.round_id}/roster', headers=hdr(admin))
    assert roster.status_code == 200, roster.text
    row = next(row for row in roster.json() if row['student_id'] == str(students[0].id))
    assert row['mail_status'] == 'SENT' and row['delivery_mode'] == 'smtp' and not row['can_send_activation']
    assert session.scalar(select(m.AuditEvent.id).where(m.AuditEvent.resource_id == users[0].id,
        m.AuditEvent.action == 'STUDENT_ACTIVATION_SENT')) is not None
    activated = client.post(f'/api/v1/rounds/{topic.round_id}/roster/{students[2].id}/activation-link', headers=hdr(admin))
    assert activated.status_code == 409
    monkeypatch.setattr('backend.api.account._mail_link', lambda *_: (_ for _ in ()).throw(RuntimeError('synthetic failure')))
    failed = client.post(f'/api/v1/rounds/{topic.round_id}/roster/{students[1].id}/activation-link', headers=hdr(admin))
    assert failed.status_code == 200 and failed.json()['sent'] is False
