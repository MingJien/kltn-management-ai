"""Approved lecturer profiles and private, versioned change requests."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "20261102_0018"
down_revision = "20261030_0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lecturer_profile", sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("lecturer_profile", sa.Column("profile_data", pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("lecturer_profile", sa.Column("avatar_file_id", pg.UUID(as_uuid=True), sa.ForeignKey("stored_file.id", ondelete="RESTRICT")))
    op.add_column("lecturer_profile", sa.Column("profile_verified_at", sa.DateTime(timezone=True)))
    op.add_column("lecturer_profile", sa.Column("profile_verified_by", pg.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="RESTRICT")))
    op.create_check_constraint("profile_data_object", "lecturer_profile", "jsonb_typeof(profile_data) = 'object'")
    op.create_table("lecturer_profile_change",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        *[sa.Column(name, pg.UUID(as_uuid=True), sa.ForeignKey(target+".id", ondelete="RESTRICT"), nullable=nullable)
          for name,target,nullable in [("lecturer_id","lecturer_profile",False),("avatar_file_id","stored_file",True),
              ("original_avatar_file_id","stored_file",True),("reviewed_by","user_account",True)]],
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("base_profile_version", sa.Integer(), nullable=False),
        sa.Column("proposed_data", pg.JSONB(), nullable=False),
        sa.Column("original_data", pg.JSONB(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("submission_note", sa.Text()), sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("decision_reason", sa.Text()),
        sa.UniqueConstraint("lecturer_id","version_no"),
        sa.CheckConstraint("version_no > 0 AND base_profile_version > 0", name="version_positive"),
        sa.CheckConstraint("state IN ('DRAFT','SUBMITTED','APPROVED','RETURNED','WITHDRAWN')", name="state"),
        sa.CheckConstraint("jsonb_typeof(proposed_data) = 'object' AND jsonb_typeof(original_data) = 'object'", name="data_objects"),
        sa.CheckConstraint("state NOT IN ('SUBMITTED','APPROVED','RETURNED') OR submitted_at IS NOT NULL", name="submitted_timestamp"),
        sa.CheckConstraint("state NOT IN ('APPROVED','RETURNED') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND decision_reason IS NOT NULL)", name="decision_recorded"))
    op.create_index("uq_lecturer_profile_change_open","lecturer_profile_change",["lecturer_id"],unique=True,
        postgresql_where=sa.text("state IN ('DRAFT','SUBMITTED')"))
    op.create_index("ix_lecturer_profile_change_state_created","lecturer_profile_change",["state","created_at"])


def downgrade():
    raise RuntimeError("Preserve approved profile and review history; use a forward migration")
