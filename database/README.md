# PostgreSQL `kltn_management`

The application database uses 33 business tables and `alembic_version`. Current Alembic head is `20261021_0003`.

| File | Purpose |
| --- | --- |
| [official/kltn-management-schema.sql](official/kltn-management-schema.sql) | Schema-only snapshot of the current database structure; no user data. |

Update an existing database only through [the official Alembic migrations](../backend/migrations_official/) using `alembic.ini`. Never run the SQL snapshot against a database that already contains data.

See the [ERD](../docs/design/erd-kltn-management.md) and [data dictionary](../docs/design/database-dictionary.md) for relationships and column meanings.
