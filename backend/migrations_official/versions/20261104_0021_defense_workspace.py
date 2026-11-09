"""Online withdrawals and council defense records."""
from alembic import op

revision = "20261104_0021"
down_revision = "20261103_0020"
branch_labels = None
depends_on = None


def upgrade():
    table = "thesis_withdrawal_request"
    op.drop_constraint(op.f("ck_thesis_withdrawal_request_advisor_stamp"), table, type_="check")
    op.drop_constraint(op.f("ck_thesis_withdrawal_request_outcome_stamp"), table, type_="check")
    op.create_check_constraint("advisor_stamp", table,
        "state NOT IN ('ADVISOR_CONFIRMED','RETURNED') OR "
        "(advisor_reviewed_by IS NOT NULL AND advisor_reviewed_at IS NOT NULL AND advisor_comment IS NOT NULL)")
    op.create_check_constraint("outcome_stamp", table,
        "state NOT IN ('RECORDED','NOT_GRANTED') OR (recorded_by IS NOT NULL AND recorded_at IS NOT NULL "
        "AND official_reference IS NOT NULL AND effective_on IS NOT NULL)")
    op.execute("""CREATE TABLE defense_council (
    round_id UUID NOT NULL,
    department_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    reference VARCHAR(300) NOT NULL,
    members JSONB NOT NULL,
    created_by UUID NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_defense_council PRIMARY KEY (id),
    CONSTRAINT uq_defense_council_round_id_department_id_name UNIQUE (round_id, department_id, name),
    CONSTRAINT fk_defense_council_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_defense_council_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT,
    CONSTRAINT fk_defense_council_created_by_user_account FOREIGN KEY(created_by) REFERENCES user_account (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE defense_slot (
    thesis_id UUID NOT NULL,
    council_id UUID NOT NULL,
    report_version_id UUID NOT NULL,
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
    room VARCHAR(200) NOT NULL,
    roster JSONB NOT NULL,
    marks JSONB NOT NULL,
    attendance JSONB NOT NULL,
    minutes JSONB NOT NULL,
    finalized_by UUID,
    finalized_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_defense_slot PRIMARY KEY (id),
    CONSTRAINT ck_defense_slot_time_order CHECK (ends_at > starts_at),
    CONSTRAINT ck_defense_slot_finalized_stamp CHECK ((finalized_at IS NULL) = (finalized_by IS NULL)),
    CONSTRAINT uq_defense_slot_thesis_id UNIQUE (thesis_id),
    CONSTRAINT fk_defense_slot_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT fk_defense_slot_council_id_defense_council FOREIGN KEY(council_id) REFERENCES defense_council (id) ON DELETE RESTRICT,
    CONSTRAINT fk_defense_slot_report_version_id_document_version FOREIGN KEY(report_version_id) REFERENCES document_version (id) ON DELETE RESTRICT,
    CONSTRAINT fk_defense_slot_finalized_by_user_account FOREIGN KEY(finalized_by) REFERENCES user_account (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_defense_slot_council_start ON defense_slot (council_id, starts_at)""")


def downgrade():
    raise RuntimeError("Restore a backup to preserve withdrawal decisions and defense records.")
