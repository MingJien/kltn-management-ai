"""Run real UI -> API -> PostgreSQL tests in an owned disposable schema.

Command: python -m tools.run_e2e
Requires frontend npm dependencies and `npx playwright install chromium`.
Never reuses or stops a user's running API/Vite server.
"""
from __future__ import annotations

import csv
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
API_PORT, WEB_PORT = 8001, 5174


def free_port(port: int):
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'Port {port} is in use; refusing to reuse or stop an existing server')


def main() -> int:
    from backend.db.validate_schema import load_env
    load_env()
    for port in (API_PORT, WEB_PORT):
        free_port(port)
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise RuntimeError('Node.js/npm is required')
    url = make_url(os.environ['DATABASE_URL']).set(database='kltn_dev')
    schema = 'e2e_' + uuid4().hex[:16]
    assert re.fullmatch(r'e2e_[0-9a-f]{16}', schema)
    directory = ROOT / 'tmp' / schema
    directory.mkdir(parents=True)
    engine = create_engine(url)
    created = False
    api = None
    try:
        with engine.begin() as connection:
            assert connection.scalar(text('select count(*) from pg_namespace where nspname=:s'), {'s':schema}) == 0
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            created = True
        options = dict(url.query)
        options['options'] = f'-csearch_path={schema}'
        private_url = url.set(query=options).render_as_string(hide_password=False)
        env = os.environ.copy()
        env.update(DATABASE_URL=private_url, KLTN_ENV='test', KLTN_DEV_AUTH='false',
            AUTH_SESSION_SECRET=secrets.token_urlsafe(48), PYTHONIOENCODING='utf-8',
            KLTN_FRONTEND_URL=f'http://127.0.0.1:{WEB_PORT}', VITE_API_URL=f'http://127.0.0.1:{API_PORT}',
            KLTN_EVIDENCE_DIR=str(directory / 'uploads'), KLTN_E2E_RUN_DIR=str(directory))
        migration = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'],
            cwd=ROOT, env=env, text=True, capture_output=True)
        if migration.returncode:
            print('FAIL isolated migration (connection details withheld)')
            return migration.returncode
        # Fixture generation only targets this random schema. In particular,
        # it never reads or rewrites database/tai-khoan-demo.local.csv.
        os.environ.update(env)
        from tools import seed_demo
        seed_demo.CREDENTIALS_PATH = directory / 'credentials.csv'
        saved_argv = sys.argv
        try:
            sys.argv = ['seed_demo', '--execute', '--create-credentials']
            seed_demo.main()
        finally:
            sys.argv = saved_argv
        with seed_demo.CREDENTIALS_PATH.open(encoding='utf-8-sig', newline='') as handle:
            accounts = {row['tai_khoan_demo']:{'email':row['email_dang_nhap'],'password':row['mat_khau_demo']}
                for row in csv.DictReader(handle, delimiter=';')}
        from backend.db.models import entities as m
        from backend.services.passwords import hash_password
        private_engine = create_engine(private_url)
        with Session(private_engine) as session, session.begin():
            assert session.scalar(text('select current_schema()')) == schema
            now = datetime.now(timezone.utc)
            for key in ('proposalPeer','race1','race2','race3'):
                password = secrets.token_urlsafe(20)
                email = key.lower() + '@e2e.test'
                user = m.UserAccount(id=uuid4(),email=email,password_hash=hash_password(password),
                    email_verified_at=now,base_role='STUDENT',status='ACTIVE')
                session.add(user); session.flush()
                student = m.StudentProfile(id=uuid4(),user_id=user.id,student_code='E2E-'+key,
                    department_id=seed_demo.uid('department'),display_name='SV kiểm thử '+key)
                session.add(student); session.flush()
                session.add(m.EligibilitySnapshot(id=uuid4(),student_id=student.id,
                    round_id=seed_demo.uid('round'),version=1,evidence_ref='SYNTHETIC',
                    captured_at=now,confirmed_by=seed_demo.uid('user-lecturer-2'),confirmed_at=now,state='CONFIRMED'))
                accounts[key] = {'email':email,'password':password}
        private_engine.dispose()
        env['KLTN_E2E_ACCOUNTS_JSON'] = json.dumps(accounts)
        with (directory / 'api.log').open('w', encoding='utf-8') as log:
            api = subprocess.Popen([sys.executable,'-m','uvicorn','backend.api.main:app',
                '--host','127.0.0.1','--port',str(API_PORT)],cwd=ROOT,env=env,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            deadline = time.monotonic() + 30
            while True:
                if api.poll() is not None:
                    raise RuntimeError('Isolated API exited; see the local temporary API log')
                try:
                    with urlopen(f'http://127.0.0.1:{API_PORT}/health/ready', timeout=1) as response:
                        if response.status == 200:
                            break
                except Exception:
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Isolated API did not become ready')
                    time.sleep(.2)
            print('PASS isolated fixture: kltn_dev, owned schema, cookie auth, synthetic accounts',flush=True)
            result = subprocess.run([npm,'run','test:e2e'],cwd=ROOT/'frontend',env=env)
            return result.returncode
    finally:
        if api and api.poll() is None:
            api.terminate()
            try: api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api.kill(); api.wait(timeout=10)
        if created:
            with engine.begin() as connection:
                owner = connection.scalar(text('select nspowner::regrole::text from pg_namespace where nspname=:s'),{'s':schema})
                assert owner == connection.scalar(text('select current_user'))
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            print('Removed only the schema created by this E2E run',flush=True)
        engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
