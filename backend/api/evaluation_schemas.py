"""Inputs for NV6. Form fields follow the faculty's Mẫu 7 and Mẫu 8."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ReviewerCreate(Input):
    lecturer_id: UUID
    due_at: datetime
    reason: str = Field(min_length=5, max_length=2000)
    source_reference: str = Field(min_length=3, max_length=500)

    @field_validator("due_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Hạn phản biện phải có múi giờ")
        return value


class Reason(Input):
    reason: str = Field(min_length=5, max_length=2000)


class ReviewerDeadline(Reason):
    due_at: datetime
    source_reference: str = Field(min_length=3, max_length=500)

    @field_validator("due_at")
    @classmethod
    def timezone_required(cls, value):
        return ReviewerCreate.timezone_required(value)


class ReviewCreate(Reason):
    thesis_member_id: UUID
    report_version_id: UUID
    kind: Literal["ADVISOR", "REVIEWER"]


class ReviewSave(Input):
    sections: dict[str, str]
    thesis_completed: bool | None = None
    allow_defense: bool | None = None
    source_reference: str | None = Field(default=None, max_length=500)

    @field_validator("sections")
    @classmethod
    def bounded_sections(cls, value):
        if len(value) > 5 or any(len(k) > 50 or len(v) > 6000 for k, v in value.items()):
            raise ValueError("Mỗi mục nhận xét tối đa 6.000 ký tự")
        if any(ord(c) < 32 and c not in "\t\r\n" for text in value.values() for c in text):
            raise ValueError("Nhận xét chứa ký tự điều khiển không hợp lệ")
        return {k: v.strip() for k, v in value.items()}


class ReviewSubmit(Input):
    confirm_signed_copy: Literal[True]


class EligibilityCreate(Reason):
    thesis_member_id: UUID
    report_version_id: UUID | None
    advisor_review_id: UUID | None
    discipline_status: Literal["CLEAR", "WARNING_OR_HIGHER", "UNKNOWN"]
    source_reference: str = Field(min_length=3, max_length=500)
