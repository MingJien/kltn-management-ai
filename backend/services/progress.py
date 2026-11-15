"""Versioned progress submissions and individual work evidence."""
from uuid import uuid4
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select

from backend.api.core_schemas import MilestoneOut, ProgressOut, ReviewOut, WorkOut
from backend.db.models import entities as m
from backend.services import documents
from backend.services.documents import require_clean
from backend.services.registration import profile, row_version
from backend.services.theses import audit, eligible_lecturer, now, rights, thesis_access


def milestone_scope(thesis):
    return (m.ProgressMilestone.thesis_id.is_(None) | (m.ProgressMilestone.thesis_id == thesis.id))


def milestones(session, thesis, user=None):
    query=select(m.ProgressMilestone).where(m.ProgressMilestone.round_id==thesis.round_id,milestone_scope(thesis))
    if user is None or "progress:view" not in rights(session,user,thesis):
        query=query.where(m.ProgressMilestone.thesis_id.is_(None))
    return session.scalars(query.order_by(m.ProgressMilestone.due_at,m.ProgressMilestone.code,m.ProgressMilestone.version_no)).all()


def milestone_out(item):
    return MilestoneOut(id=item.id,code=item.code,title=item.title,version_no=item.version_no,
        row_version=item.row_version,state=item.state,due_at=item.due_at,expected_ratio=item.expected_ratio,
        scope="THESIS" if item.thesis_id else "ROUND",thesis_id=item.thesis_id)


def _milestone_right(session,user,thesis,private):
    action="milestone:manage_own" if private else "milestone:manage"
    if action not in rights(session,user,thesis):
        raise HTTPException(403,"Chỉ GVHD chính thức quản lý mốc nội bộ; người điều phối chỉ quản lý mốc chung của đợt")


def _notify_milestone(session,user,thesis,item,event,message):
    if item.thesis_id:
        from backend.services import workflow_notices as notices
        from backend.services.theses import primary_advisor
        advisor=primary_advisor(session,thesis.id)
        recipients=set(session.scalars(select(m.StudentProfile.user_id).join(m.ThesisMember,
            m.ThesisMember.student_id==m.StudentProfile.id).where(m.ThesisMember.thesis_id==thesis.id,m.ThesisMember.active.is_(True))))
        if advisor:
            recipients.add(session.get(m.LecturerProfile,advisor.lecturer_id).user_id)
        for recipient in recipients:
            notices.emit(session,user.id,{recipient},event,"account",recipient,message,f"/theses/{thesis.id}?section=progress")
    else:
        from backend.services.notifications import notify_round_participants
        notify_round_participants(session,round_id=thesis.round_id,actor_user_id=user.id,kind=event,message=message,section="progress")


def _audit_milestone(session,user,thesis,item,event,reason):
    audit(session,user,event,"progress_milestone" if item.thesis_id else "round",
        item.id if item.thesis_id else thesis.round_id,reason)


def create_milestone(session, user, thesis_id, data):
    private=data.scope=="THESIS"
    thesis=thesis_access(session,user,thesis_id,lock=True,write=True)
    _milestone_right(session,user,thesis,private)
    round_=session.scalar(select(m.ThesisRound).where(m.ThesisRound.id==thesis.round_id).with_for_update())
    if round_.state=="ARCHIVED":
        raise HTTPException(409,"Đợt đã lưu trữ")
    scope=m.ProgressMilestone.thesis_id==thesis.id if private else m.ProgressMilestone.thesis_id.is_(None)
    previous=session.scalar(select(m.ProgressMilestone).where(m.ProgressMilestone.round_id==thesis.round_id,
        scope,m.ProgressMilestone.code==data.code).order_by(m.ProgressMilestone.version_no.desc()).limit(1))
    if previous and previous.state=="OPEN":
        raise HTTPException(409,"Đóng phiên bản mốc đang mở trước khi ban hành phiên bản mới cùng mã")
    item=m.ProgressMilestone(id=uuid4(),round_id=thesis.round_id,thesis_id=thesis.id if private else None,
        code=data.code,title=data.title,due_at=data.due_at,expected_ratio=data.expected_ratio,
        source_type="ADVISOR" if private else "ROUND_POLICY",version_no=previous.version_no+1 if previous else 1,state="OPEN")
    session.add(item);session.flush()
    _audit_milestone(session,user,thesis,item,"MILESTONE_OPENED",f"{item.code}: {item.title}")
    _notify_milestone(session,user,thesis,item,"MILESTONE_OPENED",f"Đã mở mốc {item.title} cho {'khóa luận của bạn' if private else 'toàn đợt'}.")
    session.commit()
    return milestone_out(item)


