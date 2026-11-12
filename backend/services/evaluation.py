"""NV6: explicit academic authority, private drafts and version-bound school eligibility."""
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from backend.db.models import entities as m
from backend.services import documents, file_scanner, membership_revision, workflow_notices as notices
from backend.services.registration import _is_department_head, profile, row_version
from backend.services.theses import audit, effective, now, primary_advisor, resource_role

FORM_FIELDS = {
    "ADVISOR": [
        {"key": "attitude", "label": "1. Tinh thần, thái độ của sinh viên"},
        {"key": "content", "label": "2. Sự đáp ứng của nội dung khóa luận"},
        {"key": "presentation", "label": "3. Hình thức khóa luận"}],
    # Keep the numbering in the official Mẫu 8, including the absent number 3.
    "REVIEWER": [
        {"key": "presentation", "label": "1. Hình thức trình bày, kết cấu, bố cục"},
        {"key": "research", "label": "2. Tính cấp thiết, tổng quan, mục đích, nhiệm vụ, đối tượng, phạm vi, phương pháp và ý nghĩa đề tài"},
        {"key": "contribution", "label": "4. Kết quả và đóng góp mới về khoa học"},
        {"key": "discussion", "label": "5. Những điểm cần trao đổi với tác giả"},
        {"key": "overall", "label": "6. Đánh giá chung"}],
}
MUTABLE = {"ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"}


def permissions(session, user, thesis):
    result = set()
    if user.base_role == "STUDENT":
        member = session.scalar(select(m.ThesisMember.id).join(m.StudentProfile,
            m.StudentProfile.id == m.ThesisMember.student_id).where(m.ThesisMember.thesis_id == thesis.id,
            m.StudentProfile.user_id == user.id, m.ThesisMember.active.is_(True)))
        if member:
            result.add("evaluation:view")
    elif user.base_role == "LECTURER":
        lecturer = profile(session, user, "LECTURER")
        if _is_department_head(session, lecturer.id, thesis.department_id):
            result.update({"evaluation:view", "evaluation:manage", "evaluation:eligibility", "evaluation:record"})
        if resource_role(session,user.id,"REVIEW_RECORDS_MANAGER",round_id=thesis.round_id):
            result.update({"evaluation:view","evaluation:record"})
        advisor = primary_advisor(session, thesis.id)
        if advisor and advisor.lecturer_id == lecturer.id:
            result.update({"evaluation:view", "evaluation:advisor"})
        if session.scalar(select(m.ReviewerAssignment.id).where(m.ReviewerAssignment.thesis_id == thesis.id,
            m.ReviewerAssignment.lecturer_id == lecturer.id, m.ReviewerAssignment.review_scope == "THESIS",
            m.ReviewerAssignment.state == "ACTIVE").limit(1)):
            result.update({"evaluation:view", "evaluation:reviewer"})
    return result


def access(session, user, thesis_id, action="evaluation:view", *, write=False):
    query = select(m.Thesis).where(m.Thesis.id == thesis_id)
    thesis = session.scalar(query.with_for_update() if write else query)
    actions = permissions(session, user, thesis) if thesis else set()
    if "evaluation:view" not in actions:
        raise HTTPException(404, "Không tìm thấy hồ sơ phản biện trong phạm vi của bạn")
    if action not in actions:
        raise HTTPException(403, "Thao tác này cần đúng phân công hoặc thẩm quyền bộ môn")
    if write and thesis.state not in MUTABLE | {"READY_FOR_DEFENSE"}:
        raise HTTPException(409, "Hồ sơ đã kết thúc hoặc khóa giai đoạn phản biện")
    return thesis


def ensure_open(thesis):
    if thesis.state not in MUTABLE:
        raise HTTPException(409, "Hồ sơ đã chốt đủ điều kiện. TBM cần mở xét lại kèm lý do trước khi sửa")


def members(session, thesis):
    return session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.active.is_(True)).order_by(m.ThesisMember.id)).all()


def member_for(session, thesis, identifier):
    member = session.get(m.ThesisMember, identifier)
    if not member or member.thesis_id != thesis.id or not member.active:
        raise HTTPException(404, "Sinh viên không thuộc nhóm khóa luận hiện hành")
    return member


def report(session, thesis):
    return session.scalar(select(m.DocumentVersion).join(m.Document,
        m.Document.id == m.DocumentVersion.document_id).where(m.Document.thesis_id == thesis.id,
        m.Document.document_type == "REPORT", m.Document.state == "ACTIVE",
        m.DocumentVersion.state != "SUPERSEDED").order_by(
        m.DocumentVersion.submitted_at.desc(), m.DocumentVersion.id.desc()).limit(1))


