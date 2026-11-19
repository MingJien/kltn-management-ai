"""Private repository for approved post-defense manuscripts."""
from pathlib import Path
from types import SimpleNamespace
from typing import NamedTuple
from unicodedata import combining, normalize
from uuid import UUID, uuid4

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from sqlalchemy import Text, case, cast, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH, aggregate_order_by

from backend.db.models import entities as m
from backend.services import defense, defense_register, documents, evaluation, workflow_notices
from backend.services.registration import _is_department_head, row_version
from backend.services.theses import audit, effective, now, participation_revoked, primary_advisor
from backend.api.defense_schemas import normalize_academic_text

VISIBLE_STATES = ("DEFENDED", "COMPLETED")
RESUBMISSION_STATES = {"RETURNED", "REOPENED"}
VIETNAMESE_LETTERS = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
PLAIN_LETTERS = "".join(ch for ch in normalize("NFD", VIETNAMESE_LETTERS) if not combining(ch)).replace("đ", "d")

class ArchiveAccess(NamedTuple):
    member: bool
    advisor: bool
    manager: bool
    approver: bool
    suspended: bool
    student_id: UUID | None = None

    @property
    def can_view(self):
        return self.member or self.advisor or self.manager


def visible(session, thesis):
    return thesis.state in VISIBLE_STATES or (thesis.state == "ARCHIVED" and
        session.scalar(select(m.ThesisArchiveVersion.id).where(m.ThesisArchiveVersion.thesis_id == thesis.id).limit(1)) is not None)


def visible_condition():
    has_history = select(m.ThesisArchiveVersion.id).where(m.ThesisArchiveVersion.thesis_id == m.Thesis.id).correlate(m.Thesis).exists()
    return or_(m.Thesis.state.in_(VISIBLE_STATES), (m.Thesis.state == "ARCHIVED") & has_history)


def access(session, user, thesis):
    student = defense.student_for(session, user)
    if student:
        member = session.scalar(select(m.ThesisMember.id).where(m.ThesisMember.thesis_id == thesis.id,
            m.ThesisMember.student_id == student.id, m.ThesisMember.active.is_(True))) is not None
        return ArchiveAccess(member=member, advisor=False, manager=False, approver=False,
                             suspended=member and participation_revoked(session, student.id, thesis.round_id),
                             student_id=student.id)
    lecturer = defense.lecturer_for(session, user)
    if not lecturer:
        return ArchiveAccess(False, False, False, False, False)
    advisor = primary_advisor(session, thesis.id)
    valid_scope = defense.valid_council_scope(session.get(m.ThesisRound, thesis.round_id),
                                              session.get(m.Department, thesis.department_id))
    manager = valid_scope and defense.manages(session, user, lecturer, thesis.round_id, thesis.department_id)
    return ArchiveAccess(member=False, advisor=bool(advisor and advisor.lecturer_id == lecturer.id),
                         manager=manager, approver=manager and _is_department_head(session, lecturer.id, thesis.department_id),
                         suspended=False)


def versions(session, thesis_id):
    return session.scalars(select(m.ThesisArchiveVersion).where(m.ThesisArchiveVersion.thesis_id == thesis_id)
        .order_by(m.ThesisArchiveVersion.version_no.desc())).all()


def pending_correction(session, student_results):
    ids = [row["slot_id"] for row in student_results if row]
    if not ids:
        return None
    return session.scalar(select(m.DefenseCorrection.slot_id).where(
        m.DefenseCorrection.slot_id.in_(ids), m.DefenseCorrection.state == "PENDING").limit(1))


def ready_results(session, thesis, rows):
    members = evaluation.members(session, thesis)
    by_student = {row["student_id"]: row for row in rows if row["thesis_id"] == str(thesis.id)}
    results = [by_student.get(str(member.student_id)) for member in members]
    if not results or not all(row and row["status"] != "PENDING" and row["council_closed"] for row in results):
        return None
    if not any(row["status"] == "GRADED" for row in results):
        return None
    if pending_correction(session, results):
        return None
    return results


