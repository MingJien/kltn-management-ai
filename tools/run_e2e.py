"""Run real UI -> API -> PostgreSQL tests in a dedicated test database.

Command: python -m tools.run_e2e [playwright spec filter...]
With no filters, use a fresh schema per spec file. Use --isolate-specs [filename patterns...] to select files in the same mode.
Requires frontend npm dependencies and `npx playwright install chromium`.
Never reuses or stops a user's running API/Vite server.

The run uses a new owned schema, never public. Running on kltn_management needs
KLTN_E2E_ALLOW_ISOLATED_SCHEMA=true; no existing schema is reused or cleaned up.
"""
from __future__ import annotations

import csv
import io
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
from fnmatch import fnmatch
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_PORT, DEFAULT_WEB_PORT = 8001, 5174


def free_port(port: int):
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'Port {port} is in use; refusing to reuse or stop an existing server')


def available_port(preferred: int) -> int:
    """Keep the familiar port when free; otherwise use an OS-assigned free port."""
    if preferred:
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(('127.0.0.1', preferred)) != 0:
                return preferred
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def main() -> int:
    from backend.db.validate_schema import load_env
    load_env()
    from backend.services.file_scanner import start_local_daemon
    print("Checking real ClamAV scanner...", flush=True)
    if not start_local_daemon():
        raise RuntimeError("E2E BLOCKED: real ClamAV daemon is not ready; uploads must not be falsely marked CLEAN")
    ephemeral = os.getenv('KLTN_E2E_EPHEMERAL_PORTS') == 'true'
    api_port = available_port(0 if ephemeral else DEFAULT_API_PORT)
    web_port = available_port(0 if ephemeral else DEFAULT_WEB_PORT)
    if api_port == web_port:
        web_port = available_port(0)
    for port in (api_port, web_port):
        free_port(port)
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise RuntimeError('Node.js/npm is required')
    url = make_url(os.environ['DATABASE_URL'])
    if not url.database or (url.database == 'kltn_management' and
            os.getenv('KLTN_E2E_ALLOW_ISOLATED_SCHEMA') != 'true'):
        raise RuntimeError('E2E BLOCKED: a dedicated test database is required, or explicitly '
            'allow a fresh isolated schema in kltn_management with '
            'KLTN_E2E_ALLOW_ISOLATED_SCHEMA=true. Existing schemas are never reused.')
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
            KLTN_ALLOW_SYNTHETIC_SEED='true', KLTN_PROPOSAL_DIR=str(directory / 'uploads' / 'proposals'),
            KLTN_DOCUMENT_DIR=str(directory / 'uploads' / 'documents'),
            KLTN_E2E_PYTHON=sys.executable,
            KLTN_FRONTEND_URL=f'http://127.0.0.1:{web_port}', VITE_API_URL=f'http://127.0.0.1:{api_port}',
            KLTN_E2E_API_PORT=str(api_port), KLTN_E2E_WEB_PORT=str(web_port),
            KLTN_EVIDENCE_DIR=str(directory / 'uploads' / 'registration'), KLTN_E2E_RUN_DIR=str(directory),
            # Never deliver synthetic test account links through the developer's real SMTP.
            KLTN_MAIL_FROM='', KLTN_SMTP_HOST='', KLTN_SMTP_USER='', KLTN_SMTP_PASSWORD='')
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
            if os.getenv('KLTN_E2E_SAMPLE_DEPARTMENT') == 'true':
                # Use the public roster example codes only inside this disposable schema.
                session.get(m.Faculty, seed_demo.uid('faculty')).name = 'Khoa Công nghệ và Kỹ thuật (giả lập)'
                department = session.get(m.Department, seed_demo.uid('department'))
                department.code, department.name = 'BM-CNTT', 'Công nghệ thông tin (giả lập)'
            admin_password = secrets.token_urlsafe(20)
            admin = m.UserAccount(id=uuid4(), email='admin@e2e.test',
                password_hash=hash_password(admin_password), email_verified_at=now,
                base_role='ADMIN', status='ACTIVE')
            session.add(admin)
            accounts['admin'] = {'email':admin.email, 'password':admin_password}
            for key in ('proposalPeer','race1','race2','race3','proposalFlow','returnFlow','auditSv1','auditSv2','auditSv3','nv5Student','nv5Outsider','annotationStudent','formStudent','formMember','nv6Student','nv6Member','nv6Outsider'):
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
        # A synthetic, parseable PDF for NV6 report and manual-signature workflow QA.
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        synthetic_pdf = directory / 'synthetic-nv6.pdf'
        writer.write(synthetic_pdf)
        env['KLTN_E2E_NV6_FILE'] = str(synthetic_pdf)
        specs = {Path(arg).name for arg in sys.argv[1:]}
        if "ai-report-live.spec.ts" in specs:
            from tools.e2e_ai_fixture import add_report_pair
            with Session(private_engine) as session, session.begin():
                assert session.scalar(text('select current_schema()')) == schema
                add_report_pair(session, datetime.now(timezone.utc))
            private_engine.dispose()
        if specs & {"defense-live.spec.ts", "defense-absence-live.spec.ts", "defense-batch-live.spec.ts"}:
            from tools.e2e_defense_fixture import add_ready_thesis
            with Session(private_engine) as session, session.begin():
                assert session.scalar(text('select current_schema()')) == schema
                instant = datetime.now(timezone.utc)
                thesis_id = add_ready_thesis(session, instant, synthetic_pdf.read_bytes(), accounts)
                env['KLTN_E2E_DEFENSE_THESIS'] = str(thesis_id)
                if "defense-absence-live.spec.ts" in specs:
                    from tools.e2e_absence_fixture import add_second_member
                    add_second_member(session, instant, thesis_id)
                if "defense-batch-live.spec.ts" in specs:
                    from tools.e2e_batch_fixture import add_second_thesis
                    env['KLTN_E2E_DEFENSE_SECOND_THESIS'] = str(add_second_thesis(
                        session, instant, synthetic_pdf.read_bytes()))
            env['KLTN_E2E_ACCOUNTS_JSON'] = json.dumps(accounts)
            private_engine.dispose()
        if specs & {"archive-live.spec.ts", "mobile-layout.spec.ts"}:
            from tools.e2e_archive_fixture import add_defended_thesis
            with Session(private_engine) as session, session.begin():
                assert session.scalar(text('select current_schema()')) == schema
                env["KLTN_E2E_ARCHIVE_THESIS"] = str(add_defended_thesis(
                    session, datetime.now(timezone.utc), synthetic_pdf.read_bytes()))
                if "mobile-layout.spec.ts" in specs:
                    env["KLTN_E2E_LECTURER_ID"] = str(seed_demo.uid("lecturer-1"))
                    for duty in ("REVIEW_RECORDS_MANAGER", "ELIGIBILITY_VERIFIER"):
                        session.add(m.ResourceAssignment(user_id=seed_demo.uid("user-lecturer-2"),
                            round_id=seed_demo.uid("round"), assignment_type=duty, effective_from=now, state="ACTIVE"))
            private_engine.dispose()
        # Read the actual faculty templates and fill a synthetic local copy for print QA.
        # The original templates are never written to, and copies stay Git-ignored.
        from backend.services.form_templates import template_available, official_template, official_template_by_id
        from docx import Document
        for kind in ('plan','proposal'):
            if template_available(kind):
                doc = Document(io.BytesIO(official_template(kind)))
                doc.add_paragraph('DU LIEU GIA KIEM THU NV5 - KHONG PHAI HO SO SINH VIEN THAT')
                output = directory / f'synthetic-{kind}.docx'
                doc.save(output)
                env[f'KLTN_E2E_{kind.upper()}_FILE'] = str(output)
        for form_code in ('1a','1b'):
            content, _, _ = official_template_by_id('mau-0'+form_code, 'STUDENT')
            doc = Document(io.BytesIO(content))
            doc.add_paragraph('DU LIEU GIA KIEM THU - KHONG PHAI DON CUA SINH VIEN THAT')
            output = directory / f'synthetic-form-{form_code}.docx'
            doc.save(output)
            env[f'KLTN_E2E_FORM_{form_code.upper()}_FILE'] = str(output)
        with (directory / 'api.log').open('w', encoding='utf-8') as log:
            api = subprocess.Popen([sys.executable,'-m','uvicorn','backend.api.main:app',
                '--host','127.0.0.1','--port',str(api_port)],cwd=ROOT,env=env,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            deadline = time.monotonic() + 30
            while True:
                if api.poll() is not None:
                    raise RuntimeError('Isolated API exited; see the local temporary API log')
                try:
                    with urlopen(f'http://127.0.0.1:{api_port}/health/ready', timeout=1) as response:
                        if response.status == 200:
                            break
                except Exception:
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Isolated API did not become ready')
                    time.sleep(.2)
            print(f'PASS isolated fixture: database {url.database}, owned schema, cookie auth, synthetic accounts',flush=True)
            command = [npm,'run','test:e2e']
            if len(sys.argv) > 1:
                command += ['--', *sys.argv[1:]]
            result = subprocess.run(command,cwd=ROOT/'frontend',env=env)
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


def run_isolated_specs(patterns: list[str]) -> int:
    specs = sorted((ROOT / 'frontend' / 'e2e').rglob('*.spec.ts'))
    selected = [spec for spec in specs if not patterns or any(fnmatch(spec.name, pattern) for pattern in patterns)]
    if not selected:
        print('No E2E specs match the supplied filename patterns.', file=sys.stderr)
        return 2
    failed = []
    env = dict(os.environ, KLTN_E2E_EPHEMERAL_PORTS='true')
    for index, spec in enumerate(selected, 1):
        print(f'[{index}/{len(selected)}] {spec.name} with a fresh test schema', flush=True)
        result = subprocess.run([sys.executable, '-m', 'tools.run_e2e', spec.name], cwd=ROOT, env=env)
        if result.returncode:
            failed.append(spec.name)
    print(f'Passed spec files: {len(selected) - len(failed)}/{len(selected)}', flush=True)
    if failed:
        print('Failed spec files: ' + ', '.join(failed), file=sys.stderr, flush=True)
    return int(bool(failed))


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] == '--isolate-specs':
        raise SystemExit(run_isolated_specs(args[1:]))
    raise SystemExit(main())
