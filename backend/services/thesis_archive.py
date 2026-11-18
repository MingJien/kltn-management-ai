"""Private repository for approved post-defense manuscripts."""
from pathlib import Path
from types import SimpleNamespace
from unicodedata import combining, normalize
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import Text, cast, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import JSONPATH

from backend.db.models import entities as m
from backend.services import defense, defense_register, documents, evaluation, workflow_notices
from backend.services.registration import _is_department_head, row_version
from backend.services.theses import audit, effective, now, primary_advisor

VISIBLE_STATES = ("DEFENDED", "COMPLETED")
RESUBMISSION_STATES = {"RETURNED", "REOPENED"}
VIETNAMESE_LETTERS = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
PLAIN_LETTERS = "".join(ch for ch in normalize("NFD", VIETNAMESE_LETTERS) if not combining(ch)).replace("đ", "d")


def access(session, user, thesis):
    lecturer = defense.lecturer_for(session, user)
    student = defense.student_for(session, user)
    advisor = primary_advisor(session, thesis.id)
    member = bool(student and any(row.student_id == student.id for row in evaluation.members(session, thesis)))
    advisor_owns = bool(lecturer and advisor and advisor.lecturer_id == lecturer.id)
    manager = defense.manages(session,user,lecturer,thesis.round_id,thesis.department_id)
    approver = bool(lecturer and _is_department_head(session, lecturer.id, thesis.department_id))
    return member, advisor_owns, manager, approver


def versions(session, thesis_id):
    return session.scalars(select(m.ThesisArchiveVersion).where(m.ThesisArchiveVersion.thesis_id == thesis_id)
        .order_by(m.ThesisArchiveVersion.version_no.desc())).all()


def pending_correction(session, student_results):
    ids = [row["slot_id"] for row in student_results if row]
    if not ids:
        return None
    return session.scalar(select(m.DefenseCorrection.slot_id).where(
        m.DefenseCorrection.slot_id.in_(ids), m.DefenseCorrection.state == "PENDING").limit(1))


def submission_snapshot(session, thesis, rows):
    members = evaluation.members(session, thesis)
    by_student = {row["student_id"]: row for row in rows if row["thesis_id"] == str(thesis.id)}
    results = [by_student.get(str(member.student_id)) for member in members]
    if not results or not all(row and row["status"] != "PENDING" and row["council_closed"] for row in results):
        return None
    if not any(row["status"] == "GRADED" for row in results):
        return None
    if pending_correction(session, results):
        return None
    advisor = primary_advisor(session, thesis.id)
    lecturer = session.get(m.LecturerProfile, advisor.lecturer_id) if advisor else None
    return {"title": thesis.current_title, "advisor": lecturer.display_name if lecturer else "",
            "round": session.get(m.ThesisRound, thesis.round_id).code,
            "department": session.get(m.Department, thesis.department_id).name,
            "students": [{"name": row["name"], "code": row["code"], "slot_id": row["slot_id"]} for row in results]}


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
    member, _, _, approver = permissions
    snapshot = submission_snapshot(session, thesis, rows)
    history = versions(session, thesis.id)
    latest = history[0] if history else None
    blockers = []
    by_student = {row["student_id"]: row for row in rows if row["thesis_id"] == str(thesis.id)}
    students = []
    for active in evaluation.members(session, thesis):
        student = session.get(m.StudentProfile, active.student_id)
        students.append({"name": student.display_name, "code": student.student_code})
        row = by_student.get(str(student.id))
        if not row or row["status"] == "PENDING" or not row["council_closed"]:
            message = ("Chưa xếp lịch" if not row else row["outcome_label"] if row["status"] == "PENDING"
                       else "Hội đồng chưa khóa bảng điểm")
            blockers.append({"message": f"{student.display_name} ({student.student_code}): {message}",
                             "url": f"/defense?slot={row['slot_id']}&tab=results" if row else f"/evaluation/{thesis.id}"})
    assignment = primary_advisor(session, thesis.id)
    advisor = session.get(m.LecturerProfile, assignment.lecturer_id) if assignment else None
    identity = {"title": thesis.current_title, "advisor": advisor.display_name if advisor else "", "students": students}
    if snapshot is None and not blockers:
        slot_id = pending_correction(session, by_student.values())
        blockers.append({"message": "Còn đề nghị đính chính kết quả đang chờ xử lý", "url": f"/defense?slot={slot_id}&tab=results"}
                        if slot_id else {"message": "Chưa có sinh viên được chốt điểm để nộp lưu bản báo cáo", "url": "/defense"})
    return {"id": thesis.id, "title": thesis.current_title, "round_id": thesis.round_id,
            "topic_code": session.get(m.Topic, thesis.topic_id).code,
            "round": session.get(m.ThesisRound, thesis.round_id).code,
            "department": session.get(m.Department, thesis.department_id).name,
            "snapshot": latest.snapshot if latest else snapshot or identity, "blockers": blockers,
            "can_submit": bool(member and snapshot and (not latest or latest.state in RESUBMISSION_STATES)),
            "can_decide": bool(approver and latest and latest.state == "SUBMITTED"),
            "can_approve": snapshot is not None,
            "can_reopen": bool(approver and latest and latest.state == "ACCEPTED"),
            "waiting": snapshot is None and latest is None,
            "versions": [version_out(session, row) for row in history]}


