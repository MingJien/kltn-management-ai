"""Allow a request without guessing an extension deadline."""
from alembic import op
import sqlalchemy as sa
revision = "20261110_0025"
down_revision = "20261110_0024"
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column("thesis_extension_request", "requested_until_at", existing_type=sa.DateTime(timezone=True), nullable=True)

def downgrade():
    if op.get_bind().scalar(sa.text("select count(*) from thesis_extension_request where requested_until_at is null")):
        raise RuntimeError("Cannot downgrade: extension requests without a proposed deadline exist")
    op.alter_column("thesis_extension_request", "requested_until_at", existing_type=sa.DateTime(timezone=True), nullable=False)