def normalized_identity(source):
    """Render legacy and new labels alike, retaining the values attached to this version."""
    identity = dict(source)
    for field in ("title", "advisor", "topic_code", "round", "academic_year", "department", "department_code"):
        if isinstance(identity.get(field), str):
            identity[field] = normalize_academic_text(identity[field])
    student_fields = {"name", "code", "class_name", "major_code", "major", "training_cohort"}
    identity["students"] = [
        {key: normalize_academic_text(value) if key in student_fields and isinstance(value, str) else value
         for key, value in student.items()} for student in source.get("students") or []
    ]
    return identity


def submission_snapshot(session, thesis, results):
    advisor = primary_advisor(session, thesis.id)
    lecturer = session.get(m.LecturerProfile, advisor.lecturer_id) if advisor else None
    department = session.get(m.Department, thesis.department_id)
    round_ = session.get(m.ThesisRound, thesis.round_id)
    return normalized_identity({"title": thesis.current_title, "topic_code": session.get(m.Topic, thesis.topic_id).code,
            "advisor": lecturer.display_name if lecturer else "", "round": round_.code,
            "academic_year": session.get(m.AcademicYear, round_.academic_year_id).code,
            "department": department.name, "department_code": department.code,
            "students": [{key: row[key] for key in ("name", "code", "student_id", "slot_id",
                          "class_name", "major_code", "major", "training_cohort")} for row in results]})


def matches_defense(snapshot, results):
    saved = {(normalize_academic_text(row.get("code") or ""), row.get("slot_id")) for row in snapshot.get("students") or []}
    return saved == {(normalize_academic_text(row["code"]), row["slot_id"]) for row in results}


def notify_ready(session, user, thesis):
    if thesis.state != "DEFENDED" or session.scalar(select(m.ThesisArchiveVersion.id)
            .where(m.ThesisArchiveVersion.thesis_id == thesis.id).limit(1)):
        return
    sessions = defense_register.council_sessions(session, thesis.round_id, thesis_id=thesis.id)
    if ready_results(session, thesis, defense_register.rows_for_sessions(session, sessions)):
        notice(session, user, thesis, "THESIS_ARCHIVE_READY", "Đã khóa kết quả bảo vệ. Nhóm có thể nộp bản hoàn thiện")


def version_out(session, row):
    file = session.get(m.StoredFile, row.file_id)
    reopened = session.scalar(select(m.AuditEvent).where(
        m.AuditEvent.resource_type == "thesis_archive_version", m.AuditEvent.resource_id == row.id,
        m.AuditEvent.action == "THESIS_ARCHIVE_REOPENED")) if row.state == "REOPENED" else None
    return {"id": row.id, "number": row.version_no, "revision": row.row_version, "state": row.state,
            "filename": file.original_name, "created_at": row.created_at, "decided_at": row.decided_at,
            "submitted_by": workflow_notices.actor_name(session, row.submitted_by),
            "decided_by": workflow_notices.actor_name(session, row.decided_by) if row.decided_by else None,
            "decision_note": row.decision_note,
            "reopened": {"by": workflow_notices.actor_name(session, reopened.actor_id),
                         "at": reopened.occurred_at, "reason": reopened.reason} if reopened else None}


