"""Private repository for approved post-defense manuscripts."""
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import defense, defense_register, documents, evaluation, workflow_notices
from backend.services.registration import _is_department_head, row_version
from backend.services.theses import audit, now, primary_advisor


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


def submission_snapshot(session, thesis, rows):
    members = evaluation.members(session, thesis)
    by_student = {row["student_id"]: row for row in rows if row["thesis_id"] == str(thesis.id)}
    results = [by_student.get(str(member.student_id)) for member in members]
    if not results or not all(row and row["status"] != "PENDING" and row["council_closed"] for row in results):
        return None
    if not any(row["status"] == "GRADED" for row in results):
        return None
    advisor = primary_advisor(session, thesis.id)
    lecturer = session.get(m.LecturerProfile, advisor.lecturer_id) if advisor else None
    return {"title": thesis.current_title, "advisor": lecturer.display_name if lecturer else "",
            "round": session.get(m.ThesisRound, thesis.round_id).code,
            "department": session.get(m.Department, thesis.department_id).name,
            "students": [{"name": row["name"], "code": row["code"], "slot_id": row["slot_id"]} for row in results]}


def version_out(session, row):
    file = session.get(m.StoredFile, row.file_id)
    return {"id": row.id, "number": row.version_no, "revision": row.row_version, "state": row.state,
            "filename": file.original_name, "created_at": row.created_at, "decided_at": row.decided_at,
            "decided_by": workflow_notices.actor_name(session, row.decided_by) if row.decided_by else None,
            "decision_note": row.decision_note}


def workspace(session, user, *, round_id=None):
    query = select(m.Thesis).where(m.Thesis.state.in_(["DEFENDED", "COMPLETED"])).order_by(m.Thesis.current_title)
    if round_id:
        query = query.where(m.Thesis.round_id == round_id)
    result_rows = {}
    items = []
    for thesis in session.scalars(query):
        member, advisor, manager, approver = access(session, user, thesis)
        if not (member or advisor or manager):
            continue
        if thesis.round_id not in result_rows:
            result_rows[thesis.round_id] = defense_register.rows_for_sessions(session, defense_register.council_sessions(session, thesis.round_id))
        snapshot = submission_snapshot(session, thesis, result_rows[thesis.round_id])
        history = versions(session, thesis.id)
        latest = history[0] if history else None
        items.append({"id": thesis.id, "round_id": thesis.round_id, "title": thesis.current_title,
            "round": session.get(m.ThesisRound, thesis.round_id).code, "department": session.get(m.Department, thesis.department_id).name,
            "snapshot": latest.snapshot if latest else snapshot,
            "can_submit": bool(member and snapshot and (not latest or latest.state == "RETURNED")),
            "can_decide": bool(approver and latest and latest.state == "SUBMITTED"),
            "waiting": snapshot is None and latest is None,
            "versions": [version_out(session, row) for row in history]})
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
    rows = defense_register.rows_for_sessions(session,defense_register.council_sessions(session,thesis.round_id))
    snapshot = submission_snapshot(session, thesis, rows)
    if not snapshot:
        raise HTTPException(409,"Chờ chốt kết quả từng thành viên và khóa bảng điểm hội đồng trước khi nộp lưu")
    history = versions(session,thesis.id)
    if history and history[0].state != "RETURNED":
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
        download(session,user,identifier)
    item.state, item.decided_by, item.decided_at, item.decision_note = decision,user.id,now(),reason
    item.row_version += 1
    event = "THESIS_ARCHIVE_" + decision
    audit(session,user,event,"thesis",thesis.id,reason)
    notice(session,user,thesis,event,"Đã đưa khóa luận vào kho nội bộ" if decision == "ACCEPTED" else "Bộ môn yêu cầu nộp lại bản lưu")
    session.commit()


def download(session, user, identifier):
    item = session.get(m.ThesisArchiveVersion, identifier)
    thesis = session.get(m.Thesis,item.thesis_id) if item else None
    if not thesis or not any(access(session,user,thesis)[:3]):
        raise HTTPException(404,"Không tìm thấy tệp lưu trữ trong phạm vi của bạn")
    file = documents.require_clean(session.get(m.StoredFile,item.file_id),"mở bản khóa luận lưu")
    return documents.stored_download(session,SimpleNamespace(stored_file_id=file.id,content_sha256=file.sha256,
        download_label=f"Ban-luu-KLTN-v{item.version_no}",download_identity=item.snapshot["title"]))
