"""Prepare local email/password accounts without dropping existing DEV/OIDC identities.

Password hashes are stored only after a future registration flow has verified
email ownership. Existing synthetic and OIDC-linked rows remain valid.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261003_0010"
down_revision: Union[str, None] = "20261003_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("user_account", "external_subject", existing_type=sa.String(255), nullable=True)
    op.add_column("user_account", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("user_account", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column("user_account", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(op.f("ck_user_account_identity_present"), "user_account", "external_subject IS NOT NULL OR email IS NOT NULL")
    op.create_check_constraint(op.f("ck_user_account_local_credentials_pair"), "user_account", "(email IS NULL AND password_hash IS NULL) OR (email IS NOT NULL AND password_hash IS NOT NULL)")
    op.create_check_constraint(op.f("ck_user_account_email_normalized"), "user_account", "email IS NULL OR email = lower(email)")
    op.create_index("uq_user_account_email_lower", "user_account", [sa.text("lower(email)")], unique=True, postgresql_where=sa.text("email IS NOT NULL"))


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM user_account WHERE external_subject IS NULL "
        "OR email IS NOT NULL OR password_hash IS NOT NULL OR email_verified_at IS NOT NULL) "
        "THEN RAISE EXCEPTION 'Local account credentials would be lost'; END IF; END $$"
    ))
    op.drop_index("uq_user_account_email_lower", table_name="user_account")
    op.drop_constraint(op.f("ck_user_account_email_normalized"), "user_account", type_="check")
    op.drop_constraint(op.f("ck_user_account_local_credentials_pair"), "user_account", type_="check")
    op.drop_constraint(op.f("ck_user_account_identity_present"), "user_account", type_="check")
    op.drop_column("user_account", "email_verified_at")
    op.drop_column("user_account", "password_hash")
    op.drop_column("user_account", "email")
    op.alter_column("user_account", "external_subject", existing_type=sa.String(255), nullable=False)
