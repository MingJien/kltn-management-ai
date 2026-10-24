"""Allow notifications for lecturer registration decisions."""

from alembic import op
import sqlalchemy as sa

revision = "20261024_0006"
down_revision = "20261022_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE user_notification DROP CONSTRAINT ck_user_notification_kind"))
    op.execute(sa.text("""ALTER TABLE user_notification ADD CONSTRAINT ck_user_notification_kind
        CHECK (kind IN ('PROPOSAL_SUBMITTED','PROPOSAL_APPROVED','REGISTRATION_SUBMITTED',
                        'REGISTRATION_JOINED','REGISTRATION_ACCEPTED','REGISTRATION_REJECTED'))"""))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM user_notification WHERE kind IN ('REGISTRATION_ACCEPTED','REGISTRATION_REJECTED')"))
    op.execute(sa.text("ALTER TABLE user_notification DROP CONSTRAINT ck_user_notification_kind"))
    op.execute(sa.text("""ALTER TABLE user_notification ADD CONSTRAINT ck_user_notification_kind
        CHECK (kind IN ('PROPOSAL_SUBMITTED','PROPOSAL_APPROVED','REGISTRATION_SUBMITTED','REGISTRATION_JOINED'))"""))