def _locked_milestone(session,user,thesis_id,milestone_id,expected):
    thesis=thesis_access(session,user,thesis_id,lock=True,write=True)
    item=session.scalar(select(m.ProgressMilestone).where(m.ProgressMilestone.id==milestone_id,
        m.ProgressMilestone.round_id==thesis.round_id,milestone_scope(thesis)).with_for_update())
    if not item:
        raise HTTPException(404,"Không tìm thấy mốc trong phạm vi khóa luận")
    _milestone_right(session,user,thesis,item.thesis_id is not None)
    round_=session.get(m.ThesisRound,thesis.round_id)
    if round_.state=="ARCHIVED":raise HTTPException(409,"Đợt đã lưu trữ")
    row_version(expected,item.row_version)
    return thesis,item


def close_milestone(session,user,thesis_id,milestone_id,data,expected):
    thesis,item=_locked_milestone(session,user,thesis_id,milestone_id,expected)
    if item.state!="OPEN":raise HTTPException(409,"Mốc đã đóng")
    item.state,item.row_version="CLOSED",item.row_version+1
    _audit_milestone(session,user,thesis,item,"MILESTONE_CLOSED",f"{item.code}: {data.reason}")
    _notify_milestone(session,user,thesis,item,"MILESTONE_CLOSED",f"Mốc {item.title} đã đóng nhận báo cáo. Chỉ nộp lại khi GVHD yêu cầu sửa.")
    session.commit()
    return milestone_out(item)


def extend_milestone(session,user,thesis_id,milestone_id,data,expected):
    thesis,item=_locked_milestone(session,user,thesis_id,milestone_id,expected)
    scope=m.ProgressMilestone.thesis_id==item.thesis_id if item.thesis_id else m.ProgressMilestone.thesis_id.is_(None)
    latest=session.scalar(select(func.max(m.ProgressMilestone.version_no)).where(m.ProgressMilestone.round_id==thesis.round_id,
        scope,m.ProgressMilestone.code==item.code))
    if item.version_no!=latest:raise HTTPException(409,"Mốc đã có phiên bản mới; không thể mở lại phiên bản cũ")
    if not item.due_at:raise HTTPException(409,"Mốc chưa có hạn nộp")
    if data.due_at<=item.due_at or data.due_at<=now():raise HTTPException(422,"Hạn mới phải sau hạn cũ và sau thời điểm hiện tại")
    old_due=item.due_at;reopening=item.state=="CLOSED"
    item.due_at,item.state,item.row_version=data.due_at,"OPEN",item.row_version+1
    event="MILESTONE_REOPENED" if reopening else "MILESTONE_EXTENDED"
    _audit_milestone(session,user,thesis,item,event,f"{item.code}: {old_due.isoformat()} -> {data.due_at.isoformat()}; {data.reason}")
    _notify_milestone(session,user,thesis,item,event,f"Mốc {item.title} đã được gia hạn{' và mở nhận lại' if reopening else ''}. Báo cáo cũ giữ nguyên dấu trễ.")
    session.commit()
    return milestone_out(item)