def entry(session, thesis, permissions, rows):
    results = ready_results(session, thesis, rows)
    history = versions(session, thesis.id)
    latest = history[0] if history else None
    blockers = []
    by_student = {row["student_id"]: row for row in rows if row["thesis_id"] == str(thesis.id)}
    own_slots = {row["slot_id"] for row in rows if row["student_id"] == str(permissions.student_id)}
    def result_link(slot_id):
        if permissions.manager or slot_id in own_slots:
            return f"/defense?slot={slot_id}&tab=results"
        return None

    students = []
    for active in evaluation.members(session, thesis):
        student = session.get(m.StudentProfile, active.student_id)
        students.append({"name": student.display_name, "code": student.student_code})
        row = by_student.get(str(student.id))
        if not row or row["status"] == "PENDING" or not row["council_closed"]:
            message = ("Chưa xếp lịch" if not row else row["outcome_label"] if row["status"] == "PENDING"
                       else "Hội đồng chưa khóa bảng điểm")
            blockers.append({"message": f"{student.display_name} ({student.student_code}): {message}",
                             "url": result_link(row["slot_id"]) if row else f"/evaluation/{thesis.id}"})
    if results is None and not blockers:
        slot_id = pending_correction(session, by_student.values())
        blockers.append({"message": "Còn đề nghị đính chính kết quả đang chờ xử lý", "url": result_link(str(slot_id))}
                        if slot_id else {"message": "Chưa có sinh viên được chốt điểm để nộp lưu bản báo cáo", "url": "/defense"})
    source_changed = bool(results and latest and latest.state == "SUBMITTED" and not matches_defense(latest.snapshot, results))
    if source_changed:
        blockers.append({"message": "Phiên bảo vệ hoặc MSSV đã thay đổi. Bộ môn cần yêu cầu nhóm nộp lại bản hoàn thiện.",
                         "url": "/defense"})
    if latest:
        identity = normalized_identity(latest.snapshot)
    elif results:
        identity = submission_snapshot(session, thesis, results)
    else:
        assignment = primary_advisor(session, thesis.id)
        advisor = session.get(m.LecturerProfile, assignment.lecturer_id) if assignment else None
        identity = normalized_identity({"title": thesis.current_title, "advisor": advisor.display_name if advisor else "", "students": students})
    if not permissions.manager and not permissions.member:
        for blocker in blockers:
            blocker["url"] = None
    writable = thesis.state in VISIBLE_STATES
    return {"id": thesis.id, "title": thesis.current_title, "round_id": thesis.round_id,
            "topic_code": identity.get("topic_code") or session.get(m.Topic, thesis.topic_id).code,
            "round": identity.get("round") or session.get(m.ThesisRound, thesis.round_id).code,
            "department": identity.get("department") or session.get(m.Department, thesis.department_id).name,
            "snapshot": identity, "blockers": blockers, "submission_suspended": permissions.suspended,
            "can_submit": bool(writable and permissions.member and not permissions.suspended and results and (not latest or latest.state in RESUBMISSION_STATES)),
            "can_decide": bool(writable and permissions.approver and latest and latest.state == "SUBMITTED"),
            "can_approve": bool(writable and results and not source_changed),
            "can_reopen": bool(writable and permissions.approver and latest and latest.state == "ACCEPTED"),
            "waiting": results is None and latest is None,
            "versions": [version_out(session, row) for row in history]}


def details(session, user, thesis_id):
    thesis = session.get(m.Thesis, thesis_id)
    if not thesis or not visible(session, thesis):
        raise HTTPException(404, "Không tìm thấy hồ sơ nộp lưu trong phạm vi được xem")
    permissions = access(session, user, thesis)
    if not permissions.can_view:
        raise HTTPException(404, "Không tìm thấy hồ sơ nộp lưu trong phạm vi được xem")
    sessions = defense_register.council_sessions(session, thesis.round_id, thesis_id=thesis.id)
    return entry(session, thesis, permissions, defense_register.rows_for_sessions(session, sessions))


def listing_scope(session, user):
    student = defense.student_for(session, user)
    if student:
        return select(m.ThesisMember.id).where(m.ThesisMember.thesis_id == m.Thesis.id,
            m.ThesisMember.active.is_(True), m.ThesisMember.student_id == student.id).exists(), []
    lecturer = defense.lecturer_for(session, user)
    if not lecturer:
        return False, []
    from backend.services.nv6_reporting import scopes
    scopes_for_manager = scopes(session, user)
    managed = [(scope["round_id"], scope["department_id"]) for scope in scopes_for_manager]
    advising = select(m.AdvisorAssignment.id).where(m.AdvisorAssignment.thesis_id == m.Thesis.id,
        m.AdvisorAssignment.lecturer_id == lecturer.id, effective(m.AdvisorAssignment)).exists()
    return or_(advising, tuple_(m.Thesis.round_id, m.Thesis.department_id).in_(managed)), scopes_for_manager