def review_current(session, thesis, member, current_report):
    advisor = primary_advisor(session, thesis.id)
    if not advisor or not current_report:
        return None
    return session.scalar(select(m.ThesisReview).where(m.ThesisReview.thesis_member_id == member.id,
        m.ThesisReview.advisor_assignment_id == advisor.id,
        m.ThesisReview.report_version_id == current_report.id,
        m.ThesisReview.kind == "ADVISOR", m.ThesisReview.state == "SUBMITTED")
        .order_by(m.ThesisReview.version_no.desc()).limit(1))


def last_check(session, member):
    return session.scalar(select(m.DefenseEligibilityCheck).where(
        m.DefenseEligibilityCheck.thesis_member_id == member.id).order_by(
        m.DefenseEligibilityCheck.version_no.desc()).limit(1))


def requirements(session, current_report, review, discipline_status):
    report_file = session.get(m.StoredFile, current_report.stored_file_id) if current_report else None
    signed = session.get(m.StoredFile, review.signed_file_id) if review and review.signed_file_id else None
    complete = bool(review and review.thesis_completed and report_file and report_file.scan_state == "CLEAN")
    consent = bool(review and review.allow_defense and ((signed and signed.scan_state == "CLEAN") or review.paper_confirmed_at))
    return [
        {"key": "discipline", "label": "Không bị kỷ luật từ cảnh cáo toàn Trường", "met": discipline_status == "CLEAR"},
        {"key": "completion", "label": "Hoàn thành KLTN, GVHD xác nhận trên đúng bản báo cáo", "met": complete},
        {"key": "consent", "label": "GVHD đồng ý bảo vệ bằng văn bản đã ký (Mẫu 7)", "met": consent},
    ]


def eligibility_out(session, thesis, member, current_report):
    blocked = membership_revision.blockers(session, thesis, current_report)
    review = review_current(session, thesis, member, current_report) if not blocked else None
    check = last_check(session, member)
    conditions = requirements(session, current_report, review, check.discipline_status if check else "UNKNOWN")
    fresh = bool(check and check.report_version_id == (current_report.id if current_report else None)
        and check.advisor_review_id == (review.id if review else None))
    state = "ELIGIBLE" if not blocked and fresh and check.state == "ELIGIBLE" and all(x["met"] for x in conditions) else (
        "STALE" if check and not fresh else "BLOCKED" if check else "NOT_CHECKED")
    return {"state": state, "conditions": conditions, "advisor_review_id": review.id if review else None,
        "discipline_status": check.discipline_status if check else "UNKNOWN",
        "source_reference": check.source_reference if check else None,
        "reason": check.reason if check else None, "checked_at": check.checked_at if check else None}


def notify(session, user, thesis, recipients, event, message):
    notices.emit(session, user.id, recipients, event, "defense", thesis.id,
        f"{message} · {thesis.current_title}", f"/evaluation/{thesis.id}")


def people(session, thesis):
    ids = notices.department_heads(session, thesis.department_id)
    advisor = primary_advisor(session, thesis.id)
    if advisor:
        ids.add(session.get(m.LecturerProfile, advisor.lecturer_id).user_id)
    ids |= set(session.scalars(select(m.ResourceAssignment.user_id).where(
        m.ResourceAssignment.round_id==thesis.round_id,m.ResourceAssignment.assignment_type=="REVIEW_RECORDS_MANAGER",effective(m.ResourceAssignment))))
    return ids


def assignments(session, thesis):
    return session.scalars(select(m.ReviewerAssignment).where(m.ReviewerAssignment.thesis_id == thesis.id,
        m.ReviewerAssignment.review_scope == "THESIS").order_by(m.ReviewerAssignment.assigned_at.desc())).all()


def reviewer_department_ids(session, thesis):
    """Reviewers may be chosen from active departments of the same faculty."""
    from backend.services.faculty_pool import department_ids
    return department_ids(session, thesis.department_id)


def assign(session, user, thesis_id, data, expected):
    thesis = access(session, user, thesis_id, "evaluation:manage", write=True)
    row_version(expected, thesis.row_version)
    lecturer = session.get(m.LecturerProfile, data.lecturer_id)
    account = session.get(m.UserAccount, lecturer.user_id) if lecturer else None
    if not lecturer or lecturer.department_id not in reviewer_department_ids(session, thesis) or not account or account.status != "ACTIVE":
        raise HTTPException(422, "Chọn GV đang hoạt động thuộc bộ môn phù hợp với khóa luận")
    advisor = primary_advisor(session, thesis.id)
    if advisor and advisor.lecturer_id == lecturer.id:
        raise HTTPException(422, "GVHD không được đồng thời phản biện cùng khóa luận")
    active = [a for a in assignments(session, thesis) if a.state == "ACTIVE"]
    if any(a.lecturer_id == lecturer.id for a in active):
        raise HTTPException(409, "GV này đang được phân công phản biện")
    if len(active) >= 2:
        raise HTTPException(409, "Đã có hai GV phản biện; thu hồi phân công cũ trước khi thay thế")
    if data.due_at <= now():
        raise HTTPException(422, "Hạn phản biện phải sau thời điểm hiện tại")
    item = m.ReviewerAssignment(id=uuid4(), thesis_id=thesis.id, lecturer_id=lecturer.id,
        review_scope="THESIS", assigned_by=user.id, assigned_at=now(), state="ACTIVE",
        due_at=data.due_at, assignment_reason=data.reason, source_reference=data.source_reference)
    session.add(item)
    thesis.row_version += 1
    audit(session, user, "THESIS_REVIEWER_ASSIGNED", "thesis", thesis.id,
        f"{item.id} · {lecturer.display_name}: {data.reason}", source_reference=data.source_reference)
    notify(session, user, thesis, {lecturer.user_id}, "THESIS_REVIEWER_ASSIGNED", "Bạn được giao phản biện khóa luận")
    session.commit()
    return workspace(session, user, thesis_id)


