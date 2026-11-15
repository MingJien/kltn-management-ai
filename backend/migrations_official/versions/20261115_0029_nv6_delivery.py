"""Preserve issued defense documents and reviewed thesis archive versions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20261115_0029"
down_revision = "20261112_0028"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "defense_print_record",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column("round_id", UUID(), sa.ForeignKey("thesis_round.id"), nullable=False),
        sa.Column("slot_id", UUID(), sa.ForeignKey("defense_slot.id")),
        sa.Column("created_by", UUID(), sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("form", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("source", JSONB(), nullable=False),
        sa.CheckConstraint("(form IN (6,9) AND slot_id IS NOT NULL) OR (form IN (10,11) AND slot_id IS NULL)", name="scope"),
    )
    op.create_index("ix_defense_print_record_round", "defense_print_record", ["round_id", "created_at"])
    op.create_table(
        "thesis_archive_version",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column("thesis_id", UUID(), sa.ForeignKey("thesis.id"), nullable=False),
        sa.Column("file_id", UUID(), sa.ForeignKey("stored_file.id"), nullable=False),
        sa.Column("submitted_by", UUID(), sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("decided_by", UUID(), sa.ForeignKey("user_account.id")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_note", sa.Text()),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("thesis_id", "version_no"),
        sa.CheckConstraint("state IN ('SUBMITTED','RETURNED','ACCEPTED')", name="state"),
        sa.CheckConstraint("(state = 'SUBMITTED' AND decided_at IS NULL AND decided_by IS NULL AND decision_note IS NULL) OR (state IN ('RETURNED','ACCEPTED') AND decided_at IS NOT NULL AND decided_by IS NOT NULL AND decision_note IS NOT NULL AND length(trim(decision_note)) >= 5)", name="decision"),
    )
    op.create_index("uq_thesis_archive_pending", "thesis_archive_version", ["thesis_id"], unique=True,
                    postgresql_where=sa.text("state = 'SUBMITTED'"))


def downgrade():
    op.drop_table("thesis_archive_version")
    op.drop_table("defense_print_record")
