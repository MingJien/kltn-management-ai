"""Topic codes, receiving lecturer and per-member supporting evidence.

Revision ID: 20261004_0011
Revises: 20261003_0010
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261004_0011"
down_revision = "20261003_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("topic", sa.Column("code", sa.String(40), nullable=True))
    op.add_column("topic", sa.Column("receiving_lecturer_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(sa.text("""
        WITH numbered AS (
            SELECT t.id, 'DT-' || EXTRACT(YEAR FROM y.starts_on)::int || '-' ||
                EXTRACT(YEAR FROM y.ends_on)::int AS prefix,
                row_number() OVER (PARTITION BY EXTRACT(YEAR FROM y.starts_on),
                    EXTRACT(YEAR FROM y.ends_on) ORDER BY t.created_at, t.id) AS seq
            FROM topic t JOIN thesis_round r ON r.id=t.round_id
            JOIN academic_year y ON y.id=r.academic_year_id
        ) UPDATE topic t SET code=n.prefix || '-' || lpad(n.seq::text, 4, '0')
          FROM numbered n WHERE n.id=t.id
    """))
    op.execute(sa.text("""
        UPDATE topic t SET receiving_lecturer_id=l.id FROM lecturer_profile l
        WHERE t.proposer_type='LECTURER' AND l.user_id=t.proposer_user_id
    """))
    op.alter_column("topic", "code", nullable=False)
    op.create_unique_constraint(op.f("uq_topic_code"), "topic", ["code"])
    op.create_foreign_key(op.f("fk_topic_receiving_lecturer_id_lecturer_profile"),
        "topic", "lecturer_profile", ["receiving_lecturer_id"], ["id"], ondelete="RESTRICT")
    op.add_column("registration_member", sa.Column("evidence_file_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(op.f("fk_registration_member_evidence_file_id_stored_file"),
        "registration_member", "stored_file", ["evidence_file_id"], ["id"], ondelete="RESTRICT")


def downgrade():
    raise RuntimeError("This revision stores topic identifiers and evidence links; do not discard them automatically.")
