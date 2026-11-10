from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CouncilMember(Input):
    lecturer_id: UUID
    role: Literal["CHAIR", "SECRETARY", "REVIEWER", "MEMBER"]


class CouncilInput(Input):
    round_id: UUID
    department_id: UUID
    name: str = Field(min_length=3, max_length=200)
    reference: str = Field(min_length=3, max_length=300)
    members: list[CouncilMember] = Field(min_length=5, max_length=5)


class SlotInput(Input):
    council_id: UUID
    thesis_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    room: str = Field(min_length=2, max_length=200)
    prior_slot_id: UUID | None = None
    thesis_member_ids: list[UUID] = Field(default_factory=list, max_length=3)


class AbsenceDecision(Input):
    outcome: Literal["NOT_PASSED", "SUPPLEMENTARY"]
    reference: str = Field(min_length=5, max_length=300)
    reason: str = Field(min_length=10, max_length=1000)
    revision: int = Field(default=0, ge=0)


class MarkInput(Input):
    thesis_member_id: UUID
    lecturer_id: UUID
    scores: list[Decimal] = Field(min_length=12, max_length=12)
    note: str = Field(default="", max_length=3000)
    paper_entry_reason: str = Field(default="", max_length=500)
    ballot_revision: int | None = Field(default=None, ge=0)
    context_token: str | None = Field(default=None, max_length=64)


class AttendanceInput(Input):
    status: Literal["PRESENT", "ABSENT"]
    reason: str = Field(default="", max_length=500)


class BonusInput(Input):
    points: Decimal = Field(ge=0, le=1, decimal_places=2)
    reference: str = Field(default="", max_length=500)
    evidence_version_id: UUID | None = None


class MinutesInput(Input):
    discussion: str = Field(min_length=5, max_length=10000)
    conclusion: str = Field(min_length=5, max_length=5000)


class CouncilAttendance(Input):
    present_ids: list[UUID] = Field(min_length=3, max_length=5)
    reason: str = Field(min_length=5, max_length=1000)


class ReopenInput(Input):
    reason: str = Field(min_length=5, max_length=1000)
    confirm_unsigned: Literal[True]
