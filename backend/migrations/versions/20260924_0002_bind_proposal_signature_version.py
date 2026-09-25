"""Bind proposal confirmations to the exact proposal version.

Revision ID: 20260924_0002
Revises: 20260920_0001

The foundation database has no signature rows. Refuse to guess a version for
existing confirmations: a signed historical version cannot be inferred safely.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260924_0002"
down_revision: Union[str, None] = "20260920_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM signature_confirmation) "
        "THEN RAISE EXCEPTION 'Cannot infer historical proposal version for existing signatures'; "
        "END IF; END $$"
    ))
    op.add_column(
        "signature_confirmation",
        sa.Column("proposal_version_no", sa.Integer(), nullable=False),
    )
    op.create_check_constraint(
        "ck_signature_confirmation_proposal_version_positive",
        "signature_confirmation",
        "proposal_version_no > 0",
    )
    op.create_foreign_key(
        "fk_signature_confirmation_proposal_version_pair",
        "signature_confirmation",
        "proposal_version",
        ["proposal_id", "proposal_version_no"],
        ["proposal_id", "version_no"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_signature_confirmation_proposal_version_pair",
        "signature_confirmation",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_signature_confirmation_proposal_version_positive",
        "signature_confirmation",
        type_="check",
    )
    op.drop_column("signature_confirmation", "proposal_version_no")