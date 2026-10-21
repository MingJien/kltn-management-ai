"""Freeze the milestone deadline seen by each progress submission.

Older reports predate deadline history. Their snapshot uses the deadline at
migration time; the system cannot reconstruct any earlier extension.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261020_0002"
down_revision = "20261015_0001_official"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("progress_report", sa.Column("due_at_at_submission", sa.DateTime(timezone=True), nullable=True))
    op.execute(sa.text("""
        UPDATE progress_report AS report
        SET due_at_at_submission = milestone.due_at
        FROM progress_milestone AS milestone
        WHERE milestone.id = report.milestone_id
    """))


def downgrade() -> None:
    op.drop_column("progress_report", "due_at_at_submission")
