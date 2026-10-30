"""Report-book deadline and thesis-scoped notices on the existing notification table.

No new table: user_notification gains an optional thesis/subject/message/url so a
notice can point at the exact thesis or account action, while legacy proposal and
registration notices keep their registration link.
"""
from alembic import op

revision = "20261028_0013"
down_revision = "20261028_0012"
branch_labels = None
depends_on = None

KINDS = (
    "PROPOSAL_SUBMITTED", "PROPOSAL_APPROVED", "PROPOSAL_REVIEWED", "PROPOSAL_FINALIZED",
    "REGISTRATION_SUBMITTED", "REGISTRATION_JOINED", "REGISTRATION_ACCEPTED",
    "REGISTRATION_REJECTED",
    "MILESTONE_OPENED", "MILESTONE_EXTENDED", "MILESTONE_REOPENED", "MILESTONE_CLOSED",
    "DOCUMENT_DEADLINE_SET", "DOCUMENT_DEADLINE_EXTENDED", "DOCUMENT_DEADLINE_REOPENED",
    "DOCUMENT_DEADLINE_CLOSED",
    "PROGRESS_SUBMITTED", "PROGRESS_CONFIRMED", "PROGRESS_REVISION_REQUIRED",
    "PROGRESS_COMMENT",
    "DOCUMENT_SUBMITTED", "DOCUMENT_ACCEPTED", "DOCUMENT_REVISION_REQUESTED",
    "WORK_SUBMITTED", "WORK_APPROVED", "WORK_REVISION_REQUIRED",
    "ACCOUNT_LOCKED", "ACCOUNT_UNLOCKED", "ACCOUNT_DISABLED", "ACCOUNT_RESTORED",
    "ACCOUNT_LINK_REISSUED", "ACCOUNT_EMAIL_CORRECTED",
)
_OLD_KINDS = (
    "PROPOSAL_SUBMITTED", "PROPOSAL_APPROVED", "REGISTRATION_SUBMITTED",
    "REGISTRATION_JOINED", "REGISTRATION_ACCEPTED", "REGISTRATION_REJECTED",
)
_kind_list = ",".join("'" + kind + "'" for kind in KINDS)
_old_kind_list = ",".join("'" + kind + "'" for kind in _OLD_KINDS)


def upgrade() -> None:
    # A report book for the similarity check keeps its own immutable versions.
    op.execute("ALTER TABLE document_deadline DROP CONSTRAINT ck_document_deadline_document_type")
    op.execute("""ALTER TABLE document_deadline ADD CONSTRAINT ck_document_deadline_document_type
        CHECK (document_type IN ('PROPOSAL','PLAN','REPORT','SUPPORTING'))""")

    # Notices no longer require a registration; they may target a thesis or an account.
    op.execute("ALTER TABLE user_notification ALTER COLUMN registration_id DROP NOT NULL")
    op.execute("ALTER TABLE user_notification ADD COLUMN thesis_id UUID")
    op.execute("ALTER TABLE user_notification ADD COLUMN subject_type VARCHAR(40)")
    op.execute("ALTER TABLE user_notification ADD COLUMN subject_id UUID")
    op.execute("ALTER TABLE user_notification ADD COLUMN message TEXT")
    op.execute("ALTER TABLE user_notification ADD COLUMN url VARCHAR(300)")
    op.execute("""ALTER TABLE user_notification ADD CONSTRAINT fk_user_notification_thesis_id_thesis
        FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT""")
    op.execute("""CREATE INDEX ix_user_notification_thesis_created
        ON user_notification (thesis_id, created_at)""")
    op.execute("ALTER TABLE user_notification DROP CONSTRAINT ck_user_notification_kind")
    op.execute("""ALTER TABLE user_notification ADD CONSTRAINT ck_user_notification_kind
        CHECK (kind IN (""" + _kind_list + "))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_notification_thesis_created")
    op.execute("ALTER TABLE user_notification DROP CONSTRAINT ck_user_notification_kind")
    op.execute("ALTER TABLE user_notification ADD CONSTRAINT ck_user_notification_kind"
               " CHECK (kind IN (" + _old_kind_list + "))")
    op.execute("DELETE FROM user_notification WHERE kind NOT IN (" + _old_kind_list + ")")
    op.execute("ALTER TABLE user_notification DROP CONSTRAINT fk_user_notification_thesis_id_thesis")
    op.execute("ALTER TABLE user_notification DROP COLUMN url")
    op.execute("ALTER TABLE user_notification DROP COLUMN message")
    op.execute("ALTER TABLE user_notification DROP COLUMN subject_id")
    op.execute("ALTER TABLE user_notification DROP COLUMN subject_type")
    op.execute("ALTER TABLE user_notification DROP COLUMN thesis_id")
    op.execute("DELETE FROM user_notification WHERE registration_id IS NULL")
    op.execute("ALTER TABLE user_notification ALTER COLUMN registration_id SET NOT NULL")
    op.execute("ALTER TABLE document_deadline DROP CONSTRAINT ck_document_deadline_document_type")
    op.execute("""ALTER TABLE document_deadline ADD CONSTRAINT ck_document_deadline_document_type
        CHECK (document_type IN ('PROPOSAL','PLAN','SUPPORTING'))""")
