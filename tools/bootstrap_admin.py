"""One-time deployment bootstrap for the first ADMIN; never accepts a password."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend.api.account import _mail_link
from backend.db.models import entities as m
from backend.services.account_tokens import make_token
from backend.services.passwords import unusable_password
from backend.db.validate_schema import load_env
from backend.services.roster import EMAIL


def main() -> None:
    parser = argparse.ArgumentParser(description="Invite the first KLTN administrator")
    parser.add_argument("--execute", action="store_true", help="Actually create and invite the account")
    parser.add_argument("--demo", action="store_true",
                        help="Use only the local kltn_dev demo database and require real SMTP")
    args = parser.parse_args()
    load_env()
    email = os.getenv("KLTN_BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    if not EMAIL.fullmatch(email):
        parser.error("Set KLTN_BOOTSTRAP_ADMIN_EMAIL to the approved administrator email")
    if len(os.getenv("AUTH_SESSION_SECRET", "")) < 32:
        parser.error("Configure a stable AUTH_SESSION_SECRET first")
    if os.getenv("KLTN_ENV") == "production" and not (
            os.getenv("KLTN_SMTP_HOST") and os.getenv("KLTN_MAIL_FROM")
            and os.getenv("KLTN_FRONTEND_URL", "").startswith("https://")):
        parser.error("Production requires HTTPS frontend and SMTP before bootstrap")
    database_url = os.environ["DATABASE_URL"]
    if args.demo:
        if os.getenv("KLTN_ENV") != "development":
            parser.error("--demo is available only when KLTN_ENV=development")
        if args.execute and not all(os.getenv(key, "").strip() for key in (
                "KLTN_MAIL_FROM", "KLTN_SMTP_HOST", "KLTN_SMTP_USER", "KLTN_SMTP_PASSWORD")):
            parser.error("Configure the complete SMTP settings before --demo bootstrap")
        database_url = make_url(database_url).set(database="kltn_dev").render_as_string(
            hide_password=False)
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            actual_database = conn.execute(text("SELECT current_database()")).scalar_one()
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if args.demo and (actual_database != "kltn_dev" or revision != "20261010_0013"):
            parser.error("Demo bootstrap requires kltn_dev at Alembic 20261010_0013")
        print(f"Target database: {actual_database}; Alembic revision: {revision}")
        if not args.execute:
            print("Ready: pass --execute to invite the first administrator")
            return
        with Session(engine, expire_on_commit=False) as session:
            admins = session.scalars(select(m.UserAccount).where(
                m.UserAccount.base_role == "ADMIN").with_for_update()).all()
            if admins:
                if len(admins) != 1 or admins[0].email != email or admins[0].email_verified_at:
                    parser.error("An administrator already exists; bootstrap will not change it")
                account = admins[0]
                # A resent invitation revokes every earlier activation link.
                account.row_version += 1
                session.add(m.AuditEvent(id=uuid4(), actor_id=None,
                    action="ADMIN_BOOTSTRAP_REISSUED", resource_type="user_account",
                    resource_id=account.id, occurred_at=datetime.now(timezone.utc),
                    correlation_id=uuid4()))
                session.commit()
            else:
                if session.scalar(select(m.UserAccount.id).where(func.lower(m.UserAccount.email) == email)):
                    parser.error("Email is already assigned to a different account")
                account = m.UserAccount(id=uuid4(), base_role="ADMIN", email=email,
                    password_hash=unusable_password(), status="DISABLED")
                session.add(account)
                session.add(m.AuditEvent(id=uuid4(), actor_id=None, action="ADMIN_BOOTSTRAP_INVITED",
                    resource_type="user_account", resource_id=account.id,
                    occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
                session.commit()
            make_token(account, "activate")  # Fail before delivery if token signing is unavailable.
            _mail_link(account, "activate")
            print("Administrator activation link delivered; the recipient sets their own password")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
