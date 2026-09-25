"""Allow advisory comments from assigned lecturers without confirming progress."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260925_0005"
down_revision: Union[str, None] = "20260925_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_progress_review_decision"), "progress_review", type_="check")
    op.execute(sa.text(
        "ALTER TABLE progress_review ADD CONSTRAINT ck_progress_review_decision "
        "CHECK (decision IN ('COMMENT_ONLY','CONFIRM','REVISION_REQUIRED'))"
    ))


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM progress_review WHERE decision = 'COMMENT_ONLY') "
        "THEN RAISE EXCEPTION 'COMMENT_ONLY reviews would be lost by downgrade'; END IF; END $$"
    ))
    op.drop_constraint(op.f("ck_progress_review_decision"), "progress_review", type_="check")
    op.execute(sa.text(
        "ALTER TABLE progress_review ADD CONSTRAINT ck_progress_review_decision "
        "CHECK (decision IN ('CONFIRM','REVISION_REQUIRED'))"
    ))
