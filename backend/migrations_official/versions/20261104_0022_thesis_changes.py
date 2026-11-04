"""Group topic changes and one-time thesis extensions."""
from alembic import op

revision = "20261104_0022"
down_revision = "20261104_0021"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
CREATE TABLE thesis_change_request (
	thesis_id UUID NOT NULL,
	kind VARCHAR(20) NOT NULL,
	state VARCHAR(25) NOT NULL,
	requested_by UUID NOT NULL,
	reason TEXT NOT NULL,
	proposed_title VARCHAR(500) NOT NULL,
	proposed_description TEXT NOT NULL,
	target_topic_id UUID,
	snapshot JSONB NOT NULL,
	consents JSONB NOT NULL,
	reviews JSONB NOT NULL,
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
	decided_by UUID,
	decided_at TIMESTAMP WITH TIME ZONE,
	decision_reason TEXT,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	CONSTRAINT pk_thesis_change_request PRIMARY KEY (id),
	CONSTRAINT ck_thesis_change_request_kind CHECK (kind IN ('ADJUSTMENT','REPLACEMENT')),
	CONSTRAINT ck_thesis_change_request_state CHECK (state IN ('SUBMITTED','ADVISOR_REVIEWED','APPROVED','REJECTED','CANCELLED')),
	CONSTRAINT ck_thesis_change_request_reason CHECK (length(trim(reason)) >= 10),
	CONSTRAINT ck_thesis_change_request_decision CHECK (state != 'APPROVED' OR (decided_by IS NOT NULL AND decided_at IS NOT NULL)),
	CONSTRAINT fk_thesis_change_request_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
	CONSTRAINT fk_thesis_change_request_requested_by_user_account FOREIGN KEY(requested_by) REFERENCES user_account (id) ON DELETE RESTRICT,
	CONSTRAINT fk_thesis_change_request_target_topic_id_topic FOREIGN KEY(target_topic_id) REFERENCES topic (id) ON DELETE RESTRICT,
	CONSTRAINT fk_thesis_change_request_decided_by_user_account FOREIGN KEY(decided_by) REFERENCES user_account (id) ON DELETE RESTRICT
)
    """)
    op.execute("""
CREATE UNIQUE INDEX uq_thesis_change_open ON thesis_change_request (thesis_id) WHERE state IN ('SUBMITTED','ADVISOR_REVIEWED')
    """)
    op.execute("""
CREATE TABLE thesis_extension (
	thesis_id UUID NOT NULL,
	original_due_at TIMESTAMP WITH TIME ZONE NOT NULL,
	until_at TIMESTAMP WITH TIME ZONE NOT NULL,
	decision_on DATE NOT NULL,
	reference VARCHAR(500) NOT NULL,
	reason TEXT NOT NULL,
	recorded_by UUID NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	evidence_file_id UUID,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_thesis_extension PRIMARY KEY (id),
	CONSTRAINT uq_thesis_extension_thesis_id UNIQUE (thesis_id),
	CONSTRAINT ck_thesis_extension_later_due CHECK (until_at > original_due_at),
	CONSTRAINT ck_thesis_extension_reference CHECK (length(trim(reference)) >= 5),
	CONSTRAINT fk_thesis_extension_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
	CONSTRAINT fk_thesis_extension_recorded_by_user_account FOREIGN KEY(recorded_by) REFERENCES user_account (id) ON DELETE RESTRICT,
	CONSTRAINT fk_thesis_extension_evidence_file_id_stored_file FOREIGN KEY(evidence_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT
)
    """)


def downgrade():
    raise RuntimeError("Restore a backup to retain change decisions and extension records.")
