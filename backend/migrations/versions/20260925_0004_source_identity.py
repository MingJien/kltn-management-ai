"""Keep stable external source identity and URL for rebuildable corpus ingestion."""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260925_0004"
down_revision: Union[str, None] = "20260925_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("repository_item", sa.Column("external_source_id", sa.String(200), nullable=True))
    op.add_column("repository_item", sa.Column("source_url", sa.String(1000), nullable=True))
    op.create_unique_constraint("uq_repository_item_external_source_id", "repository_item", ["external_source_id"])
    op.create_check_constraint("ck_repository_item_source_url_https", "repository_item", "source_url IS NULL OR source_url LIKE 'https://%'")
    op.drop_constraint("ck_repository_item_has_source_reference", "repository_item", type_="check")
    op.create_check_constraint(
        "ck_repository_item_has_source_reference", "repository_item",
        "source_ref IS NOT NULL OR source_url IS NOT NULL OR stored_file_id IS NOT NULL OR published_document_version_id IS NOT NULL",
    )


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM repository_item WHERE source_url IS NOT NULL AND source_ref IS NULL "
        "AND stored_file_id IS NULL AND published_document_version_id IS NULL) "
        "THEN RAISE EXCEPTION 'URL-only corpus source would be lost by downgrade'; END IF; END $$"
    ))
    op.drop_constraint("ck_repository_item_has_source_reference", "repository_item", type_="check")
    op.create_check_constraint(
        "ck_repository_item_has_source_reference", "repository_item",
        "source_ref IS NOT NULL OR stored_file_id IS NOT NULL OR published_document_version_id IS NOT NULL",
    )
    op.drop_constraint("ck_repository_item_source_url_https", "repository_item", type_="check")
    op.drop_constraint("uq_repository_item_external_source_id", "repository_item", type_="unique")
    op.drop_column("repository_item", "source_url")
    op.drop_column("repository_item", "external_source_id")
