"""Round reports and data checks share the same result register as Mẫu 10/11."""
from collections import Counter
from hashlib import sha256
import json

from fastapi import HTTPException
from sqlalchemy import func, select

from backend.api.defense_schemas import normalize_academic_text
from backend.db.models import entities as m
from backend.services import defense, defense_register, evaluation
from backend.services.theses import audit


def scopes(session, user):
    lecturer = defense.lecturer_for(session, user)
    if not lecturer and user.base_role != "ADMIN":
        return []
    rounds = session.scalars(select(m.ThesisRound).order_by(m.ThesisRound.created_at.desc())).all()
    departments = session.scalars(select(m.Department).order_by(m.Department.code)).all()
    return [{"round_id": round_.id, "round_code": round_.code, "department_id": department.id,
             "department": department.name} for round_ in rounds for department in departments
            if defense.valid_council_scope(round_, department) and (
                user.base_role == "ADMIN" or defense.manages(session,user,lecturer,round_.id,department.id))]


def workspace(session, user, round_id, department_id):
    from backend.services.thesis_archive import submission_snapshot

    available = {scope["department_id"] for scope in scopes(session,user) if scope["round_id"] == round_id}
    if not available or (department_id and department_id not in available):
        raise HTTPException(404,"Không tìm thấy báo cáo trong phạm vi được giao")
    selected = {department_id} if department_id else available
    sessions = [(slot,council) for slot,council in defense_register.council_sessions(session,round_id) if council.department_id in selected]
    results = {row["student_id"]: row for row in defense_register.rows_for_sessions(session,sessions)}
    theses = session.scalars(select(m.Thesis).where(m.Thesis.round_id == round_id, m.Thesis.department_id.in_(selected),
        m.Thesis.state != "WITHDRAWN").order_by(m.Thesis.current_title)).all()
    majors = {(row.department_id,row.code): row.name for row in session.scalars(
        select(m.DepartmentMajor).where(m.DepartmentMajor.department_id.in_(selected)))}
    expired = set(session.scalars(select(m.ThesisExtensionRequest.thesis_id)
        .join(m.Thesis, m.Thesis.id == m.ThesisExtensionRequest.thesis_id)
        .where(m.Thesis.round_id == round_id, m.Thesis.department_id.in_(selected), m.Thesis.state == "ARCHIVED",
               m.ThesisExtensionRequest.state == "EXPIRED", m.ThesisExtensionRequest.extension_id.is_not(None))))
    eligibility_counts, result_counts, score_counts = Counter(), Counter(), Counter()
    archive_counts, attendance_counts, classification_counts = Counter(), Counter(), Counter()
    rows = []
    for thesis in theses:
        report = evaluation.report(session,thesis)
        archive_state = session.scalar(select(m.ThesisArchiveVersion.state).where(m.ThesisArchiveVersion.thesis_id == thesis.id)
            .order_by(m.ThesisArchiveVersion.version_no.desc()).limit(1))
        if archive_state:
            archive_counts[archive_state] += 1
        elif thesis.state in {"DEFENDED", "COMPLETED"}:
            ready_to_submit = submission_snapshot(session, thesis, results.values())
            archive_counts["NOT_SUBMITTED" if ready_to_submit else "WAITING_RESULTS"] += 1
        for member in evaluation.members(session,thesis):
            student = session.get(m.StudentProfile,member.student_id)
            latest = results.get(str(student.id))
            if latest and latest["thesis_id"] != str(thesis.id):
                latest = None
            eligibility = evaluation.eligibility_out(session,thesis,member,report)["state"]
            status = latest["status"] if latest else "EXTENSION_EXPIRED" if thesis.id in expired else "NOT_SCHEDULED"
            eligibility_counts[eligibility] += 1
            result_counts[status] += 1
            grade = latest["grade"] if latest else None
            if latest:
                attendance_counts[latest["attendance_status"] or "NOT_RECORDED"] += 1
            if grade is not None:
                score_counts[str(grade)] += 1
                classification_counts[latest["classification"] or "Chưa ghi nhận"] += 1
            class_name = latest["class_name"] if latest else student.class_name
            cohort = latest["training_cohort"] if latest else student.training_cohort
            major_code = latest["major_code"] if latest else student.major_code
            major = majors.get((student.department_id, major_code))
            issues = [f"Thiếu {label}" for label, value in (
                ("lớp", class_name), ("ngành", major_code), ("khóa học", cohort),
                ("ngày sinh", latest["birth_date"] if latest else student.birth_date)) if not value]
            if major_code and (not major or major.startswith("Chưa xác minh")):
                issues.append("Ngành chưa đối chiếu danh mục")
            for label, value in (("Lớp", class_name), ("Khóa học", cohort)):
                if value and normalize_academic_text(value) != value:
                    issues.append(f"{label} cần chuẩn hóa cách ghi")
            rows.append({"id": str(member.id), "thesis_id": thesis.id, "title": thesis.current_title,
                "name": student.display_name, "code": student.student_code, "class_name": class_name,
                "eligibility": eligibility, "result": status, "grade": grade, "issues": issues,
                "attendance": latest["attendance_status"] if latest else None,
                "classification": latest["classification"] if latest else None, "slot_id": latest["slot_id"] if latest else None})
    return {"generated_at": defense.now(), "theses": len(theses), "students": len(rows),
            "sessions": len(sessions), "councils": len({council.id for _,council in sessions}),
            "eligibility": dict(eligibility_counts), "results": dict(result_counts),
            "score_counts": dict(score_counts), "archives": dict(archive_counts),
            "attendance": dict(attendance_counts), "classifications": dict(classification_counts),
            "incomplete_profiles": sum(bool(row["issues"]) for row in rows),
            "rows": rows if user.base_role == "LECTURER" else []}


