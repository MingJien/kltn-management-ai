"""Admin directory projection for account roles currently assigned in KLTN."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.db.models import entities as m


RESOURCE_ROLE_LABELS = {
    "FORM_MANAGER": "Quản lý biểu mẫu và tài liệu Khoa",
    "REVIEW_RECORDS_MANAGER": "Tiếp nhận hồ sơ phản biện",
    "ELIGIBILITY_IMPORTER": "Nhập danh sách đủ điều kiện",
    "ELIGIBILITY_VERIFIER": "Điều chỉnh/thu hồi danh sách",
    "ACCOUNT_MANAGER": "Quản lý tài khoản sinh viên",
    "KLTN_COORDINATOR": "Điều phối KLTN theo đợt",
    "PROGRESS_REVIEWER": "Góp ý chéo tiến độ",
}


def _search_key(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.replace("đ", "d").replace("Đ", "D").casefold()


def _active_window(model, now: datetime):
    return (
        model.state == "ACTIVE",
        model.effective_from <= now,
        or_(model.effective_to.is_(None), model.effective_to > now),
    )


def _add_role(
    roles: dict[UUID, list[dict[str, str | None]]],
    user_id: UUID,
    code: str,
    label: str,
    scope: str | None,
) -> None:
    entry = {"code": code, "label": label, "scope": scope}
    if entry not in roles[user_id]:
        roles[user_id].append(entry)


def _roles_for_accounts(
    session: Session, user_ids: list[UUID], now: datetime,
) -> dict[UUID, list[dict[str, str | None]]]:
    roles: dict[UUID, list[dict[str, str | None]]] = defaultdict(list)
    if not user_ids:
        return roles

    for start in range(0, len(user_ids), 500):
        chunk = user_ids[start : start + 500]

        positions = session.execute(
            select(
                m.LecturerProfile.user_id,
                m.OrganizationalPosition.code,
                m.Department.code.label("department_code"),
                m.Department.name.label("department_name"),
                m.Faculty.code.label("faculty_code"),
                m.Faculty.name.label("faculty_name"),
            )
            .select_from(m.PositionAssignment)
            .join(m.LecturerProfile, m.LecturerProfile.id == m.PositionAssignment.lecturer_id)
            .join(m.OrganizationalPosition, m.OrganizationalPosition.id == m.PositionAssignment.position_id)
            .outerjoin(m.Department, m.Department.id == m.PositionAssignment.department_id)
            .outerjoin(m.Faculty, m.Faculty.id == m.PositionAssignment.faculty_id)
            .where(
                m.LecturerProfile.user_id.in_(chunk),
                *_active_window(m.PositionAssignment, now),
            )
        ).all()
        for row in positions:
            label = {
                "DEPARTMENT_HEAD": "Trưởng bộ môn",
                "FACULTY_DEAN": "Lãnh đạo Khoa",
            }.get(row.code, row.code.replace("_", " ").title())
            scope = (
                f"{row.department_code} · {row.department_name}"
                if row.department_code else
                f"{row.faculty_code} · {row.faculty_name}"
                if row.faculty_code else None
            )
            _add_role(roles, row.user_id, row.code, label, scope)

        resources = session.execute(
            select(
                m.ResourceAssignment.user_id,
                m.ResourceAssignment.assignment_type,
                m.ThesisRound.code.label("round_code"),
                m.Thesis.current_title.label("thesis_title"),
            )
            .select_from(m.ResourceAssignment)
            .outerjoin(m.ThesisRound, m.ThesisRound.id == m.ResourceAssignment.round_id)
            .outerjoin(m.Thesis, m.Thesis.id == m.ResourceAssignment.thesis_id)
            .where(
                m.ResourceAssignment.user_id.in_(chunk),
                *_active_window(m.ResourceAssignment, now),
            )
        ).all()
        for row in resources:
            label = RESOURCE_ROLE_LABELS.get(
                row.assignment_type, row.assignment_type.replace("_", " ").title()
            )
            scope = row.round_code or row.thesis_title
            _add_role(roles, row.user_id, row.assignment_type, label, scope)

        advisors = session.execute(
            select(
                m.LecturerProfile.user_id,
                m.ThesisRound.code.label("round_code"),
                m.Thesis.current_title.label("thesis_title"),
            )
            .select_from(m.AdvisorAssignment)
            .join(m.LecturerProfile, m.LecturerProfile.id == m.AdvisorAssignment.lecturer_id)
            .join(m.Thesis, m.Thesis.id == m.AdvisorAssignment.thesis_id)
            .join(m.ThesisRound, m.ThesisRound.id == m.Thesis.round_id)
            .where(
                m.LecturerProfile.user_id.in_(chunk),
                *_active_window(m.AdvisorAssignment, now),
            )
        ).all()
        for row in advisors:
            scope = " · ".join(part for part in (row.round_code, row.thesis_title) if part)
            _add_role(roles, row.user_id, "PRIMARY_ADVISOR", "Giảng viên hướng dẫn", scope or None)

        reviewers = session.execute(
            select(m.LecturerProfile.user_id, m.ReviewerAssignment.review_scope)
            .select_from(m.ReviewerAssignment)
            .join(m.LecturerProfile, m.LecturerProfile.id == m.ReviewerAssignment.lecturer_id)
            .where(
                m.LecturerProfile.user_id.in_(chunk),
                m.ReviewerAssignment.state == "ACTIVE",
            )
        ).all()
        for row in reviewers:
            is_proposal = row.review_scope == "PROPOSAL"
            code = "PROPOSAL_REVIEWER" if is_proposal else "THESIS_REVIEWER"
            label = "Phản biện đề cương" if is_proposal else "Phản biện khóa luận"
            scope = "Đề cương" if is_proposal else "Khóa luận"
            _add_role(roles, row.user_id, code, label, scope)

    return {
        user_id: sorted(entries, key=lambda item: (item["label"] or "", item["scope"] or ""))
        for user_id, entries in roles.items()
    }


def lecturer_duties_for_user(session: Session, user_id: UUID) -> list[dict[str, str | None]]:
    """Return the active roles and scoped assignments for a lecturer account."""
    return _roles_for_accounts(session, [user_id], datetime.now(timezone.utc)).get(user_id, [])


def build_account_directory(
    session: Session,
    *,
    search: str,
    category: str,
    additional_role: str,
    offset: int,
    limit: int,
    account_status: str = "ALL",
) -> dict:
    """Return one row per account, with tabs/counts and current additional duties."""
    rows = session.execute(
        select(
            m.UserAccount.id.label("id"),
            m.UserAccount.email.label("email"),
            m.UserAccount.base_role.label("base_role"),
            m.UserAccount.status.label("status"),
            m.UserAccount.email_verified_at.label("email_verified_at"),
            m.StudentProfile.student_code.label("student_code"),
            m.StudentProfile.display_name.label("student_name"),
            m.LecturerProfile.display_name.label("lecturer_name"),
            m.LecturerProfile.lecturer_code.label("lecturer_code"),
        )
        .select_from(m.UserAccount)
        .outerjoin(m.StudentProfile, m.StudentProfile.user_id == m.UserAccount.id)
        .outerjoin(m.LecturerProfile, m.LecturerProfile.user_id == m.UserAccount.id)
        .order_by(m.UserAccount.base_role, m.UserAccount.email, m.UserAccount.id)
    ).all()

    now = datetime.now(timezone.utc)
    roles_by_user = _roles_for_accounts(session, [row.id for row in rows], now)
    counts = {
        "ALL": len(rows),
        "STUDENT": sum(row.base_role == "STUDENT" for row in rows),
        "LECTURER": sum(row.base_role == "LECTURER" for row in rows),
        "ADMIN": sum(row.base_role == "ADMIN" for row in rows),
        "LECTURER_WITH_DUTIES": sum(
            row.base_role == "LECTURER" and bool(roles_by_user.get(row.id))
            for row in rows
        ),
    }

    role_users: dict[str, set[UUID]] = defaultdict(set)
    role_labels: dict[str, str] = {}
    for row in rows:
        if row.base_role != "LECTURER":
            continue
        for role in roles_by_user.get(row.id, []):
            role_users[role["code"]].add(row.id)
            role_labels[role["code"]] = role["label"] or role["code"]
    role_catalog = [
        {"code": code, "label": role_labels[code], "count": len(user_ids)}
        for code, user_ids in sorted(
            role_users.items(), key=lambda item: (role_labels[item[0]].casefold(), item[0])
        )
    ]

    query = _search_key(search.strip())
    filtered = []
    for row in rows:
        user_roles = roles_by_user.get(row.id, [])
        state = "PENDING" if row.status == "DISABLED" and row.email_verified_at is None else row.status
        if account_status != "ALL" and state != account_status:
            continue
        if category == "STUDENT" and row.base_role != "STUDENT":
            continue
        if category == "LECTURER" and row.base_role != "LECTURER":
            continue
        if category == "ADMIN" and row.base_role != "ADMIN":
            continue
        if category == "LECTURER_WITH_DUTIES" and not (
            row.base_role == "LECTURER" and user_roles
        ):
            continue
        if additional_role and not any(role["code"] == additional_role for role in user_roles):
            continue
        if query:
            haystack = _search_key(" ".join(filter(None, (
                row.email, row.student_code, row.student_name,
                row.lecturer_code, row.lecturer_name,
            ))))
            if query not in haystack:
                continue
        filtered.append(row)

    items = []
    for row in filtered[offset : offset + limit]:
        display_name = row.student_name or row.lecturer_name or row.email
        items.append({
            "id": str(row.id),
            "email": row.email,
            "base_role": row.base_role,
            "status": row.status,
            "verified": row.email_verified_at is not None,
            "student_code": row.student_code,
            "lecturer_code": row.lecturer_code,
            "display_name": display_name,
            "additional_roles": roles_by_user.get(row.id, []) if row.base_role in {"LECTURER", "ADMIN"} else [],
        })
    return {
        "items": items,
        "total": len(filtered),
        "counts": counts,
        "role_catalog": role_catalog,
    }