def revoke(session, user, thesis_id, assignment_id, data, expected):
    thesis = access(session, user, thesis_id, "evaluation:manage", write=True)
    row_version(expected, thesis.row_version)
    item = session.get(m.ReviewerAssignment, assignment_id)
    if not item or item.thesis_id != thesis.id or item.review_scope != "THESIS":
        raise HTTPException(404, "Không tìm thấy phân công phản biện")
    if item.state != "ACTIVE":
        raise HTTPException(409, "Phân công đã được thu hồi")
    item.state = "REVOKED"
    item.row_version += 1
    thesis.row_version += 1
    audit(session, user, "THESIS_REVIEWER_REVOKED", "thesis", thesis.id,
        data.reason, source_reference=str(item.id))
    lecturer = session.get(m.LecturerProfile, item.lecturer_id)
    # The former reviewer can read the withdrawal notice without retaining private-file access.
    notices.emit(session, user.id, {lecturer.user_id}, "THESIS_REVIEWER_REVOKED", "account", lecturer.user_id,
        f"Bộ môn đã thu hồi phân công phản biện: {thesis.current_title}. Lý do: {data.reason}", "/evaluation")
    session.commit()
    return workspace(session, user, thesis_id)


def update_deadline(session, user, thesis_id, assignment_id, data, expected):
    thesis = access(session, user, thesis_id, "evaluation:manage", write=True)
    row_version(expected, thesis.row_version)
    item = session.get(m.ReviewerAssignment, assignment_id)
    if not item or item.thesis_id != thesis.id or item.review_scope != "THESIS" or item.state != "ACTIVE":
        raise HTTPException(404, "Không tìm thấy phân công phản biện đang hiệu lực")
    if data.due_at <= now() or (item.due_at and data.due_at <= item.due_at):
        raise HTTPException(422, "Hạn gia hạn phải sau hạn hiện tại và sau thời điểm hiện tại")
    original = item.due_at
    item.due_at = data.due_at
    item.row_version += 1
    thesis.row_version += 1
    audit(session, user, "THESIS_REVIEW_DEADLINE_EXTENDED", "thesis", thesis.id,
        f"{item.id}: {original} → {data.due_at}. {data.reason}", source_reference=data.source_reference)
    notify(session, user, thesis, {session.get(m.LecturerProfile, item.lecturer_id).user_id},
        "THESIS_REVIEW_DEADLINE_EXTENDED", "Bộ môn đã gia hạn gửi nhận xét phản biện")
    session.commit()
    return workspace(session, user, thesis_id)


def writing_assignment(session, user, thesis, kind):
    action = "evaluation:advisor" if kind == "ADVISOR" else "evaluation:reviewer"
    if action not in permissions(session, user, thesis):
        raise HTTPException(403, "Chỉ GVHD hoặc GV phản biện được phân công mới được viết phiếu của mình")
    lecturer = profile(session, user, "LECTURER")
    if kind == "ADVISOR":
        return lecturer, primary_advisor(session, thesis.id)
    return lecturer, session.scalar(select(m.ReviewerAssignment).where(
        m.ReviewerAssignment.thesis_id == thesis.id, m.ReviewerAssignment.lecturer_id == lecturer.id,
        m.ReviewerAssignment.review_scope == "THESIS", m.ReviewerAssignment.state == "ACTIVE"))