def catalog_query(session, user, *, mode, state, search, round_id, department_id, page, limit):
    """Filter and paginate authorized rows before loading any document history."""
    archive = m.ThesisArchiveVersion
    latest = (select(archive.id, archive.thesis_id, archive.version_no, archive.state, archive.snapshot,
                     archive.created_at, archive.decided_at)
              .distinct(archive.thesis_id).order_by(archive.thesis_id, archive.version_no.desc()).subquery())
    authorized, managed = listing_scope(session, user)
    visible = (visible_condition(), authorized)
    options = session.execute(select(m.ThesisRound.id, m.ThesisRound.code, m.Department.id, m.Department.name)
        .select_from(m.Thesis).join(m.ThesisRound, m.ThesisRound.id == m.Thesis.round_id)
        .join(m.Department, m.Department.id == m.Thesis.department_id).where(*visible)
        .distinct().order_by(m.ThesisRound.code.desc(), m.Department.name)).all()
    live_students = (select(func.jsonb_agg(aggregate_order_by(
        func.jsonb_build_object("name", m.StudentProfile.display_name, "code", m.StudentProfile.student_code),
        m.ThesisMember.is_coordinator.desc(), m.StudentProfile.student_code)))
        .select_from(m.ThesisMember).join(m.StudentProfile, m.StudentProfile.id == m.ThesisMember.student_id)
        .where(m.ThesisMember.thesis_id == m.Thesis.id, m.ThesisMember.active.is_(True)).correlate(m.Thesis).scalar_subquery())
    live_advisor = (select(m.LecturerProfile.display_name).select_from(m.AdvisorAssignment)
        .join(m.LecturerProfile, m.LecturerProfile.id == m.AdvisorAssignment.lecturer_id)
        .where(m.AdvisorAssignment.thesis_id == m.Thesis.id, effective(m.AdvisorAssignment))
        .correlate(m.Thesis).limit(1).scalar_subquery())
    # Search the same identity that the reader sees. Historical names stay with the deposited file.
    title = func.coalesce(latest.c.snapshot["title"].astext, m.Thesis.current_title)
    advisor = case((latest.c.id.is_(None), live_advisor), else_=latest.c.snapshot["advisor"].astext)
    students = case((latest.c.id.is_(None), live_students), else_=latest.c.snapshot["students"])
    query = (select(m.Thesis.id, title.label("current_title"),
        func.coalesce(latest.c.snapshot["topic_code"].astext, m.Topic.code).label("topic_code"),
        func.coalesce(latest.c.snapshot["round"].astext, m.ThesisRound.code).label("round"),
        func.coalesce(latest.c.snapshot["department"].astext, m.Department.name).label("department"),
        advisor.label("advisor"), func.coalesce(students, func.jsonb_build_array()).label("students"), latest.c.snapshot,
        latest.c.state, latest.c.version_no, latest.c.created_at,
        case((latest.c.state.in_(["ACCEPTED","REOPENED"]), latest.c.decided_at)).label("approved_at"))
        .select_from(m.Thesis).join(m.Topic, m.Topic.id == m.Thesis.topic_id)
        .join(m.ThesisRound, m.ThesisRound.id == m.Thesis.round_id)
        .join(m.Department, m.Department.id == m.Thesis.department_id)
        .outerjoin(latest, latest.c.thesis_id == m.Thesis.id).where(*visible))
    if mode == "catalog":
        query = query.where(latest.c.state == "ACCEPTED")
    elif state == "EMPTY":
        query = query.where(latest.c.id.is_(None))
    elif state:
        query = query.where(latest.c.state == state)
    if round_id:
        query = query.where(m.Thesis.round_id == round_id)
    if department_id:
        query = query.where(m.Thesis.department_id == department_id)
    entries = query.subquery()
    col = entries.c
    query = select(entries)
    order = []
    needle = " ".join("".join(ch for ch in normalize("NFD", search.lower()).replace("đ", "d")
                              if not combining(ch)).split())
    if needle:
        def folded(value):
            return func.translate(func.lower(func.normalize(value)), VIETNAMESE_LETTERS, PLAIN_LETTERS)

        codes = func.jsonb_path_query_array(col.students, cast("$[*].code", JSONPATH))
        names = func.jsonb_path_query_array(col.students, cast("$[*].name", JSONPATH))
        haystack = folded(func.concat_ws(" ", col.topic_code, col.current_title, col.advisor, cast(names, Text), cast(codes, Text)))
        for term in dict.fromkeys(needle.split()):
            query = query.where(haystack.contains(term, autoescape=True))
        exact_code = or_(folded(col.topic_code) == needle, func.jsonb_exists(cast(folded(cast(codes, Text)), JSONB), needle))
        exact_title = func.regexp_replace(func.trim(folded(col.current_title)), "[[:space:]]+", " ", "g") == needle
        order.append(case((exact_code, 0), (exact_title, 1), else_=2))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    page = min(page, max(1, (total + limit - 1) // limit))
    if mode == "catalog":
        order.append(col.approved_at.desc().nulls_last())
    else:
        order.append(case((col.state == "SUBMITTED", col.created_at)).asc().nulls_last())
    rows = session.execute(query.order_by(*order, col.current_title, col.id)
                           .offset((page - 1) * limit).limit(limit)).mappings()
    items = []
    for row in rows:
        item = dict(row)
        item.pop("created_at")
        students = item.pop("students")
        if item["snapshot"] is None:
            item["snapshot"] = {"title": item["current_title"], "advisor": item["advisor"], "students": students}
        item["snapshot"] = normalized_identity(item["snapshot"])
        for field in ("topic_code", "round", "department"):
            item[field] = normalize_academic_text(item[field])
        item["current_title"], item["advisor"] = item["snapshot"]["title"], item["snapshot"].get("advisor")
        items.append(item)
    # Keep an authorized round selectable even before its first defense.
    filters = {(s["round_id"], s["department_id"]): {"round_id": s["round_id"], "round": s["round_code"],
               "department_id": s["department_id"], "department": s["department"]} for s in managed}
    for rid, code, did, name in options:
        filters[rid, did] = {"round_id": rid, "round": code, "department_id": did, "department": name}
    return {"items": items, "total": total, "page": page, "limit": limit, "scopes": list(filters.values())}


def workspace(session, user, *, round_id=None):
    authorized, _ = listing_scope(session, user)
    query = select(m.Thesis).where(visible_condition(), authorized).order_by(m.Thesis.current_title)
    if round_id:
        query = query.where(m.Thesis.round_id == round_id)
    result_rows = {}
    items = []
    for thesis in session.scalars(query):
        permissions = access(session, user, thesis)
        if not permissions.can_view:
            continue
        if thesis.round_id not in result_rows:
            result_rows[thesis.round_id] = defense_register.rows_for_sessions(session, defense_register.council_sessions(session, thesis.round_id))
        items.append(entry(session, thesis, permissions, result_rows[thesis.round_id]))
    return items


def readers(session, thesis):
    ids = {session.get(m.StudentProfile, row.student_id).user_id for row in evaluation.members(session,thesis)}
    advisor = primary_advisor(session,thesis.id)
    if advisor:
        ids.add(session.get(m.LecturerProfile,advisor.lecturer_id).user_id)
    return ids | workflow_notices.department_heads(session,thesis.department_id)


def notice(session, user, thesis, event, label):
    workflow_notices.emit(session,user.id,readers(session,thesis),event,"thesis_archive",thesis.id,
        f"{label} · {thesis.current_title}",f"/repository?focus={thesis.id}")


def check_submission(session, user, identifier, expected, *, lock=False):
    query = select(m.Thesis).where(m.Thesis.id == identifier)
    if lock:
        # Use the same transaction order as defense corrections. Scanning happens before taking these locks.
        session.execute(select(func.pg_advisory_xact_lock(66102)))
        session.scalar(select(m.StudentProfile.id).where(m.StudentProfile.user_id == user.id).with_for_update())
        query = query.with_for_update().execution_options(populate_existing=True)
    thesis = session.scalar(query)
    permissions = access(session, user, thesis) if thesis else None
    if not permissions or not permissions.member:
        raise HTTPException(404,"Không tìm thấy hồ sơ lưu trữ của bạn")
    if permissions.suspended:
        raise HTTPException(403, "Quyền tham gia đợt của bạn đã bị thu hồi. Bạn vẫn được xem hồ sơ nộp lưu.")
    if thesis.state not in VISIBLE_STATES:
        raise HTTPException(409,"Chỉ nộp lưu sau khi hồ sơ đã bảo vệ và đủ kết quả")
    latest = session.scalar(select(m.ThesisArchiveVersion).where(m.ThesisArchiveVersion.thesis_id == thesis.id)
        .order_by(m.ThesisArchiveVersion.version_no.desc()).limit(1).execution_options(populate_existing=True))
    number = latest.version_no if latest else 0
    if expected is not None and number != expected:
        raise HTTPException(409, "Nhóm đã có bản nộp mới hơn. Hãy đối chiếu phiên bản trước khi gửi.")
    if latest and latest.state not in RESUBMISSION_STATES:
        raise HTTPException(409,"Hồ sơ đã nộp. Kiểm tra kết quả xử lý trước khi gửi bản mới")
    sessions = defense_register.council_sessions(session, thesis.round_id, thesis_id=thesis.id)
    rows = ready_results(session, thesis, defense_register.rows_for_sessions(session, sessions))
    if not rows:
        raise HTTPException(409,"Chờ chốt kết quả từng thành viên và khóa bảng điểm hội đồng trước khi nộp lưu")
    return thesis, number, rows


async def submit(session, user, identifier, request, expected=None):
    _, number, _ = await run_in_threadpool(check_submission, session, user, identifier, expected)
    name, content, mime = await documents.read_upload(request)
    if Path(name).suffix.lower() not in {".pdf", ".docx"}:
        raise HTTPException(422,"Nộp cuốn báo cáo hoàn thiện dạng PDF hoặc DOCX")
    return await run_in_threadpool(save_submission, session, user, identifier, number, name, content, mime)


def save_submission(session, user, identifier, number, name, content, mime):
    documents.file_scanner.require_available()
    file, digest, path = documents.persist_upload(session,name,content,mime)
    try:
        documents.file_scanner.scan(file,path)
        documents.require_clean(file, "nộp lưu khóa luận")
        thesis, _, rows = check_submission(session, user, identifier, number, lock=True)
        item = m.ThesisArchiveVersion(id=uuid4(), thesis_id=thesis.id, file_id=file.id, submitted_by=user.id,
            version_no=number+1, state="SUBMITTED", snapshot=submission_snapshot(session, thesis, rows))
        session.add(item)
        audit(session,user,"THESIS_ARCHIVE_SUBMITTED","thesis",thesis.id,after_hash=digest)
        notice(session,user,thesis,"THESIS_ARCHIVE_SUBMITTED","Đã nộp bản khóa luận chờ duyệt lưu")
        session.commit()
    except Exception:
        session.rollback()
        path.unlink(missing_ok=True)
        raise
    return version_out(session,item)


def decide(session, user, identifier, expected, decision, reason):
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    item = session.get(m.ThesisArchiveVersion, identifier)
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == item.thesis_id).with_for_update()) if item else None
    if not thesis or not access(session,user,thesis).approver:
        raise HTTPException(404,"Không tìm thấy hồ sơ lưu trữ trong bộ môn của bạn")
    if thesis.state not in VISIBLE_STATES:
        raise HTTPException(409, "Hồ sơ khóa luận đã đóng thao tác nộp lưu")
    item = session.scalar(select(m.ThesisArchiveVersion).where(m.ThesisArchiveVersion.id == identifier)
        .with_for_update().execution_options(populate_existing=True))
    row_version(expected,item.row_version)
    if item.state != "SUBMITTED":
        raise HTTPException(409,"Hồ sơ đã được xử lý. Làm mới danh sách để xem kết quả")
    if decision == "ACCEPTED":
        sessions = defense_register.council_sessions(session, thesis.round_id, thesis_id=thesis.id)
        rows = ready_results(session, thesis, defense_register.rows_for_sessions(session, sessions))
        if not rows:
            raise HTTPException(409,"Kết quả bảo vệ đang được đối chiếu. Chỉ duyệt lưu khi hồ sơ đủ điều kiện")
        if not matches_defense(item.snapshot, rows):
            raise HTTPException(409, "Phiên bảo vệ hoặc MSSV đã thay đổi. Yêu cầu nhóm nộp lại bản hoàn thiện theo kết quả mới.")
        download(session,user,identifier)
        if thesis.state == "DEFENDED":
            thesis.state = "COMPLETED"
            thesis.row_version += 1
    item.state, item.decided_by, item.decided_at, item.decision_note = decision,user.id,now(),reason
    item.row_version += 1
    event = "THESIS_ARCHIVE_" + decision
    audit(session,user,event,"thesis",thesis.id,reason)
    notice(session,user,thesis,event,"Đã đưa khóa luận vào kho nội bộ" if decision == "ACCEPTED" else "Bộ môn yêu cầu nộp lại bản lưu")
    session.commit()


