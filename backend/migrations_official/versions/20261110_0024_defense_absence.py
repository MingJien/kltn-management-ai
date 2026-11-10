"""Preserve defense attempts and record individual faculty absence decisions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261110_0024"
down_revision = "20261108_0023"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("uq_defense_slot_thesis_id", "defense_slot", type_="unique")
    op.add_column("defense_slot", sa.Column("prior_slot_id", postgresql.UUID(), nullable=True))
    op.create_foreign_key("fk_defense_slot_prior_slot_id_defense_slot", "defense_slot", "defense_slot", ["prior_slot_id"], ["id"], ondelete="RESTRICT")
    op.create_index("uq_defense_slot_active_thesis", "defense_slot", ["thesis_id"], unique=True, postgresql_where=sa.text("finalized_at IS NULL"))
    op.create_table("defense_absence_decision",
        sa.Column("id",postgresql.UUID(),primary_key=True),
        sa.Column("slot_id",postgresql.UUID(),sa.ForeignKey("defense_slot.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("thesis_member_id",postgresql.UUID(),sa.ForeignKey("thesis_member.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("outcome",sa.String(30),nullable=False),
        sa.Column("reference",sa.String(300),nullable=False),sa.Column("reason",sa.Text(),nullable=False),
        sa.Column("recorded_by",postgresql.UUID(),sa.ForeignKey("user_account.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("recorded_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("row_version",sa.Integer(),server_default="1",nullable=False),
        sa.UniqueConstraint("slot_id","thesis_member_id"),
        sa.CheckConstraint("outcome IN ('NOT_PASSED','SUPPLEMENTARY')",name="outcome"))


def downgrade():
    raise RuntimeError("Submitted absence decisions and defense attempts require a reviewed backup; no destructive downgrade.")