def details(session, user, thesis_id):
    thesis = session.get(m.Thesis, thesis_id)
    if not thesis or thesis.state not in VISIBLE_STATES:
        raise HTTPException(404, "Không tìm thấy hồ sơ nộp lưu trong phạm vi được xem")
    permissions = access(session, user, thesis)
    if not any(permissions[:3]):
        raise HTTPException(404, "Không tìm thấy hồ sơ nộp lưu trong phạm vi được xem")
    sessions = defense_register.council_sessions(session, thesis.round_id, thesis_id=thesis.id)
    return entry(session, thesis, permissions, defense_register.rows_for_sessions(session, sessions))


def visibility_filter(session, user):
    student = defense.student_for(session, user)
    if student:
        return select(m.ThesisMember.id).where(m.ThesisMember.thesis_id == m.Thesis.id,
            m.ThesisMember.active.is_(True), m.ThesisMember.student_id == student.id).exists()
    lecturer = defense.lecturer_for(session, user)
    if not lecturer:
        return False
    from backend.services.nv6_reporting import scopes
    managed = [(scope["round_id"], scope["department_id"]) for scope in scopes(session, user)]
    advising = select(m.AdvisorAssignment.id).where(m.AdvisorAssignment.thesis_id == m.Thesis.id,
        m.AdvisorAssignment.lecturer_id == lecturer.id, effective(m.AdvisorAssignment)).exists()
    return or_(advising, tuple_(m.Thesis.round_id, m.Thesis.department_id).in_(managed))


