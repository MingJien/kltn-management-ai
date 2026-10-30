"""NV5 implemented routes. Academic authority always comes from a scoped assignment."""
from uuid import UUID
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, UploadFile, File, Form
from pydantic import ValidationError
from fastapi.responses import FileResponse, Response
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.api.core_schemas import (
    AuditOut, LecturerAssignment,
    RegistrationFormsOut, PrintExportOut,
    DocumentCreate, DocumentDecision, DocumentOut, DocumentWithdraw, DocumentDeadlineOut, DocumentDeadlineSet, DocumentDeadlineClose, MilestoneClose, MilestoneCreate, MilestoneExtend, MilestoneOut,
    ProgressCreate, ProgressDecision, ProgressOut, ProgressAnnotationSave, ProgressAnnotationOut, ProgressAnnotationsOut, ProposalFinalization, ProposalOut,
    ProposalReviewCreate, ProposalSignedCopy, ThesisWorkspaceOut, WorkCreate, WorkDecision, WorkOut,
)
from backend.api.dependencies import current_user, get_session
from backend.db.models import entities as m
from backend.services import school_forms, deadlines, documents, progress, progress_annotations, proposals, theses, registration_forms
from backend.services.proposal_export import export_document, export_proposal, document_print_history, proposal_print_history
from backend.services.form_templates import list_official_templates, official_template, official_template_by_id, allowed_form

router = APIRouter(prefix="/api/v1", tags=["NV5 core"])


@router.get("/form-templates")
def get_form_templates(round_id: UUID | None = None, user=Depends(current_user), session=Depends(get_session)):
    return school_forms.compatibility_list(session,user,round_id)


