"""NV6: scoped thesis review forms and per-student defense eligibility history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "20261030_0017"
down_revision = "20261029_0016"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("reviewer_assignment", sa.Column("due_at", sa.DateTime(timezone=True)))
    op.add_column("reviewer_assignment", sa.Column("assignment_reason", sa.Text()))
    op.add_column("reviewer_assignment", sa.Column("source_reference", sa.String(500)))
    op.create_table("thesis_review",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        *[sa.Column(name, pg.UUID(as_uuid=True), sa.ForeignKey(target + ".id", ondelete="RESTRICT"), nullable=nullable)
          for name, target, nullable in [
            ("thesis_id", "thesis", False), ("thesis_member_id", "thesis_member", False),
            ("lecturer_id", "lecturer_profile", False), ("advisor_assignment_id", "advisor_assignment", True),
            ("reviewer_assignment_id", "reviewer_assignment", True), ("report_version_id", "document_version", False),
            ("signed_file_id", "stored_file", True)]],
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("sections", pg.JSONB(), nullable=False),
        sa.Column("thesis_completed", sa.Boolean()), sa.Column("allow_defense", sa.Boolean()),
        sa.Column("source_reference", sa.String(500)), sa.Column("revision_reason", sa.Text(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("thesis_member_id", "lecturer_id", "kind", "version_no"),
        sa.CheckConstraint("kind IN ('ADVISOR','REVIEWER')", name="kind"),
        sa.CheckConstraint("state IN ('DRAFT','SUBMITTED')", name="state"),
        sa.CheckConstraint("version_no > 0", name="version_positive"),
        sa.CheckConstraint("(kind = 'ADVISOR' AND advisor_assignment_id IS NOT NULL AND reviewer_assignment_id IS NULL) OR (kind = 'REVIEWER' AND reviewer_assignment_id IS NOT NULL AND advisor_assignment_id IS NULL)", name="assignment_matches_kind"),
        sa.CheckConstraint("state = 'DRAFT' OR (signed_file_id IS NOT NULL AND submitted_at IS NOT NULL)", name="submitted_has_signed_copy"))
    op.create_index("ix_thesis_review_thesis_member", "thesis_review", ["thesis_id", "thesis_member_id"])
    op.create_table("defense_eligibility_check",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        *[sa.Column(name, pg.UUID(as_uuid=True), sa.ForeignKey(target + ".id", ondelete="RESTRICT"), nullable=nullable)
          for name, target, nullable in [
            ("thesis_id", "thesis", False), ("thesis_member_id", "thesis_member", False),
            ("report_version_id", "document_version", True), ("advisor_review_id", "thesis_review", True),
            ("checked_by", "user_account", False)]],
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("discipline_status", sa.String(30), nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False), sa.Column("state", sa.String(20), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("thesis_member_id", "version_no"),
        sa.CheckConstraint("version_no > 0", name="version_positive"),
        sa.CheckConstraint("discipline_status IN ('CLEAR','WARNING_OR_HIGHER','UNKNOWN')", name="discipline_status"),
        sa.CheckConstraint("state IN ('ELIGIBLE','BLOCKED')", name="state"))
    op.create_index("ix_defense_eligibility_check_thesis_member", "defense_eligibility_check", ["thesis_id", "thesis_member_id"])


def downgrade():
    raise RuntimeError("Preserve signed reviews and eligibility decisions; use a forward migration")
