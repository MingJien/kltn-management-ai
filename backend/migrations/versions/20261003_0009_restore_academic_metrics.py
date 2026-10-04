"""Restore credit ratio and GPA as optional eligibility evidence.

Revision 0008 already ran locally, so it remains immutable. These values are
useful for explaining the academic threshold; discipline/criminal detail stays
out of this application. Existing rows remain NULL because dropped values
cannot be reconstructed from the application database.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261003_0009"
down_revision: Union[str, None] = "20261003_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("eligibility_snapshot", sa.Column("passed_credit_ratio", sa.Numeric(5, 4), nullable=True))
    op.add_column("eligibility_snapshot", sa.Column("gpa_4", sa.Numeric(3, 2), nullable=True))
    op.create_check_constraint(op.f("ck_eligibility_snapshot_credit_ratio"), "eligibility_snapshot", "passed_credit_ratio >= 0 AND passed_credit_ratio <= 1")
    op.create_check_constraint(op.f("ck_eligibility_snapshot_gpa"), "eligibility_snapshot", "gpa_4 >= 0 AND gpa_4 <= 4")


def downgrade() -> None:
    # Do not silently discard newly entered academic measurements.
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM eligibility_snapshot "
        "WHERE passed_credit_ratio IS NOT NULL OR gpa_4 IS NOT NULL) "
        "THEN RAISE EXCEPTION 'Academic eligibility measurements would be lost'; "
        "END IF; END $$"
    ))
    op.drop_constraint(op.f("ck_eligibility_snapshot_gpa"), "eligibility_snapshot", type_="check")
    op.drop_constraint(op.f("ck_eligibility_snapshot_credit_ratio"), "eligibility_snapshot", type_="check")
    op.drop_column("eligibility_snapshot", "gpa_4")
    op.drop_column("eligibility_snapshot", "passed_credit_ratio")
