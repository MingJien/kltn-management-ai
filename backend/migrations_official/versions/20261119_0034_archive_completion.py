"""Reflect an existing effective archive approval in the thesis lifecycle."""
from alembic import op
import sqlalchemy as sa

revision = "20261119_0034"
down_revision = "20261118_0033"
branch_labels = depends_on = None


def upgrade():
    op.execute(sa.text("""
        UPDATE thesis AS t
           SET state = 'COMPLETED', row_version = t.row_version + 1, updated_at = now()
          FROM (SELECT DISTINCT ON (thesis_id) thesis_id, state
                  FROM thesis_archive_version ORDER BY thesis_id, version_no DESC) AS latest
         WHERE t.id = latest.thesis_id AND t.state = 'DEFENDED' AND latest.state = 'ACCEPTED'
    """))


def downgrade():
    # COMPLETED is also valid in the previous schema. Retain verified academic history.
    pass
