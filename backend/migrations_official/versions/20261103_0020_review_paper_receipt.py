"""Separate authenticated review submission from receipt of the signed paper."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
revision="20261103_0020"
down_revision="20261102_0019"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("thesis_review",sa.Column("paper_reference",sa.String(500)))
    op.add_column("thesis_review",sa.Column("paper_export_code",sa.String(100)))
    op.add_column("thesis_review",sa.Column("paper_confirmed_by",pg.UUID(as_uuid=True),sa.ForeignKey("user_account.id",ondelete="RESTRICT")))
    op.add_column("thesis_review",sa.Column("paper_confirmed_at",sa.DateTime(timezone=True)))
    op.drop_constraint(op.f("ck_thesis_review_submitted_has_signed_copy"),"thesis_review",type_="check")
    op.create_check_constraint("submitted_metadata","thesis_review","state = 'DRAFT' OR submitted_at IS NOT NULL")
    op.create_check_constraint("paper_receipt_metadata","thesis_review","(paper_confirmed_by IS NULL AND paper_confirmed_at IS NULL AND paper_reference IS NULL AND paper_export_code IS NULL) OR (state = 'SUBMITTED' AND paper_confirmed_by IS NOT NULL AND paper_confirmed_at IS NOT NULL AND length(trim(paper_reference)) >= 5 AND paper_export_code IS NOT NULL)")

def downgrade():
    raise RuntimeError("Paper receipts are historical evidence; restore a backup instead of destructive downgrade.")
