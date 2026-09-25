"""Allow a typed corpus independent of operational theses.

Existing rows are managed theses. The migration preserves them without rewriting
the two previously applied revisions. PostgreSQL validates the new constraints.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260925_0003"
down_revision: Union[str, None] = "20260924_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("repository_item", "thesis_id", existing_type=UUID(as_uuid=True), nullable=True)
    op.alter_column("repository_item", "published_document_version_id", existing_type=UUID(as_uuid=True), nullable=True)
    op.add_column("repository_item", sa.Column("stored_file_id", UUID(as_uuid=True), nullable=True))
    op.add_column("repository_item", sa.Column("origin_type", sa.String(30), nullable=False, server_default="MANAGED_THESIS"))
    op.add_column("repository_item", sa.Column("source_ref", sa.String(500), nullable=True))
    op.add_column("repository_item", sa.Column("provenance", sa.Text(), nullable=True))
    op.add_column("repository_item", sa.Column("source_version", sa.String(100), nullable=True))
    op.create_foreign_key("fk_repository_item_stored_file_id_stored_file", "repository_item", "stored_file", ["stored_file_id"], ["id"], ondelete="RESTRICT")
    op.create_check_constraint("ck_repository_item_origin_type", "repository_item", "origin_type IN ('MANAGED_THESIS','IMPORTED_DOCUMENT','OFFICIAL_SOURCE')")
    op.create_check_constraint("ck_repository_item_source_type", "repository_item", "source_type IN ('THESIS','CAPSTONE_PROJECT','TERM_PROJECT','COURSE_PROJECT','REGULATION','FORM','GUIDELINE','SYNTHETIC_TEST')")
    op.create_check_constraint(
        "ck_repository_item_origin_source_consistency", "repository_item",
        "(origin_type = 'MANAGED_THESIS' AND source_type = 'THESIS' AND thesis_id IS NOT NULL AND published_document_version_id IS NOT NULL) OR "
        "(origin_type = 'IMPORTED_DOCUMENT' AND source_type IN ('THESIS','CAPSTONE_PROJECT','TERM_PROJECT','COURSE_PROJECT','SYNTHETIC_TEST') AND thesis_id IS NULL AND published_document_version_id IS NULL) OR "
        "(origin_type = 'OFFICIAL_SOURCE' AND source_type IN ('REGULATION','FORM','GUIDELINE') AND thesis_id IS NULL AND published_document_version_id IS NULL)",
    )
    op.create_check_constraint("ck_repository_item_has_source_reference", "repository_item", "source_ref IS NOT NULL OR stored_file_id IS NOT NULL OR published_document_version_id IS NOT NULL")
    op.create_index("ix_repository_item_source_type_visibility", "repository_item", ["source_type", "visibility"])

    op.alter_column("search_index_metadata", "document_version_id", existing_type=UUID(as_uuid=True), nullable=True)
    op.add_column("similarity_match", sa.Column("source_repository_item_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_similarity_match_source_repository_item_id_repository_item", "similarity_match", "repository_item", ["source_repository_item_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM repository_item WHERE thesis_id IS NULL OR published_document_version_id IS NULL) "
        "THEN RAISE EXCEPTION 'Imported corpus would be lost by downgrade'; END IF; END $$"
    ))
    op.drop_constraint("fk_similarity_match_source_repository_item_id_repository_item", "similarity_match", type_="foreignkey")
    op.drop_column("similarity_match", "source_repository_item_id")
    op.alter_column("search_index_metadata", "document_version_id", existing_type=UUID(as_uuid=True), nullable=False)
    op.drop_index("ix_repository_item_source_type_visibility", table_name="repository_item")
    for name in ("has_source_reference", "origin_source_consistency", "source_type", "origin_type"):
        op.drop_constraint("ck_repository_item_" + name, "repository_item", type_="check")
    op.drop_constraint("fk_repository_item_stored_file_id_stored_file", "repository_item", type_="foreignkey")
    for name in ("source_version", "provenance", "source_ref", "origin_type", "stored_file_id"):
        op.drop_column("repository_item", name)
    op.alter_column("repository_item", "published_document_version_id", existing_type=UUID(as_uuid=True), nullable=False)
    op.alter_column("repository_item", "thesis_id", existing_type=UUID(as_uuid=True), nullable=False)
