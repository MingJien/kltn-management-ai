"""Allow a retained approved archive version to be withdrawn for replacement."""
from alembic import op
from sqlalchemy import text

revision = "20261118_0033"
down_revision = "20261117_0032"
branch_labels = depends_on = None


def constraints(allow_reopen):
    closed = "'RETURNED','ACCEPTED','REOPENED'" if allow_reopen else "'RETURNED','ACCEPTED'"
    for name in ("state", "decision"):
        op.drop_constraint(op.f(f"ck_thesis_archive_version_{name}"), "thesis_archive_version", type_="check")
    op.create_check_constraint("state", "thesis_archive_version", f"state IN ('SUBMITTED',{closed})")
    op.create_check_constraint("decision", "thesis_archive_version",
        "(state = 'SUBMITTED' AND decided_at IS NULL AND decided_by IS NULL AND decision_note IS NULL) OR "
        f"(state IN ({closed}) AND decided_at IS NOT NULL AND decided_by IS NOT NULL "
        "AND decision_note IS NOT NULL AND length(trim(decision_note)) >= 5)")


def upgrade():
    constraints(True)


def downgrade():
    # Keep the file in history and preserve the need for resubmission.
    op.execute(text("UPDATE thesis_archive_version SET state = 'RETURNED' WHERE state = 'REOPENED'"))
    constraints(False)
