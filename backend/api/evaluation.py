"""NV6 week-one review and defense eligibility API."""
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query, Request
from backend.api.dependencies import current_user, get_session
from backend.api.evaluation_schemas import ReviewerCreate, ReviewerDeadline, Reason, ReviewCreate, ReviewSave, ReviewSubmit, EligibilityCreate, PaperReceipt
from backend.services import evaluation as service

router = APIRouter(prefix="/api/v1", tags=["NV6 review and eligibility"])


def transaction(session=Depends(get_session)):
    try:
        yield session
    except Exception:
        session.rollback()
        raise


@router.get("/evaluations")
def listing(q: str = Query(default="", max_length=200), limit: int = Query(default=20, ge=1, le=100),
            offset: int = Query(default=0, ge=0), user=Depends(current_user), session=Depends(transaction)):
    return service.listing(session, user, q.strip(), limit, offset)


@router.get("/theses/{thesis_id}/evaluation")
def detail(thesis_id: UUID, user=Depends(current_user), session=Depends(transaction)):
    return service.workspace(session, user, thesis_id)


@router.post("/theses/{thesis_id}/evaluation/reviewers", status_code=201)
def assign(thesis_id: UUID, data: ReviewerCreate, if_match: int = Header(alias="If-Match", ge=1),
           user=Depends(current_user), session=Depends(transaction)):
    return service.assign(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/evaluation/reviewers/{assignment_id}/revoke")
def revoke(thesis_id: UUID, assignment_id: UUID, data: Reason, if_match: int = Header(alias="If-Match", ge=1),
           user=Depends(current_user), session=Depends(transaction)):
    return service.revoke(session, user, thesis_id, assignment_id, data, if_match)


@router.post("/theses/{thesis_id}/evaluation/reviews", status_code=201)
def create(thesis_id: UUID, data: ReviewCreate, if_match: int = Header(alias="If-Match", ge=1),
           user=Depends(current_user), session=Depends(transaction)):
    return service.create_review(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/evaluation/reviewers/{assignment_id}/deadline")
def deadline(thesis_id: UUID, assignment_id: UUID, data: ReviewerDeadline, if_match: int = Header(alias="If-Match", ge=1),
             user=Depends(current_user), session=Depends(transaction)):
    return service.update_deadline(session, user, thesis_id, assignment_id, data, if_match)


@router.put("/theses/{thesis_id}/evaluation/reviews/{review_id}")
def save(thesis_id: UUID, review_id: UUID, data: ReviewSave, if_match: int = Header(alias="If-Match", ge=1),
         user=Depends(current_user), session=Depends(transaction)):
    return service.save_review(session, user, thesis_id, review_id, data, if_match)


@router.post("/theses/{thesis_id}/evaluation/reviews/{review_id}/signed-copy", status_code=201,
    openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {
        "schema": {"type": "string", "format": "binary"}}}}})
async def upload(thesis_id: UUID, review_id: UUID, request: Request,
                 if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(transaction)):
    return await service.upload_signed(session, user, thesis_id, review_id, request, if_match)


@router.post("/theses/{thesis_id}/evaluation/reviews/{review_id}/scan")
def scan(thesis_id: UUID, review_id: UUID, if_match: int = Header(alias="If-Match", ge=1),
         user=Depends(current_user), session=Depends(transaction)):
    return service.scan_signed(session, user, thesis_id, review_id, if_match)


@router.post("/theses/{thesis_id}/evaluation/reviews/{review_id}/submit")
def submit(thesis_id: UUID, review_id: UUID, data: ReviewSubmit,
           if_match: int = Header(alias="If-Match", ge=1), user=Depends(current_user), session=Depends(transaction)):
    return service.submit_review(session, user, thesis_id, review_id, data, if_match)


@router.get("/theses/{thesis_id}/evaluation/reviews/{review_id}/signed-copy")
def download(thesis_id: UUID, review_id: UUID, user=Depends(current_user), session=Depends(transaction)):
    return service.signed_download(session, user, thesis_id, review_id)


@router.post("/theses/{thesis_id}/evaluation/reviews/{review_id}/print-copy")
def export(thesis_id: UUID, review_id: UUID, if_match: int = Header(alias="If-Match", ge=1),
           user=Depends(current_user), session=Depends(transaction)):
    from backend.services.review_form_export import export_review
    return export_review(session, user, thesis_id, review_id, if_match)


@router.get("/theses/{thesis_id}/evaluation/reports/{version_id}")
def report_download(thesis_id: UUID, version_id: UUID, user=Depends(current_user), session=Depends(transaction)):
    return service.report_download(session, user, thesis_id, version_id)


@router.post("/theses/{thesis_id}/evaluation/eligibility")
def eligibility(thesis_id: UUID, data: EligibilityCreate, if_match: int = Header(alias="If-Match", ge=1),
                user=Depends(current_user), session=Depends(transaction)):
    return service.check_eligibility(session, user, thesis_id, data, if_match)


@router.post("/theses/{thesis_id}/evaluation/reopen")
def reopen(thesis_id: UUID, data: Reason, if_match: int = Header(alias="If-Match", ge=1),
           user=Depends(current_user), session=Depends(transaction)):
    return service.reopen(session, user, thesis_id, data, if_match)

@router.post("/theses/{thesis_id}/evaluation/reviews/{review_id}/paper-receipt")
def paper_receipt(thesis_id: UUID,review_id: UUID,data:PaperReceipt,if_match:int=Header(alias="If-Match",ge=1),
                  user=Depends(current_user),session=Depends(transaction)):
    return service.record_paper(session,user,thesis_id,review_id,data,if_match)
