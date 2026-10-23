"""Per-round document-type deadlines, preserving each submitted version's due date."""

from alembic import op
import sqlalchemy as sa

revision = "20261022_0005"
down_revision = "20261021_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""CREATE TABLE document_deadline (
        round_id UUID NOT NULL,
        document_type VARCHAR(30) NOT NULL,
        due_at TIMESTAMP WITH TIME ZONE NOT NULL,
        state VARCHAR(20) DEFAULT 'OPEN' NOT NULL,
        set_by UUID NOT NULL,
        reason TEXT NOT NULL,
        id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        row_version INTEGER DEFAULT '1' NOT NULL,
        CONSTRAINT pk_document_deadline PRIMARY KEY (id),
        CONSTRAINT uq_document_deadline_round_id_document_type UNIQUE (round_id, document_type),
        CONSTRAINT ck_document_deadline_document_type CHECK (document_type IN ('PROPOSAL','PLAN','SUPPORTING')),
        CONSTRAINT ck_document_deadline_state CHECK (state IN ('OPEN','CLOSED')),
        CONSTRAINT fk_document_deadline_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
        CONSTRAINT fk_document_deadline_set_by_user_account FOREIGN KEY (set_by) REFERENCES user_account (id) ON DELETE RESTRICT
    );"""))
    op.execute(sa.text("ALTER TABLE proposal_version ADD COLUMN due_at_at_submission TIMESTAMP WITH TIME ZONE"))
    op.execute(sa.text("ALTER TABLE document_version ADD COLUMN due_at_at_submission TIMESTAMP WITH TIME ZONE"))


def downgrade() -> None:
    raise RuntimeError("Permanent submission deadlines and version history are intentionally non-destructive")
