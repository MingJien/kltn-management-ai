"""Keep issued documents and archive provenance protected from deletion."""
from alembic import op

revision = "20261115_0030"
down_revision = "20261115_0029"
branch_labels = depends_on = None

LINKS = (
    ("defense_print_record", "round_id", "thesis_round"),
    ("defense_print_record", "slot_id", "defense_slot"),
    ("defense_print_record", "created_by", "user_account"),
    ("thesis_archive_version", "thesis_id", "thesis"),
    ("thesis_archive_version", "file_id", "stored_file"),
    ("thesis_archive_version", "submitted_by", "user_account"),
    ("thesis_archive_version", "decided_by", "user_account"),
)


def replace_links(ondelete):
    for table, column, target in LINKS:
        name = f"fk_{table}_{column}_{target}"
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, target, [column], ["id"], ondelete=ondelete)


def upgrade():
    replace_links("RESTRICT")


def downgrade():
    replace_links(None)
