"""Add the department-to-major catalog without replacing existing student records."""

from alembic import op
import sqlalchemy as sa


revision = "20261021_0004"
down_revision = "20261021_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""CREATE TABLE department_major (
        department_id UUID NOT NULL,
        code VARCHAR(32) NOT NULL,
        name VARCHAR(255) NOT NULL,
        active BOOLEAN DEFAULT true NOT NULL,
        id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_department_major PRIMARY KEY (id),
        CONSTRAINT uq_department_major_department_id_code UNIQUE (department_id, code),
        CONSTRAINT fk_department_major_department_id_department FOREIGN KEY (department_id) REFERENCES department (id) ON DELETE RESTRICT
    );"""))
    # Preserve historical demo/legacy students before enforcing the relationship.
    # These unknown mappings remain inactive until an approved catalog confirms them.
    op.execute(sa.text("""INSERT INTO department_major
        (id, department_id, code, name, active)
        SELECT gen_random_uuid(), department_id, major_code,
               'Chưa xác minh (dữ liệu có trước danh mục)', false
        FROM student_profile
        WHERE major_code IS NOT NULL
        GROUP BY department_id, major_code;"""))
    op.execute(sa.text("""ALTER TABLE student_profile
        ADD CONSTRAINT fk_student_profile_department_major
        FOREIGN KEY (department_id, major_code)
        REFERENCES department_major (department_id, code) ON DELETE RESTRICT;"""))


def downgrade() -> None:
    raise RuntimeError("The permanent department-major catalog is intentionally non-destructive")
