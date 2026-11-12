"""Student training cohort used by the faculty M6 original."""
from alembic import op
import sqlalchemy as sa

revision = "20261112_0028"
down_revision = "20261112_0027"
branch_labels = depends_on = None


def upgrade():
    op.add_column("student_profile", sa.Column("training_cohort", sa.String(50), nullable=True))


def downgrade():
    op.drop_column("student_profile", "training_cohort")