def create_review(session, user, thesis_id, data, expected):
    thesis = access(session, user, thesis_id, write=True)
    if data.kind == "ADVISOR":
        ensure_open(thesis)
    row_version(expected, thesis.row_version)
    member = member_for(session, thesis, data.thesis_member_id)
    current = report(session, thesis)
    membership_revision.ensure_ready(session, thesis, current)
    if not current or current.id != data.report_version_id:
        raise HTTPException(409, "Bản báo cáo đã thay đổi hoặc chưa được nộp; tải lại hồ sơ")
    documents.require_clean(session.get(m.StoredFile, current.stored_file_id), "viết phiếu nhận xét")
    lecturer, assignment = writing_assignment(session, user, thesis, data.kind)
    related = session.scalars(select(m.ThesisReview).where(m.ThesisReview.thesis_member_id == member.id,
        m.ThesisReview.lecturer_id == lecturer.id, m.ThesisReview.kind == data.kind)).all()
    column = "advisor_assignment_id" if data.kind == "ADVISOR" else "reviewer_assignment_id"
    if any(r.state == "DRAFT" and r.report_version_id == current.id and getattr(r, column) == assignment.id for r in related):
        raise HTTPException(409, "Đã có phiếu nháp cho sinh viên và bản báo cáo này; mở phiếu để tiếp tục")
    item = m.ThesisReview(id=uuid4(), thesis_id=thesis.id, thesis_member_id=member.id,
        lecturer_id=lecturer.id, kind=data.kind, version_no=max([r.version_no for r in related], default=0)+1,
        report_version_id=current.id, sections={}, revision_reason=data.reason,
        **{column: assignment.id})
    session.add(item)
    thesis.row_version += 1
    session.flush()
    session.commit()
    return review_out(session, item, can_edit=True)


def editable_review(session, user, thesis_id, review_id, expected):
    thesis = access(session, user, thesis_id, write=True)
    item = session.get(m.ThesisReview, review_id)
    if not item or item.thesis_id != thesis.id:
        raise HTTPException(404, "Không tìm thấy phiếu nhận xét")
    if item.kind == "ADVISOR":
        ensure_open(thesis)
    lecturer, assignment = writing_assignment(session, user, thesis, item.kind)
    column = "advisor_assignment_id" if item.kind == "ADVISOR" else "reviewer_assignment_id"
    if item.lecturer_id != lecturer.id or getattr(item, column) != assignment.id:
        raise HTTPException(404, "Phiếu không thuộc phân công hiện hành của bạn")
    member_for(session, thesis, item.thesis_member_id)
    row_version(expected, item.row_version)
    if item.state != "DRAFT":
        raise HTTPException(409, "Phiếu đã gửi được giữ nguyên; tạo phiên bản mới kèm lý do để sửa")
    current = report(session, thesis)
    membership_revision.ensure_ready(session, thesis, current)
    if not current or item.report_version_id != current.id:
        raise HTTPException(409, "Đã có bản báo cáo khác; tạo phiếu mới cho bản hiện hành")
    return thesis, item


def save_review(session, user, thesis_id, review_id, data, expected):
    thesis, item = editable_review(session, user, thesis_id, review_id, expected)
    keys = {x["key"] for x in FORM_FIELDS[item.kind]}
    if set(data.sections) - keys:
        raise HTTPException(422, "Mục nhận xét không thuộc biểu mẫu đã chọn")
    if item.kind == "REVIEWER" and (data.thesis_completed is not None or data.allow_defense is not None):
        raise HTTPException(422, "Xác nhận hoàn thành và đồng ý bảo vệ thuộc Mẫu 7 của GVHD")
    changed = (item.sections != data.sections or item.thesis_completed != data.thesis_completed
        or item.allow_defense != data.allow_defense or item.source_reference != data.source_reference)
    if changed:
        # A signed copy must correspond to the last saved contents.
        item.signed_file_id = None
    item.sections = data.sections
    item.thesis_completed, item.allow_defense = data.thesis_completed, data.allow_defense
    item.source_reference = data.source_reference
    item.row_version += 1
    thesis.row_version += 1
    session.commit()
    return review_out(session, item, can_edit=True)


async def upload_signed(session, user, thesis_id, review_id, request, expected):
    path = None
    try:
        thesis, item = editable_review(session, user, thesis_id, review_id, expected)
        name, content, mime = await documents.read_upload(request)
        if Path(name).suffix.lower() not in {".pdf", ".docx"}:
            raise HTTPException(422, "Bản đã ký phải là PDF hoặc DOCX, tối đa 10 MB")
        stored, _, path = documents.persist_upload(session, name, content, mime)
        session.flush()
        file_scanner.scan(stored, path)
        item.signed_file_id = stored.id
        item.row_version += 1
        thesis.row_version += 1
        result = review_out(session, item, can_edit=True)
        session.commit()
        return result
    except Exception:
        session.rollback()
        if path and path.is_file():
            path.unlink()
        raise


def scan_signed(session, user, thesis_id, review_id, expected):
    _, item = editable_review(session, user, thesis_id, review_id, expected)
    stored = session.get(m.StoredFile, item.signed_file_id) if item.signed_file_id else None
    if not stored:
        raise HTTPException(404, "Chưa đính kèm bản đã ký")
    file_scanner.scan(stored, documents.storage_root() / Path(stored.storage_key).name)
    item.row_version += 1
    session.commit()
    return review_out(session, item, can_edit=True)


