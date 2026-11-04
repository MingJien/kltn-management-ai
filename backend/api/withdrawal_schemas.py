from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator


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


class AdvisorDecision(BaseModel):
    decision: Literal["CONFIRM", "RETURN"]
    comment: str = Field(min_length=5, max_length=3000)

    @field_validator("comment")
    @classmethod
    def trimmed(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Cần ý kiến từ 5 ký tự")
        return value.strip()


class ReceiptRecord(BaseModel):
    received_on: date
    receiving_unit: str = Field(min_length=3, max_length=200)
    reference: str = Field(min_length=3, max_length=500)
    note: str = Field(default="", max_length=1000)
    confirm_receipt: Literal[True]

    @field_validator("receiving_unit", "reference", "note")
    @classmethod
    def trimmed_receipt(cls, value, info):
        value = value.strip()
        if info.field_name in {"receiving_unit", "reference"} and len(value) < 3:
            raise ValueError("Cần nhập ít nhất 3 ký tự")
        return value


class ExternalOutcome(BaseModel):
    outcome: Literal["WITHDRAWN", "NOT_GRANTED"]
    reference: str = Field(min_length=5, max_length=500)
    note: str = Field(min_length=5, max_length=3000)
    effective_on: date
    confirm_evidence: Literal[True]

    @field_validator("reference", "note")
    @classmethod
    def trimmed(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Cần nội dung từ 5 ký tự")
        return value.strip()
