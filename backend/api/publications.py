"""Publication evidence follows academic approval separately from document receipt."""
from decimal import Decimal
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from backend.api.dependencies import current_user
from backend.api.evaluation import transaction
from backend.services import publications as service

router = APIRouter(prefix="/api/v1/theses/{thesis_id}/publication-claims", tags=["Minh chứng điểm thưởng"])

class PublicationSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=5, max_length=300)
    venue: str = Field(min_length=3, max_length=300)
    reference: str = Field(min_length=5, max_length=500)
    contribution: str = Field(min_length=10, max_length=3000)
    student_ids: list[UUID] = Field(min_length=1, max_length=3)
    evidence_version_id: UUID

class PublicationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    outcome: Literal["CONFIRM", "REVISION_REQUIRED", "APPROVE", "REJECT"]
    reason: str = Field(min_length=5, max_length=1000)
    points: dict[UUID, Decimal] = Field(default_factory=dict)

@router.get("")
def listing(thesis_id: UUID, user=Depends(current_user), session=Depends(transaction)):
    return service.listing(session, user, thesis_id)

@router.post("", status_code=201)
def submit(thesis_id: UUID, data: PublicationSubmission, user=Depends(current_user), session=Depends(transaction)):
    return service.submit(session, user, thesis_id, data)

@router.post("/{identifier}/decision")
def decide(thesis_id: UUID, identifier: UUID, data: PublicationDecision, version: int = Header(alias="If-Match", ge=1),
           user=Depends(current_user), session=Depends(transaction)):
    return service.decide(session, user, thesis_id, identifier, version, data)
