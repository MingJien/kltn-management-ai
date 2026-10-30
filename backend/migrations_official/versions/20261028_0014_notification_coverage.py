"""Notice kinds for the remaining person-to-person actions.

No new table: user_notification keeps its single-table design; these kinds cover
the proposal upload/reviewer assignment, the cross-progress reviewer assignment,
the registration form (Mẫu 1a/1b) upload and the Dean's proposal confirmation.
"""
from alembic import op

revision = "20261028_0014"
down_revision = "20261028_0013"
branch_labels = None
depends_on = None

_ADDED = (
    "REGISTRATION_FORM_SUBMITTED",
    "PROPOSAL_REVIEWER_ASSIGNED",
    "PROGRESS_REVIEWER_ASSIGNED",
    "PROPOSAL_DEAN_CONFIRMED",
)
_BASE = (
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


def _list(values: tuple[str, ...]) -> str:
    return ",".join("'" + value + "'" for value in values)


def upgrade() -> None:
    op.execute("ALTER TABLE user_notification DROP CONSTRAINT ck_user_notification_kind")
    op.execute("ALTER TABLE user_notification ADD CONSTRAINT ck_user_notification_kind"
               " CHECK (kind IN (" + _list(_BASE + _ADDED) + "))")


def downgrade() -> None:
    op.execute("ALTER TABLE user_notification DROP CONSTRAINT ck_user_notification_kind")
    op.execute("DELETE FROM user_notification WHERE kind IN (" + _list(_ADDED) + ")")
    op.execute("ALTER TABLE user_notification ADD CONSTRAINT ck_user_notification_kind"
               " CHECK (kind IN (" + _list(_BASE) + "))")
