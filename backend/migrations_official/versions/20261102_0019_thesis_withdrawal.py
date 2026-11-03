"""Student withdrawal and externally processed school outcomes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "20261102_0019"
down_revision = "20261102_0018"
branch_labels = None
depends_on = None


def upgrade():
    # A membership change requires a new proposal approval without erasing prior signatures.
    op.drop_constraint("uq_signature_confirmation_proposal_id_signature_type", "signature_confirmation", type_="unique")
    op.create_unique_constraint("uq_signature_confirmation_proposal_version_type", "signature_confirmation",
        ["proposal_id", "proposal_version_no", "signature_type"])
    op.add_column("thesis_round", sa.Column("execution_starts_on", sa.Date()))
    op.add_column("thesis_round", sa.Column("execution_start_reference", sa.String(500)))
    op.create_check_constraint("execution_start_pair", "thesis_round",
        "(execution_starts_on IS NULL AND execution_start_reference IS NULL) OR (execution_starts_on IS NOT NULL AND execution_start_reference IS NOT NULL AND length(trim(execution_start_reference)) >= 5)")
    op.create_table("thesis_withdrawal_request",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        *[sa.Column(name, pg.UUID(as_uuid=True), sa.ForeignKey(target+".id", ondelete="RESTRICT"), nullable=nullable)
          for name,target,nullable in [("thesis_id","thesis",False),("student_id","student_profile",False),
              ("advisor_reviewed_by","user_account",True),("evidence_file_id","stored_file",True),
              ("recorded_by","user_account",True)]],
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("application_data", pg.JSONB(), nullable=False),
        sa.Column("execution_starts_on", sa.Date(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(25), nullable=False, server_default="SUBMITTED"),
        sa.Column("advisor_reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("advisor_comment", sa.Text()),
        sa.Column("official_reference", sa.String(500)),
        sa.Column("outcome_note", sa.Text()),
        sa.Column("effective_on", sa.Date()),
        sa.Column("recorded_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("state IN ('SUBMITTED','ADVISOR_CONFIRMED','RETURNED','CANCELLED','RECORDED','NOT_GRANTED')", name="state"),
        sa.CheckConstraint("length(trim(reason)) >= 10", name="reason"),
        sa.CheckConstraint("jsonb_typeof(application_data) = 'object'", name="application_data"),
        sa.CheckConstraint("state NOT IN ('ADVISOR_CONFIRMED','RETURNED','RECORDED','NOT_GRANTED') OR (advisor_reviewed_by IS NOT NULL AND advisor_reviewed_at IS NOT NULL AND advisor_comment IS NOT NULL)", name="advisor_stamp"),
        sa.CheckConstraint("state NOT IN ('RECORDED','NOT_GRANTED') OR (recorded_by IS NOT NULL AND recorded_at IS NOT NULL AND official_reference IS NOT NULL AND evidence_file_id IS NOT NULL AND effective_on IS NOT NULL)", name="outcome_stamp"))
    op.create_index("uq_withdrawal_member_open", "thesis_withdrawal_request", ["thesis_id","student_id"], unique=True,
        postgresql_where=sa.text("state IN ('SUBMITTED','ADVISOR_CONFIRMED','RECORDED')"))
    op.create_index("ix_withdrawal_student_state", "thesis_withdrawal_request", ["student_id","state"])


def downgrade():
    raise RuntimeError("Preserve withdrawal requests and external outcomes; use a forward migration")
