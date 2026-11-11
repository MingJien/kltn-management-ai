"""Version-bound, two-stage approval of research bonus evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "20261111_0026"
down_revision = "20261110_0025"
branch_labels = depends_on = None


def upgrade():
    op.create_table("publication_claim",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("thesis_id", pg.UUID(as_uuid=True), sa.ForeignKey("thesis.id"), nullable=False),
        sa.Column("evidence_version_id", pg.UUID(as_uuid=True), sa.ForeignKey("document_version.id"), nullable=False),
        sa.Column("submitted_by", pg.UUID(as_uuid=True), sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("details", pg.JSONB(), nullable=False),
        sa.Column("history", pg.JSONB(), nullable=False),
        sa.CheckConstraint("state IN ('SUBMITTED','ADVISOR_CONFIRMED','APPROVED','REJECTED','REVISION_REQUIRED')", name="state"))
    op.create_index("ix_publication_claim_thesis", "publication_claim", ["thesis_id"])


def downgrade():
    op.drop_table("publication_claim")