def submit_review(session, user, thesis_id, review_id, data, expected):
    thesis, item = editable_review(session, user, thesis_id, review_id, expected)
    if any(not item.sections.get(field["key"], "").strip() for field in FORM_FIELDS[item.kind]):
        raise HTTPException(422, "Điền đầy đủ các mục nhận xét theo biểu mẫu trước khi gửi")
    if item.kind == "ADVISOR" and (item.thesis_completed is None or item.allow_defense is None):
        raise HTTPException(422, "GVHD cần xác nhận hoàn thành và đề nghị cho bảo vệ hoặc không")
    if not (getattr(data,"confirm_content",None) or getattr(data,"confirm_signed_copy",None)):
        raise HTTPException(422,"Xác nhận nội dung nhận xét trước khi gửi")
    if item.signed_file_id:
        documents.require_clean(session.get(m.StoredFile,item.signed_file_id),"gửi bản nhận xét có đính kèm")
    item.state, item.submitted_at = "SUBMITTED", now()
    item.row_version += 1
    thesis.row_version += 1
    student = session.get(m.StudentProfile, session.get(m.ThesisMember, item.thesis_member_id).student_id)
    audit(session, user, "THESIS_REVIEW_SUBMITTED", "thesis", thesis.id,
        f"Mẫu {'7' if item.kind == 'ADVISOR' else '8'} · {student.student_code} · v{item.version_no}: {item.revision_reason}",
        source_reference=item.source_reference)
    notify(session, user, thesis, people(session, thesis) | {student.user_id}, "THESIS_REVIEW_SUBMITTED",
        f"Đã gửi nhận xét Mẫu {'7' if item.kind == 'ADVISOR' else '8'} cho {student.display_name}")
    session.commit()
    return review_out(session, item, can_edit=False)


def review_visible(session, user, thesis, item):
    actions = permissions(session, user, thesis)
    if item.state == "DRAFT":
        return user.base_role == "LECTURER" and session.get(m.LecturerProfile, item.lecturer_id).user_id == user.id
    if "evaluation:manage" in actions or "evaluation:advisor" in actions or "evaluation:record" in actions:
        return True
    if user.base_role == "LECTURER":
        return session.get(m.LecturerProfile, item.lecturer_id).user_id == user.id
    member = session.get(m.ThesisMember, item.thesis_member_id)
    return session.get(m.StudentProfile, member.student_id).user_id == user.id


def review_out(session, item, *, can_edit=False):
    file = session.get(m.StoredFile, item.signed_file_id) if item.signed_file_id else None
    return {"id": item.id, "thesis_member_id": item.thesis_member_id, "lecturer_id": item.lecturer_id,
        "lecturer_name": session.get(m.LecturerProfile, item.lecturer_id).display_name,
        "report_version_id": item.report_version_id, "kind": item.kind, "version_no": item.version_no,
        "row_version": item.row_version, "sections": item.sections, "state": item.state,
        "thesis_completed": item.thesis_completed, "allow_defense": item.allow_defense,
        "source_reference": item.source_reference, "revision_reason": item.revision_reason,
        "signed_file": {"name": file.original_name, "scan_state": file.scan_state} if file else None,
        "submitted_at": item.submitted_at, "can_edit": can_edit,
        "paper_receipt": {"reference":item.paper_reference,"export_code":item.paper_export_code,
            "confirmed_at":item.paper_confirmed_at,"confirmed_by":notices.actor_name(session,item.paper_confirmed_by)} if item.paper_confirmed_at else None,
        "export_history": [{"code":event.source_reference,"at":event.occurred_at}
            for event in session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_type=="thesis_review",
                m.AuditEvent.resource_id==item.id,m.AuditEvent.action=="THESIS_REVIEW_EXPORTED").order_by(m.AuditEvent.occurred_at.desc()))]}


def signed_download(session, user, thesis_id, review_id):
    thesis = access(session, user, thesis_id)
    item = session.get(m.ThesisReview, review_id)
    if not item or item.thesis_id != thesis.id or not review_visible(session, user, thesis, item):
        raise HTTPException(404, "Không tìm thấy phiếu trong phạm vi được xem")
    stored = session.get(m.StoredFile, item.signed_file_id) if item.signed_file_id else None
    # Reuse checksum and path validation after checking the exact review ACL.
    from types import SimpleNamespace
    response = documents.stored_download(session, SimpleNamespace(stored_file_id=stored.id, content_sha256=stored.sha256) if stored else None)
    from backend.services.download_names import filename
    from urllib.parse import quote
    student = session.get(m.StudentProfile,session.get(m.ThesisMember,item.thesis_member_id).student_id)
    name = filename("Mau-07-GVHD-Da-ky" if item.kind=="ADVISOR" else "Mau-08-Phan-bien-Da-ky", student.student_code,item.version_no,Path(stored.original_name).suffix)
    response.headers["Content-Disposition"] = "attachment; filename*=UTF-8''" + quote(name)
    return response


