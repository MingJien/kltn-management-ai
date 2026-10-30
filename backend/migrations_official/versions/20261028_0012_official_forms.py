"""Versioned faculty forms/publications for assigned rounds; independent official chain."""
from alembic import op

revision = "20261028_0012"
down_revision = "20261028_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE official_form (
	round_id UUID NOT NULL,
	code VARCHAR(50) NOT NULL,
	title VARCHAR(255) NOT NULL,
	document_kind VARCHAR(20) NOT NULL,
	audience VARCHAR(30) NOT NULL,
	state VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
	created_by UUID NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	CONSTRAINT pk_official_form PRIMARY KEY (id),
	CONSTRAINT uq_official_form_round_id_code UNIQUE (round_id, code),
	CONSTRAINT ck_official_form_document_kind CHECK (document_kind IN ('FORM','PUBLICATION')),
	CONSTRAINT ck_official_form_audience CHECK (audience IN ('STUDENT_AND_LECTURER','LECTURER')),
	CONSTRAINT ck_official_form_state CHECK (state IN ('ACTIVE','ARCHIVED')),
	CONSTRAINT fk_official_form_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
	CONSTRAINT fk_official_form_created_by_user_account FOREIGN KEY(created_by) REFERENCES user_account (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE official_form_version (
	official_form_id UUID NOT NULL,
	version_no INTEGER NOT NULL,
	stored_file_id UUID NOT NULL,
	uploaded_by UUID NOT NULL,
	source_reference VARCHAR(500) NOT NULL,
	change_reason TEXT NOT NULL,
	state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
	published_by UUID,
	published_at TIMESTAMP WITH TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	CONSTRAINT pk_official_form_version PRIMARY KEY (id),
	CONSTRAINT uq_official_form_version_official_form_id_version_no UNIQUE (official_form_id, version_no),
	CONSTRAINT ck_official_form_version_version_positive CHECK (version_no > 0),
	CONSTRAINT ck_official_form_version_state CHECK (state IN ('DRAFT','PUBLISHED','SUPERSEDED','WITHDRAWN')),
	CONSTRAINT ck_official_form_version_publisher_pair CHECK ((published_at IS NULL) = (published_by IS NULL)),
	CONSTRAINT ck_official_form_version_published_stamp CHECK (state NOT IN ('PUBLISHED','SUPERSEDED') OR published_at IS NOT NULL),
	CONSTRAINT ck_official_form_version_draft_stamp CHECK (state != 'DRAFT' OR published_at IS NULL),
	CONSTRAINT fk_official_form_version_official_form_id_official_form FOREIGN KEY(official_form_id) REFERENCES official_form (id) ON DELETE RESTRICT,
	CONSTRAINT fk_official_form_version_stored_file_id_stored_file FOREIGN KEY(stored_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
	CONSTRAINT fk_official_form_version_uploaded_by_user_account FOREIGN KEY(uploaded_by) REFERENCES user_account (id) ON DELETE RESTRICT,
	CONSTRAINT fk_official_form_version_published_by_user_account FOREIGN KEY(published_by) REFERENCES user_account (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE UNIQUE INDEX uq_official_form_current ON official_form_version (official_form_id) WHERE state = 'PUBLISHED'""")


def downgrade():
    raise RuntimeError("Keep published institutional files and their versions; use additive migrations")