def reopen(session, user, identifier, expected, reason):
    item = session.get(m.ThesisArchiveVersion, identifier)
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == item.thesis_id).with_for_update()) if item else None
    if not thesis or not access(session, user, thesis).approver:
        raise HTTPException(404, "Không tìm thấy bản lưu trong bộ môn của bạn")
    if thesis.state not in VISIBLE_STATES:
        raise HTTPException(409, "Hồ sơ khóa luận đã đóng thao tác nộp lưu")
    latest = session.scalar(select(m.ThesisArchiveVersion).where(m.ThesisArchiveVersion.thesis_id == thesis.id)
        .order_by(m.ThesisArchiveVersion.version_no.desc()).limit(1).with_for_update()
        .execution_options(populate_existing=True))
    if latest.id != identifier or latest.state != "ACCEPTED":
        raise HTTPException(409, "Chỉ mở lại phiên bản đã duyệt đang có hiệu lực")
    row_version(expected, latest.row_version)
    latest.state = "REOPENED"
    latest.row_version += 1
    if thesis.state == "COMPLETED":
        thesis.state = "DEFENDED"
        thesis.row_version += 1
    audit(session, user, "THESIS_ARCHIVE_REOPENED", "thesis_archive_version", latest.id, reason)
    audit(session, user, "THESIS_ARCHIVE_REOPENED", "thesis", thesis.id, reason, source_reference=str(latest.id))
    notice(session, user, thesis, "THESIS_ARCHIVE_REOPENED", "Bộ môn đã thu hồi bản lưu và yêu cầu nộp bản thay thế")
    session.commit()


def download(session, user, identifier):
    item = session.get(m.ThesisArchiveVersion, identifier)
    thesis = session.get(m.Thesis,item.thesis_id) if item else None
    if not thesis or not visible(session, thesis) or not access(session,user,thesis).can_view:
        raise HTTPException(404,"Không tìm thấy tệp lưu trữ trong phạm vi của bạn")
    file = documents.require_clean(session.get(m.StoredFile,item.file_id),"mở bản khóa luận lưu")
    return documents.stored_download(session,SimpleNamespace(stored_file_id=file.id,content_sha256=file.sha256,
        download_label=f"Ban-luu-KLTN-v{item.version_no}",
        download_identity=item.snapshot.get("topic_code") or session.get(m.Topic, thesis.topic_id).code))