def report_download(session, user, thesis_id, version_id):
    thesis = access(session, user, thesis_id)
    version = session.get(m.DocumentVersion, version_id)
    document = session.get(m.Document, version.document_id) if version else None
    if not document or document.thesis_id != thesis.id or document.document_type != "REPORT":
        raise HTTPException(404, "Không tìm thấy phiên bản cuốn báo cáo")
    return documents.stored_download(session, version)


def check_eligibility(session, user, thesis_id, data, expected):
    thesis = access(session, user, thesis_id, "evaluation:eligibility", write=True)
    row_version(expected, thesis.row_version)
    from backend.services.thesis_changes import open_request
    if open_request(session,thesis):
        raise HTTPException(409, "Cần xử lý yêu cầu đổi đề tài trước khi xét điều kiện bảo vệ")
    if session.scalar(select(m.ThesisWithdrawalRequest.id).where(
        m.ThesisWithdrawalRequest.thesis_id == thesis.id,
        m.ThesisWithdrawalRequest.state.in_(["SUBMITTED", "ADVISOR_CONFIRMED"]),
    ).limit(1)):
        raise HTTPException(409, "Cần xử lý yêu cầu xin thôi đang chờ trước khi xét bảo vệ")
    member = member_for(session, thesis, data.thesis_member_id)
    current = report(session, thesis)
    blocked = membership_revision.blockers(session, thesis, current)
    review = review_current(session, thesis, member, current) if not blocked else None
    if data.report_version_id != (current.id if current else None) or data.advisor_review_id != (review.id if review else None):
        raise HTTPException(409, "Báo cáo hoặc Mẫu 7 đã đổi; tải lại trước khi xét điều kiện")
    conditions = requirements(session, current, review, data.discipline_status)
    previous = last_check(session, member)
    item = m.DefenseEligibilityCheck(id=uuid4(), thesis_id=thesis.id, thesis_member_id=member.id,
        report_version_id=current.id if current else None, advisor_review_id=review.id if review else None,
        version_no=previous.version_no+1 if previous else 1, discipline_status=data.discipline_status,
        source_reference=data.source_reference, reason=data.reason, checked_by=user.id, checked_at=now(),
        state="ELIGIBLE" if not blocked and all(c["met"] for c in conditions) else "BLOCKED")
    session.add(item)
    session.flush()
    ready = all(eligibility_out(session, thesis, mem, current)["state"] == "ELIGIBLE" for mem in members(session, thesis))
    if ready:
        thesis.state = "READY_FOR_DEFENSE"
    elif thesis.state == "READY_FOR_DEFENSE":
        thesis.state = "IN_PROGRESS"
    thesis.row_version += 1
    student = session.get(m.StudentProfile, member.student_id)
    audit(session, user, "DEFENSE_ELIGIBILITY_CHECKED", "defense_eligibility_check", item.id,
        f"{student.student_code} · {item.state}: {data.reason}", source_reference=data.source_reference)
    notify(session, user, thesis, people(session, thesis) | {student.user_id}, "DEFENSE_ELIGIBILITY_CHECKED",
        f"{student.display_name}: {'đủ' if item.state == 'ELIGIBLE' else 'chưa đủ'} điều kiện dự bảo vệ")
    session.commit()
    return workspace(session, user, thesis_id)


def reopen(session, user, thesis_id, data, expected):
    thesis = access(session, user, thesis_id, "evaluation:eligibility", write=True)
    row_version(expected, thesis.row_version)
    if thesis.state != "READY_FOR_DEFENSE":
        raise HTTPException(409, "Chỉ mở xét lại hồ sơ đã chốt đủ điều kiện bảo vệ")
    if session.scalar(select(m.DefenseSlot.id).where(m.DefenseSlot.thesis_id == thesis.id)):
        raise HTTPException(409, "Hủy lịch bảo vệ trước khi mở xét lại điều kiện")
    current = report(session, thesis)
    for member in members(session, thesis):
        previous = last_check(session, member)
        review = review_current(session, thesis, member, current)
        session.add(m.DefenseEligibilityCheck(id=uuid4(), thesis_id=thesis.id, thesis_member_id=member.id,
            version_no=previous.version_no+1 if previous else 1, report_version_id=current.id if current else None,
            advisor_review_id=review.id if review else None, discipline_status="UNKNOWN", state="BLOCKED",
            source_reference="REOPEN", reason=data.reason, checked_by=user.id, checked_at=now()))
        notify(session, user, thesis, {session.get(m.StudentProfile, member.student_id).user_id},
            "DEFENSE_ELIGIBILITY_REOPENED", "Bộ môn đã mở xét lại điều kiện bảo vệ")
    thesis.state = "IN_PROGRESS"
    thesis.row_version += 1
    audit(session, user, "DEFENSE_ELIGIBILITY_REOPENED", "thesis", thesis.id, data.reason)
    notify(session, user, thesis, people(session, thesis), "DEFENSE_ELIGIBILITY_REOPENED", "Bộ môn đã mở xét lại điều kiện bảo vệ")
    session.commit()
    return workspace(session, user, thesis_id)


