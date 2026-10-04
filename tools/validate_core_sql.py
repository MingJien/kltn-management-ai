"""Run the submitted core SQL in a disposable schema; never touch public data."""
from __future__ import annotations
import os
import re
import subprocess
from uuid import uuid4
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from backend.db.base import Base
from backend.db.validate_schema import load_env
from tools.export_core_database_sql import OUTPUT, TABLES
from tools.export_database_sql import pg_dump_path


def main():
    load_env()
    url = make_url(os.environ['DATABASE_URL']).set(database='kltn_dev')
    engine = create_engine(url)
    name = 'core_check_' + uuid4().hex
    assert re.fullmatch(r'core_check_[a-f0-9]{32}', name)
    created = False
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{name}"'))
            created = True
        sql = OUTPUT.read_text(encoding='utf-8').replace('search_path = public', f'search_path = "{name}"').replace("n.nspname = 'public'", f"n.nspname = '{name}'")
        with engine.connect() as conn:
            conn.connection.driver_connection.execute(sql)
            conn.commit()
            inspector = inspect(conn)
            assert set(inspector.get_table_names(schema=name)) == set(TABLES)
            keys = 0
            for table in TABLES:
                model = Base.metadata.tables[table]
                assert {c['name'] for c in inspector.get_columns(table, schema=name)} == set(model.columns.keys())
                assert set(inspector.get_pk_constraint(table,schema=name)['constrained_columns']) == {c.name for c in model.primary_key.columns}
                live = {(tuple(f['constrained_columns']), f['referred_table'],tuple(f['referred_columns'])) for f in inspector.get_foreign_keys(table,schema=name)}
                expected = {(tuple(c.name for c in fk.columns),fk.referred_table.name,tuple(e.column.name for e in fk.elements)) for fk in model.foreign_key_constraints}
                assert live == expected
                keys += len(live)
        env=os.environ.copy()
        env.update(PGHOST=url.host or '127.0.0.1',PGPORT=str(url.port or 5432),PGDATABASE=url.database,PGUSER=url.username or '',PGPASSWORD=url.password or '')
        dump=subprocess.run([pg_dump_path(),'--schema-only','--no-owner','--no-privileges','--schema',name],env=env,capture_output=True,text=True)
        assert dump.returncode == 0, 'pg_dump failed; credentials not logged'
        assert len(re.findall(r'^CREATE TABLE ',dump.stdout,re.M)) == len(TABLES)
        assert not re.search(r'\bALTER TABLE\b',sql,re.I)
        print(f'PASS core SQL: {len(TABLES)} tables, {len(TABLES)} PK, {keys} FK; pg_dump schema-only PASS; 0 ALTER TABLE')
    finally:
        if created:
            with engine.begin() as conn:
                owner=conn.scalar(text('SELECT nspowner::regrole::text FROM pg_namespace WHERE nspname=:name'),{'name':name})
                assert owner == conn.scalar(text('SELECT current_user')), 'Unexpected schema owner'
                conn.execute(text(f'DROP SCHEMA "{name}" CASCADE'))
        engine.dispose()


if __name__=='__main__':
    main()
