from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileData(Input):
    display_name: str = Field(min_length=2, max_length=255)
    academic_degree: Literal["BACHELOR","MASTER","DOCTOR","DOCTOR_OF_SCIENCE"] | None = None
    academic_title: Literal["NONE","ASSOCIATE_PROFESSOR","PROFESSOR"] | None = None
    professional_title: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=30)
    show_phone: bool = False
    office_location: str | None = Field(default=None, max_length=200)
    office_hours: str | None = Field(default=None, max_length=400)
    website: str | None = Field(default=None, max_length=1000)
    biography: str | None = Field(default=None, max_length=3000)
    education: str | None = Field(default=None, max_length=2000)
    experience: str | None = Field(default=None, max_length=2000)
    specializations: list[str] = Field(default_factory=list, max_length=12)
    research_interests: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("*", mode="before")
    @classmethod
    def empty_optional(cls, value, info):
        if isinstance(value,str):
            if any(ord(c)<32 and c not in "\r\n\t" for c in value):
                raise ValueError("Thông tin chứa ký tự điều khiển không hợp lệ")
            if not value.strip() and info.field_name!="display_name":return None
        return value

    @field_validator("contact_email")
    @classmethod
    def email(cls,value):
        if value:
            from backend.services.roster import EMAIL
            value=value.strip().lower()
            if not EMAIL.fullmatch(value):raise ValueError("Email liên hệ không đúng định dạng")
            return value
        return value

    @field_validator("contact_phone")
    @classmethod
    def phone(cls,value):
        if value and (any(c not in "+0123456789()- ." for c in value) or not 8<=sum(c.isdigit() for c in value)<=16):
            raise ValueError("Số điện thoại cần 8–16 chữ số, có thể kèm mã quốc gia")
        return value

    @field_validator("website")
    @classmethod
    def website_link(cls,value):
        if value:
            url=urlsplit(value)
            if url.scheme not in {"http","https"} or not url.hostname or url.username or url.password:
                raise ValueError("Liên kết cần địa chỉ http/https hợp lệ, không chứa tài khoản hoặc mật khẩu")
        return value

    @field_validator("specializations","research_interests")
    @classmethod
    def tags(cls,value):
        if any(not s.strip() or len(s.strip())>80 or any(ord(c)<32 for c in s) for s in value):
            raise ValueError("Mỗi mục chuyên môn từ 1 đến 80 ký tự")
        return list(dict.fromkeys(s.strip() for s in value))


class Note(Input):
    reason: str = Field(min_length=5,max_length=2000)


class Submission(Input):
    note: str = Field(min_length=5,max_length=2000)


class Decision(Note):
    decision: Literal["APPROVE","RETURN"]
    confirm_verified: bool = False


class IdentityUpdate(Note):
    display_name: str = Field(min_length=2,max_length=255)
    lecturer_code: str = Field(min_length=1,max_length=32,pattern=r"^[\w.-]+$")
    department_id: UUID
    source_reference: str = Field(min_length=3,max_length=500)