@router.get("/form-templates/{template_id}/download")
def download_official_template(template_id: str, round_id: UUID | None = None, user=Depends(current_user), session=Depends(get_session)):
    managed=school_forms.compatibility_download(session,user,template_id,round_id)
    if managed is not None:return managed
    content, filename, media_type = official_template_by_id(template_id, user.base_role)
    return Response(
        content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=official-form{'.xlsx' if filename.endswith('.xlsx') else '.docx'}; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/form-templates/plan")
def plan_template(round_id: UUID | None = None, user=Depends(current_user), session=Depends(get_session)):
    managed=school_forms.compatibility_download(session,user,"plan",round_id)
    if managed is not None:return managed
    allowed_form({"id": "mau-02"}, user.base_role)
    return Response(official_template("plan"),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="mau-02-ke-hoach.docx"',
                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/form-templates/proposal")
def proposal_template(round_id: UUID | None = None, user=Depends(current_user), session=Depends(get_session)):
    managed=school_forms.compatibility_download(session,user,"proposal",round_id)
    if managed is not None:return managed
    allowed_form({"id": "mau-03"}, user.base_role)
    return Response(official_template("proposal"),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="mau-03-de-cuong.docx"',
                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


def core_session(session: Session = Depends(get_session)):
    try:
        yield session
    except Exception:
        session.rollback()
        raise


def _actor_name(session, item):
    for cls in (m.StudentProfile, m.LecturerProfile):
        profile = session.scalar(select(cls).where(cls.user_id == item.actor_id))
        if profile:
            return profile.display_name
    return "Hệ thống"


@router.get("/topic-registrations/{registration_id}/forms", response_model=RegistrationFormsOut)
def registration_form_list(registration_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return registration_forms.listing(session, user, registration_id)


@router.post("/topic-registrations/{registration_id}/forms", status_code=201, response_model=RegistrationFormsOut,
    openapi_extra={"requestBody":{"required":True,"content":{"application/octet-stream":{"schema":{"type":"string","format":"binary"}}}}})
async def registration_form_upload(registration_id: UUID, request: Request,
        form_code: Literal["1A", "1B"] = Header(alias="X-Form-Code"),
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return await registration_forms.upload(session, user, registration_id, request, if_match)


@router.get("/topic-registrations/{registration_id}/forms/{version_id}/download")
def registration_form_download(registration_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return registration_forms.download(session, user, registration_id, version_id)


@router.post("/topic-registrations/{registration_id}/forms/{version_id}/scan", response_model=RegistrationFormsOut)
def registration_form_scan(registration_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return registration_forms.rescan(session, user, registration_id, version_id)


@router.post("/topic-registrations/{registration_id}/forms/{version_id}/print-copy")
def registration_form_print(registration_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return registration_forms.print_copy(session, user, registration_id, version_id)


@router.get("/topic-registrations/{registration_id}/forms/{version_id}/print-history", response_model=list[PrintExportOut])
def registration_form_print_history(registration_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return registration_forms.print_history(session, user, registration_id, version_id)


@router.get("/theses", response_model=list[ThesisWorkspaceOut])
def list_theses(user=Depends(current_user), session=Depends(core_session)):
    return theses.list_theses(session, user)


@router.get("/theses/{thesis_id}", response_model=ThesisWorkspaceOut)
def thesis_detail(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return theses.workspace_out(session, user, theses.thesis_access(session, user, thesis_id))


@router.get("/theses/{thesis_id}/proposal", response_model=ProposalOut)
def proposal_detail(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return proposals.get_proposal(session, user, thesis_id)


@router.post("/theses/{thesis_id}/proposal/versions", response_model=ProposalOut, status_code=201,
    openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def proposal_upload(thesis_id: UUID, request: Request,
        if_match: int = Header(alias="If-Match", ge=0), x_file_name: str = Header(alias="X-File-Name"),
        user=Depends(current_user), session=Depends(core_session)):
    return await proposals.upload_version(session, user, thesis_id, request, if_match)


@router.post("/theses/{thesis_id}/proposal/versions/{version_id}/scan", response_model=ProposalOut)
def proposal_scan(thesis_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return proposals.rescan_version(session, user, thesis_id, version_id)


@router.get("/theses/{thesis_id}/proposal/versions/{version_id}/download", response_class=FileResponse,
    responses={200: {"content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
def proposal_download(thesis_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return proposals.download_version(session, user, thesis_id, version_id)


@router.post("/theses/{thesis_id}/proposal/versions/{version_id}/print-copy",
    responses={200: {"content": {"application/pdf": {},
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}}}})
def proposal_print_copy(thesis_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return export_proposal(session, user, thesis_id, version_id)


@router.get("/theses/{thesis_id}/proposal/versions/{version_id}/print-history", response_model=list[PrintExportOut])
def proposal_export_history(thesis_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return proposal_print_history(session, user, thesis_id, version_id)


@router.post("/theses/{thesis_id}/proposal/reviewers", response_model=ProposalOut)
def proposal_reviewer(thesis_id: UUID, data: LecturerAssignment,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return proposals.assign_reviewer(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/proposal/reviews", response_model=ProposalOut)
def proposal_review(thesis_id: UUID, data: ProposalReviewCreate,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return proposals.review(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/proposal/department-finalization", response_model=ProposalOut)
def proposal_finalize(thesis_id: UUID, data: ProposalFinalization,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return proposals.finalize(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/proposal/dean-signed-copy", response_model=ProposalOut)
def proposal_dean_copy(thesis_id: UUID, data: ProposalSignedCopy,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return proposals.record_dean_confirmation(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/progress-reviewers", status_code=204)
def cross_reviewer(thesis_id: UUID, data: LecturerAssignment, if_match: int = Header(alias="If-Match", ge=1),
        user=Depends(current_user), session=Depends(core_session)):
    progress.assign_cross_reviewer(session, user, thesis_id, data, if_match)


@router.get("/theses/{thesis_id}/milestones", response_model=list[MilestoneOut])
def milestones(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    thesis = theses.thesis_access(session, user, thesis_id)
    return [progress.milestone_out(item) for item in progress.milestones(session, thesis)]


@router.get("/theses/{thesis_id}/document-deadlines", response_model=list[DocumentDeadlineOut])
def document_deadlines(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return deadlines.list_for_thesis(session, user, thesis_id)


@router.post("/theses/{thesis_id}/document-deadlines", response_model=DocumentDeadlineOut)
def document_deadline_set(thesis_id: UUID, data: DocumentDeadlineSet,
        if_match: int | None = Header(default=None, alias="If-Match", ge=1),
        user=Depends(current_user), session=Depends(core_session)):
    return deadlines.set_deadline(session, user, thesis_id, data, if_match)


@router.get("/theses/{thesis_id}/document-deadline-history", response_model=list[AuditOut])
def document_deadline_history(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    thesis = theses.thesis_access(session, user, thesis_id)
    identifiers = select(m.DocumentDeadline.id).where(m.DocumentDeadline.round_id == thesis.round_id)
    rows = session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_type == "document_deadline",
        m.AuditEvent.resource_id.in_(identifiers),
        m.AuditEvent.action.in_(["DOCUMENT_DEADLINE_SET","DOCUMENT_DEADLINE_EXTENDED","DOCUMENT_DEADLINE_REOPENED","DOCUMENT_DEADLINE_CLOSED"]))
        .order_by(m.AuditEvent.occurred_at.desc()).limit(100)).all()
    return [AuditOut(action=item.action, actor_name=_actor_name(session, item), reason=item.reason, occurred_at=item.occurred_at) for item in rows]


@router.post("/theses/{thesis_id}/document-deadlines/{document_type}/close", response_model=DocumentDeadlineOut)
def document_deadline_close(thesis_id: UUID, document_type: str, data: DocumentDeadlineClose,
        if_match: int = Header(alias="If-Match", ge=1),
        user=Depends(current_user), session=Depends(core_session)):
    if document_type not in {"PROPOSAL", "PLAN", "REPORT", "SUPPORTING"}:
        raise HTTPException(422, "Loại tài liệu không hợp lệ")
    return deadlines.close_deadline(session, user, thesis_id, document_type, data.reason, if_match)


@router.post("/theses/{thesis_id}/progress-reviewers/{lecturer_id}/revoke", status_code=204)
def cross_reviewer_revoke(thesis_id: UUID, lecturer_id: UUID, data: MilestoneClose,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    progress.revoke_cross_reviewer(session, user, thesis_id, lecturer_id, data, if_match)


@router.post("/theses/{thesis_id}/milestones", response_model=MilestoneOut, status_code=201)
def milestone_create(thesis_id: UUID, data: MilestoneCreate, user=Depends(current_user), session=Depends(core_session)):
    return progress.create_milestone(session, user, thesis_id, data)


@router.post("/theses/{thesis_id}/milestones/{milestone_id}/close", response_model=MilestoneOut)
def milestone_close(thesis_id: UUID, milestone_id: UUID, data: MilestoneClose,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return progress.close_milestone(session, user, thesis_id, milestone_id, data, if_match)


@router.post("/theses/{thesis_id}/milestones/{milestone_id}/extend", response_model=MilestoneOut)
def milestone_extend(thesis_id: UUID, milestone_id: UUID, data: MilestoneExtend,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return progress.extend_milestone(session, user, thesis_id, milestone_id, data, if_match)


@router.get("/theses/{thesis_id}/progress-reports", response_model=list[ProgressOut])
def reports(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    theses.thesis_access(session, user, thesis_id, action="progress:view")
    rows = session.scalars(select(m.ProgressReport).where(m.ProgressReport.thesis_id == thesis_id)
        .order_by(m.ProgressReport.created_at.desc(), m.ProgressReport.version_no.desc())).all()
    return [progress.progress_out(session, item) for item in rows]


@router.post("/theses/{thesis_id}/progress-reports", response_model=ProgressOut, status_code=201)
def report_create(thesis_id: UUID, data: ProgressCreate, user=Depends(current_user), session=Depends(core_session)):
    return progress.create_progress(session, user, thesis_id, data)


@router.post("/theses/{thesis_id}/progress-reports/{report_id}/evidence", response_model=ProgressOut,
    openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def report_evidence(thesis_id: UUID, report_id: UUID, request: Request,
        if_match: int = Header(alias="If-Match", ge=1), x_file_name: str = Header(alias="X-File-Name"),
        user=Depends(current_user), session=Depends(core_session)):
    return await progress.attach_evidence(session, user, thesis_id, report_id, request, if_match)


@router.post("/theses/{thesis_id}/progress-submissions", response_model=ProgressOut, status_code=201)
async def report_with_file(thesis_id: UUID, report: str = Form(max_length=20000),
        file: UploadFile = File(), user=Depends(current_user), session=Depends(core_session)):
    """Submit text and file atomically; retains the JSON-only report endpoint."""
    try:
        try:
            data = ProgressCreate.model_validate_json(report)
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        name = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
        if not name or len(name) > 180 or any(ord(c) < 32 for c in name):
            raise HTTPException(422, "Tên tệp không hợp lệ")
        content = await file.read(documents.MAX_BYTES + 1)
        if len(content) > documents.MAX_BYTES:
            raise HTTPException(413, "Tệp tối đa 10 MB")
        mime = documents.valid_content(name, content)
        return await progress.create_progress_with_evidence(session, user, thesis_id, data, (name, content, mime))
    finally:
        await file.close()


@router.get("/theses/{thesis_id}/progress-reports/{report_id}/evidence", response_class=FileResponse)
def report_file(thesis_id: UUID, report_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return progress.download_evidence(session, user, thesis_id, report_id)


@router.post("/theses/{thesis_id}/progress-reports/{report_id}/evidence/scan")
def report_file_scan(thesis_id: UUID, report_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return progress.rescan_evidence(session, user, thesis_id, report_id)


@router.post("/theses/{thesis_id}/progress-reports/{report_id}/review", response_model=ProgressOut)
def report_review(thesis_id: UUID, report_id: UUID, data: ProgressDecision,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return progress.review_progress(session, user, thesis_id, report_id, data, if_match)


@router.get("/theses/{thesis_id}/progress-reports/{report_id}/annotations", response_model=ProgressAnnotationsOut)
def report_annotations(thesis_id: UUID, report_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.list_annotations(session, user, thesis_id, report_id)


@router.put("/theses/{thesis_id}/progress-reports/{report_id}/annotations/{annotation_id}", response_model=ProgressAnnotationOut)
def report_annotation_save(thesis_id: UUID, report_id: UUID, annotation_id: UUID, data: ProgressAnnotationSave,
        if_match: int = Header(alias="If-Match", ge=0), user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.save_annotation(session, user, thesis_id, report_id, annotation_id, data, if_match)


@router.delete("/theses/{thesis_id}/progress-reports/{report_id}/annotations/{annotation_id}", status_code=204)
def report_annotation_delete(thesis_id: UUID, report_id: UUID, annotation_id: UUID,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    progress_annotations.delete_annotation(session, user, thesis_id, report_id, annotation_id, if_match)


@router.get("/theses/{thesis_id}/work-assignments", response_model=list[WorkOut])
def work(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    theses.thesis_access(session, user, thesis_id, action="work:view")
    rows = session.scalars(select(m.MemberWorkAssignment).join(m.ThesisMember, m.ThesisMember.id == m.MemberWorkAssignment.thesis_member_id)
        .where(m.ThesisMember.thesis_id == thesis_id).order_by(m.MemberWorkAssignment.created_at.desc(), m.MemberWorkAssignment.version_no.desc())).all()
    return [progress.work_out(session, item) for item in rows]


@router.post("/theses/{thesis_id}/work-assignments", response_model=WorkOut, status_code=201)
def work_create(thesis_id: UUID, data: WorkCreate, user=Depends(current_user), session=Depends(core_session)):
    return progress.create_work(session, user, thesis_id, data)


@router.post("/theses/{thesis_id}/work-assignments/{work_id}/review", response_model=WorkOut)
def work_review(thesis_id: UUID, work_id: UUID, data: WorkDecision,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return progress.review_work(session, user, thesis_id, work_id, data, if_match)


@router.get("/theses/{thesis_id}/documents", response_model=list[DocumentOut])
def docs(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    theses.thesis_access(session, user, thesis_id, action="document:view")
    rows = session.scalars(select(m.Document).where(m.Document.thesis_id == thesis_id,
        m.Document.state == "ACTIVE", m.Document.visibility == "ASSIGNED").order_by(m.Document.created_at, m.Document.id)).all()
    return [documents.document_out(session, item) for item in rows if "progress:view" in theses.rights(session,user,session.get(m.Thesis,thesis_id)) or not documents.is_progress_evidence(session,item.id)]


@router.post("/theses/{thesis_id}/documents", response_model=DocumentOut, status_code=201)
def document_create(thesis_id: UUID, data: DocumentCreate, user=Depends(current_user), session=Depends(core_session)):
    return documents.create_document(session, user, thesis_id, data)


@router.post("/theses/{thesis_id}/documents/{document_id}/withdraw", status_code=204)
def document_withdraw(thesis_id: UUID, document_id: UUID, data: DocumentWithdraw,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    documents.withdraw_document(session, user, thesis_id, document_id, data, if_match)


@router.post("/theses/{thesis_id}/documents/{document_id}/versions", response_model=DocumentOut, status_code=201,
    openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def document_upload(thesis_id: UUID, document_id: UUID, request: Request,
        if_match: int = Header(alias="If-Match", ge=1), x_file_name: str = Header(alias="X-File-Name"),
        user=Depends(current_user), session=Depends(core_session)):
    return await documents.upload_version(session, user, thesis_id, document_id, request, if_match)


@router.post("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/scan", response_model=DocumentOut)
def document_scan(thesis_id: UUID, document_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return documents.rescan_version(session, user, thesis_id, document_id, version_id)


@router.post("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/review", response_model=DocumentOut)
def document_review(thesis_id: UUID, document_id: UUID, version_id: UUID, data: DocumentDecision,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return documents.review_version(session, user, thesis_id, document_id, version_id, data, if_match)


@router.get("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/download", response_class=FileResponse,
    responses={200: {"content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
def document_download(thesis_id: UUID, document_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return documents.download_version(session, user, thesis_id, document_id, version_id)


@router.post("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/print-copy",
    responses={200: {"content": {"application/pdf": {},
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}}}})
def document_print_copy(thesis_id: UUID, document_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return export_document(session, user, thesis_id, document_id, version_id)


@router.get("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/print-history", response_model=list[PrintExportOut])
def document_export_history(thesis_id: UUID, document_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return document_print_history(session, user, thesis_id, document_id, version_id)


@router.get("/theses/{thesis_id}/milestone-history", response_model=list[AuditOut])
def milestone_history(thesis_id: UUID, limit: int = Query(default=50, ge=1, le=100),
        user=Depends(current_user), session=Depends(core_session)):
    thesis = theses.thesis_access(session, user, thesis_id)
    rows = session.scalars(select(m.AuditEvent).where(
        m.AuditEvent.resource_type == "round", m.AuditEvent.resource_id == thesis.round_id,
        m.AuditEvent.action.in_(["MILESTONE_OPENED", "MILESTONE_EXTENDED", "MILESTONE_REOPENED", "MILESTONE_CLOSED"]),
    ).order_by(m.AuditEvent.occurred_at.desc()).limit(limit)).all()
    return [AuditOut(action=item.action, actor_name=_actor_name(session, item), reason=item.reason,
        occurred_at=item.occurred_at) for item in rows]


@router.get("/theses/{thesis_id}/audit", response_model=list[AuditOut])
def thesis_audit(thesis_id: UUID, limit: int = Query(default=50, ge=1, le=100),
        user=Depends(current_user), session=Depends(core_session)):
    thesis = theses.thesis_access(session, user, thesis_id, action="audit:view")
    from backend.services.activity import progress_privacy
    rows = session.scalars(select(m.AuditEvent).where(or_(
        and_(m.AuditEvent.resource_type == "thesis", m.AuditEvent.resource_id == thesis_id),
        and_(m.AuditEvent.resource_type == "round", m.AuditEvent.resource_id == thesis.round_id,
             m.AuditEvent.action.in_(["MILESTONE_OPENED", "MILESTONE_EXTENDED", "MILESTONE_REOPENED", "MILESTONE_CLOSED"])),
    ),progress_privacy(session,user)).order_by(m.AuditEvent.occurred_at.desc()).limit(limit)).all()
    return [AuditOut(action=item.action, actor_name=_actor_name(session, item), reason=item.reason, occurred_at=item.occurred_at) for item in rows]


@router.get("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/annotations", response_model=ProgressAnnotationsOut)
def document_annotations(thesis_id: UUID, document_id: UUID, version_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.list_annotations(session, user, thesis_id, version_id, kind="document", document_id=document_id)


@router.put("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/annotations/{annotation_id}", response_model=ProgressAnnotationOut)
def document_annotation_save(thesis_id: UUID, document_id: UUID, version_id: UUID, annotation_id: UUID, data: ProgressAnnotationSave,
        if_match: int = Header(alias="If-Match", ge=0), user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.save_annotation(session, user, thesis_id, version_id, annotation_id, data, if_match, kind="document", document_id=document_id)


@router.delete("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/annotations/{annotation_id}", status_code=204)
def document_annotation_delete(thesis_id: UUID, document_id: UUID, version_id: UUID, annotation_id: UUID,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    progress_annotations.delete_annotation(session, user, thesis_id, version_id, annotation_id, if_match, kind="document", document_id=document_id)


@router.get("/theses/{thesis_id}/proposal/versions/{version_id}/annotations", response_model=ProgressAnnotationsOut)
def proposal_annotations(thesis_id: UUID, version_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.list_annotations(session, user, thesis_id, version_id, kind="proposal")


@router.put("/theses/{thesis_id}/proposal/versions/{version_id}/annotations/{annotation_id}", response_model=ProgressAnnotationOut)
def proposal_annotation_save(thesis_id: UUID, version_id: UUID, annotation_id: UUID, data: ProgressAnnotationSave,
        if_match: int = Header(alias="If-Match", ge=0), user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.save_annotation(session, user, thesis_id, version_id, annotation_id, data, if_match, kind="proposal")


@router.delete("/theses/{thesis_id}/proposal/versions/{version_id}/annotations/{annotation_id}", status_code=204)
def proposal_annotation_delete(thesis_id: UUID, version_id: UUID, annotation_id: UUID,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    progress_annotations.delete_annotation(session, user, thesis_id, version_id, annotation_id, if_match, kind="proposal")


@router.post("/theses/{thesis_id}/progress-reports/{version_id}/annotations/{annotation_id}/attachment", response_model=ProgressAnnotationOut, status_code=201)
async def progress_review_attachment_upload(thesis_id: UUID, version_id: UUID, annotation_id: UUID, request: Request,
        if_match: int = Header(alias="If-Match", ge=0), user=Depends(current_user), session=Depends(core_session)):
    return await progress_annotations.upload_attachment(session, user, thesis_id, version_id, annotation_id, request, if_match, kind="progress")


@router.get("/theses/{thesis_id}/progress-reports/{version_id}/annotations/{annotation_id}/attachment")
def progress_review_attachment_download(thesis_id: UUID, version_id: UUID, annotation_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.download_attachment(session, user, thesis_id, version_id, annotation_id, kind="progress")


@router.post("/theses/{thesis_id}/progress-reports/{version_id}/annotations/{annotation_id}/attachment/scan", response_model=ProgressAnnotationOut)
def progress_review_attachment_scan(thesis_id: UUID, version_id: UUID, annotation_id: UUID,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.rescan_attachment(session, user, thesis_id, version_id, annotation_id, if_match, kind="progress")


@router.post("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/annotations/{annotation_id}/attachment", response_model=ProgressAnnotationOut, status_code=201)
async def document_review_attachment_upload(thesis_id: UUID, document_id: UUID, version_id: UUID, annotation_id: UUID, request: Request,
        if_match: int = Header(alias="If-Match", ge=0), user=Depends(current_user), session=Depends(core_session)):
    return await progress_annotations.upload_attachment(session, user, thesis_id, version_id, annotation_id, request, if_match, kind="document", document_id=document_id)


@router.get("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/annotations/{annotation_id}/attachment")
def document_review_attachment_download(thesis_id: UUID, document_id: UUID, version_id: UUID, annotation_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.download_attachment(session, user, thesis_id, version_id, annotation_id, kind="document", document_id=document_id)


@router.post("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/annotations/{annotation_id}/attachment/scan", response_model=ProgressAnnotationOut)
def document_review_attachment_scan(thesis_id: UUID, document_id: UUID, version_id: UUID, annotation_id: UUID,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.rescan_attachment(session, user, thesis_id, version_id, annotation_id, if_match, kind="document", document_id=document_id)


@router.post("/theses/{thesis_id}/proposal/versions/{version_id}/annotations/{annotation_id}/attachment", response_model=ProgressAnnotationOut, status_code=201)
async def proposal_review_attachment_upload(thesis_id: UUID, version_id: UUID, annotation_id: UUID, request: Request,
        if_match: int = Header(alias="If-Match", ge=0), user=Depends(current_user), session=Depends(core_session)):
    return await progress_annotations.upload_attachment(session, user, thesis_id, version_id, annotation_id, request, if_match, kind="proposal")


@router.get("/theses/{thesis_id}/proposal/versions/{version_id}/annotations/{annotation_id}/attachment")
def proposal_review_attachment_download(thesis_id: UUID, version_id: UUID, annotation_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.download_attachment(session, user, thesis_id, version_id, annotation_id, kind="proposal")


@router.post("/theses/{thesis_id}/proposal/versions/{version_id}/annotations/{annotation_id}/attachment/scan", response_model=ProgressAnnotationOut)
def proposal_review_attachment_scan(thesis_id: UUID, version_id: UUID, annotation_id: UUID,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return progress_annotations.rescan_attachment(session, user, thesis_id, version_id, annotation_id, if_match, kind="proposal")
