"""Reuse version-bound review notes for documents and proposals without new tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261027_0010"
down_revision = "20261027_0009"
branch_labels = None
depends_on = None


def upgrade():
    table = "progress_review_annotation"
    op.alter_column(table, "progress_report_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    for target in ("document_version", "proposal_version"):
        op.add_column(table, sa.Column(target + "_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey(target + ".id", ondelete="RESTRICT"), nullable=True))
        op.create_index(f"ix_progress_review_annotation_{target.split('_')[0]}_reviewer",
            table, [target + "_id", "reviewer_id", "state"])
    op.create_check_constraint("one_target", table,
        "num_nonnulls(progress_report_id, document_version_id, proposal_version_id) = 1")


def downgrade():
    raise RuntimeError("Keep published version-bound feedback; use an additive migration")
