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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin, VersionedMixin


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
    major_code: Mapped[Optional[str]] = mapped_column(String(32))


class LecturerProfile(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lecturer_profile"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    lecturer_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    department_id: Mapped[uuid.UUID] = fk("department.id")
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)


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
    )
    academic_year_id: Mapped[uuid.UUID] = fk("academic_year.id")
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    round_type: Mapped[str] = mapped_column(String(20), nullable=False)
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")


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
        UniqueConstraint("proposal_id", "signature_type"),
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
    __table_args__ = (
        UniqueConstraint("round_id", "code", "version_no"),
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("expected_ratio IS NULL OR (expected_ratio >= 0 AND expected_ratio <= 100)", name="expected_ratio"),
        CheckConstraint("source_type IN ('ROUND_POLICY','STUDENT_PLAN')", name="source_type"),
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
        CheckConstraint("document_type IN ('PROPOSAL','PLAN','SUPPORTING')", name="document_type"),
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


class AuditEvent(UuidPrimaryKeyMixin, Base):
    __tablename__ = "audit_event"
    actor_id: Mapped[Optional[uuid.UUID]] = fk("user_account.id", nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    before_hash: Mapped[Optional[str]] = mapped_column(String(64))
    after_hash: Mapped[Optional[str]] = mapped_column(String(64))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)


class UserNotification(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_notification"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('PROPOSAL_SUBMITTED','PROPOSAL_APPROVED','REGISTRATION_SUBMITTED','REGISTRATION_JOINED','REGISTRATION_ACCEPTED','REGISTRATION_REJECTED')",
            name="kind",
        ),
        Index("ix_user_notification_recipient_created", "recipient_user_id", "created_at"),
    )
    recipient_user_id: Mapped[uuid.UUID] = fk("user_account.id")
    actor_user_id: Mapped[uuid.UUID] = fk("user_account.id")
    registration_id: Mapped[uuid.UUID] = fk("topic_registration.id")
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
