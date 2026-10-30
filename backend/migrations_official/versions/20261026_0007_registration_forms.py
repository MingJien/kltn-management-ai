"""Immutable submitted registration forms, before a thesis exists."""
from alembic import op
import sqlalchemy as sa

revision = "20261026_0007"
down_revision = "20261024_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""CREATE TABLE registration_form_version (
        registration_id UUID NOT NULL,
        stored_file_id UUID NOT NULL,
        submitted_by UUID NOT NULL,
        form_code VARCHAR(2) NOT NULL,
        version_no INTEGER NOT NULL,
        content_sha256 VARCHAR(64) NOT NULL,
        registration_fingerprint VARCHAR(64) NOT NULL,
        submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
        id UUID NOT NULL,
        CONSTRAINT pk_registration_form_version PRIMARY KEY (id),
        CONSTRAINT uq_registration_form_version_registration_id_version_no UNIQUE (registration_id, version_no),
        CONSTRAINT ck_registration_form_version_version_positive CHECK (version_no > 0),
        CONSTRAINT ck_registration_form_version_form_code CHECK (form_code IN ('1A','1B')),
        CONSTRAINT ck_registration_form_version_hash_length CHECK (length(content_sha256) = 64 AND length(registration_fingerprint) = 64),
        CONSTRAINT fk_registration_form_version_registration_id_topic_registration FOREIGN KEY (registration_id) REFERENCES topic_registration (id) ON DELETE RESTRICT,
        CONSTRAINT fk_registration_form_version_stored_file_id_stored_file FOREIGN KEY (stored_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
        CONSTRAINT fk_registration_form_version_submitted_by_student_profile FOREIGN KEY (submitted_by) REFERENCES student_profile (id) ON DELETE RESTRICT
    );"""))


def downgrade():
    raise RuntimeError("Registration form history must not be destroyed by downgrade")
