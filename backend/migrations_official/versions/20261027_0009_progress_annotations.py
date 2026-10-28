"""Version-bound PDF pins and private autosaved lecturer drafts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261027_0009"
down_revision = "20261026_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "progress_review_annotation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("progress_report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("progress_report.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lecturer_profile.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stored_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stored_file.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("x", sa.Numeric(8, 7), nullable=True),
        sa.Column("y", sa.Numeric(8, 7), nullable=True),
        sa.Column("location_label", sa.String(255), nullable=False, server_default=""),
        sa.Column("quoted_text", sa.String(1000), nullable=False, server_default=""),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("state", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("state IN ('DRAFT','PUBLISHED')", name="state"),
        sa.CheckConstraint("page_number IS NULL OR page_number BETWEEN 1 AND 10000", name="page_number"),
        sa.CheckConstraint("(x IS NULL AND y IS NULL) OR (page_number IS NOT NULL AND x IS NOT NULL AND y IS NOT NULL AND x BETWEEN 0 AND 1 AND y BETWEEN 0 AND 1)", name="coordinates"),
        sa.CheckConstraint("(state = 'DRAFT' AND published_at IS NULL) OR (state = 'PUBLISHED' AND published_at IS NOT NULL AND length(trim(comment)) > 0)", name="publication"),
    )
    op.create_index("ix_progress_review_annotation_report_reviewer", "progress_review_annotation", ["progress_report_id", "reviewer_id", "state"])


def downgrade():
    raise RuntimeError("Published review locations and historical feedback must be preserved")
