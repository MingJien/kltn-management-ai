"""Keep topic publication lifecycle separate from academic workflow state."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "20261029_0016"
down_revision = "20261028_0015"
branch_labels = None
depends_on = None
def upgrade():
    op.add_column("topic", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("topic", sa.Column("archived_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("topic", sa.Column("archive_reason", sa.Text(), nullable=True))
    op.create_foreign_key("fk_topic_archived_by_user_account", "topic", "user_account", ["archived_by"], ["id"], ondelete="RESTRICT")
def downgrade():
    raise RuntimeError("Preserve topic archive history; use a forward migration")
