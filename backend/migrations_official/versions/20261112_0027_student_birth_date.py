"""Optional verified student date of birth for the original M11 grade sheet."""
from alembic import op
import sqlalchemy as sa

revision = "20261112_0027"
down_revision = "20261111_0026"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("student_profile", sa.Column("birth_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("student_profile", "birth_date")