def progress_out(session, item):
    reviews = session.scalars(select(m.ProgressReview).where(m.ProgressReview.progress_report_id == item.id)
        .order_by(m.ProgressReview.created_at, m.ProgressReview.id)).all()
    version = session.scalar(select(m.DocumentVersion).join(m.Document, m.Document.id == m.DocumentVersion.document_id)
        .where(m.Document.thesis_id == item.thesis_id, m.DocumentVersion.stored_file_id == item.evidence_file_id)
        .limit(1)) if item.evidence_file_id else None
    file = session.get(m.StoredFile, item.evidence_file_id) if item.evidence_file_id else None
    return ProgressOut(id=item.id, milestone_id=item.milestone_id, version_no=item.version_no,
        row_version=item.row_version, state=item.state, summary=item.summary, reported_ratio=item.reported_ratio,
        submitted_by_name=session.get(m.StudentProfile, item.submitted_by).display_name,
        submitted_by_student_id=item.submitted_by, submitted_at=item.created_at,
        due_at_at_submission=item.due_at_at_submission,
        late=bool(item.due_at_at_submission and item.created_at > item.due_at_at_submission),
        evidence_document_version_id=version.id if version else None,
        evidence_scan_state=file.scan_state if file else None,
        evidence_file_name=file.original_name if file else None,
        reviews=[ReviewOut(reviewer_name=session.get(m.LecturerProfile, review.reviewer_id).display_name,
            decision=review.decision, comment=review.comment, created_at=review.created_at) for review in reviews])


def create_progress(session, user, thesis_id, data, *, commit=True):
    thesis = thesis_access(session, user, thesis_id, action="progress:submit", lock=True, write=True)
    milestone = session.scalar(select(m.ProgressMilestone).where(m.ProgressMilestone.id == data.milestone_id,
        m.ProgressMilestone.round_id == thesis.round_id, milestone_scope(thesis)).with_for_update())
    if not milestone:
        raise HTTPException(409, "Mốc không thuộc đợt khóa luận này")
    latest = session.scalar(select(m.ProgressReport).where(m.ProgressReport.thesis_id == thesis.id,
        m.ProgressReport.milestone_id == milestone.id).order_by(m.ProgressReport.version_no.desc()).limit(1))
    current_time = now()
    revision_requested = latest is not None and latest.state == "REVISION_REQUIRED"
    if not revision_requested and milestone.state != "OPEN":
        raise HTTPException(409, "Mốc đã đóng; chỉ được nộp lại khi GVHD yêu cầu sửa")
    if latest and not revision_requested:
        reviewed = session.scalar(select(m.ProgressReview.id).where(
            m.ProgressReview.progress_report_id == latest.id).limit(1)) is not None
        if (latest.state != "SUBMITTED" or reviewed or not milestone.due_at or
                current_time > milestone.due_at):
            raise HTTPException(409, "Chỉ tự nộp bản sửa trước hạn khi GVHD chưa phản hồi; sau đó cần yêu cầu sửa")
        latest.row_version += 1
    file_id = None
    if data.document_version_id:
        version = session.scalar(select(m.DocumentVersion).join(m.Document, m.Document.id == m.DocumentVersion.document_id)
            .where(m.DocumentVersion.id == data.document_version_id, m.Document.thesis_id == thesis.id,
                m.Document.state == "ACTIVE", m.DocumentVersion.state != "DRAFT"))
        file = session.get(m.StoredFile, version.stored_file_id) if version else None
        if not file:
            raise HTTPException(422, "Minh chứng phải là phiên bản tài liệu hợp lệ của khóa luận này")
        require_clean(file, "dùng làm minh chứng")
        file_id = file.id
    student = profile(session, user, "STUDENT")
    item = m.ProgressReport(id=uuid4(), thesis_id=thesis.id, milestone_id=milestone.id,
        version_no=latest.version_no + 1 if latest else 1, summary=data.summary,
        reported_ratio=data.reported_ratio, submitted_by=student.id, evidence_file_id=file_id,
        due_at_at_submission=milestone.due_at, created_at=current_time, state="SUBMITTED")
    session.add(item)
    audit(session, user, "PROGRESS_SELF_CORRECTED" if latest and not revision_requested else "PROGRESS_SUBMITTED",
        "thesis", thesis.id, f"{milestone.code}; version={item.version_no}")
    session.flush()
    from backend.services.notifications import notify_thesis_advisor

    notify_thesis_advisor(session, thesis=thesis, actor_user_id=user.id, kind="PROGRESS_SUBMITTED",
        message=f"{student.display_name} đã nộp báo cáo tiến độ mốc {milestone.code} (lần {item.version_no}).")
    result = progress_out(session, item)
    if commit:
        session.commit()
    return result