def workspace(session, user, thesis_id):
    thesis = access(session, user, thesis_id)
    actions = permissions(session, user, thesis)
    current = report(session, thesis)
    workflow_blockers = membership_revision.blockers(session, thesis, current)
    current_file = session.get(m.StoredFile, current.stored_file_id) if current else None
    visible_members = []
    for member in members(session, thesis):
        student = session.get(m.StudentProfile, member.student_id)
        if user.base_role == "STUDENT" and student.user_id != user.id:
            continue
        visible_members.append({"id": member.id, "student_id": student.id, "name": student.display_name,
            "student_code": student.student_code,
            "eligibility": eligibility_out(session, thesis, member, current) if (
                user.base_role == "STUDENT" or "evaluation:eligibility" in actions or "evaluation:advisor" in actions) else None})
    reviews = session.scalars(select(m.ThesisReview).where(m.ThesisReview.thesis_id == thesis.id)
        .order_by(m.ThesisReview.created_at.desc(), m.ThesisReview.id)).all()
    visible_reviews = []
    for item in reviews:
        if not review_visible(session, user, thesis, item):
            continue
        editable = False
        if not workflow_blockers and session.get(m.ThesisMember, item.thesis_member_id).active and item.state == "DRAFT" and (thesis.state in MUTABLE or (thesis.state == "READY_FOR_DEFENSE" and item.kind == "REVIEWER")) and current and item.report_version_id == current.id:
            try:
                lecturer, assignment = writing_assignment(session, user, thesis, item.kind)
                editable = item.lecturer_id == lecturer.id and assignment.id == (
                    item.advisor_assignment_id if item.kind == "ADVISOR" else item.reviewer_assignment_id)
            except HTTPException:
                pass
        visible_reviews.append(review_out(session, item, can_edit=editable))
    candidates = []
    if "evaluation:manage" in actions:
        advisor = primary_advisor(session, thesis.id)
        for lecturer in session.scalars(select(m.LecturerProfile).join(m.UserAccount,
            m.UserAccount.id == m.LecturerProfile.user_id).where(m.LecturerProfile.department_id.in_(reviewer_department_ids(session, thesis)),
            m.UserAccount.status == "ACTIVE").order_by(m.LecturerProfile.display_name)):
            if not advisor or lecturer.id != advisor.lecturer_id:
                load = session.scalar(select(func.count()).select_from(m.ReviewerAssignment).where(
                    m.ReviewerAssignment.lecturer_id == lecturer.id, m.ReviewerAssignment.review_scope == "THESIS",
                    m.ReviewerAssignment.state == "ACTIVE"))
                from backend.services.faculty_pool import suggestion
                topic=session.get(m.Topic,thesis.topic_id)
                candidates.append({"id": lecturer.id, "name": lecturer.display_name, "code": lecturer.lecturer_code, "department": session.get(m.Department, lecturer.department_id).name, "active_load": load,
                    **suggestion(lecturer,thesis.current_title+" "+(topic.description or ""))})
        candidates.sort(key=lambda row:(-len(row["recommendation_reasons"]),row["active_load"],row["name"]))
    history = []
    if "evaluation:eligibility" in actions or user.base_role == "STUDENT":
        member_ids = [member["id"] for member in visible_members]
        for check in session.scalars(select(m.DefenseEligibilityCheck).where(
            m.DefenseEligibilityCheck.thesis_member_id.in_(member_ids)).order_by(m.DefenseEligibilityCheck.checked_at.desc())):
            history.append({"id": check.id, "thesis_member_id": check.thesis_member_id, "version_no": check.version_no,
                "state": check.state, "discipline_status": check.discipline_status, "source_reference": check.source_reference,
                "reason": check.reason, "checked_at": check.checked_at, "checked_by": notices.actor_name(session, check.checked_by)})
    revocations = {event.source_reference: event for event in session.scalars(select(m.AuditEvent).where(
        m.AuditEvent.resource_type == "thesis", m.AuditEvent.resource_id == thesis.id,
        m.AuditEvent.action == "THESIS_REVIEWER_REVOKED").order_by(m.AuditEvent.occurred_at))}
    return {"thesis_id": thesis.id, "title": thesis.current_title, "state": thesis.state,
        "row_version": thesis.row_version, "round_id": thesis.round_id,
        "round_label": session.get(m.ThesisRound, thesis.round_id).code, "actions": sorted(actions),
        "form_fields": FORM_FIELDS, "members": visible_members, "reviews": visible_reviews,
        "report": {"id": current.id, "version_no": current.version_no, "name": current_file.original_name,
            "scan_state": current_file.scan_state} if current else None,
        "assignments": [{"id": a.id, "lecturer_id": a.lecturer_id,
            "name": session.get(m.LecturerProfile, a.lecturer_id).display_name, "state": a.state,
            "due_at": a.due_at, "overdue": bool(a.due_at and a.due_at < now() and not all(
                any(r.reviewer_assignment_id == a.id and r.thesis_member_id == member.id and r.state == "SUBMITTED"
                    and current and r.report_version_id == current.id for r in reviews) for member in members(session, thesis))),
            "reason": a.assignment_reason, "source_reference": a.source_reference,
            "revoked_reason": revocations[str(a.id)].reason if str(a.id) in revocations else None} for a in assignments(session, thesis)],
        "reviewer_department": session.get(m.Department,thesis.department_id).name, "candidates": candidates, "eligibility_history": history, "workflow_blockers": workflow_blockers}


