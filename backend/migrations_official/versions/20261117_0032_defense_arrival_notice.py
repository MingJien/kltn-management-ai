"""Shared arrival time and versioned council schedule publication."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID,JSONB

revision="20261117_0032"
down_revision="20261116_0031"
branch_labels=depends_on=None

def upgrade():
    op.add_column('defense_slot',sa.Column('arrival_at',sa.DateTime(timezone=True),nullable=True))
    op.create_check_constraint('arrival_order','defense_slot','arrival_at IS NULL OR arrival_at <= starts_at')
    op.create_table('defense_schedule_notice',
        sa.Column('id',UUID(),primary_key=True),
        sa.Column('council_id',UUID(),sa.ForeignKey('defense_council.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('version',sa.Integer(),nullable=False),sa.Column('snapshot',JSONB(),nullable=False),
        sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('published_by',UUID(),sa.ForeignKey('user_account.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('published_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('council_id','version'))

def downgrade():
    op.drop_table('defense_schedule_notice')
    op.drop_constraint('ck_defense_slot_arrival_order','defense_slot',type_='check')
    op.drop_column('defense_slot','arrival_at')
