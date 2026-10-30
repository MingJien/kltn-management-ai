"""Persist per-account notices for proposal and registration activity."""
from alembic import op
import sqlalchemy as sa

revision = "20261021_0003"
down_revision = "20261020_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""CREATE TABLE user_notification (
        recipient_user_id UUID NOT NULL,
        actor_user_id UUID NOT NULL,
        registration_id UUID NOT NULL,
        kind VARCHAR(32) NOT NULL,
        read_at TIMESTAMP WITH TIME ZONE,
        revoked_at TIMESTAMP WITH TIME ZONE,
        id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_user_notification PRIMARY KEY (id),
        CONSTRAINT ck_user_notification_kind CHECK (kind IN ('PROPOSAL_SUBMITTED','PROPOSAL_APPROVED','REGISTRATION_SUBMITTED','REGISTRATION_JOINED')),
        CONSTRAINT fk_user_notification_recipient_user_id_user_account FOREIGN KEY(recipient_user_id) REFERENCES user_account (id) ON DELETE RESTRICT,
        CONSTRAINT fk_user_notification_actor_user_id_user_account FOREIGN KEY(actor_user_id) REFERENCES user_account (id) ON DELETE RESTRICT,
        CONSTRAINT fk_user_notification_registration_id_topic_registration FOREIGN KEY(registration_id) REFERENCES topic_registration (id) ON DELETE RESTRICT
    );"""))
    op.execute(sa.text("""CREATE INDEX ix_user_notification_recipient_created
        ON user_notification (recipient_user_id, created_at);"""))


def downgrade() -> None:
    op.drop_index("ix_user_notification_recipient_created", table_name="user_notification")
    op.drop_table("user_notification")
