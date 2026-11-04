from uuid import UUID

from fastapi import APIRouter, Depends, Header

from backend.api.change_schemas import AdvisorReview, ChangeCreate, ExtensionRecord, FinalDecision, GroupConsent
from backend.api.dependencies import current_user
from backend.api.evaluation import transaction
from backend.services import thesis_changes as service

router = APIRouter(prefix="/api/v1", tags=["Đổi đề tài và gia hạn"])


@router.get("/thesis-changes")
def listing(user=Depends(current_user),session=Depends(transaction)):
    return service.workspace(session,user)


@router.post("/theses/{thesis_id}/change-requests",status_code=201)
def create(thesis_id:UUID,data:ChangeCreate,version:int=Header(alias="If-Match",ge=1),
           user=Depends(current_user),session=Depends(transaction)):
    return service.create(session,user,thesis_id,data,version)


@router.post("/thesis-changes/{identifier}/consent")
def consent(identifier:UUID,data:GroupConsent,version:int=Header(alias="If-Match",ge=1),
            user=Depends(current_user),session=Depends(transaction)):
    return service.consent(session,user,identifier,data,version)


@router.post("/thesis-changes/{identifier}/advisor-review")
def review(identifier:UUID,data:AdvisorReview,version:int=Header(alias="If-Match",ge=1),
           user=Depends(current_user),session=Depends(transaction)):
    return service.review(session,user,identifier,data,version)


@router.post("/thesis-changes/{identifier}/decision")
def decide(identifier:UUID,data:FinalDecision,version:int=Header(alias="If-Match",ge=1),
           user=Depends(current_user),session=Depends(transaction)):
    return service.decide(session,user,identifier,data,version)


@router.post("/thesis-changes/{identifier}/cancel")
def cancel(identifier:UUID,version:int=Header(alias="If-Match",ge=1),
           user=Depends(current_user),session=Depends(transaction)):
    return service.cancel(session,user,identifier,version)


@router.post("/theses/{thesis_id}/extension",status_code=201)
def extension(thesis_id:UUID,data:ExtensionRecord,version:int=Header(alias="If-Match",ge=1),
              user=Depends(current_user),session=Depends(transaction)):
    return service.record_extension(session,user,thesis_id,data,version)


@router.get("/theses/{thesis_id}/extension/evidence")
def extension_evidence(thesis_id:UUID,user=Depends(current_user),session=Depends(transaction)):
    return service.extension_download(session,user,thesis_id)
