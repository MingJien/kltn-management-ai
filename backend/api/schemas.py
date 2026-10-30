from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RequirementInput(BaseModel):
    requirement_type: Literal["PREFERRED_GPA", "SKILL", "TECHNOLOGY", "KNOWLEDGE", "OTHER"]
    value_text: str = Field(default="", max_length=1000)
    preferred_gpa: float | None = Field(default=None, ge=0, le=4)

    @model_validator(mode="after")
    def valid_requirement(self):
        self.value_text = self.value_text.strip()
        if self.requirement_type == "PREFERRED_GPA":
            if self.preferred_gpa is None:
                raise ValueError("GPA requirement needs a value between 0 and 4")
        elif not self.value_text or self.preferred_gpa is not None:
            raise ValueError("Non-GPA requirements need text, without a GPA value")
        return self


class LecturerOut(BaseModel):
    id: UUID
    display_name: str
    lecturer_code: str
    department_name: str | None = None
    faculty_name: str | None = None


class NotificationOut(BaseModel):
    id: UUID
    message: str
    created_at: datetime
    read_at: datetime | None
    url: str


class NotificationSummaryOut(BaseModel):
    unread_count: int
    items: list[NotificationOut]


class TitleVersionOut(BaseModel):
    version_no: int
    title: str
    change_reason: str | None
    created_at: datetime


class TopicRegisteredStudentOut(BaseModel):
    student_id: UUID
    student_code: str
    display_name: str
    class_name: str | None = None
    is_coordinator: bool = False
    consent_status: str = "PENDING"
    registration_state: str | None = None


class TopicOut(BaseModel):
    id: UUID
    round_id: UUID
    title: str
    description: str | None
    max_students: int
    state: str
    row_version: int
    department_id: UUID
    proposer_user_id: UUID
    decision_reason: str | None = None
    code: str
    round_label: str
    proposer_type: str
    receiving_lecturer_id: UUID | None
    receiving_lecturer_name: str | None
    requirements: list[RequirementInput]
    title_versions: list[TitleVersionOut]
    available: bool
    registered_member_count: int = 0
    remaining_slots: int = 0
    registration_state: str | None = None
    archived_at: datetime | None = None
    archive_reason: str | None = None
    has_links: bool = False
    registered_students: list[TopicRegisteredStudentOut] = []


class TopicCreate(BaseModel):
    round_id: UUID
    title: str = Field(min_length=5, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    max_students: int = Field(default=3, ge=1, le=3)
    requirements: list[RequirementInput] = Field(default_factory=list, max_length=10)
    receiving_lecturer_id: UUID | None = None


class TopicUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    max_students: int | None = Field(default=None, ge=1, le=3)
    requirements: list[RequirementInput] | None = Field(default=None, max_length=10)
    receiving_lecturer_id: UUID | None = None


class TopicDecision(BaseModel):
    decision: Literal["APPROVE", "RETURN", "REJECT"]
    reason: str | None = Field(default=None, max_length=2000)
    revised_title: str | None = Field(default=None, min_length=5, max_length=500)
    receiving_lecturer_id: UUID | None = None


class OpenRoundOut(BaseModel):
    id: UUID
    code: str
    closes_at: datetime
    academic_year: str
    label: str


class RegistrationCreate(BaseModel):
    topic_id: UUID
    # Legacy clients may send their own ID. Selecting another student is rejected.
    member_student_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=1)
    confirm_creator: bool = True
    expected_member_count: int | None = Field(default=None, ge=1, le=3)


class StudentProposalCreate(TopicCreate):
    member_student_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=1)
    confirm_creator: bool = True
    expected_member_count: int | None = Field(default=None, ge=1, le=3)


class RegistrationMemberOut(BaseModel):
    student_id: UUID
    student_code: str
    display_name: str
    is_coordinator: bool
    active: bool
    consent_status: str
    evidence_file_name: str | None = None
    evidence_scan_state: str | None = None
    can_upload_evidence: bool = False
    can_withdraw: bool = False


class MemberResponse(BaseModel):
    consent_status: Literal["ACCEPTED"]


class RegistrationOut(BaseModel):
    id: UUID
    topic_id: UUID
    round_id: UUID
    state: str
    row_version: int
    expected_member_count: int
    submitted_at: datetime | None = None
    member_student_ids: list[UUID]
    members: list[RegistrationMemberOut]
    lecturer_decided_at: datetime | None = None
    thesis_id: UUID | None = None
    topic_title: str
    topic_proposer_user_id: UUID
    topic_code: str
    topic_state: str
    proposer_type: str
    receiving_lecturer_id: UUID | None
    receiving_lecturer_user_id: UUID | None
    receiving_lecturer_name: str | None
    lecturer_reason: str | None


class PendingRegistrationSummaryOut(BaseModel):
    count: int
    items: list[RegistrationOut]


class LecturerDecision(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]
    reason: str | None = Field(default=None, max_length=2000)


class RejectedProposalResolution(BaseModel):
    decision: Literal["REASSIGN", "RETURN_TO_STUDENT"]
    reason: str = Field(min_length=3, max_length=2000)
    receiving_lecturer_id: UUID | None = None


class LecturerDutyOut(BaseModel):
    code: str
    label: str
    scope: str | None = None


class ContextOut(BaseModel):
    user_id: UUID
    base_role: str
    student_id: UUID | None = None
    lecturer_id: UUID | None = None
    actions: list[str]
    display_name: str
    department_id: UUID | None = None
    department_code: str | None = None
    department_name: str | None = None
    email: str | None = None
    student_code: str | None = None
    class_name: str | None = None
    major_code: str | None = None
    major_name: str | None = None
    lecturer_code: str | None = None
    lecturer_duties: list[LecturerDutyOut] = Field(default_factory=list)
    csrf_token: str | None = None
    can_change_password: bool = False


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


class MyEligibilityOut(BaseModel):
    eligible: bool
    has_active_registration: bool


class ThesisOut(BaseModel):
    id: UUID
    title: str
    state: str
    member_student_ids: list[UUID]
    advisor_lecturer_id: UUID
