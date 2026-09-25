"""Record each student's own response to a group registration invitation.

This stores consent evidence for the future registration workflow; the current
prototype endpoint still does not enforce member confirmation.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260925_0007"
down_revision: Union[str, None] = "20260925_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("registration_member", sa.Column("consent_status", sa.String(20), nullable=False, server_default="PENDING"))
    op.add_column("registration_member", sa.Column("responded_by_user_id", sa.UUID(), nullable=True))
    op.add_column("registration_member", sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_registration_member_responded_by_user_id_user_account", "registration_member", "user_account", ["responded_by_user_id"], ["id"], ondelete="RESTRICT")
    op.execute(sa.text(
        "ALTER TABLE registration_member ADD CONSTRAINT ck_registration_member_consent_consistency "
        "CHECK ((consent_status = 'PENDING' AND responded_by_user_id IS NULL AND responded_at IS NULL) "
        "OR (consent_status IN ('ACCEPTED','DECLINED') AND responded_by_user_id IS NOT NULL AND responded_at IS NOT NULL))"
    ))


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM registration_member WHERE consent_status <> 'PENDING') "
        "THEN RAISE EXCEPTION 'Member response evidence would be lost by downgrade'; END IF; END $$"
    ))
    op.drop_constraint(op.f("ck_registration_member_consent_consistency"), "registration_member", type_="check")
    op.drop_constraint(op.f("fk_registration_member_responded_by_user_id_user_account"), "registration_member", type_="foreignkey")
    op.drop_column("registration_member", "responded_at")
    op.drop_column("registration_member", "responded_by_user_id")
    op.drop_column("registration_member", "consent_status")
