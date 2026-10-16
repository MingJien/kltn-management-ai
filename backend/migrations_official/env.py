"""Alembic environment for the permanent kltn_management database only.

An explicit DATABASE_URL is required; this migration environment never
selects a database implicitly.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from backend.db.metadata import target_metadata

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("Set DATABASE_URL explicitly to the new kltn_management database")
url = make_url(database_url)
if url.database != "kltn_management" or not url.drivername.startswith("postgresql"):
    raise RuntimeError("Official migrations only accept PostgreSQL database kltn_management")
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # The preflight SELECT starts a SQLAlchemy transaction. Own it explicitly
    # so a successful Alembic run commits DDL and its version row together.
    with connectable.begin() as connection:
        actual = connection.exec_driver_sql("SELECT current_database()").scalar_one()
        if actual != "kltn_management":
            raise RuntimeError(f"Refusing migration against {actual!r}")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
