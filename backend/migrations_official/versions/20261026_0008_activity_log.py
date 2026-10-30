"""Searchable source references and chronological activity history."""
from alembic import op
import sqlalchemy as sa

revision = "20261026_0008"
down_revision = "20261026_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_event", sa.Column("source_reference", sa.String(500), nullable=True))
    op.create_index("ix_audit_event_occurred_id", "audit_event", ["occurred_at", "id"])


def downgrade():
    raise RuntimeError("Activity history and source references must be preserved")
