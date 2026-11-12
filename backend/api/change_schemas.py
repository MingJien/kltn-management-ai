from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ChangeCreate(Input):
    scope: Literal["GROUP", "INDIVIDUAL"] = "GROUP"
    kind: Literal["ADJUSTMENT", "REPLACEMENT"]
    proposed_title: str = Field(default="", max_length=500)
    proposed_description: str = Field(default="", max_length=10000)
    target_topic_id: UUID | None = None
    reason: str = Field(min_length=10, max_length=3000)
    confirm_consequences: Literal[True]


class GroupConsent(Input):
    decision: Literal["AGREE", "DECLINE"]


class AdvisorReview(Input):
    role: Literal["CURRENT_ADVISOR", "NEW_ADVISOR"]
    decision: Literal["AGREE", "REJECT"]
    reason: str = Field(min_length=5, max_length=3000)


class FinalDecision(Input):
    decision: Literal["APPROVE", "REJECT"]
    reason: str = Field(min_length=5, max_length=3000)


class ExtensionRecord(Input):
    decision_on: date
    until_at: AwareDatetime
    reference: str = Field(min_length=5, max_length=500)
    reason: str = Field(min_length=10, max_length=3000)
    evidence_file_id: UUID | None = None
    confirm_decision: Literal[True]


class ExtensionCreate(Input):
    until_at: AwareDatetime | None = None
    reason: str = Field(min_length=10,max_length=3000)
    confirm_consequences: Literal[True]


class ExtensionReview(Input):
    decision: Literal["AGREE","REJECT"]
    reason: str = Field(min_length=5,max_length=3000)


class ExtensionDecision(Input):
    decision: Literal["APPROVE","REJECT"]
    reason: str = Field(min_length=5,max_length=3000)
    decision_on: date | None = None
    extension_starts_at: AwareDatetime | None = None
    until_at: AwareDatetime | None = None
    reference: str | None = Field(default=None,min_length=5,max_length=500)
    confirm_decision: bool = False


class ConsentDeadline(Input):
    due_at: AwareDatetime | None = None
    reason: str = Field(min_length=5,max_length=2000)
