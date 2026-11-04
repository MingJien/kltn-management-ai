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
    members: list[CouncilMember] = Field(min_length=3, max_length=7)


class SlotInput(Input):
    council_id: UUID
    thesis_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    room: str = Field(min_length=2, max_length=200)


class MarkInput(Input):
    thesis_member_id: UUID
    lecturer_id: UUID
    scores: list[Decimal] = Field(min_length=12, max_length=12)
    note: str = Field(default="", max_length=3000)
    paper_entry_reason: str = Field(default="", max_length=500)


class AttendanceInput(Input):
    status: Literal["PRESENT", "ABSENT"]
    reason: str = Field(default="", max_length=500)


class BonusInput(Input):
    points: Decimal = Field(ge=0, le=1, decimal_places=2)
    reference: str = Field(default="", max_length=500)


class MinutesInput(Input):
    discussion: str = Field(min_length=5, max_length=10000)
    conclusion: str = Field(min_length=5, max_length=5000)
