"""Controlled corrections to closed defense records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "20261116_0031"
down_revision = "20261115_0030"
branch_labels = depends_on = None


def upgrade():
    op.create_table('defense_correction',
        sa.Column('id',UUID(),primary_key=True),
        sa.Column('slot_id',UUID(),sa.ForeignKey('defense_slot.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('requested_by',UUID(),sa.ForeignKey('user_account.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('source_version',sa.Integer(),nullable=False),sa.Column('state',sa.String(20),nullable=False),
        sa.Column('proposal',JSONB(),nullable=False),sa.Column('before',JSONB(),nullable=False),
        sa.Column('reason',sa.Text(),nullable=False),sa.Column('reference',sa.String(500),nullable=False),
        sa.Column('decided_by',UUID(),sa.ForeignKey('user_account.id',ondelete='RESTRICT')),
        sa.Column('decided_at',sa.DateTime(timezone=True)),sa.Column('decision_note',sa.Text()),
        sa.Column('row_version',sa.Integer(),server_default='1',nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint("state IN ('PENDING','APPROVED','REJECTED','CANCELLED')",name='state'))
    op.create_index('uq_defense_correction_pending','defense_correction',['slot_id'],unique=True,postgresql_where=sa.text("state = 'PENDING'"))


def downgrade():
    op.drop_table("defense_correction")
