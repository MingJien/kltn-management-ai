from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.api import account


@pytest.mark.parametrize('role,name,initiator,expected_role,expected_source', [
    ('STUDENT', 'Nguyễn An Demo', 'staff', 'sinh viên', 'Đây là liên kết kích hoạt tài khoản sinh viên của bạn'),
    ('STUDENT', 'Nguyễn An Demo', 'self', 'sinh viên', 'Đây là liên kết kích hoạt tài khoản sinh viên của bạn'),
    ('LECTURER', 'Lê Bình Demo', 'staff', 'giảng viên', 'Đây là liên kết kích hoạt tài khoản giảng viên của bạn'),
    ('LECTURER', 'Lê Bình Demo', 'self', 'giảng viên', 'Đây là liên kết kích hoạt tài khoản giảng viên của bạn'),
])
def test_activation_message_matches_recipient_and_source(monkeypatch, role, name, initiator, expected_role, expected_source):
    monkeypatch.setenv('KLTN_ENV', 'development')
    monkeypatch.setenv('KLTN_FRONTEND_URL', 'http://127.0.0.1:1573')
    monkeypatch.setattr(account, 'make_token', lambda user, purpose: 'synthetic-token')
    sent = []
    monkeypatch.setattr(account, 'send_account_link', lambda *args: sent.append(args))
    user = SimpleNamespace(id=uuid4(), email='one+demo@example.invalid', row_version=3, base_role=role)
    code = "0012345678" if role == "STUDENT" else "GV-001"
    recipient = account._mail_recipient(user, name, initiator, code)
    account._mail_link(recipient, 'activate')
    email, subject, body = sent[0]
    assert email == user.email and expected_role in subject
    assert name in body and f'Email đăng nhập: {user.email}' in body
    assert (f"MSSV: {code}" if role == "STUDENT" else f"Mã giảng viên: {code}") in body
    assert expected_source in body and '24 giờ' in body
    assert 'http://127.0.0.1:1573/account/activate?token=synthetic-token' in body
    assert 'chỉ dùng một lần' in body


def test_password_reset_email_has_correct_expiry_and_no_false_name(monkeypatch):
    monkeypatch.setenv('KLTN_ENV', 'development')
    monkeypatch.setenv('KLTN_FRONTEND_URL', 'http://127.0.0.1:1573')
    monkeypatch.setattr(account, 'make_token', lambda user, purpose: 'fake')
    sent = []
    monkeypatch.setattr(account, 'send_account_link', lambda *args: sent.append(args))
    account._mail_link(SimpleNamespace(email='admin@example.invalid'), 'reset')
    assert 'Xin chào,' in sent[0][2] and '30 phút' in sent[0][2]
    assert '/account/reset-password?token=fake' in sent[0][2]