async def attach_evidence(session, user, thesis_id, report_id, request, expected, *, submitted_upload=None):
    """Attach a local file to an already submitted report without changing its submission time."""
    path = None
    try:
        thesis = thesis_access(session, user, thesis_id, action="progress:submit", lock=True, write=True)
        student = profile(session, user, "STUDENT")
        report = session.scalar(select(m.ProgressReport).where(m.ProgressReport.id == report_id,
            m.ProgressReport.thesis_id == thesis.id).with_for_update())
        if not report:
            raise HTTPException(404, "Không tìm thấy báo cáo")
        row_version(expected, report.row_version)
        if report.submitted_by != student.id:
            raise HTTPException(403, "Chỉ người nộp được thêm minh chứng cho báo cáo này")
        if report.state != "SUBMITTED" or report.evidence_file_id:
            raise HTTPException(409, "Báo cáo đã được xử lý hoặc đã có minh chứng")
        latest = session.scalar(select(func.max(m.ProgressReport.version_no)).where(
            m.ProgressReport.thesis_id == thesis.id, m.ProgressReport.milestone_id == report.milestone_id))
        if report.version_no != latest:
            raise HTTPException(409, "Chỉ được thêm minh chứng cho phiên bản báo cáo mới nhất")
        if session.scalar(select(m.ProgressReview.id).where(m.ProgressReview.progress_report_id == report.id).limit(1)):
            raise HTTPException(409, "Báo cáo đã được nhận xét; không thể thêm minh chứng")
        milestone = session.get(m.ProgressMilestone, report.milestone_id)
        if not milestone or (submitted_upload is None and
                (milestone.state != "OPEN" or not milestone.due_at or now() > milestone.due_at)):
            raise HTTPException(409, "Đã hết hạn thêm minh chứng; cần GVHD yêu cầu sửa để nộp phiên bản mới")
        name, content, mime = submitted_upload if submitted_upload is not None else await documents.read_upload(request)
        file, digest, path = documents.persist_upload(session, name, content, mime)
        documents.file_scanner.scan(file, path)
        item = m.Document(id=uuid4(), thesis_id=thesis.id,
            title=f"Minh chứng tiến độ {milestone.code} · lần {report.version_no}",
            document_type="SUPPORTING", visibility="ASSIGNED", state="ACTIVE")
        session.add(item)
        session.flush()
        version = m.DocumentVersion(id=uuid4(), document_id=item.id, version_no=1,
            stored_file_id=file.id, submitted_by=student.id, submitted_at=now(),
            due_at_at_submission=milestone.due_at, content_sha256=digest, state="SUBMITTED")
        session.add(version)
        report.evidence_file_id = file.id
        report.row_version += 1
        audit(session, user, "PROGRESS_EVIDENCE_UPLOADED", "thesis", thesis.id,
            f"Báo cáo {report.id}; tệp {name}; SHA-256 {digest}")
        session.flush()
        result = progress_out(session, report)
        session.commit()
        return result
    except Exception:
        session.rollback()
        if path and path.is_file():
            try:
                path.unlink()
            except OSError:
                pass
        raise


async def create_progress_with_evidence(session, user, thesis_id, data, upload):
    """The report and its optional file are submitted once, including a permitted late/revision submission."""
    try:
        created = create_progress(session, user, thesis_id, data, commit=False)
        return await attach_evidence(session, user, thesis_id, created.id, None, created.row_version,
                                     submitted_upload=upload)
    except Exception:
        session.rollback()
        raise


