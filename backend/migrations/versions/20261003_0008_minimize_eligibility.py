"""Keep the Faculty's per-round decision, not underlying sensitive records.

The official source remains with the responsible office. This migration only
removes details from the KLTN application; it cannot erase exported backups.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261003_0008"
down_revision: Union[str, None] = "20260925_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_eligibility_snapshot_credit_ratio"), "eligibility_snapshot", type_="check")
    op.drop_constraint(op.f("ck_eligibility_snapshot_gpa"), "eligibility_snapshot", type_="check")
    op.drop_column("eligibility_snapshot", "passed_credit_ratio")
    op.drop_column("eligibility_snapshot", "gpa_4")
    op.drop_column("eligibility_snapshot", "discipline_status")
    op.drop_column("eligibility_snapshot", "criminal_case_status")


def downgrade() -> None:
    # The source details were deliberately discarded. A downgrade restores
    # only nullable placeholders and cannot reconstruct historical values.
    op.add_column("eligibility_snapshot", sa.Column("passed_credit_ratio", sa.Numeric(5, 4), nullable=True))
    op.add_column("eligibility_snapshot", sa.Column("gpa_4", sa.Numeric(3, 2), nullable=True))
    op.add_column("eligibility_snapshot", sa.Column("discipline_status", sa.String(40), nullable=True))
    op.add_column("eligibility_snapshot", sa.Column("criminal_case_status", sa.String(40), nullable=True))
    op.create_check_constraint(op.f("ck_eligibility_snapshot_credit_ratio"), "eligibility_snapshot", "passed_credit_ratio >= 0 AND passed_credit_ratio <= 1")
    op.create_check_constraint(op.f("ck_eligibility_snapshot_gpa"), "eligibility_snapshot", "gpa_4 >= 0 AND gpa_4 <= 4")
