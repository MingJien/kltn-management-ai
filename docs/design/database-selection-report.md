# Current PostgreSQL schema

The application uses PostgreSQL database `kltn_management` at Alembic revision
`20261015_0001_official`: 32 business tables plus `alembic_version`.

The schema is defined by [`backend/migrations_official/`](../../backend/migrations_official/)
and can be inspected in the [schema-only export](../../database/official/kltn-management-schema.sql).
The export is generated from the official initial migration; it is not an
alternative migration history and must not be run on the database in use.

The old consolidated and core SQL exports are not part of the current schema.