def evidence_version(session, user, thesis_id, report_id, *, write=False):
    thesis_access(session, user, thesis_id, action="progress:view", write=write, lock=write)
    report = session.scalar(select(m.ProgressReport).where(m.ProgressReport.id == report_id,
        m.ProgressReport.thesis_id == thesis_id))
    version = session.scalar(select(m.DocumentVersion).join(m.Document,
        m.Document.id == m.DocumentVersion.document_id).where(m.Document.thesis_id == thesis_id,
            m.DocumentVersion.stored_file_id == report.evidence_file_id)) if report and report.evidence_file_id else None
    if version is None:
        raise HTTPException(404, "Không tìm thấy minh chứng của báo cáo")
    return version


def download_evidence(session, user, thesis_id, report_id):
    version = evidence_version(session, user, thesis_id, report_id)
    return documents.stored_download(session, version)


def rescan_evidence(session, user, thesis_id, report_id):
    version = evidence_version(session, user, thesis_id, report_id, write=True)
    file = session.get(m.StoredFile, version.stored_file_id)
    if file.scan_state == "INFECTED":
        raise HTTPException(409, "Tệp nhiễm mã độc; cần yêu cầu nộp phiên bản mới")
    documents.file_scanner.require_available()
    state = documents.file_scanner.scan(file, documents.storage_root() / Path(file.storage_key).name)
    audit(session, user, "PROGRESS_EVIDENCE_SCANNED", "thesis", thesis_id, f"{report_id}: {state}")
    session.commit()
    return {"scan_state":state}


def review_progress(session, user, thesis_id, report_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, lock=True, write=True)
    permissions = rights(session, user, thesis)
    if data.decision == "COMMENT_ONLY" and "progress:comment" not in permissions:
        raise HTTPException(403, "Góp ý chéo cần phân công riêng; GVHD chính chọn xác nhận hoặc yêu cầu sửa")
    if "progress:review" not in permissions and not (data.decision == "COMMENT_ONLY" and "progress:comment" in permissions):
        raise HTTPException(403, "Chỉ GVHD chính được xác nhận/yêu cầu sửa; người góp ý chéo chỉ nhận xét")
    report = session.scalar(select(m.ProgressReport).where(m.ProgressReport.id == report_id,
        m.ProgressReport.thesis_id == thesis.id).with_for_update())
    if not report:
        raise HTTPException(404, "Không tìm thấy báo cáo")
    row_version(expected, report.row_version)
    latest = session.scalar(select(func.max(m.ProgressReport.version_no)).where(m.ProgressReport.thesis_id == thesis.id,
        m.ProgressReport.milestone_id == report.milestone_id))
    if report.version_no != latest or report.state != "SUBMITTED":
        raise HTTPException(409, "Chỉ nhận xét phiên bản mới nhất đang chờ duyệt")
    if data.decision == "CONFIRM" and report.evidence_file_id:
        require_clean(session.get(m.StoredFile, report.evidence_file_id), "xác nhận tiến độ")
    lecturer = profile(session, user, "LECTURER")
    if session.scalar(select(m.ProgressReview.id).where(m.ProgressReview.progress_report_id == report.id,
            m.ProgressReview.reviewer_id == lecturer.id)):
        raise HTTPException(409, "Bạn đã gửi nhận xét cho phiên bản này")
    from backend.services.progress_annotations import publish_annotations
    publish_annotations(session, report, lecturer, summary_comment=data.comment)
    session.add(m.ProgressReview(id=uuid4(), progress_report_id=report.id, reviewer_id=lecturer.id,
        decision=data.decision, comment=data.comment))
    if data.decision != "COMMENT_ONLY":
        report.state = "CONFIRMED" if data.decision == "CONFIRM" else "REVISION_REQUIRED"
    report.row_version += 1
    audit(session, user, "PROGRESS_" + data.decision, "thesis", thesis.id, data.comment)
    session.flush()
    from backend.services.notifications import notify_thesis_advisor, notify_thesis_students

    milestone = session.get(m.ProgressMilestone, report.milestone_id)
    milestone_label = f"{milestone.code} — {milestone.title}" if milestone else "tiến độ"
    if data.decision == "COMMENT_ONLY":
        message = f"{lecturer.display_name} đã góp ý báo cáo {milestone_label}: {data.comment[:200]}"
        notify_thesis_students(session, thesis=thesis, actor_user_id=user.id,
            kind="PROGRESS_COMMENT", message=message)
        notify_thesis_advisor(session, thesis=thesis, actor_user_id=user.id,
            kind="PROGRESS_COMMENT", message=message)
    else:
        decided = "xác nhận tiến độ" if data.decision == "CONFIRM" else "yêu cầu sửa và nộp lại"
        notify_thesis_students(session, thesis=thesis, actor_user_id=user.id,
            kind="PROGRESS_CONFIRMED" if data.decision == "CONFIRM" else "PROGRESS_REVISION_REQUIRED",
            message=f"GVHD {lecturer.display_name} đã {decided} báo cáo {milestone_label}. Nhận xét: {data.comment[:200]}")
    result = progress_out(session, report)
    session.commit()
    return result


