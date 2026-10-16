"""Keep class and major from the approved student roster.

Revision ID: 20261010_0013
Revises: 20261004_0012
"""

from alembic import op
import sqlalchemy as sa

revision = "20261010_0013"
down_revision = "20261004_0012"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable so existing student profiles and their registration history remain intact.
    op.add_column("student_profile", sa.Column("class_name", sa.String(length=100), nullable=True))
    op.add_column("student_profile", sa.Column("major_code", sa.String(length=32), nullable=True))


def downgrade():
    raise RuntimeError("Class and major may contain imported data; do not discard automatically.")
