"""One result per student across the original and supplementary sessions."""
from fastapi import HTTPException
from sqlalchemy import select

from backend.db.models import entities as m
from backend.services import defense, defense_templates
from backend.services.theses import resource_role


def rounds_for_export(session, user):
    lecturer = defense.lecturer_for(session, user)
    if not lecturer:
        return []
    return [round_ for round_ in session.scalars(select(m.ThesisRound).order_by(m.ThesisRound.created_at.desc()))
            if resource_role(session, user.id, "KLTN_COORDINATOR", round_id=round_.id)]


def council_sessions(session, round_id, *, thesis_id=None):
    query = (select(m.DefenseSlot, m.DefenseCouncil)
        .join(m.DefenseCouncil, m.DefenseCouncil.id == m.DefenseSlot.council_id)
        .where(m.DefenseCouncil.round_id == round_id))
    if thesis_id is not None:
        query = query.where(m.DefenseSlot.thesis_id == thesis_id)
    return session.execute(query.order_by(m.DefenseSlot.starts_at, m.DefenseSlot.id)).all()


def require_round_access(session, user, round_id, sessions=None):
    lecturer = defense.lecturer_for(session, user)
    round_ = session.get(m.ThesisRound, round_id)
    if not round_ or not lecturer or not resource_role(session, user.id, "KLTN_COORDINATOR", round_id=round_id):
        raise HTTPException(404, "Không tìm thấy bảng điểm toàn đợt trong phạm vi điều phối")
    if sessions is None:
        sessions = council_sessions(session, round_id)
    departments = {council.department_id for _, council in sessions}
    if any(not defense.manages(session, user, lecturer, round_id, department_id) for department_id in departments):
        raise HTTPException(403, "Cần quyền điều phối toàn bộ hội đồng có lịch trong đợt để xuất danh sách đầy đủ")
    return round_, sessions


def rows_for_sessions(session, sessions):
    decisions = {(item.slot_id, str(item.thesis_member_id)): item for item in session.scalars(
        select(m.DefenseAbsenceDecision).where(m.DefenseAbsenceDecision.slot_id.in_([slot.id for slot, _ in sessions])))}
    rows = {}
    # Follow the chain even if the meeting date was entered out of order.
    by_id = {slot.id: slot for slot, _ in sessions}

    def depth(slot):
        seen = {slot.id}
        prior = slot.prior_slot_id
        while prior in by_id and prior not in seen:
            seen.add(prior)
            prior = by_id[prior].prior_slot_id
        return len(seen)

    for slot, council in sorted(sessions, key=lambda pair: (depth(pair[0]), pair[0].starts_at, pair[0].id)):
        results = defense.results(slot, council)
        for student in defense_templates.academic_roster(session, slot):
            result = results[student["id"]]
            grade = result["average"] if slot.finalized_at else None
            decision = decisions.get((slot.id, student["id"]))
            if grade is not None:
                status, label = "GRADED", "Đã chốt điểm"
            elif not slot.finalized_at:
                status, label = "PENDING", "Chưa chốt kết quả"
            elif decision and decision.outcome == "NOT_PASSED":
                status, label = "ABSENT_FINAL", "Không đạt do vắng · " + decision.reference
            elif decision:
                status, label = "PENDING", "Chờ bảo vệ bổ sung · " + decision.reference
            else:
                status, label = "PENDING", "Vắng · chờ quyết định của Khoa"
            rows[student["student_id"]] = {**student, "grade": grade, "status": status, "outcome_label": label,
                "attendance_status": result["attendance"].get("status"),
                "classification": slot.minutes.get("classifications", {}).get(student["id"]) if grade is not None else None,
                "slot_id": str(slot.id), "thesis_id": str(slot.thesis_id), "slot_revision": slot.row_version,
                "council": council.name, "council_closed": bool(council.closed_at)}
    return sorted(rows.values(), key=lambda row: (row["class_name"].casefold(), row["code"]))


def export_readiness(rows, sessions, unscheduled):
    issues = []
    if not rows:
        issues.append("Chưa có sinh viên được xếp lịch trong đợt")
    unlocked = {council.name for _, council in sessions if not council.closed_at}
    if unlocked:
        issues.append(f"Còn {len(unlocked)} hội đồng chưa khóa bảng điểm")
    pending = sum(row["status"] == "PENDING" for row in rows)
    if pending:
        issues.append(f"Còn {pending} sinh viên chờ kết quả hoặc quyết định của Khoa")
    if unscheduled:
        issues.append(f"Còn {len(unscheduled)} sinh viên đủ điều kiện chưa được xếp lịch")
    return issues


def unscheduled_students(session, round_id, rows):
    from backend.services import evaluation
    scheduled={row['student_id'] for row in rows}
    unscheduled=[]
    theses = session.scalars(select(m.Thesis).where(
        m.Thesis.round_id == round_id, m.Thesis.state.not_in(["WITHDRAWN", "ARCHIVED"])
    ).order_by(m.Thesis.current_title, m.Thesis.id))
    for thesis in theses:
        members = [member for member in evaluation.members(session, thesis) if str(member.student_id) not in scheduled]
        if not members:
            continue
        report=evaluation.report(session,thesis)
        for member in members:
            if evaluation.eligibility_out(session,thesis,member,report)['state']=='ELIGIBLE':
                student=session.get(m.StudentProfile,member.student_id)
                unscheduled.append({'name':student.display_name,'code':student.student_code,'thesis_id':str(thesis.id)})
    return unscheduled


def workspace(session, user, round_id):
    round_, sessions = require_round_access(session, user, round_id)
    rows = rows_for_sessions(session, sessions)
    unscheduled = unscheduled_students(session, round_id, rows)
    return {"code": round_.code, "issues": export_readiness(rows, sessions, unscheduled), "rows": [
        {"name": row["name"], "code": row["code"], "class_name": row["class_name"], "grade": row["grade"],
         "status": row["outcome_label"], "slot_id": row["slot_id"], "council": row["council"],
         "has_birth_date": bool(row["birth_date"])} for row in rows], 'unscheduled':unscheduled,
         'scheduled_count':len(rows),'graded_count':sum(row['grade'] is not None for row in rows)}
