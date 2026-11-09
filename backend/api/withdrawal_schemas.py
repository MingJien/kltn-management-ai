from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StartDate(BaseModel):
    starts_on: date
    reference: str = Field(min_length=5, max_length=500)

    @field_validator("reference")
    @classmethod
    def trimmed(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Cần căn cứ từ 5 ký tự")
        return value.strip()


class WithdrawalCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=3000)
    confirm_replacement: Literal[True]

    @field_validator("reason")
    @classmethod
    def trimmed(cls, value):
        if len(value.strip()) < 10:
            raise ValueError("Lý do cần ít nhất 10 ký tự")
        return value.strip()


class WithdrawalDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    outcome: Literal["WITHDRAWN", "NOT_GRANTED"]
    note: str = Field(min_length=5, max_length=3000)

    @field_validator("note")
    @classmethod
    def trimmed(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Cần lý do xử lý từ 5 ký tự")
        return value.strip()
