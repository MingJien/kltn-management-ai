"""Contracts for the delivered thesis workspace, separate from design-only APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, AwareDatetime

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]


class LecturerAssignment(BaseModel):
    lecturer_id: UUID
    reason: Reason


class MilestoneCreate(BaseModel):
    scope: Literal["ROUND", "THESIS"] = "ROUND"
    code: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Z0-9_-]{1,50}$")]
    title: ShortText
    due_at: AwareDatetime
    expected_ratio: float | None = Field(default=None, ge=0, le=100)


class MilestoneClose(BaseModel):
    reason: Reason


class MilestoneExtend(BaseModel):
    due_at: AwareDatetime
    reason: Reason


class ProgressCreate(BaseModel):
    milestone_id: UUID
    summary: LongText
    reported_ratio: float = Field(ge=0, le=100)
    document_version_id: UUID | None = None


class ProgressDecision(BaseModel):
    decision: Literal["COMMENT_ONLY", "CONFIRM", "REVISION_REQUIRED"]
    comment: LongText


class DocumentCreate(BaseModel):
    title: ShortText
    document_type: Literal["PROPOSAL", "PLAN", "REPORT", "SUPPORTING"]


class DocumentDecision(BaseModel):
    decision: Literal["ACCEPT", "REVISION_REQUIRED"]
    comment: LongText


class DocumentWithdraw(BaseModel):
    reason: Reason


class WorkCreate(BaseModel):
    student_id: UUID
    work_description: LongText
    expected_output: LongText


class WorkDecision(BaseModel):
    decision: Literal["APPROVE", "REVISION_REQUIRED"]
    comment: LongText


class ProposalReviewCreate(BaseModel):
    decision: Literal["COMMENT", "CONFIRM", "REVISION_REQUIRED"]
    comment: LongText


class ProposalFinalization(BaseModel):
    reason: Reason


class ProposalSignedCopy(BaseModel):
    official_ref: ShortText


class AdvisorOut(BaseModel):
    id: UUID
    lecturer_id: UUID
    display_name: str
    state: str
    effective_from: datetime
    effective_to: datetime | None


class PendingAdvisorOut(BaseModel):
    lecturer_id: UUID
    display_name: str


class ThesisMemberOut(BaseModel):
    student_id: UUID
    display_name: str
    student_code: str
    is_coordinator: bool


class ThesisWorkspaceOut(BaseModel):
    id: UUID
    registration_id: UUID
    title: str
    state: str
    row_version: int
    round_id: UUID
    round_label: str
    extension_until_at: datetime | None = None
    member_student_ids: list[UUID]
    members: list[ThesisMemberOut]
    advisor_lecturer_id: UUID | None
    advisor_name: str | None
    advisor_history: list[AdvisorOut]
    pending_advisor: PendingAdvisorOut | None
    cross_reviewers: list[PendingAdvisorOut]
    actions: list[str]


class RegistrationFormVersionOut(BaseModel):
    id: UUID
    version_no: int
    form_code: Literal["1A", "1B"]
    file_name: str
    byte_size: int
    scan_state: str
    submitted_at: datetime
    submitted_by_name: str
    current: bool


class RegistrationFormsOut(BaseModel):
    form_code: Literal["1A", "1B"]
    can_submit: bool
    registration_version: int
    versions: list[RegistrationFormVersionOut]


class MilestoneOut(BaseModel):
    scope: Literal["ROUND", "THESIS"] = "ROUND"
    thesis_id: UUID | None = None
    id: UUID
    code: str
    title: str
    version_no: int
    row_version: int
    state: str
    due_at: datetime | None
    expected_ratio: float | None


class DocumentDeadlineOut(BaseModel):
    id: UUID
    document_type: str
    due_at: datetime
    state: str
    row_version: int
    reason: str


class DocumentDeadlineSet(BaseModel):
    document_type: Literal["PROPOSAL", "PLAN", "REPORT", "SUPPORTING"]
    due_at: AwareDatetime
    reason: str = Field(min_length=3, max_length=2000)


class DocumentDeadlineClose(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class ReviewOut(BaseModel):
    reviewer_name: str
    decision: str
    comment: str
    created_at: datetime


class PrintExportOut(BaseModel):
    id: UUID
    actor_name: str
    document_code: str
    version_no: int
    exported_at: datetime
    copy_status: Literal["SUBMITTED", "APPROVED"]


class ProposalVersionOut(BaseModel):
    id: UUID
    version_no: int
    file_name: str
    byte_size: int
    sha256: str
    submitted_by_name: str
    submitted_at: datetime
    due_at_at_submission: datetime | None
    late: bool
    scan_state: str
    reviews: list[ReviewOut]


class ProposalOut(BaseModel):
    id: UUID | None
    thesis_id: UUID
    state: str
    row_version: int
    current_version_no: int | None
    versions: list[ProposalVersionOut]
    reviewers: list[PendingAdvisorOut]
    department_confirmed: bool
    dean_confirmed: bool


class ProgressOut(BaseModel):
    id: UUID
    milestone_id: UUID
    version_no: int
    row_version: int
    state: str
    summary: str
    reported_ratio: float | None
    submitted_by_name: str
    submitted_by_student_id: UUID
    submitted_at: datetime
    due_at_at_submission: datetime | None
    late: bool
    evidence_document_version_id: UUID | None
    evidence_scan_state: str | None
    evidence_file_name: str | None
    reviews: list[ReviewOut]


class ProgressAnnotationSave(BaseModel):
    annotation_kind: Literal["PIN", "SUMMARY", "ATTACHMENT"] = "PIN"
    page_number: int | None = Field(default=None, ge=1, le=10000)
    x: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    y: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    location_label: str = Field(default="", max_length=255)
    quoted_text: str = Field(default="", max_length=1000)
    comment: str = Field(default="", max_length=2000)


class ReviewAttachmentOut(BaseModel):
    file_name: str
    byte_size: int
    scan_state: str


class ProgressAnnotationOut(ProgressAnnotationSave):
    attachment: ReviewAttachmentOut | None = None
    id: UUID
    reviewer_id: UUID
    reviewer_name: str
    state: str
    row_version: int
    updated_at: datetime
    published_at: datetime | None


class ProgressAnnotationsOut(BaseModel):
    annotations: list[ProgressAnnotationOut]
    can_edit: bool
    read_only_reason: str | None = None


class DocumentVersionOut(BaseModel):
    id: UUID
    version_no: int
    row_version: int
    state: str
    file_name: str
    byte_size: int
    sha256: str
    scan_state: str
    submitted_at: datetime
    due_at_at_submission: datetime | None
    late: bool
    submitted_by_name: str
    reviews: list[ReviewOut]


class DocumentOut(BaseModel):
    id: UUID
    title: str
    document_type: str
    row_version: int
    visibility: str
    versions: list[DocumentVersionOut]


class WorkOut(BaseModel):
    id: UUID
    student_id: UUID
    student_name: str
    version_no: int
    row_version: int
    work_description: str
    expected_output: str
    state: str
    review_comment: str | None
    reviewed_by_name: str | None


class AuditOut(BaseModel):
    action: str
    actor_name: str
    reason: str | None
    occurred_at: datetime
