"""NV5 implemented routes. Academic authority always comes from a scoped assignment."""
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.core_schemas import (
    AdvisorNomination, AdvisorResponse, AuditOut,
    DocumentCreate, DocumentDecision, DocumentOut, MilestoneClose, MilestoneCreate, MilestoneOut,
    ProgressCreate, ProgressDecision, ProgressOut, ProposalFinalization, ProposalOut,
    ProposalReviewCreate, ProposalSignedCopy, ThesisWorkspaceOut, WorkCreate, WorkDecision, WorkOut,
)
from backend.api.dependencies import current_user, get_session
from backend.db.models import entities as m
from backend.services import documents, progress, proposals, theses

router = APIRouter(prefix="/api/v1", tags=["NV5 core"])


def core_session(session: Session = Depends(get_session)):
    try:
        yield session
    except Exception:
        session.rollback()
        raise


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


@router.get("/theses/{thesis_id}/proposal/versions/{version_id}/download", response_class=FileResponse,
    responses={200: {"content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
def proposal_download(thesis_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return proposals.download_version(session, user, thesis_id, version_id)


@router.post("/theses/{thesis_id}/proposal/reviewers", response_model=ProposalOut)
def proposal_reviewer(thesis_id: UUID, data: AdvisorNomination,
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


@router.post("/theses/{thesis_id}/advisor-nomination", response_model=ThesisWorkspaceOut)
def nominate(thesis_id: UUID, data: AdvisorNomination, if_match: int = Header(alias="If-Match", ge=1),
        user=Depends(current_user), session=Depends(core_session)):
    return theses.nominate_advisor(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/advisor-response", response_model=ThesisWorkspaceOut)
def advisor_response(thesis_id: UUID, data: AdvisorResponse, if_match: int = Header(alias="If-Match", ge=1),
        user=Depends(current_user), session=Depends(core_session)):
    return theses.respond_advisor(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/progress-reviewers", status_code=204)
def cross_reviewer(thesis_id: UUID, data: AdvisorNomination, if_match: int = Header(alias="If-Match", ge=1),
        user=Depends(current_user), session=Depends(core_session)):
    progress.assign_cross_reviewer(session, user, thesis_id, data, if_match)


@router.get("/theses/{thesis_id}/milestones", response_model=list[MilestoneOut])
def milestones(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    thesis = theses.thesis_access(session, user, thesis_id)
    return [progress.milestone_out(item) for item in progress.milestones(session, thesis)]


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


@router.get("/theses/{thesis_id}/progress-reports", response_model=list[ProgressOut])
def reports(thesis_id: UUID, user=Depends(current_user), session=Depends(core_session)):
    theses.thesis_access(session, user, thesis_id, action="progress:view")
    rows = session.scalars(select(m.ProgressReport).where(m.ProgressReport.thesis_id == thesis_id)
        .order_by(m.ProgressReport.created_at.desc(), m.ProgressReport.version_no.desc())).all()
    return [progress.progress_out(session, item) for item in rows]


@router.post("/theses/{thesis_id}/progress-reports", response_model=ProgressOut, status_code=201)
def report_create(thesis_id: UUID, data: ProgressCreate, user=Depends(current_user), session=Depends(core_session)):
    return progress.create_progress(session, user, thesis_id, data)


@router.post("/theses/{thesis_id}/progress-reports/{report_id}/review", response_model=ProgressOut)
def report_review(thesis_id: UUID, report_id: UUID, data: ProgressDecision,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return progress.review_progress(session, user, thesis_id, report_id, data, if_match)


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
    return [documents.document_out(session, item) for item in rows]


@router.post("/theses/{thesis_id}/documents", response_model=DocumentOut, status_code=201)
def document_create(thesis_id: UUID, data: DocumentCreate, user=Depends(current_user), session=Depends(core_session)):
    return documents.create_document(session, user, thesis_id, data)


@router.post("/theses/{thesis_id}/documents/{document_id}/versions", response_model=DocumentOut, status_code=201,
    openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def document_upload(thesis_id: UUID, document_id: UUID, request: Request,
        if_match: int = Header(alias="If-Match", ge=1), x_file_name: str = Header(alias="X-File-Name"),
        user=Depends(current_user), session=Depends(core_session)):
    return await documents.upload_version(session, user, thesis_id, document_id, request, if_match)


@router.post("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/review", response_model=DocumentOut)
def document_review(thesis_id: UUID, document_id: UUID, version_id: UUID, data: DocumentDecision,
        if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(core_session)):
    return documents.review_version(session, user, thesis_id, document_id, version_id, data, if_match)


@router.get("/theses/{thesis_id}/documents/{document_id}/versions/{version_id}/download", response_class=FileResponse,
    responses={200: {"content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
def document_download(thesis_id: UUID, document_id: UUID, version_id: UUID,
        user=Depends(current_user), session=Depends(core_session)):
    return documents.download_version(session, user, thesis_id, document_id, version_id)


@router.get("/theses/{thesis_id}/audit", response_model=list[AuditOut])
def thesis_audit(thesis_id: UUID, limit: int = Query(default=50, ge=1, le=100),
        user=Depends(current_user), session=Depends(core_session)):
    theses.thesis_access(session, user, thesis_id, action="audit:view")
    rows = session.scalars(select(m.AuditEvent).where(m.AuditEvent.resource_type == "thesis", m.AuditEvent.resource_id == thesis_id)
        .order_by(m.AuditEvent.occurred_at.desc()).limit(limit)).all()
    def actor_name(item):
        for cls in (m.StudentProfile, m.LecturerProfile):
            profile = session.scalar(select(cls).where(cls.user_id == item.actor_id))
            if profile:
                return profile.display_name
        return "Hệ thống"
    return [AuditOut(action=item.action, actor_name=actor_name(item), reason=item.reason, occurred_at=item.occurred_at) for item in rows]
