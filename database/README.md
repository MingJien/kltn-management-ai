# PostgreSQL `kltn_management`

The application database currently uses Alembic revision `20261015_0001_official`: 32 business tables and `alembic_version`.

| File | Purpose |
| --- | --- |
| [official/kltn-management-schema.sql](official/kltn-management-schema.sql) | Schema-only snapshot of the current database structure; no user data. |

Update an existing database only through [the official Alembic migrations](../backend/migrations_official/) using `alembic-official.ini`. Never run the SQL snapshot against a database that already contains data.

See the [ERD](../docs/design/erd-kltn-management.md) and [data dictionary](../docs/design/database-dictionary.md) for relationships and column meanings.