def assign_cross_reviewer(session, user, thesis_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="progress:assign_reviewer", lock=True, write=True)
    row_version(expected, thesis.row_version)
    lecturer = eligible_lecturer(session, data.lecturer_id, thesis.department_id)
    from backend.services.theses import primary_advisor, resource_role
    advisor = primary_advisor(session, thesis.id)
    if advisor and advisor.lecturer_id == lecturer.id:
        raise HTTPException(422, "GVHD chính không đồng thời là người góp ý chéo")
    if resource_role(session, lecturer.user_id, "PROGRESS_REVIEWER", thesis_id=thesis.id):
        raise HTTPException(409, "Giảng viên đã được phân công góp ý chéo")
    session.add(m.ResourceAssignment(id=uuid4(), user_id=lecturer.user_id, thesis_id=thesis.id,
        assignment_type="PROGRESS_REVIEWER", state="ACTIVE", effective_from=now()))
    thesis.row_version += 1
    audit(session, user, "PROGRESS_REVIEWER_ASSIGNED", "thesis", thesis.id, f"{lecturer.lecturer_code}: {data.reason}")
    session.flush()
    from backend.services.notifications import notify_user

    notify_user(session, recipient_user_id=lecturer.user_id, actor_user_id=user.id,
        kind="PROGRESS_REVIEWER_ASSIGNED",
        message=(f"Bạn được phân công góp ý chéo tiến độ khóa luận {thesis.current_title}. "
                 f"Lý do: {data.reason[:200]}"),
        url=f"/theses/{thesis.id}?section=progress")
    session.commit()


def work_out(session, item):
    member = session.get(m.ThesisMember, item.thesis_member_id)
    student = session.get(m.StudentProfile, member.student_id)
    return WorkOut(id=item.id, student_id=student.id, student_name=student.display_name,
        version_no=item.version_no, row_version=item.row_version, work_description=item.work_description,
        expected_output=item.expected_output, state=item.state, review_comment=item.review_comment,
        reviewed_by_name=session.get(m.LecturerProfile, item.reviewed_by).display_name if item.reviewed_by else None)


def revoke_cross_reviewer(session, user, thesis_id, lecturer_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="progress:assign_reviewer", lock=True, write=True)
    row_version(expected, thesis.row_version)
    lecturer = session.get(m.LecturerProfile, lecturer_id)
    from backend.services.theses import resource_role
    assignment = resource_role(session, lecturer.user_id, "PROGRESS_REVIEWER", thesis_id=thesis.id) if lecturer else None
    if not assignment:
        raise HTTPException(404, "Không tìm thấy phân công góp ý chéo")
    assignment.state = "REVOKED"
    assignment.effective_to = now()
    thesis.row_version += 1
    audit(session, user, "PROGRESS_REVIEWER_REVOKED", "thesis", thesis.id, f"{lecturer.lecturer_code}: {data.reason}")
    session.commit()


