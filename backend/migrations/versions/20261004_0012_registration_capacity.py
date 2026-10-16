"""Store intended group capacity without changing historical membership.

Revision ID: 20261004_0012
Revises: 20261004_0011
"""
from alembic import op
import sqlalchemy as sa

revision = "20261004_0012"
down_revision = "20261004_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("topic_registration", sa.Column(
        "expected_member_count", sa.Integer(), nullable=False, server_default="1"))
    # Preserve the composition and consent of old registrations. A planned
    # capacity is not evidence that a student agreed to join.
    op.execute(sa.text("""
        UPDATE topic_registration r SET expected_member_count = t.max_students
        FROM topic t WHERE t.id=r.topic_id
    """))
    op.create_check_constraint(op.f("ck_topic_registration_expected_member_count"),
        "topic_registration", "expected_member_count BETWEEN 1 AND 3")


def downgrade():
    raise RuntimeError("This revision records group capacity; do not discard it automatically.")