def academic_member(session, user, round_id, member_id):
    member = session.get(m.ThesisMember, member_id)
    thesis = session.get(m.Thesis, member.thesis_id) if member else None
    lecturer = defense.lecturer_for(session,user)
    if not (member and member.active and thesis and thesis.round_id == round_id and
            defense.manages(session,user,lecturer,round_id,thesis.department_id)):
        raise HTTPException(404,"Không tìm thấy sinh viên trong phạm vi bạn quản lý")
    return thesis, member


def profile_data(student):
    return {"class_name": student.class_name or "", "major_code": student.major_code or "",
            "training_cohort": student.training_cohort or "", "birth_date": student.birth_date.isoformat() if student.birth_date else ""}


def profile_revision(data):
    return sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def profile_for_check(session, user, round_id, member_id):
    _, member = academic_member(session,user,round_id,member_id)
    student = session.get(m.StudentProfile,member.student_id)
    data = profile_data(student)
    majors = session.scalars(select(m.DepartmentMajor).where(m.DepartmentMajor.department_id==student.department_id,
        m.DepartmentMajor.active.is_(True)).order_by(m.DepartmentMajor.code)).all()
    return {**data, "revision": profile_revision(data), "majors": [{"code": major.code,"name": major.name}
        for major in majors if not major.name.startswith("Chưa xác minh")]}


def correct_profile(session, user, round_id, member_id, signature, data):
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    thesis, member = academic_member(session,user,round_id,member_id)
    if session.scalar(select(m.DefenseSlot.id).where(m.DefenseSlot.thesis_id==thesis.id,
            m.DefenseSlot.roster.contains([{"id":str(member.id)}])).limit(1)):
        raise HTTPException(409,"Sinh viên đã có lịch. Mở phiên bảo vệ để đính chính dữ liệu trên bản xuất")
    student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.id==member.student_id).with_for_update())
    old = profile_revision(profile_data(student))
    if signature != old:
        raise HTTPException(409,"Dữ liệu đã thay đổi. Tải lại thông tin học vụ trước khi lưu")
    defense.validate_academic_profile(session,student,data)
    student.class_name,student.major_code = data.class_name,data.major_code
    student.birth_date,student.training_cohort = data.birth_date,data.training_cohort or None
    new = profile_revision(profile_data(student))
    if old == new:
        raise HTTPException(422,"Thông tin học vụ chưa thay đổi")
    audit(session,user,"DEFENSE_ACADEMIC_PROFILE_CORRECTED","thesis",thesis.id,f"{student.student_code} · {data.reason}",
          before_hash=old,after_hash=new,source_reference=data.source_reference)
    session.commit()
