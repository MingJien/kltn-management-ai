from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TopicOut(BaseModel):
    id: UUID
    round_id: UUID
    title: str
    description: str | None
    max_students: int
    state: str


class RegistrationCreate(BaseModel):
    topic_id: UUID
    member_student_ids: list[UUID] = Field(min_length=1, max_length=3)


class RegistrationMemberOut(BaseModel):
    student_id: UUID
    student_code: str
    display_name: str
    is_coordinator: bool
    active: bool
    consent_status: str


class MemberResponse(BaseModel):
    consent_status: Literal["ACCEPTED", "DECLINED"]


class RegistrationOut(BaseModel):
    id: UUID
    topic_id: UUID
    round_id: UUID
    state: str
    row_version: int
    member_student_ids: list[UUID]
    members: list[RegistrationMemberOut]
    lecturer_decided_at: datetime | None = None
    thesis_id: UUID | None = None


class LecturerDecision(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]
    reason: str | None = Field(default=None, max_length=2000)


class ContextOut(BaseModel):
    user_id: UUID
    base_role: str
    student_id: UUID | None = None
    lecturer_id: UUID | None = None
    actions: list[str]


class ErrorOut(BaseModel):
    detail: str


class HealthOut(BaseModel):
    status: str


class SimilarTopicRequest(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    abstract: str | None = Field(default=None, max_length=5000)
    keywords: list[str] = Field(default_factory=list)
    domain: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    source_id: str
    source_type: str
    origin_type: str
    title: str
    score: float
    provenance: str
    source_ref: str | None
    source_url: str | None
    source_version: str
    representation: str
    excerpt: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class Citation(BaseModel):
    source_id: str
    source_type: str
    origin_type: str
    title: str
    provenance: str
    source_ref: str | None
    source_url: str | None
    source_version: str
    representation: str
    excerpt: str


class ChatOut(BaseModel):
    status: Literal["NO_EVIDENCE", "RETRIEVAL_ONLY", "ANSWERED"]
    answer: str | None
    citations: list[Citation]
    provider_status: Literal["NOT_CONFIGURED"] = "NOT_CONFIGURED"


class EligibleStudentOut(BaseModel):
    id: UUID
    display_name: str
    student_code: str


class ThesisOut(BaseModel):
    id: UUID
    title: str
    state: str
    member_student_ids: list[UUID]
    advisor_lecturer_id: UUID