def report_submitted(session, user, thesis):
    recipients = notices.department_heads(session, thesis.department_id)
    recipients |= {session.get(m.LecturerProfile, a.lecturer_id).user_id for a in assignments(session, thesis) if a.state == "ACTIVE"}
    advisor = primary_advisor(session, thesis.id)
    if advisor:
        recipients.discard(session.get(m.LecturerProfile, advisor.lecturer_id).user_id)  # already notified by document workflow
    notify(session, user, thesis, recipients, "THESIS_REPORT_UPDATED", "Có bản báo cáo KLTN mới; nhận xét và điều kiện cần đối chiếu bản hiện hành")


def listing(session, user, search, limit, offset):
    from backend.services.theses import list_theses
    # Reuse the application's scoped thesis catalogue, then apply the stricter NV6 permission.
    rows = [row for row in list_theses(session, user) if "evaluation:view" in row.actions
        and search.casefold() in (row.title + " " + row.round_label + " " + " ".join(
            member.display_name + " " + member.student_code for member in row.members)).casefold()]
    items = []
    for row in rows[offset:offset+limit]:
        thesis = session.get(m.Thesis, row.id)
        active = [a for a in assignments(session, thesis) if a.state == "ACTIVE"]
        items.append({"id": row.id, "title": row.title, "round_label": row.round_label, "state": row.state,
            "members": [{"name": member.display_name, "code": member.student_code} for member in row.members],
            "reviewer_count": len(active), "report_available": report(session, thesis) is not None,
            "advisor_name": row.advisor_name})
    return {"total": len(rows), "items": items}

def review_fingerprint(session,item):
    import hashlib,json
    thesis=session.get(m.Thesis,item.thesis_id)
    values=[str(item.id),str(item.report_version_id),item.sections,item.thesis_completed,item.allow_defense,item.source_reference,thesis.current_title]
    return hashlib.sha256(json.dumps(values,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def record_paper(session,user,thesis_id,review_id,data,expected):
    thesis=access(session,user,thesis_id,write=True)
    item=session.scalar(select(m.ThesisReview).where(m.ThesisReview.id==review_id,m.ThesisReview.thesis_id==thesis.id).with_for_update())
    if not item or item.state!="SUBMITTED":
        raise HTTPException(409,"Chỉ ghi nhận bản giấy của phiếu đã gửi")
    if "evaluation:record" not in permissions(session,user,thesis):
        lecturer, assignment = writing_assignment(session, user, thesis, item.kind)
        column = "advisor_assignment_id" if item.kind == "ADVISOR" else "reviewer_assignment_id"
        if item.lecturer_id != lecturer.id or getattr(item, column) != assignment.id:
            raise HTTPException(403, "Chỉ người viết phiếu hiện hành hoặc người được giao tiếp nhận được xác nhận")
    row_version(expected,item.row_version)
    if item.paper_confirmed_at:
        raise HTTPException(409,"Bản giấy đã được ghi nhận; lịch sử được giữ nguyên")
    exported=session.scalar(select(m.AuditEvent).where(m.AuditEvent.resource_type=="thesis_review",m.AuditEvent.resource_id==item.id,
        m.AuditEvent.action=="THESIS_REVIEW_EXPORTED",m.AuditEvent.source_reference==data.export_code))
    if not exported or ("content_sha256="+review_fingerprint(session,item)) not in (exported.reason or ""):
        raise HTTPException(422,"Mã bản xuất không thuộc đúng nội dung phiếu này; xuất lại phiếu hiện tại để đối chiếu")
    item.paper_reference,item.paper_export_code=data.reference,data.export_code
    item.paper_confirmed_by,item.paper_confirmed_at=user.id,now()
    item.row_version+=1;thesis.row_version+=1
    audit(session,user,"THESIS_REVIEW_PAPER_RECEIVED","thesis_review",item.id,data.reference,source_reference=data.export_code)
    author=session.get(m.LecturerProfile,item.lecturer_id).user_id
    student=session.get(m.StudentProfile,session.get(m.ThesisMember,item.thesis_member_id).student_id).user_id
    notify(session,user,thesis,people(session,thesis)|{author,student},"THESIS_REVIEW_PAPER_RECEIVED","Đã xác nhận văn bản nhận xét có chữ ký; bộ môn có thể xét lại điều kiện")
    session.commit()
    return workspace(session,user,thesis.id)
