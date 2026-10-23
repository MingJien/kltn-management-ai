"""Idempotently load the reviewed faculty/department/major catalog into kltn_management."""

from __future__ import annotations

import csv
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.api.dependencies import database_url
from backend.db.models import entities as m


CATALOG = Path(__file__).resolve().parents[1] / "database/official/department-major-catalog.csv"
FACULTY_CODE = "KHOA-CNKT"  # Internal code; the supplied workbook does not specify an official faculty code.
FACULTY_NAME = "Khoa Công nghệ và Kỹ thuật"
REQUIRED_HEAD = "20261022_0005"


def main() -> None:
    with CATALOG.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 10 or len({row["major_code"] for row in rows}) != 10:
        raise RuntimeError("Expected the reviewed 10-major catalog")
    departments = {}
    for row in rows:
        code, name = row["department_code"], row["department_name"]
        if code in departments and departments[code] != name:
            raise RuntimeError(f"Inconsistent department name for {code}")
        departments[code] = name
    if len(departments) != 4:
        raise RuntimeError("Expected four departments")

    engine = create_engine(database_url(), pool_pre_ping=True)
    try:
        with Session(engine) as session, session.begin():
            if session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() != REQUIRED_HEAD:
                raise RuntimeError("Upgrade the official database to 20261022_0005 first")
            faculty = session.scalar(select(m.Faculty).where(m.Faculty.code == FACULTY_CODE))
            if faculty is None:
                faculty = m.Faculty(id=uuid4(), code=FACULTY_CODE, name=FACULTY_NAME)
                session.add(faculty)
                session.flush()
            elif faculty.name != FACULTY_NAME:
                raise RuntimeError("Existing faculty code has a different name; resolve manually")
            for code, name in departments.items():
                matches = session.scalars(select(m.Department).where(m.Department.code == code)).all()
                if len(matches) > 1 or (matches and matches[0].faculty_id != faculty.id):
                    raise RuntimeError(f"Department code {code} is already used outside this faculty")
                department = matches[0] if matches else m.Department(
                    id=uuid4(), faculty_id=faculty.id, code=code, name=name)
                if not matches:
                    session.add(department)
                    session.flush()
                elif department.name != name:
                    raise RuntimeError(f"Department name differs for {code}; resolve manually")
                if not department.active:
                    raise RuntimeError(f"Department {code} was disabled; resolve manually")
                for row in (item for item in rows if item["department_code"] == code):
                    major = session.scalar(select(m.DepartmentMajor).where(
                        m.DepartmentMajor.department_id == department.id,
                        m.DepartmentMajor.code == row["major_code"]))
                    if major is None:
                        session.add(m.DepartmentMajor(id=uuid4(), department_id=department.id,
                            code=row["major_code"], name=row["major_name"], active=True))
                    elif major.name == row["major_name"] and major.active:
                        pass
                    else:
                        raise RuntimeError(f"Existing major {row['major_code']} differs; resolve manually")
        print("PASS kltn_management: 1 faculty, 4 departments, 10 active department-major mappings")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