def catalog_query(session, user, *, mode, state, search, round_id, department_id, page, limit):
    """Filter and paginate authorized rows before loading any document history."""
    archive = m.ThesisArchiveVersion
    latest = (select(archive.id, archive.thesis_id, archive.version_no, archive.state, archive.snapshot,
                     archive.decided_at)
              .distinct(archive.thesis_id).order_by(archive.thesis_id, archive.version_no.desc()).subquery())
    visible = (m.Thesis.state.in_(VISIBLE_STATES), visibility_filter(session, user))
    options = session.execute(select(m.ThesisRound.id, m.ThesisRound.code, m.Department.id, m.Department.name)
        .select_from(m.Thesis).join(m.ThesisRound, m.ThesisRound.id == m.Thesis.round_id)
        .join(m.Department, m.Department.id == m.Thesis.department_id).where(*visible)
        .distinct().order_by(m.ThesisRound.code.desc(), m.Department.name)).all()
    query = (select(m.Thesis.id, m.Thesis.current_title, m.Topic.code.label("topic_code"),
        m.ThesisRound.code.label("round"), m.Department.name.label("department"), latest.c.snapshot,
        latest.c.state, latest.c.version_no, latest.c.decided_at.label("approved_at"))
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
    member_text = (select(func.string_agg(func.concat_ws(" ", m.StudentProfile.display_name,
        m.StudentProfile.student_code), " ")).select_from(m.ThesisMember)
        .join(m.StudentProfile, m.StudentProfile.id == m.ThesisMember.student_id)
        .where(m.ThesisMember.thesis_id == m.Thesis.id, m.ThesisMember.active.is_(True)).correlate(m.Thesis).scalar_subquery())
    advisor_text = (select(m.LecturerProfile.display_name).select_from(m.AdvisorAssignment)
        .join(m.LecturerProfile, m.LecturerProfile.id == m.AdvisorAssignment.lecturer_id)
        .where(m.AdvisorAssignment.thesis_id == m.Thesis.id, effective(m.AdvisorAssignment))
        .correlate(m.Thesis).limit(1).scalar_subquery())
    snapshot_text = func.concat_ws(" ", latest.c.snapshot["title"].astext, latest.c.snapshot["advisor"].astext,
        cast(func.jsonb_path_query_array(latest.c.snapshot, cast("$.students[*].name", JSONPATH)), Text),
        cast(func.jsonb_path_query_array(latest.c.snapshot, cast("$.students[*].code", JSONPATH)), Text))
    if search:
        terms = normalize("NFD", search.lower()).replace("đ", "d")
        terms = "".join(ch for ch in terms if not combining(ch)).split()
        haystack = func.translate(func.lower(func.concat_ws(" ", m.Topic.code, m.Thesis.current_title,
            snapshot_text, member_text, advisor_text)), VIETNAMESE_LETTERS, PLAIN_LETTERS)
        for term in terms:
            query = query.where(haystack.contains(term, autoescape=True))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    page = min(page, max(1, (total + limit - 1) // limit))
    order = (latest.c.decided_at.desc().nulls_last() if mode == "catalog"
             else (latest.c.state == "SUBMITTED").desc().nulls_last())
    rows = session.execute(query.add_columns(advisor_text.label("advisor"))
        .order_by(order, m.Thesis.current_title, m.Thesis.id).offset((page - 1) * limit).limit(limit)).mappings().all()
    return {"items": [dict(row) for row in rows], "total": total, "page": page, "limit": limit,
            "scopes": [{"round_id": rid, "round": code, "department_id": did, "department": name}
                       for rid, code, did, name in options]}


def workspace(session, user, *, round_id=None):
    query = select(m.Thesis).where(m.Thesis.state.in_(VISIBLE_STATES)).order_by(m.Thesis.current_title)
    if round_id:
        query = query.where(m.Thesis.round_id == round_id)
    result_rows = {}
    items = []
    for thesis in session.scalars(query):
        permissions = access(session, user, thesis)
        if not any(permissions[:3]):
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


async def submit(session, user, identifier, request):
    thesis = session.get(m.Thesis, identifier)
    if not thesis or not access(session,user,thesis)[0]:
        raise HTTPException(404,"Không tìm thấy hồ sơ lưu trữ của bạn")
    name, content, mime = await documents.read_upload(request)
    if Path(name).suffix.lower() not in {".pdf", ".docx"}:
        raise HTTPException(422,"Nộp cuốn báo cáo hoàn thiện dạng PDF hoặc DOCX")
    thesis = session.scalar(select(m.Thesis).where(m.Thesis.id == identifier).with_for_update())
    if thesis.state not in {"DEFENDED", "COMPLETED"} or not access(session,user,thesis)[0]:
        raise HTTPException(409,"Chỉ nộp lưu sau khi hồ sơ đã bảo vệ và đủ kết quả")
    rows = defense_register.rows_for_sessions(session,defense_register.council_sessions(session,thesis.round_id,thesis_id=thesis.id))
    snapshot = submission_snapshot(session, thesis, rows)
    if not snapshot:
        raise HTTPException(409,"Chờ chốt kết quả từng thành viên và khóa bảng điểm hội đồng trước khi nộp lưu")
    history = versions(session,thesis.id)
    if history and history[0].state not in RESUBMISSION_STATES:
        raise HTTPException(409,"Hồ sơ đã nộp. Kiểm tra kết quả xử lý trước khi gửi bản mới")
    documents.file_scanner.require_available()
    file, digest, path = documents.persist_upload(session,name,content,mime)
    try:
        documents.file_scanner.scan(file,path)
        documents.require_clean(file, "nộp lưu khóa luận")
        item = m.ThesisArchiveVersion(id=uuid4(), thesis_id=thesis.id, file_id=file.id, submitted_by=user.id,
            version_no=(history[0].version_no+1 if history else 1), state="SUBMITTED", snapshot=snapshot)
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
    thesis = session.get(m.Thesis,item.thesis_id) if item else None
    if not thesis or not access(session,user,thesis)[3]:
        raise HTTPException(404,"Không tìm thấy hồ sơ lưu trữ trong bộ môn của bạn")
    item = session.scalar(select(m.ThesisArchiveVersion).where(m.ThesisArchiveVersion.id == identifier)
        .with_for_update().execution_options(populate_existing=True))
    row_version(expected,item.row_version)
    if item.state != "SUBMITTED":
        raise HTTPException(409,"Hồ sơ đã được xử lý. Làm mới danh sách để xem kết quả")
    if decision == "ACCEPTED":
        sessions = defense_register.council_sessions(session, thesis.round_id, thesis_id=thesis.id)
        if not submission_snapshot(session, thesis, defense_register.rows_for_sessions(session, sessions)):
            raise HTTPException(409,"Kết quả bảo vệ đang được đối chiếu. Chỉ duyệt lưu khi hồ sơ đủ điều kiện")
        download(session,user,identifier)
    item.state, item.decided_by, item.decided_at, item.decision_note = decision,user.id,now(),reason
    item.row_version += 1
    event = "THESIS_ARCHIVE_" + decision
    audit(session,user,event,"thesis",thesis.id,reason)
    notice(session,user,thesis,event,"Đã đưa khóa luận vào kho nội bộ" if decision == "ACCEPTED" else "Bộ môn yêu cầu nộp lại bản lưu")
    session.commit()


def reopen(session, user, identifier, expected, reason):
    item = session.get(m.ThesisArchiveVersion, identifier)
    thesis = session.get(m.Thesis, item.thesis_id) if item else None
    if not thesis or not access(session, user, thesis)[3]:
        raise HTTPException(404, "Không tìm thấy bản lưu trong bộ môn của bạn")
    session.scalar(select(m.Thesis).where(m.Thesis.id == thesis.id).with_for_update())
    latest = session.scalar(select(m.ThesisArchiveVersion).where(m.ThesisArchiveVersion.thesis_id == thesis.id)
        .order_by(m.ThesisArchiveVersion.version_no.desc()).limit(1).with_for_update()
        .execution_options(populate_existing=True))
    if latest.id != identifier or latest.state != "ACCEPTED":
        raise HTTPException(409, "Chỉ mở lại phiên bản đã duyệt đang có hiệu lực")
    row_version(expected, latest.row_version)
    latest.state = "REOPENED"
    latest.row_version += 1
    audit(session, user, "THESIS_ARCHIVE_REOPENED", "thesis_archive_version", latest.id, reason)
    audit(session, user, "THESIS_ARCHIVE_REOPENED", "thesis", thesis.id, reason, source_reference=str(latest.id))
    notice(session, user, thesis, "THESIS_ARCHIVE_REOPENED", "Bộ môn đã thu hồi bản lưu và yêu cầu nộp bản thay thế")
    session.commit()


def download(session, user, identifier):
    item = session.get(m.ThesisArchiveVersion, identifier)
    thesis = session.get(m.Thesis,item.thesis_id) if item else None
    if not thesis or not any(access(session,user,thesis)[:3]):
        raise HTTPException(404,"Không tìm thấy tệp lưu trữ trong phạm vi của bạn")
    file = documents.require_clean(session.get(m.StoredFile,item.file_id),"mở bản khóa luận lưu")
    return documents.stored_download(session,SimpleNamespace(stored_file_id=file.id,content_sha256=file.sha256,
        download_label=f"Ban-luu-KLTN-v{item.version_no}",download_identity=item.snapshot["title"]))