def create_work(session, user, thesis_id, data):
    thesis = thesis_access(session, user, thesis_id, action="work:submit", lock=True, write=True)
    student = profile(session, user, "STUDENT")
    member = session.scalar(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.student_id == data.student_id, m.ThesisMember.active.is_(True)))
    coordinator = session.scalar(select(m.ThesisMember.id).where(m.ThesisMember.thesis_id == thesis.id,
        m.ThesisMember.student_id == student.id, m.ThesisMember.active.is_(True), m.ThesisMember.is_coordinator.is_(True)))
    if not member or (data.student_id != student.id and not coordinator):
        raise HTTPException(403, "Chỉ khai phần việc của mình hoặc nhóm trưởng khai cho thành viên đang hoạt động")
    latest = session.scalar(select(m.MemberWorkAssignment).where(m.MemberWorkAssignment.thesis_member_id == member.id)
        .order_by(m.MemberWorkAssignment.version_no.desc()).limit(1))
    if latest and latest.state == "SUBMITTED":
        raise HTTPException(409, "Phân công trước đang chờ GVHD duyệt")
    item = m.MemberWorkAssignment(id=uuid4(), thesis_member_id=member.id,
        version_no=latest.version_no + 1 if latest else 1, work_description=data.work_description,
        expected_output=data.expected_output, state="SUBMITTED")
    session.add(item)
    audit(session, user, "WORK_SUBMITTED", "thesis", thesis.id, student.student_code)
    session.flush()
    from backend.services.notifications import notify_thesis_advisor

    member_student = session.get(m.StudentProfile, member.student_id)
    notify_thesis_advisor(session, thesis=thesis, actor_user_id=user.id, kind="WORK_SUBMITTED",
        message=f"{student.display_name} đã gửi phân công công việc cho {member_student.display_name}.",
        section="progress")
    result = work_out(session, item)
    session.commit()
    return result


def review_work(session, user, thesis_id, work_id, data, expected):
    thesis = thesis_access(session, user, thesis_id, action="work:review", lock=True, write=True)
    item = session.scalar(select(m.MemberWorkAssignment).join(m.ThesisMember, m.ThesisMember.id == m.MemberWorkAssignment.thesis_member_id)
        .where(m.MemberWorkAssignment.id == work_id, m.ThesisMember.thesis_id == thesis.id).with_for_update())
    if not item:
        raise HTTPException(404, "Không tìm thấy phân công")
    row_version(expected, item.row_version)
    latest = session.scalar(select(func.max(m.MemberWorkAssignment.version_no)).where(m.MemberWorkAssignment.thesis_member_id == item.thesis_member_id))
    if item.state != "SUBMITTED" or item.version_no != latest:
        raise HTTPException(409, "Chỉ duyệt bản phân công mới nhất đang chờ")
    item.state = "APPROVED" if data.decision == "APPROVE" else "REVISION_REQUIRED"
    item.reviewed_by = profile(session, user, "LECTURER").id
    item.reviewed_at = now()
    item.review_comment = data.comment
    item.row_version += 1
    audit(session, user, "WORK_" + data.decision, "thesis", thesis.id, data.comment)
    session.flush()
    from backend.services.notifications import notify_user

    member = session.get(m.ThesisMember, item.thesis_member_id)
    member_student = session.get(m.StudentProfile, member.student_id) if member else None
    if member_student is not None:
        notify_user(session, recipient_user_id=member_student.user_id, actor_user_id=user.id,
            kind="WORK_APPROVED" if data.decision == "APPROVE" else "WORK_REVISION_REQUIRED",
            message=(f"GVHD đã duyệt phân công công việc của bạn: {data.comment[:200]}"
                     if data.decision == "APPROVE" else
                     f"GVHD yêu cầu sửa phân công công việc: {data.comment[:200]}"),
            url=f"/theses/{thesis.id}")
    result = work_out(session, item)
    session.commit()
    return result
