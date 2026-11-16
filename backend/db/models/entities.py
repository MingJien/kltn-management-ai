from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin, VersionedMixin


class PublicationClaim(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "publication_claim"
    __table_args__ = (CheckConstraint("state IN ('SUBMITTED','ADVISOR_CONFIRMED','APPROVED','REJECTED','REVISION_REQUIRED')", name="state"),
        Index("ix_publication_claim_thesis", "thesis_id"))
    thesis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("thesis.id"))
    evidence_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document_version.id"))
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_account.id"))
    state: Mapped[str] = mapped_column(String(30), default="SUBMITTED")
    details: Mapped[dict] = mapped_column(JSONB)
    history: Mapped[list] = mapped_column(JSONB, default=list)


def fk(target: str, *, nullable: bool = False):
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey(target, ondelete="RESTRICT"),
        nullable=nullable,
    )


class Faculty(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "faculty"
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class Department(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "department"
    __table_args__ = (UniqueConstraint("faculty_id", "code"),)
    faculty_id: Mapped[uuid.UUID] = fk("faculty.id")
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    major_code: Mapped[Optional[str]] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class DepartmentMajor(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Allowed major codes for a department; one department may offer many majors."""

    __tablename__ = "department_major"
    __table_args__ = (UniqueConstraint("department_id", "code"),)
    department_id: Mapped[uuid.UUID] = fk("department.id")
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class UserAccount(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "user_account"
    __table_args__ = (
        CheckConstraint("base_role IN ('ADMIN','LECTURER','STUDENT')", name="base_role"),
        CheckConstraint("status IN ('ACTIVE','LOCKED','DISABLED')", name="status"),
        CheckConstraint("external_subject IS NOT NULL OR email IS NOT NULL", name="identity_present"),
        CheckConstraint("(email IS NULL AND password_hash IS NULL) OR (email IS NOT NULL AND password_hash IS NOT NULL)", name="local_credentials_pair"),
        CheckConstraint("email IS NULL OR email = lower(email)", name="email_normalized"),
        Index("uq_user_account_email_lower", text("lower(email)"), unique=True, postgresql_where=text("email IS NOT NULL")),
    )
    external_subject: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    base_role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")


class StudentProfile(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_profile"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "major_code"],
            ["department_major.department_id", "department_major.code"],
            ondelete="RESTRICT",
        ),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    student_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    department_id: Mapped[uuid.UUID] = fk("department.id")
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_name: Mapped[Optional[str]] = mapped_column(String(100))
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    training_cohort: Mapped[Optional[str]] = mapped_column(String(50))
    major_code: Mapped[Optional[str]] = mapped_column(String(32))


class LecturerProfile(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "lecturer_profile"
    __table_args__ = (CheckConstraint("jsonb_typeof(profile_data) = 'object'", name="profile_data_object"),)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    lecturer_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    department_id: Mapped[uuid.UUID] = fk("department.id")
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    avatar_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)
    profile_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    profile_verified_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)


class LecturerProfileChange(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "lecturer_profile_change"
    __table_args__ = (
        UniqueConstraint("lecturer_id", "version_no"),
        CheckConstraint("version_no > 0 AND base_profile_version > 0", name="version_positive"),
        CheckConstraint("state IN ('DRAFT','SUBMITTED','APPROVED','RETURNED','WITHDRAWN')", name="state"),
        CheckConstraint("jsonb_typeof(proposed_data) = 'object' AND jsonb_typeof(original_data) = 'object'", name="data_objects"),
        CheckConstraint("state NOT IN ('SUBMITTED','APPROVED','RETURNED') OR submitted_at IS NOT NULL", name="submitted_timestamp"),
        CheckConstraint("state NOT IN ('APPROVED','RETURNED') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND decision_reason IS NOT NULL)", name="decision_recorded"),
        Index("uq_lecturer_profile_change_open", "lecturer_id", unique=True, postgresql_where=text("state IN ('DRAFT','SUBMITTED')")),
        Index("ix_lecturer_profile_change_state_created", "state", "created_at"),
    )
    lecturer_id: Mapped[uuid.UUID] = fk("lecturer_profile.id")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    base_profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    original_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    avatar_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)
    original_avatar_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")
    submission_note: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[Optional[str]] = mapped_column(Text)


class OrganizationalPosition(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizational_position"
    __table_args__ = (
        CheckConstraint("code IN ('DEPARTMENT_HEAD','FACULTY_DEAN')", name="code"),
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class PositionAssignment(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "position_assignment"
    __table_args__ = (
        CheckConstraint(
            "(faculty_id IS NOT NULL AND department_id IS NULL) OR "
            "(faculty_id IS NULL AND department_id IS NOT NULL)",
            name="exactly_one_scope",
        ),
        CheckConstraint("state IN ('ACTIVE','REVOKED','EXPIRED')", name="state"),
        CheckConstraint("effective_to IS NULL OR effective_to > effective_from", name="effective_window"),
        Index("uq_position_assignment_faculty_scope", "lecturer_id", "position_id", "faculty_id", unique=True, postgresql_where=text("faculty_id IS NOT NULL AND state = 'ACTIVE'")),
        Index("uq_position_assignment_department_scope", "lecturer_id", "position_id", "department_id", unique=True, postgresql_where=text("department_id IS NOT NULL AND state = 'ACTIVE'")),
    )
    lecturer_id: Mapped[uuid.UUID] = fk("lecturer_profile.id")
    position_id: Mapped[uuid.UUID] = fk("organizational_position.id")
    faculty_id: Mapped[Optional[uuid.UUID]] = fk("faculty.id", nullable=True)
    department_id: Mapped[Optional[uuid.UUID]] = fk("department.id", nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")


class AcademicYear(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "academic_year"
    __table_args__ = (
        CheckConstraint("ends_on > starts_on", name="date_window"),
        CheckConstraint("state IN ('DRAFT','ACTIVE','CLOSED')", name="state"),
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")


class ThesisRound(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "thesis_round"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "code"),
        CheckConstraint("round_type IN ('MAIN','SUPPLEMENTARY')", name="round_type"),
        CheckConstraint("state IN ('DRAFT','OPEN','CLOSED','ARCHIVED')", name="state"),
        CheckConstraint("closes_at > opens_at", name="time_window"),
        CheckConstraint("(execution_starts_on IS NULL AND execution_start_reference IS NULL) OR (execution_starts_on IS NOT NULL AND execution_start_reference IS NOT NULL AND length(trim(execution_start_reference)) >= 5)", name="execution_start_pair"),
    )
    academic_year_id: Mapped[uuid.UUID] = fk("academic_year.id")
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    round_type: Mapped[str] = mapped_column(String(20), nullable=False)
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")

    execution_starts_on: Mapped[Optional[date]] = mapped_column(Date)
    execution_start_reference: Mapped[Optional[str]] = mapped_column(String(500))


class ResourceAssignment(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "resource_assignment"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN round_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN thesis_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="exactly_one_resource",
        ),
        CheckConstraint("state IN ('ACTIVE','REVOKED','EXPIRED')", name="state"),
        CheckConstraint("effective_to IS NULL OR effective_to > effective_from", name="effective_window"),
        Index("uq_resource_assignment_round_scope", "assignment_type", "user_id", "round_id", unique=True, postgresql_where=text("round_id IS NOT NULL AND state = 'ACTIVE'")),
        Index("uq_resource_assignment_thesis_scope", "assignment_type", "user_id", "thesis_id", unique=True, postgresql_where=text("thesis_id IS NOT NULL AND state = 'ACTIVE'")),
    )
    assignment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[uuid.UUID] = fk("user_account.id")
    round_id: Mapped[Optional[uuid.UUID]] = fk("thesis_round.id", nullable=True)
    thesis_id: Mapped[Optional[uuid.UUID]] = fk("thesis.id", nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")


class EligibilitySnapshot(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "eligibility_snapshot"
    __table_args__ = (
        UniqueConstraint("student_id", "round_id", "version"),
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint("passed_credit_ratio >= 0 AND passed_credit_ratio <= 1", name="credit_ratio"),
        CheckConstraint("gpa_4 >= 0 AND gpa_4 <= 4", name="gpa"),
        CheckConstraint("state IN ('DRAFT','SUBMITTED','CONFIRMED','REJECTED')", name="state"),
        CheckConstraint(
            "state NOT IN ('CONFIRMED','REJECTED') OR "
            "(confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)",
            name="decision_metadata",
        ),
    )
    student_id: Mapped[uuid.UUID] = fk("student_profile.id")
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # May be unknown when only the Faculty's signed eligibility result is imported.
    passed_credit_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    gpa_4: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    evidence_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[Optional[str]] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")


class Topic(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "topic"
    __table_args__ = (
        CheckConstraint("proposer_type IN ('LECTURER','STUDENT')", name="proposer_type"),
        CheckConstraint("state IN ('DRAFT','SUBMITTED','APPROVED','RETURNED','REJECTED','LOCKED')", name="state"),
        CheckConstraint("max_students BETWEEN 1 AND 3", name="max_students"),
    )
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    receiving_lecturer_id: Mapped[Optional[uuid.UUID]] = fk("lecturer_profile.id", nullable=True)
    department_id: Mapped[uuid.UUID] = fk("department.id")
    proposer_user_id: Mapped[uuid.UUID] = fk("user_account.id")
    proposer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    current_title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    max_students: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")
    decided_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    archive_reason: Mapped[Optional[str]] = mapped_column(Text)


class TopicTitleVersion(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "topic_title_version"
    __table_args__ = (
        UniqueConstraint("topic_id", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
    )
    topic_id: Mapped[uuid.UUID] = fk("topic.id")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    changed_by: Mapped[uuid.UUID] = fk("user_account.id")
    change_reason: Mapped[Optional[str]] = mapped_column(Text)


class TopicRequirement(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "topic_requirement"
    __table_args__ = (
        CheckConstraint(
            "requirement_type IN ('PREFERRED_GPA','SKILL','TECHNOLOGY','KNOWLEDGE','OTHER')",
            name="requirement_type",
        ),
        CheckConstraint("enforcement = 'DESIRED'", name="enforcement_desired"),
        CheckConstraint("preferred_gpa IS NULL OR (preferred_gpa >= 0 AND preferred_gpa <= 4)", name="preferred_gpa"),
    )
    topic_id: Mapped[uuid.UUID] = fk("topic.id")
    requirement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value_text: Mapped[Optional[str]] = mapped_column(Text)
    preferred_gpa: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    enforcement: Mapped[str] = mapped_column(String(20), nullable=False, default="DESIRED", server_default="DESIRED")


class TopicRegistration(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "topic_registration"
    __table_args__ = (
        UniqueConstraint("id", "round_id"),
        CheckConstraint("expected_member_count BETWEEN 1 AND 3", name="expected_member_count"),
        CheckConstraint(
            "state IN ('DRAFT','SUBMITTED','LECTURER_ACCEPTED','LECTURER_REJECTED','RETURNED','FINALIZED','CANCELLED')",
            name="state",
        ),
    )
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    topic_id: Mapped[uuid.UUID] = fk("topic.id")
    created_by: Mapped[uuid.UUID] = fk("student_profile.id")
    expected_member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", server_default="DRAFT")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lecturer_decided_by: Mapped[Optional[uuid.UUID]] = fk("lecturer_profile.id", nullable=True)
    lecturer_decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lecturer_reason: Mapped[Optional[str]] = mapped_column(Text)
    department_finalized_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    department_finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class RegistrationMember(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "registration_member"
    __table_args__ = (
        ForeignKeyConstraint(
            ["registration_id", "round_id"],
            ["topic_registration.id", "topic_registration.round_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("registration_id", "student_id"),
        CheckConstraint(
            "(consent_status = 'PENDING' AND responded_by_user_id IS NULL AND responded_at IS NULL) OR "
            "(consent_status IN ('ACCEPTED','DECLINED') AND responded_by_user_id IS NOT NULL AND responded_at IS NOT NULL)",
            name="consent_consistency",
        ),
        Index(
            "uq_registration_member_student_round_active",
            "student_id",
            "round_id",
            unique=True,
            postgresql_where=text("active"),
        ),
        Index(
            "uq_registration_member_one_coordinator",
            "registration_id",
            unique=True,
            postgresql_where=text("active AND is_coordinator"),
        ),
    )
    registration_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    student_id: Mapped[uuid.UUID] = fk("student_profile.id")
    evidence_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)
    is_coordinator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    consent_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    responded_by_user_id: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Thesis(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "thesis"
    __table_args__ = (
        UniqueConstraint("round_id", "topic_id"),
        CheckConstraint(
            "state IN ('ACTIVE','PROPOSAL_APPROVED','IN_PROGRESS','EXTENDED','WITHDRAWN','READY_FOR_DEFENSE','DEFENDED','COMPLETED','ARCHIVED')",
            name="state",
        ),
    )
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    topic_id: Mapped[uuid.UUID] = fk("topic.id")
    registration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topic_registration.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    department_id: Mapped[uuid.UUID] = fk("department.id")
    current_title: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", server_default="ACTIVE")


class ThesisMember(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "thesis_member"
    __table_args__ = (
        UniqueConstraint("thesis_id", "student_id"),
        Index(
            "uq_thesis_member_one_coordinator",
            "thesis_id",
            unique=True,
            postgresql_where=text("active AND is_coordinator"),
        ),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    student_id: Mapped[uuid.UUID] = fk("student_profile.id")
    is_coordinator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class MemberWorkAssignment(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "member_work_assignment"
    __table_args__ = (
        UniqueConstraint("thesis_member_id", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("state IN ('DRAFT','SUBMITTED','APPROVED','REVISION_REQUIRED')", name="state"),
    )
    thesis_member_id: Mapped[uuid.UUID] = fk("thesis_member.id")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    work_description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", server_default="DRAFT")
    reviewed_by: Mapped[Optional[uuid.UUID]] = fk("lecturer_profile.id", nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[Optional[str]] = mapped_column(Text)


class AdvisorAssignment(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "advisor_assignment"
    __table_args__ = (
        CheckConstraint("assignment_type = 'PRIMARY'", name="assignment_type"),
        CheckConstraint("state IN ('ACTIVE','ENDED','REVOKED')", name="state"),
        Index(
            "uq_advisor_assignment_active_primary",
            "thesis_id",
            unique=True,
            postgresql_where=text("state = 'ACTIVE' AND assignment_type = 'PRIMARY'"),
        ),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    lecturer_id: Mapped[uuid.UUID] = fk("lecturer_profile.id")
    assignment_type: Mapped[str] = mapped_column(String(20), nullable=False, default="PRIMARY", server_default="PRIMARY")
    assigned_by: Mapped[uuid.UUID] = fk("user_account.id")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")


class ReviewerAssignment(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "reviewer_assignment"
    __table_args__ = (
        CheckConstraint(
            "(proposal_id IS NOT NULL AND thesis_id IS NULL) OR "
            "(proposal_id IS NULL AND thesis_id IS NOT NULL)",
            name="exactly_one_subject",
        ),
        CheckConstraint("review_scope IN ('PROPOSAL','THESIS')", name="review_scope"),
        CheckConstraint("state IN ('ACTIVE','COMPLETED','REVOKED')", name="state"),
        CheckConstraint("(review_scope = 'PROPOSAL' AND proposal_id IS NOT NULL) OR (review_scope = 'THESIS' AND thesis_id IS NOT NULL)", name="scope_matches_subject"),
        Index("uq_reviewer_assignment_proposal", "lecturer_id", "proposal_id", unique=True, postgresql_where=text("proposal_id IS NOT NULL AND state = 'ACTIVE'")),
        Index("uq_reviewer_assignment_thesis", "lecturer_id", "thesis_id", unique=True, postgresql_where=text("thesis_id IS NOT NULL AND state = 'ACTIVE'")),
    )
    lecturer_id: Mapped[uuid.UUID] = fk("lecturer_profile.id")
    proposal_id: Mapped[Optional[uuid.UUID]] = fk("proposal.id", nullable=True)
    thesis_id: Mapped[Optional[uuid.UUID]] = fk("thesis.id", nullable=True)
    review_scope: Mapped[str] = mapped_column(String(20), nullable=False)
    assigned_by: Mapped[uuid.UUID] = fk("user_account.id")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    assignment_reason: Mapped[Optional[str]] = mapped_column(Text)
    source_reference: Mapped[Optional[str]] = mapped_column(String(500))


class StoredFile(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stored_file"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="byte_size_positive"),
        CheckConstraint("scan_state IN ('QUARANTINED','CLEAN','INFECTED','FAILED')", name="scan_state"),
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(150), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scan_state: Mapped[str] = mapped_column(String(20), nullable=False, default="QUARANTINED", server_default="QUARANTINED")
    scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class OfficialForm(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "official_form"
    __table_args__ = (
        UniqueConstraint("round_id", "code"),
        CheckConstraint("document_kind IN ('FORM','PUBLICATION')", name="document_kind"),
        CheckConstraint("audience IN ('STUDENT_AND_LECTURER','LECTURER')", name="audience"),
        CheckConstraint("state IN ('ACTIVE','ARCHIVED')", name="state"),
    )
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    audience: Mapped[str] = mapped_column(String(30), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")
    created_by: Mapped[uuid.UUID] = fk("user_account.id")


class OfficialFormVersion(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "official_form_version"
    __table_args__ = (
        UniqueConstraint("official_form_id", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("state IN ('DRAFT','PUBLISHED','SUPERSEDED','WITHDRAWN')", name="state"),
        CheckConstraint("(published_at IS NULL) = (published_by IS NULL)", name="publisher_pair"),
        CheckConstraint("state NOT IN ('PUBLISHED','SUPERSEDED') OR published_at IS NOT NULL", name="published_stamp"),
        CheckConstraint("state != 'DRAFT' OR published_at IS NULL", name="draft_stamp"),
        Index("uq_official_form_current", "official_form_id", unique=True, postgresql_where=text("state = 'PUBLISHED'")),
    )
    official_form_id: Mapped[uuid.UUID] = fk("official_form.id")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    stored_file_id: Mapped[uuid.UUID] = fk("stored_file.id")
    uploaded_by: Mapped[uuid.UUID] = fk("user_account.id")
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")
    published_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Proposal(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "proposal"
    __table_args__ = (
        CheckConstraint(
            "state IN ('DRAFT','SUBMITTED','UNDER_REVIEW','REVISION_REQUIRED','ADVISOR_CONFIRMED',"
            "'DEPARTMENT_FINALIZED','DEAN_CONFIRMED','PRINT_READY')",
            name="state",
        ),
    )
    thesis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("thesis.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    current_version_no: Mapped[Optional[int]] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT", server_default="DRAFT")


class ProposalVersion(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "proposal_version"
    __table_args__ = (
        UniqueConstraint("proposal_id", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
    )
    proposal_id: Mapped[uuid.UUID] = fk("proposal.id")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    stored_file_id: Mapped[uuid.UUID] = fk("stored_file.id")
    submitted_by: Mapped[uuid.UUID] = fk("student_profile.id")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at_at_submission: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class ProposalReview(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "proposal_review"
    __table_args__ = (
        CheckConstraint("decision IN ('COMMENT','REVISION_REQUIRED','CONFIRM')", name="decision"),
    )
    proposal_version_id: Mapped[uuid.UUID] = fk("proposal_version.id")
    reviewer_assignment_id: Mapped[uuid.UUID] = fk("reviewer_assignment.id")
    reviewer_user_id: Mapped[uuid.UUID] = fk("user_account.id")
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)


class SignatureConfirmation(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "signature_confirmation"
    __table_args__ = (
        CheckConstraint("signature_type IN ('DEPARTMENT_FINALIZATION','DEAN_CONFIRMATION')", name="signature_type"),
        CheckConstraint("proposal_version_no > 0", name="proposal_version_positive"),
        UniqueConstraint("proposal_id", "proposal_version_no", "signature_type", name="uq_signature_confirmation_proposal_version_type"),
        ForeignKeyConstraint(
            ["proposal_id", "proposal_version_no"],
            ["proposal_version.proposal_id", "proposal_version.version_no"],
            name="fk_signature_confirmation_proposal_version_pair",
            ondelete="RESTRICT",
        ),
    )
    proposal_id: Mapped[uuid.UUID] = fk("proposal.id")
    proposal_version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    signature_type: Mapped[str] = mapped_column(String(40), nullable=False)
    signer_user_id: Mapped[uuid.UUID] = fk("user_account.id")
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    official_ref: Mapped[Optional[str]] = mapped_column(String(500))


class ProgressMilestone(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "progress_milestone"
    thesis_id: Mapped[Optional[uuid.UUID]] = fk("thesis.id", nullable=True)
    __table_args__ = (
        Index("uq_milestone_round_version", "round_id", "code", "version_no", unique=True,
            postgresql_where=text("thesis_id IS NULL")),
        Index("uq_milestone_thesis_version", "thesis_id", "code", "version_no", unique=True,
            postgresql_where=text("thesis_id IS NOT NULL")),
        CheckConstraint("(thesis_id IS NULL AND source_type IN ('ROUND_POLICY','STUDENT_PLAN')) OR (thesis_id IS NOT NULL AND source_type = 'ADVISOR')", name="scope"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("expected_ratio IS NULL OR (expected_ratio >= 0 AND expected_ratio <= 100)", name="expected_ratio"),
        CheckConstraint("source_type IN ('ROUND_POLICY','STUDENT_PLAN','ADVISOR')", name="source_type"),
        CheckConstraint("state IN ('DRAFT','OPEN','CLOSED','CANCELLED')", name="state"),
    )
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expected_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")


class DocumentDeadline(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "document_deadline"
    __table_args__ = (
        UniqueConstraint("round_id", "document_type"),
        CheckConstraint("document_type IN ('PROPOSAL','PLAN','REPORT','SUPPORTING')", name="document_type"),
        CheckConstraint("state IN ('OPEN','CLOSED')", name="state"),
    )
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN", server_default="OPEN")
    set_by: Mapped[uuid.UUID] = fk("user_account.id")
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ProgressReport(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "progress_report"
    __table_args__ = (
        UniqueConstraint("thesis_id", "milestone_id", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("reported_ratio IS NULL OR (reported_ratio >= 0 AND reported_ratio <= 100)", name="reported_ratio"),
        CheckConstraint("state IN ('DRAFT','SUBMITTED','CONFIRMED','REVISION_REQUIRED')", name="state"),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    milestone_id: Mapped[uuid.UUID] = fk("progress_milestone.id")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reported_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    evidence_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)
    due_at_at_submission: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_by: Mapped[uuid.UUID] = fk("student_profile.id")
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", server_default="DRAFT")


class ProgressReview(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "progress_review"
    __table_args__ = (
        CheckConstraint("decision IN ('COMMENT_ONLY','CONFIRM','REVISION_REQUIRED')", name="decision"),
        UniqueConstraint("progress_report_id", "reviewer_id"),
    )
    progress_report_id: Mapped[uuid.UUID] = fk("progress_report.id")
    reviewer_id: Mapped[uuid.UUID] = fk("lecturer_profile.id")
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)


class ProgressReviewAnnotation(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "progress_review_annotation"
    __table_args__ = (
        CheckConstraint("state IN ('DRAFT','PUBLISHED')", name="state"),
        CheckConstraint("page_number IS NULL OR page_number BETWEEN 1 AND 10000", name="page_number"),
        CheckConstraint("(x IS NULL AND y IS NULL) OR (page_number IS NOT NULL AND x IS NOT NULL AND y IS NOT NULL AND x BETWEEN 0 AND 1 AND y BETWEEN 0 AND 1)", name="coordinates"),
        CheckConstraint("(state = 'DRAFT' AND published_at IS NULL) OR (state = 'PUBLISHED' AND published_at IS NOT NULL AND length(trim(comment)) > 0)", name="publication"),
        Index("ix_progress_review_annotation_report_reviewer", "progress_report_id", "reviewer_id", "state"),
        Index("ix_progress_review_annotation_document_reviewer", "document_version_id", "reviewer_id", "state"),
        Index("ix_progress_review_annotation_proposal_reviewer", "proposal_version_id", "reviewer_id", "state"),
        CheckConstraint("num_nonnulls(progress_report_id, document_version_id, proposal_version_id) = 1", name="one_target"),
        CheckConstraint("annotation_kind IN ('PIN','SUMMARY','ATTACHMENT')", name="annotation_kind"),
        CheckConstraint("(annotation_kind = 'ATTACHMENT' AND attachment_file_id IS NOT NULL) OR (annotation_kind IN ('PIN','SUMMARY') AND attachment_file_id IS NULL)", name="attachment_kind"),
        CheckConstraint("annotation_kind = 'PIN' OR (page_number IS NULL AND x IS NULL AND y IS NULL)", name="kind_coordinates"),
        Index("uq_review_summary_progress", "progress_report_id", "reviewer_id", unique=True, postgresql_where=text("annotation_kind = 'SUMMARY' AND progress_report_id IS NOT NULL")),
        Index("uq_review_summary_document", "document_version_id", "reviewer_id", unique=True, postgresql_where=text("annotation_kind = 'SUMMARY' AND document_version_id IS NOT NULL")),
        Index("uq_review_summary_proposal", "proposal_version_id", "reviewer_id", unique=True, postgresql_where=text("annotation_kind = 'SUMMARY' AND proposal_version_id IS NOT NULL")),
    )
    progress_report_id: Mapped[Optional[uuid.UUID]] = fk("progress_report.id", nullable=True)
    document_version_id: Mapped[Optional[uuid.UUID]] = fk("document_version.id", nullable=True)
    proposal_version_id: Mapped[Optional[uuid.UUID]] = fk("proposal_version.id", nullable=True)
    reviewer_id: Mapped[uuid.UUID] = fk("lecturer_profile.id")
    stored_file_id: Mapped[uuid.UUID] = fk("stored_file.id")
    annotation_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="PIN", server_default="PIN")
    attachment_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    x: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 7))
    y: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 7))
    location_label: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    quoted_text: Mapped[str] = mapped_column(String(1000), nullable=False, default="", server_default="")
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Document(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "document"
    __table_args__ = (
        CheckConstraint("visibility IN ('PRIVATE','ASSIGNED','INTERNAL','PUBLISHED')", name="visibility"),
        CheckConstraint("state IN ('DRAFT','ACTIVE','ARCHIVED','REVOKED')", name="state"),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="PRIVATE", server_default="PRIVATE")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")


class DocumentVersion(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "document_version"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint(
            "state IN ('DRAFT','SUBMITTED','RESULT_AVAILABLE','REVISION_REQUESTED','ACCEPTED','FINAL','SUPERSEDED')",
            name="state",
        ),
    )
    document_id: Mapped[uuid.UUID] = fk("document.id")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    stored_file_id: Mapped[uuid.UUID] = fk("stored_file.id")
    submitted_by: Mapped[uuid.UUID] = fk("student_profile.id")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at_at_submission: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", server_default="DRAFT")


class ThesisReview(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    """Mẫu 7/8, per student and immutable report version; submitted rows are immutable."""
    __tablename__ = "thesis_review"
    __table_args__ = (
        UniqueConstraint("thesis_member_id", "lecturer_id", "kind", "version_no"),
        CheckConstraint("kind IN ('ADVISOR','REVIEWER')", name="kind"),
        CheckConstraint("state IN ('DRAFT','SUBMITTED')", name="state"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("(kind = 'ADVISOR' AND advisor_assignment_id IS NOT NULL AND reviewer_assignment_id IS NULL) OR (kind = 'REVIEWER' AND reviewer_assignment_id IS NOT NULL AND advisor_assignment_id IS NULL)", name="assignment_matches_kind"),
        CheckConstraint("state = 'DRAFT' OR submitted_at IS NOT NULL", name="submitted_metadata"),
        CheckConstraint("(paper_confirmed_by IS NULL AND paper_confirmed_at IS NULL AND paper_reference IS NULL AND paper_export_code IS NULL) OR (state = 'SUBMITTED' AND paper_confirmed_by IS NOT NULL AND paper_confirmed_at IS NOT NULL AND length(trim(paper_reference)) >= 5 AND paper_export_code IS NOT NULL)", name="paper_receipt_metadata"),
        Index("ix_thesis_review_thesis_member", "thesis_id", "thesis_member_id"),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    thesis_member_id: Mapped[uuid.UUID] = fk("thesis_member.id")
    lecturer_id: Mapped[uuid.UUID] = fk("lecturer_profile.id")
    advisor_assignment_id: Mapped[Optional[uuid.UUID]] = fk("advisor_assignment.id", nullable=True)
    reviewer_assignment_id: Mapped[Optional[uuid.UUID]] = fk("reviewer_assignment.id", nullable=True)
    report_version_id: Mapped[uuid.UUID] = fk("document_version.id")
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    sections: Mapped[dict] = mapped_column(JSONB, nullable=False)
    thesis_completed: Mapped[Optional[bool]] = mapped_column(Boolean)
    allow_defense: Mapped[Optional[bool]] = mapped_column(Boolean)
    signed_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)
    paper_reference: Mapped[Optional[str]] = mapped_column(String(500))
    paper_export_code: Mapped[Optional[str]] = mapped_column(String(100))
    paper_confirmed_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    paper_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source_reference: Mapped[Optional[str]] = mapped_column(String(500))
    revision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class DefenseEligibilityCheck(UuidPrimaryKeyMixin, Base):
    """Append-only school eligibility decision, separately recorded for each student."""
    __tablename__ = "defense_eligibility_check"
    __table_args__ = (
        UniqueConstraint("thesis_member_id", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("discipline_status IN ('CLEAR','WARNING_OR_HIGHER','UNKNOWN')", name="discipline_status"),
        CheckConstraint("state IN ('ELIGIBLE','BLOCKED')", name="state"),
        Index("ix_defense_eligibility_check_thesis_member", "thesis_id", "thesis_member_id"),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    thesis_member_id: Mapped[uuid.UUID] = fk("thesis_member.id")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    report_version_id: Mapped[Optional[uuid.UUID]] = fk("document_version.id", nullable=True)
    advisor_review_id: Mapped[Optional[uuid.UUID]] = fk("thesis_review.id", nullable=True)
    discipline_status: Mapped[str] = mapped_column(String(30), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    checked_by: Mapped[uuid.UUID] = fk("user_account.id")
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegistrationFormVersion(UuidPrimaryKeyMixin, Base):
    __tablename__ = "registration_form_version"
    __table_args__ = (
        UniqueConstraint("registration_id", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("form_code IN ('1A','1B')", name="form_code"),
        CheckConstraint("length(content_sha256) = 64 AND length(registration_fingerprint) = 64", name="hash_length"),
    )
    registration_id: Mapped[uuid.UUID] = fk("topic_registration.id")
    stored_file_id: Mapped[uuid.UUID] = fk("stored_file.id")
    submitted_by: Mapped[uuid.UUID] = fk("student_profile.id")
    form_code: Mapped[str] = mapped_column(String(2), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    registration_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEvent(UuidPrimaryKeyMixin, Base):
    __tablename__ = "audit_event"
    __table_args__ = (Index("ix_audit_event_occurred_id", "occurred_at", "id"),)
    actor_id: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    before_hash: Mapped[Optional[str]] = mapped_column(String(64))
    after_hash: Mapped[Optional[str]] = mapped_column(String(64))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    source_reference: Mapped[Optional[str]] = mapped_column(String(500))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)


class UserNotification(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """A short in-web notice addressed to one account.

    Older proposal/registration notices are keyed by registration; later thesis and
    account notices may instead carry thesis/subject/message/url. No separate table.
    """
    __tablename__ = "user_notification"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('PROPOSAL_SUBMITTED','PROPOSAL_APPROVED','PROPOSAL_REVIEWED','PROPOSAL_FINALIZED',"
            "'REGISTRATION_SUBMITTED','REGISTRATION_JOINED','REGISTRATION_ACCEPTED','REGISTRATION_REJECTED',"
            "'MILESTONE_OPENED','MILESTONE_EXTENDED','MILESTONE_REOPENED','MILESTONE_CLOSED',"
            "'DOCUMENT_DEADLINE_SET','DOCUMENT_DEADLINE_EXTENDED','DOCUMENT_DEADLINE_REOPENED','DOCUMENT_DEADLINE_CLOSED',"
            "'PROGRESS_SUBMITTED','PROGRESS_CONFIRMED','PROGRESS_REVISION_REQUIRED','PROGRESS_COMMENT',"
            "'DOCUMENT_SUBMITTED','DOCUMENT_ACCEPTED','DOCUMENT_REVISION_REQUESTED',"
            "'WORK_SUBMITTED','WORK_APPROVED','WORK_REVISION_REQUIRED',"
            "'ACCOUNT_LOCKED','ACCOUNT_UNLOCKED','ACCOUNT_DISABLED','ACCOUNT_RESTORED',"
            "'ACCOUNT_LINK_REISSUED','ACCOUNT_EMAIL_CORRECTED',"
            "'REGISTRATION_FORM_SUBMITTED','PROPOSAL_REVIEWER_ASSIGNED',"
            "'PROGRESS_REVIEWER_ASSIGNED','PROPOSAL_DEAN_CONFIRMED','WORKFLOW_NOTICE')",
            name="kind",
        ),
        Index("ix_user_notification_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_user_notification_thesis_created", "thesis_id", "created_at"),
    )
    recipient_user_id: Mapped[uuid.UUID] = fk("user_account.id")
    actor_user_id: Mapped[uuid.UUID] = fk("user_account.id")
    registration_id: Mapped[Optional[uuid.UUID]] = fk("topic_registration.id", nullable=True)
    thesis_id: Mapped[Optional[uuid.UUID]] = fk("thesis.id", nullable=True)
    subject_type: Mapped[Optional[str]] = mapped_column(String(40))
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    message: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ThesisWithdrawalRequest(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "thesis_withdrawal_request"
    __table_args__ = (
        CheckConstraint("state IN ('SUBMITTED','ADVISOR_CONFIRMED','RETURNED','CANCELLED','RECORDED','NOT_GRANTED')", name="state"),
        CheckConstraint("length(trim(reason)) >= 10", name="reason"),
        CheckConstraint("jsonb_typeof(application_data) = 'object'", name="application_data"),
        CheckConstraint("state NOT IN ('ADVISOR_CONFIRMED','RETURNED') OR (advisor_reviewed_by IS NOT NULL AND advisor_reviewed_at IS NOT NULL AND advisor_comment IS NOT NULL)", name="advisor_stamp"),
        CheckConstraint("state NOT IN ('RECORDED','NOT_GRANTED') OR (recorded_by IS NOT NULL AND recorded_at IS NOT NULL AND official_reference IS NOT NULL AND effective_on IS NOT NULL)", name="outcome_stamp"),
        Index("uq_withdrawal_member_open", "thesis_id", "student_id", unique=True, postgresql_where=text("state IN ('SUBMITTED','ADVISOR_CONFIRMED','RECORDED')")),
        Index("ix_withdrawal_student_state", "student_id", "state"),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    student_id: Mapped[uuid.UUID] = fk("student_profile.id")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    application_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    execution_starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(25), nullable=False, default="SUBMITTED", server_default="SUBMITTED")
    advisor_reviewed_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    advisor_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    advisor_comment: Mapped[Optional[str]] = mapped_column(Text)
    evidence_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)
    official_reference: Mapped[Optional[str]] = mapped_column(String(500))
    outcome_note: Mapped[Optional[str]] = mapped_column(Text)
    effective_on: Mapped[Optional[date]] = mapped_column(Date)
    recorded_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class DefenseCouncil(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "defense_council"
    __table_args__ = (UniqueConstraint("round_id", "department_id", "name"),)
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    department_id: Mapped[uuid.UUID] = fk("department.id")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    reference: Mapped[str] = mapped_column(String(300), nullable=False)
    members: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID] = fk("user_account.id")
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ThesisChangeRequest(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "thesis_change_request"
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="GROUP", server_default="GROUP")
    __table_args__ = (
        CheckConstraint("kind IN ('ADJUSTMENT','REPLACEMENT')", name="kind"),
        CheckConstraint("scope IN ('GROUP','INDIVIDUAL') AND (scope = 'GROUP' OR kind = 'REPLACEMENT')", name="scope"),
        CheckConstraint("state IN ('SUBMITTED','ADVISOR_REVIEWED','APPROVED','REJECTED','CANCELLED')", name="state"),
        CheckConstraint("length(trim(reason)) >= 10", name="reason"),
        CheckConstraint("state != 'APPROVED' OR (decided_by IS NOT NULL AND decided_at IS NOT NULL)", name="decision"),
        Index("uq_thesis_change_open", "thesis_id", unique=True,
            postgresql_where=text("state IN ('SUBMITTED','ADVISOR_REVIEWED')")),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    kind: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(25), default="SUBMITTED")
    requested_by: Mapped[uuid.UUID] = fk("user_account.id")
    reason: Mapped[str] = mapped_column(Text)
    proposed_title: Mapped[str] = mapped_column(String(500))
    proposed_description: Mapped[str] = mapped_column(Text)
    target_topic_id: Mapped[Optional[uuid.UUID]] = fk("topic.id", nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    consents: Mapped[dict] = mapped_column(JSONB)
    reviews: Mapped[dict] = mapped_column(JSONB)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[Optional[str]] = mapped_column(Text)


class ThesisExtension(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "thesis_extension"
    __table_args__ = (
        UniqueConstraint("thesis_id"),
        CheckConstraint("until_at > original_due_at", name="later_due"),
        CheckConstraint("length(trim(reference)) >= 5", name="reference"),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    original_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    until_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision_on: Mapped[date] = mapped_column(Date)
    reference: Mapped[str] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID] = fk("user_account.id")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence_file_id: Mapped[Optional[uuid.UUID]] = fk("stored_file.id", nullable=True)


class DefenseSlot(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "defense_slot"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="time_order"),
        CheckConstraint("(finalized_at IS NULL) = (finalized_by IS NULL)", name="finalized_stamp"),
        Index("ix_defense_slot_council_start", "council_id", "starts_at"),
        Index("uq_defense_slot_active_thesis", "thesis_id", unique=True, postgresql_where=text("finalized_at IS NULL")),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    prior_slot_id: Mapped[Optional[uuid.UUID]] = fk("defense_slot.id", nullable=True)
    council_id: Mapped[uuid.UUID] = fk("defense_council.id")
    report_version_id: Mapped[uuid.UUID] = fk("document_version.id")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    room: Mapped[str] = mapped_column(String(200), nullable=False)
    roster: Mapped[list] = mapped_column(JSONB, nullable=False)
    marks: Mapped[dict] = mapped_column(JSONB, nullable=False)
    attendance: Mapped[dict] = mapped_column(JSONB, nullable=False)
    minutes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    finalized_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class DefenseAbsenceDecision(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "defense_absence_decision"
    __table_args__ = (
        UniqueConstraint("slot_id", "thesis_member_id"),
        CheckConstraint("outcome IN ('NOT_PASSED','SUPPLEMENTARY')", name="outcome"),
    )
    slot_id: Mapped[uuid.UUID] = fk("defense_slot.id")
    thesis_member_id: Mapped[uuid.UUID] = fk("thesis_member.id")
    outcome: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str] = mapped_column(String(300))
    reason: Mapped[str] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID] = fk("user_account.id")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DefensePrintRecord(UuidPrimaryKeyMixin, Base):
    __tablename__ = "defense_print_record"
    __table_args__ = (
        CheckConstraint("(form IN (6,9) AND slot_id IS NOT NULL) OR (form IN (10,11) AND slot_id IS NULL)", name="scope"),
        Index("ix_defense_print_record_round", "round_id", "created_at"),
    )
    round_id: Mapped[uuid.UUID] = fk("thesis_round.id")
    slot_id: Mapped[Optional[uuid.UUID]] = fk("defense_slot.id", nullable=True)
    created_by: Mapped[uuid.UUID] = fk("user_account.id")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    form: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    source: Mapped[dict] = mapped_column(JSONB)


class DefenseCorrection(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "defense_correction"
    __table_args__ = (
        CheckConstraint("state IN ('PENDING','APPROVED','REJECTED','CANCELLED')", name="state"),
        Index("uq_defense_correction_pending", "slot_id", unique=True, postgresql_where=text("state = 'PENDING'")),
    )
    slot_id: Mapped[uuid.UUID] = fk("defense_slot.id")
    requested_by: Mapped[uuid.UUID] = fk("user_account.id")
    source_version: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(20))
    proposal: Mapped[dict] = mapped_column(JSONB)
    before: Mapped[dict] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(Text)
    reference: Mapped[str] = mapped_column(String(500))
    decided_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[Optional[str]] = mapped_column(Text)


class ThesisArchiveVersion(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "thesis_archive_version"
    __table_args__ = (
        UniqueConstraint("thesis_id", "version_no"),
        CheckConstraint("state IN ('SUBMITTED','RETURNED','ACCEPTED')", name="state"),
        CheckConstraint("(state = 'SUBMITTED' AND decided_at IS NULL AND decided_by IS NULL AND decision_note IS NULL) OR (state IN ('RETURNED','ACCEPTED') AND decided_at IS NOT NULL AND decided_by IS NOT NULL AND decision_note IS NOT NULL AND length(trim(decision_note)) >= 5)", name="decision"),
        Index("uq_thesis_archive_pending", "thesis_id", unique=True, postgresql_where=text("state = 'SUBMITTED'")),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    file_id: Mapped[uuid.UUID] = fk("stored_file.id")
    submitted_by: Mapped[uuid.UUID] = fk("user_account.id")
    version_no: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(20))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    decided_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[Optional[str]] = mapped_column(Text)


class ThesisExtensionRequest(UuidPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "thesis_extension_request"
    __table_args__ = (
        CheckConstraint("state IN ('SUBMITTED','ADVISOR_REVIEWED','APPROVED','REJECTED','CANCELLED','EXPIRED')", name="state"),
        CheckConstraint("requested_until_at > original_due_at", name="requested_window"),
        CheckConstraint("length(trim(reason)) >= 10", name="reason"),
        CheckConstraint("consent_due_at IS NULL OR consent_due_at > submitted_at", name="consent_window"),
        CheckConstraint("(state NOT IN ('APPROVED','REJECTED') OR (decided_by IS NOT NULL AND decided_at IS NOT NULL))", name="decision"),
        CheckConstraint("state != 'APPROVED' OR (extension_id IS NOT NULL AND extension_starts_at IS NOT NULL)", name="approved_record"),
        Index("uq_thesis_extension_request_open", "thesis_id", unique=True,
            postgresql_where=text("state IN ('SUBMITTED','ADVISOR_REVIEWED')")),
    )
    thesis_id: Mapped[uuid.UUID] = fk("thesis.id")
    requested_by: Mapped[uuid.UUID] = fk("user_account.id")
    original_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    requested_until_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(25), default="SUBMITTED")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    advisor_reviewed_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    advisor_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    advisor_reason: Mapped[Optional[str]] = mapped_column(Text)
    decided_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[Optional[str]] = mapped_column(Text)
    extension_starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    extension_id: Mapped[Optional[uuid.UUID]] = fk("thesis_extension.id", nullable=True)


class ThesisExtensionConsent(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "thesis_extension_consent"
    __table_args__ = (
        UniqueConstraint("request_id", "student_id"),
        CheckConstraint("decision IN ('PENDING','AGREE','DECLINE')", name="decision"),
        CheckConstraint("(decision = 'PENDING' AND responded_by IS NULL AND responded_at IS NULL) OR (decision IN ('AGREE','DECLINE') AND responded_by IS NOT NULL AND responded_at IS NOT NULL)", name="response"),
    )
    request_id: Mapped[uuid.UUID] = fk("thesis_extension_request.id")
    student_id: Mapped[uuid.UUID] = fk("student_profile.id")
    decision: Mapped[str] = mapped_column(String(20), default="PENDING", server_default="PENDING")
    responded_by: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
