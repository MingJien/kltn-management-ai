"""Delivery of account links. Development messages stay under the ignored tmp directory."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4



def frontend_origin(configured: str | None = None) -> str:
    """Return the configured public frontend URL for links sent by the system."""
    value = configured if configured is not None else os.getenv("KLTN_FRONTEND_URL", "http://localhost:5173")
    value = value.strip().rstrip("/") or "http://localhost:5173"
    return value


def delivery_mode() -> str:
    return "smtp" if os.getenv("KLTN_SMTP_HOST", "").strip() and os.getenv("KLTN_MAIL_FROM", "").strip() else "development_outbox"


def mail_delivery_ready() -> bool:
    """Accept a complete SMTP setup, or the explicit development outbox."""
    sender = os.getenv("KLTN_MAIL_FROM", "").strip()
    host = os.getenv("KLTN_SMTP_HOST", "").strip()
    username = os.getenv("KLTN_SMTP_USER", "").strip()
    password = os.getenv("KLTN_SMTP_PASSWORD", "").strip()
    if not any((sender, host, username, password)):
        return os.getenv("KLTN_ENV") in {"development", "test"}
    return bool(sender and host and (bool(username) == bool(password)))


def send_account_link(recipient: str, subject: str, text: str) -> None:
    if not mail_delivery_ready():
        raise RuntimeError("Email delivery is not fully configured")
    sender = os.getenv("KLTN_MAIL_FROM", "").strip()
    host = os.getenv("KLTN_SMTP_HOST", "").strip()
    if not sender or not host:
        if os.getenv("KLTN_ENV") not in {"development", "test"}:
            raise RuntimeError("Email delivery is not configured")
        # Isolate test messages from the developer's local outbox.
        test_run = os.getenv("KLTN_E2E_RUN_DIR") if os.getenv("KLTN_ENV") == "test" else None
        outbox = (Path(test_run) if test_run else Path(__file__).resolve().parents[2] / "tmp") / "mail-outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        (outbox / f"{uuid4()}.txt").write_text(
            f"To: {recipient}\nSubject: {subject}\n\n{text}", encoding="utf-8"
        )
        return
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text)
    port = int(os.getenv("KLTN_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as client:
        client.starttls(context=ssl.create_default_context())
        username = os.getenv("KLTN_SMTP_USER", "").strip()
        if username:
            client.login(username, os.environ["KLTN_SMTP_PASSWORD"].strip())
        client.send_message(message)
