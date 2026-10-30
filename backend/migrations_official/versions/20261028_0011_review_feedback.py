"""Private review summaries and immutable lecturer feedback uploads; no new tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261028_0011"
down_revision = "20261027_0010"
branch_labels = None
depends_on = None


def upgrade():
    table = "progress_review_annotation"
    op.add_column(table, sa.Column("annotation_kind", sa.String(20), nullable=False, server_default="PIN"))
    op.add_column(table, sa.Column("attachment_file_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("stored_file.id", ondelete="RESTRICT"), nullable=True))
    op.create_check_constraint("annotation_kind", table, "annotation_kind IN ('PIN','SUMMARY','ATTACHMENT')")
    op.create_check_constraint("attachment_kind", table, "(annotation_kind = 'ATTACHMENT' AND attachment_file_id IS NOT NULL) OR (annotation_kind IN ('PIN','SUMMARY') AND attachment_file_id IS NULL)")
    op.create_check_constraint("kind_coordinates", table, "annotation_kind = 'PIN' OR (page_number IS NULL AND x IS NULL AND y IS NULL)")
    for kind, target in (("progress", "progress_report_id"), ("document", "document_version_id"), ("proposal", "proposal_version_id")):
        op.create_index("uq_review_summary_" + kind, table, [target, "reviewer_id"], unique=True,
            postgresql_where=sa.text(f"annotation_kind = 'SUMMARY' AND {target} IS NOT NULL"))


def downgrade():
    raise RuntimeError("Preserve lecturer feedback and published summaries; use an additive migration")
