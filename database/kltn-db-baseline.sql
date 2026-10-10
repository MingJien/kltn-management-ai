-- KLTN PostgreSQL baseline dùng một lần trên database mới, trống.
-- Alembic 20261010_0013; không chạy lại trên kltn_ai/kltn_dev đã có bảng.
-- Tạo bảng/khóa rồi nạp duy nhất marker Alembic và rubric Mẫu 6 DRAFT.

BEGIN;

CREATE TABLE academic_year (
    code character varying(20) NOT NULL,
    starts_on date NOT NULL,
    ends_on date NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_academic_year_date_window CHECK ((ends_on > starts_on)),
    CONSTRAINT ck_academic_year_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'ACTIVE'::character varying, 'CLOSED'::character varying])::text[])))
);

CREATE TABLE advisor_assignment (
    thesis_id uuid NOT NULL,
    lecturer_id uuid NOT NULL,
    assignment_type character varying(20) DEFAULT 'PRIMARY'::character varying NOT NULL,
    assigned_by uuid NOT NULL,
    effective_from timestamp with time zone NOT NULL,
    effective_to timestamp with time zone,
    state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_advisor_assignment_assignment_type CHECK (((assignment_type)::text = 'PRIMARY'::text)),
    CONSTRAINT ck_advisor_assignment_state CHECK (((state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'ENDED'::character varying, 'REVOKED'::character varying])::text[])))
);

CREATE TABLE advisor_review (
    advisor_assignment_id uuid NOT NULL,
    thesis_member_id uuid NOT NULL,
    document_version_id uuid NOT NULL,
    version_no integer NOT NULL,
    attitude text NOT NULL,
    content_response text NOT NULL,
    presentation text NOT NULL,
    defense_recommendation character varying(20) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_advisor_review_defense_recommendation CHECK (((defense_recommendation)::text = ANY ((ARRAY['ALLOW'::character varying, 'DENY'::character varying])::text[]))),
    CONSTRAINT ck_advisor_review_version_positive CHECK ((version_no > 0))
);

CREATE TABLE alembic_version (
    version_num character varying(32) NOT NULL
);

CREATE TABLE audit_event (
    actor_id uuid,
    action character varying(100) NOT NULL,
    resource_type character varying(100) NOT NULL,
    resource_id uuid NOT NULL,
    before_hash character varying(64),
    after_hash character varying(64),
    reason text,
    occurred_at timestamp with time zone NOT NULL,
    correlation_id uuid NOT NULL,
    id uuid NOT NULL
);

CREATE TABLE bonus_evidence (
    thesis_member_id uuid NOT NULL,
    evidence_type character varying(100) NOT NULL,
    reference character varying(500) NOT NULL,
    stored_file_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE council (
    round_id uuid NOT NULL,
    department_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    decision_ref character varying(500) NOT NULL,
    decision_date date NOT NULL,
    state character varying(20) DEFAULT 'IMPORTED'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_council_state CHECK (((state)::text = ANY ((ARRAY['IMPORTED'::character varying, 'VALIDATED'::character varying, 'ACTIVE'::character varying, 'CLOSED'::character varying])::text[])))
);

CREATE TABLE council_attendance (
    session_id uuid NOT NULL,
    council_member_id uuid NOT NULL,
    present boolean NOT NULL,
    recorded_by uuid NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    note text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL
);

CREATE TABLE council_member (
    council_id uuid NOT NULL,
    lecturer_id uuid NOT NULL,
    role_code character varying(20) NOT NULL,
    role_slot integer DEFAULT 1 NOT NULL,
    active boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_council_member_active_boolean CHECK ((active = ANY (ARRAY[true, false]))),
    CONSTRAINT ck_council_member_role_code CHECK (((role_code)::text = ANY ((ARRAY['CHAIR'::character varying, 'SECRETARY'::character varying, 'REVIEWER'::character varying, 'MEMBER'::character varying])::text[]))),
    CONSTRAINT ck_council_member_role_slot CHECK (((role_slot >= 1) AND (role_slot <= 2)))
);

CREATE TABLE council_minute (
    session_id uuid NOT NULL,
    minute_no character varying(100) NOT NULL,
    current_version_no integer DEFAULT 0 NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    printed_at timestamp with time zone,
    signed_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_council_minute_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'EXPORTED'::character varying, 'PRINTED'::character varying, 'SIGNED'::character varying, 'LOCKED'::character varying, 'VOID'::character varying, 'REPLACED'::character varying])::text[])))
);

CREATE TABLE defense_eligibility_check (
    thesis_member_id uuid NOT NULL,
    round_id uuid NOT NULL,
    advisor_review_id uuid,
    discipline_result character varying(40) NOT NULL,
    completion_result character varying(40) NOT NULL,
    advisor_result character varying(40) NOT NULL,
    local_policy_result character varying(40),
    similarity_result character varying(40),
    result character varying(30) NOT NULL,
    reason text,
    checked_by uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_defense_eligibility_check_result CHECK (((result)::text = ANY ((ARRAY['ELIGIBLE'::character varying, 'NOT_ELIGIBLE'::character varying, 'PENDING_POLICY'::character varying])::text[])))
);

CREATE TABLE defense_session (
    council_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    scheduled_at timestamp with time zone NOT NULL,
    location character varying(255) NOT NULL,
    state character varying(30) DEFAULT 'SCHEDULED'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_defense_session_state CHECK (((state)::text = ANY ((ARRAY['SCHEDULED'::character varying, 'ATTENDANCE_OPEN'::character varying, 'READY'::character varying, 'POSTPONED'::character varying, 'SCORING'::character varying, 'FINALIZED'::character varying, 'CLOSED'::character varying])::text[])))
);

CREATE TABLE department (
    faculty_id uuid NOT NULL,
    code character varying(32) NOT NULL,
    name character varying(255) NOT NULL,
    major_code character varying(32),
    active boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE document (
    thesis_id uuid NOT NULL,
    document_type character varying(50) NOT NULL,
    title character varying(500) NOT NULL,
    visibility character varying(20) DEFAULT 'PRIVATE'::character varying NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_document_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'ACTIVE'::character varying, 'ARCHIVED'::character varying, 'REVOKED'::character varying])::text[]))),
    CONSTRAINT ck_document_visibility CHECK (((visibility)::text = ANY ((ARRAY['PRIVATE'::character varying, 'ASSIGNED'::character varying, 'INTERNAL'::character varying, 'PUBLISHED'::character varying])::text[])))
);

CREATE TABLE document_version (
    document_id uuid NOT NULL,
    version_no integer NOT NULL,
    stored_file_id uuid NOT NULL,
    submitted_by uuid NOT NULL,
    submitted_at timestamp with time zone NOT NULL,
    content_sha256 character varying(64) NOT NULL,
    state character varying(30) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_document_version_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'RESULT_AVAILABLE'::character varying, 'REVISION_REQUESTED'::character varying, 'ACCEPTED'::character varying, 'FINAL'::character varying, 'SUPERSEDED'::character varying])::text[]))),
    CONSTRAINT ck_document_version_version_positive CHECK ((version_no > 0))
);

CREATE TABLE eligibility_exception (
    snapshot_id uuid NOT NULL,
    official_ref character varying(500) NOT NULL,
    reason text NOT NULL,
    granted_by uuid NOT NULL,
    granted_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE eligibility_snapshot (
    student_id uuid NOT NULL,
    round_id uuid NOT NULL,
    version integer NOT NULL,
    evidence_ref character varying(500) NOT NULL,
    captured_at timestamp with time zone NOT NULL,
    confirmed_by uuid,
    confirmed_at timestamp with time zone,
    decision_reason text,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    passed_credit_ratio numeric(5,4),
    gpa_4 numeric(3,2),
    CONSTRAINT ck_eligibility_snapshot_credit_ratio CHECK (((passed_credit_ratio >= (0)::numeric) AND (passed_credit_ratio <= (1)::numeric))),
    CONSTRAINT ck_eligibility_snapshot_decision_metadata CHECK ((((state)::text <> ALL ((ARRAY['CONFIRMED'::character varying, 'REJECTED'::character varying])::text[])) OR ((confirmed_by IS NOT NULL) AND (confirmed_at IS NOT NULL)))),
    CONSTRAINT ck_eligibility_snapshot_gpa CHECK (((gpa_4 >= (0)::numeric) AND (gpa_4 <= (4)::numeric))),
    CONSTRAINT ck_eligibility_snapshot_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'CONFIRMED'::character varying, 'REJECTED'::character varying])::text[]))),
    CONSTRAINT ck_eligibility_snapshot_version_positive CHECK ((version > 0))
);

CREATE TABLE evaluation (
    session_id uuid NOT NULL,
    evaluator_member_id uuid NOT NULL,
    thesis_member_id uuid NOT NULL,
    rubric_assignment_id uuid NOT NULL,
    total_points numeric(4,2) DEFAULT '0'::numeric NOT NULL,
    bonus_points numeric(4,2) DEFAULT '0'::numeric NOT NULL,
    status character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    submitted_at timestamp with time zone,
    correction_reason text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_evaluation_bonus_points CHECK (((bonus_points >= (0)::numeric) AND (bonus_points <= (1)::numeric))),
    CONSTRAINT ck_evaluation_bonus_within_total CHECK ((bonus_points <= total_points)),
    CONSTRAINT ck_evaluation_status CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'CORRECTED'::character varying, 'LOCKED'::character varying])::text[]))),
    CONSTRAINT ck_evaluation_total_points CHECK (((total_points >= (0)::numeric) AND (total_points <= (10)::numeric)))
);

CREATE TABLE evaluation_item (
    evaluation_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    points numeric(4,2) NOT NULL,
    comment text,
    bonus_evidence_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_evaluation_item_points_nonnegative CHECK ((points >= (0)::numeric))
);

CREATE TABLE expertise_evidence (
    expertise_id uuid NOT NULL,
    evidence_type character varying(50) NOT NULL,
    reference character varying(500) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE external_procedure_outcome (
    thesis_id uuid NOT NULL,
    outcome_type character varying(20) NOT NULL,
    official_ref character varying(500) NOT NULL,
    effective_at timestamp with time zone NOT NULL,
    evidence_file_id uuid,
    recorded_by uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_external_procedure_outcome_outcome_type CHECK (((outcome_type)::text = ANY ((ARRAY['WITHDRAWAL'::character varying, 'EXTENSION'::character varying])::text[])))
);

CREATE TABLE faculty (
    code character varying(32) NOT NULL,
    name character varying(255) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE final_result (
    session_id uuid NOT NULL,
    thesis_member_id uuid NOT NULL,
    scorer_count integer NOT NULL,
    average_score numeric(4,2) NOT NULL,
    bonus_average numeric(4,2) NOT NULL,
    final_score numeric(3,1) NOT NULL,
    calculation_version integer NOT NULL,
    calculated_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_final_result_average_score CHECK (((average_score >= (0)::numeric) AND (average_score <= (10)::numeric))),
    CONSTRAINT ck_final_result_bonus_average CHECK (((bonus_average >= (0)::numeric) AND (bonus_average <= (1)::numeric))),
    CONSTRAINT ck_final_result_calculation_version CHECK ((calculation_version > 0)),
    CONSTRAINT ck_final_result_final_score CHECK (((final_score >= (0)::numeric) AND (final_score <= (10)::numeric))),
    CONSTRAINT ck_final_result_scorer_count CHECK ((scorer_count > 0))
);

CREATE TABLE lecturer_expertise (
    lecturer_id uuid NOT NULL,
    version integer NOT NULL,
    labels jsonb NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    verified_by uuid,
    verified_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_lecturer_expertise_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'SELF_DECLARED'::character varying, 'VERIFIED'::character varying, 'REJECTED'::character varying])::text[]))),
    CONSTRAINT ck_lecturer_expertise_version_positive CHECK ((version > 0))
);

CREATE TABLE lecturer_profile (
    user_id uuid NOT NULL,
    lecturer_code character varying(32) NOT NULL,
    department_id uuid NOT NULL,
    display_name character varying(255) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE member_work_assignment (
    thesis_member_id uuid NOT NULL,
    version_no integer NOT NULL,
    work_description text NOT NULL,
    expected_output text NOT NULL,
    state character varying(30) DEFAULT 'DRAFT'::character varying NOT NULL,
    reviewed_by uuid,
    reviewed_at timestamp with time zone,
    review_comment text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_member_work_assignment_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'APPROVED'::character varying, 'REVISION_REQUIRED'::character varying])::text[]))),
    CONSTRAINT ck_member_work_assignment_version_positive CHECK ((version_no > 0))
);

CREATE TABLE minute_signature (
    minute_version_id uuid NOT NULL,
    signer_member_id uuid NOT NULL,
    signed_at timestamp with time zone NOT NULL,
    signature_ref character varying(500),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE minute_version (
    minute_id uuid NOT NULL,
    version_no integer NOT NULL,
    stored_file_id uuid NOT NULL,
    generated_by uuid NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    replacement_for_id uuid,
    void_reason text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_minute_version_not_self_replacement CHECK (((replacement_for_id IS NULL) OR (replacement_for_id <> id))),
    CONSTRAINT ck_minute_version_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'EXPORTED'::character varying, 'VOID'::character varying, 'PRINTED'::character varying, 'SIGNED'::character varying])::text[]))),
    CONSTRAINT ck_minute_version_version_positive CHECK ((version_no > 0))
);

CREATE TABLE organizational_position (
    code character varying(40) NOT NULL,
    name character varying(255) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_organizational_position_code CHECK (((code)::text = ANY ((ARRAY['DEPARTMENT_HEAD'::character varying, 'FACULTY_DEAN'::character varying])::text[])))
);

CREATE TABLE position_assignment (
    lecturer_id uuid NOT NULL,
    position_id uuid NOT NULL,
    faculty_id uuid,
    department_id uuid,
    effective_from timestamp with time zone NOT NULL,
    effective_to timestamp with time zone,
    state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_position_assignment_effective_window CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT ck_position_assignment_exactly_one_scope CHECK ((((faculty_id IS NOT NULL) AND (department_id IS NULL)) OR ((faculty_id IS NULL) AND (department_id IS NOT NULL)))),
    CONSTRAINT ck_position_assignment_state CHECK (((state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'REVOKED'::character varying, 'EXPIRED'::character varying])::text[])))
);

CREATE TABLE progress_milestone (
    round_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    version_no integer NOT NULL,
    due_at timestamp with time zone,
    expected_ratio numeric(5,2),
    source_type character varying(20) NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_progress_milestone_expected_ratio CHECK (((expected_ratio IS NULL) OR ((expected_ratio >= (0)::numeric) AND (expected_ratio <= (100)::numeric)))),
    CONSTRAINT ck_progress_milestone_source_type CHECK (((source_type)::text = ANY ((ARRAY['ROUND_POLICY'::character varying, 'STUDENT_PLAN'::character varying])::text[]))),
    CONSTRAINT ck_progress_milestone_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'OPEN'::character varying, 'CLOSED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT ck_progress_milestone_version_positive CHECK ((version_no > 0))
);

CREATE TABLE progress_report (
    thesis_id uuid NOT NULL,
    milestone_id uuid NOT NULL,
    version_no integer NOT NULL,
    summary text NOT NULL,
    reported_ratio numeric(5,2),
    evidence_file_id uuid,
    submitted_by uuid NOT NULL,
    state character varying(30) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_progress_report_reported_ratio CHECK (((reported_ratio IS NULL) OR ((reported_ratio >= (0)::numeric) AND (reported_ratio <= (100)::numeric)))),
    CONSTRAINT ck_progress_report_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'CONFIRMED'::character varying, 'REVISION_REQUIRED'::character varying])::text[]))),
    CONSTRAINT ck_progress_report_version_positive CHECK ((version_no > 0))
);

CREATE TABLE progress_review (
    progress_report_id uuid NOT NULL,
    reviewer_id uuid NOT NULL,
    decision character varying(30) NOT NULL,
    comment text NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_progress_review_decision CHECK (((decision)::text = ANY ((ARRAY['COMMENT_ONLY'::character varying, 'CONFIRM'::character varying, 'REVISION_REQUIRED'::character varying])::text[])))
);

CREATE TABLE proposal (
    thesis_id uuid NOT NULL,
    current_version_no integer,
    state character varying(40) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_proposal_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'UNDER_REVIEW'::character varying, 'REVISION_REQUIRED'::character varying, 'ADVISOR_CONFIRMED'::character varying, 'DEPARTMENT_FINALIZED'::character varying, 'DEAN_CONFIRMED'::character varying, 'PRINT_READY'::character varying])::text[])))
);

CREATE TABLE proposal_review (
    proposal_version_id uuid NOT NULL,
    reviewer_assignment_id uuid NOT NULL,
    reviewer_user_id uuid NOT NULL,
    decision character varying(30) NOT NULL,
    comment text NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_proposal_review_decision CHECK (((decision)::text = ANY ((ARRAY['COMMENT'::character varying, 'REVISION_REQUIRED'::character varying, 'CONFIRM'::character varying])::text[])))
);

CREATE TABLE proposal_version (
    proposal_id uuid NOT NULL,
    version_no integer NOT NULL,
    stored_file_id uuid NOT NULL,
    submitted_by uuid NOT NULL,
    submitted_at timestamp with time zone NOT NULL,
    content_sha256 character varying(64) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_proposal_version_version_positive CHECK ((version_no > 0))
);

CREATE TABLE registration_member (
    registration_id uuid NOT NULL,
    round_id uuid NOT NULL,
    student_id uuid NOT NULL,
    is_coordinator boolean DEFAULT false NOT NULL,
    active boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    consent_status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    responded_by_user_id uuid,
    responded_at timestamp with time zone,
    evidence_file_id uuid,
    CONSTRAINT ck_registration_member_consent_consistency CHECK (((((consent_status)::text = 'PENDING'::text) AND (responded_by_user_id IS NULL) AND (responded_at IS NULL)) OR (((consent_status)::text = ANY ((ARRAY['ACCEPTED'::character varying, 'DECLINED'::character varying])::text[])) AND (responded_by_user_id IS NOT NULL) AND (responded_at IS NOT NULL))))
);

CREATE TABLE repository_item (
    thesis_id uuid,
    published_document_version_id uuid,
    title character varying(500) NOT NULL,
    abstract text,
    keywords jsonb NOT NULL,
    source_type character varying(50) DEFAULT 'THESIS'::character varying NOT NULL,
    visibility character varying(20) DEFAULT 'INTERNAL'::character varying NOT NULL,
    published_at timestamp with time zone,
    revoked_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    stored_file_id uuid,
    origin_type character varying(30) DEFAULT 'MANAGED_THESIS'::character varying NOT NULL,
    source_ref character varying(500),
    provenance text,
    source_version character varying(100),
    external_source_id character varying(200),
    source_url character varying(1000),
    CONSTRAINT ck_repository_item_ck_repository_item_has_source_reference CHECK (((source_ref IS NOT NULL) OR (source_url IS NOT NULL) OR (stored_file_id IS NOT NULL) OR (published_document_version_id IS NOT NULL))),
    CONSTRAINT ck_repository_item_ck_repository_item_origin_source_consistency CHECK (((((origin_type)::text = 'MANAGED_THESIS'::text) AND ((source_type)::text = 'THESIS'::text) AND (thesis_id IS NOT NULL) AND (published_document_version_id IS NOT NULL)) OR (((origin_type)::text = 'IMPORTED_DOCUMENT'::text) AND ((source_type)::text = ANY ((ARRAY['THESIS'::character varying, 'CAPSTONE_PROJECT'::character varying, 'TERM_PROJECT'::character varying, 'COURSE_PROJECT'::character varying, 'SYNTHETIC_TEST'::character varying])::text[])) AND (thesis_id IS NULL) AND (published_document_version_id IS NULL)) OR (((origin_type)::text = 'OFFICIAL_SOURCE'::text) AND ((source_type)::text = ANY ((ARRAY['REGULATION'::character varying, 'FORM'::character varying, 'GUIDELINE'::character varying])::text[])) AND (thesis_id IS NULL) AND (published_document_version_id IS NULL)))),
    CONSTRAINT ck_repository_item_ck_repository_item_origin_type CHECK (((origin_type)::text = ANY ((ARRAY['MANAGED_THESIS'::character varying, 'IMPORTED_DOCUMENT'::character varying, 'OFFICIAL_SOURCE'::character varying])::text[]))),
    CONSTRAINT ck_repository_item_ck_repository_item_source_type CHECK (((source_type)::text = ANY ((ARRAY['THESIS'::character varying, 'CAPSTONE_PROJECT'::character varying, 'TERM_PROJECT'::character varying, 'COURSE_PROJECT'::character varying, 'REGULATION'::character varying, 'FORM'::character varying, 'GUIDELINE'::character varying, 'SYNTHETIC_TEST'::character varying])::text[]))),
    CONSTRAINT ck_repository_item_ck_repository_item_source_url_https CHECK (((source_url IS NULL) OR ((source_url)::text ~~ 'https://%'::text))),
    CONSTRAINT ck_repository_item_visibility CHECK (((visibility)::text = ANY ((ARRAY['INTERNAL'::character varying, 'PUBLISHED'::character varying, 'REVOKED'::character varying])::text[])))
);

CREATE TABLE resource_assignment (
    assignment_type character varying(50) NOT NULL,
    user_id uuid NOT NULL,
    round_id uuid,
    thesis_id uuid,
    council_id uuid,
    effective_from timestamp with time zone NOT NULL,
    effective_to timestamp with time zone,
    state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_resource_assignment_effective_window CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT ck_resource_assignment_exactly_one_resource CHECK ((((
CASE
    WHEN (round_id IS NULL) THEN 0
    ELSE 1
END +
CASE
    WHEN (thesis_id IS NULL) THEN 0
    ELSE 1
END) +
CASE
    WHEN (council_id IS NULL) THEN 0
    ELSE 1
END) = 1)),
    CONSTRAINT ck_resource_assignment_state CHECK (((state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'REVOKED'::character varying, 'EXPIRED'::character varying])::text[])))
);

CREATE TABLE retrieval_audit (
    user_id uuid NOT NULL,
    question_hash character varying(64) NOT NULL,
    authorized_scope_hash character varying(64) NOT NULL,
    retrieved_item_count integer DEFAULT 0 NOT NULL,
    provider character varying(100),
    model_version character varying(100),
    outcome character varying(30) NOT NULL,
    correlation_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_retrieval_audit_outcome CHECK (((outcome)::text = ANY ((ARRAY['ANSWERED'::character varying, 'NO_EVIDENCE'::character varying, 'DEPENDENCY_FAILED'::character varying, 'DENIED'::character varying])::text[])))
);

CREATE TABLE reviewer_assignment (
    lecturer_id uuid NOT NULL,
    proposal_id uuid,
    thesis_id uuid,
    review_scope character varying(20) NOT NULL,
    assigned_by uuid NOT NULL,
    assigned_at timestamp with time zone NOT NULL,
    state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_reviewer_assignment_exactly_one_subject CHECK ((((proposal_id IS NOT NULL) AND (thesis_id IS NULL)) OR ((proposal_id IS NULL) AND (thesis_id IS NOT NULL)))),
    CONSTRAINT ck_reviewer_assignment_review_scope CHECK (((review_scope)::text = ANY ((ARRAY['PROPOSAL'::character varying, 'THESIS'::character varying])::text[]))),
    CONSTRAINT ck_reviewer_assignment_scope_matches_subject CHECK (((((review_scope)::text = 'PROPOSAL'::text) AND (proposal_id IS NOT NULL)) OR (((review_scope)::text = 'THESIS'::text) AND (thesis_id IS NOT NULL)))),
    CONSTRAINT ck_reviewer_assignment_state CHECK (((state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'COMPLETED'::character varying, 'REVOKED'::character varying])::text[])))
);

CREATE TABLE reviewer_review (
    reviewer_assignment_id uuid NOT NULL,
    thesis_member_id uuid NOT NULL,
    document_version_id uuid NOT NULL,
    version_no integer NOT NULL,
    presentation text NOT NULL,
    research_quality text NOT NULL,
    contribution text NOT NULL,
    questions text NOT NULL,
    overall text NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_reviewer_review_version_positive CHECK ((version_no > 0))
);

CREATE TABLE round_policy (
    round_id uuid NOT NULL,
    policy_type character varying(50) NOT NULL,
    version integer NOT NULL,
    config_json jsonb NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    effective_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_round_policy_active_has_effective_at CHECK ((((state)::text <> 'ACTIVE'::text) OR (effective_at IS NOT NULL))),
    CONSTRAINT ck_round_policy_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'ACTIVE'::character varying, 'RETIRED'::character varying])::text[]))),
    CONSTRAINT ck_round_policy_version_positive CHECK ((version > 0))
);

CREATE TABLE rubric_assignment (
    rubric_template_id uuid NOT NULL,
    round_id uuid,
    session_id uuid,
    state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_rubric_assignment_exactly_one_scope CHECK ((((round_id IS NOT NULL) AND (session_id IS NULL)) OR ((round_id IS NULL) AND (session_id IS NOT NULL)))),
    CONSTRAINT ck_rubric_assignment_state CHECK (((state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'LOCKED'::character varying, 'RETIRED'::character varying])::text[])))
);

CREATE TABLE rubric_criterion (
    rubric_template_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    label character varying(500) NOT NULL,
    max_points numeric(4,2) NOT NULL,
    criterion_type character varying(20) DEFAULT 'NORMAL'::character varying NOT NULL,
    order_no integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    parent_id uuid,
    CONSTRAINT ck_rubric_criterion_bonus_max CHECK ((((criterion_type)::text <> 'BONUS'::text) OR (max_points <= (1)::numeric))),
    CONSTRAINT ck_rubric_criterion_criterion_type CHECK (((criterion_type)::text = ANY ((ARRAY['GROUP'::character varying, 'NORMAL'::character varying, 'BONUS'::character varying])::text[]))),
    CONSTRAINT ck_rubric_criterion_max_points CHECK (((max_points > (0)::numeric) AND (max_points <= (10)::numeric))),
    CONSTRAINT ck_rubric_criterion_not_self_parent CHECK (((parent_id IS NULL) OR (parent_id <> id))),
    CONSTRAINT ck_rubric_criterion_order_positive CHECK ((order_no > 0))
);

CREATE TABLE rubric_template (
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    version_no integer NOT NULL,
    source_ref character varying(500) NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_rubric_template_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'ACTIVE'::character varying, 'RETIRED'::character varying])::text[]))),
    CONSTRAINT ck_rubric_template_version_positive CHECK ((version_no > 0))
);

CREATE TABLE search_index_metadata (
    repository_item_id uuid NOT NULL,
    document_version_id uuid,
    index_name character varying(100) NOT NULL,
    index_version character varying(100) NOT NULL,
    embedding_model character varying(150),
    chunking_version character varying(100),
    external_point_namespace character varying(200),
    state character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    indexed_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_search_index_metadata_state CHECK (((state)::text = ANY ((ARRAY['PENDING'::character varying, 'INDEXED'::character varying, 'FAILED'::character varying, 'REMOVED'::character varying])::text[])))
);

CREATE TABLE session_thesis (
    session_id uuid NOT NULL,
    thesis_id uuid NOT NULL,
    order_no integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_session_thesis_order_positive CHECK ((order_no > 0))
);

CREATE TABLE signature_confirmation (
    proposal_id uuid NOT NULL,
    signature_type character varying(40) NOT NULL,
    signer_user_id uuid NOT NULL,
    confirmed_at timestamp with time zone NOT NULL,
    official_ref character varying(500),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    proposal_version_no integer NOT NULL,
    CONSTRAINT ck_signature_confirmation_ck_signature_confirmation_pro_6af3 CHECK ((proposal_version_no > 0)),
    CONSTRAINT ck_signature_confirmation_signature_type CHECK (((signature_type)::text = ANY ((ARRAY['DEPARTMENT_FINALIZATION'::character varying, 'DEAN_CONFIRMATION'::character varying])::text[])))
);

CREATE TABLE similarity_check (
    document_version_id uuid NOT NULL,
    policy_id uuid,
    metric_code character varying(100) NOT NULL,
    lexical_coverage_pct numeric(6,3),
    semantic_candidate_score numeric(10,6),
    business_status character varying(40),
    model_version character varying(100),
    index_version character varying(100),
    corpus_snapshot character varying(200),
    state character varying(20) DEFAULT 'QUEUED'::character varying NOT NULL,
    completed_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_similarity_check_state CHECK (((state)::text = ANY ((ARRAY['QUEUED'::character varying, 'RUNNING'::character varying, 'COMPLETED'::character varying, 'FAILED'::character varying])::text[])))
);

CREATE TABLE similarity_match (
    check_id uuid NOT NULL,
    source_document_version_id uuid,
    source_ref character varying(500) NOT NULL,
    input_start integer NOT NULL,
    input_end integer NOT NULL,
    matched_text_hash character varying(64),
    lexical_score numeric(10,6),
    semantic_score numeric(10,6),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    source_repository_item_id uuid,
    CONSTRAINT ck_similarity_match_input_range CHECK (((input_start >= 0) AND (input_end > input_start)))
);

CREATE TABLE similarity_policy (
    round_id uuid NOT NULL,
    version_no integer NOT NULL,
    metric_code character varying(100),
    threshold_value numeric(10,6),
    decision_mode character varying(20) DEFAULT 'ADVISORY'::character varying NOT NULL,
    config_json jsonb NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_similarity_policy_decision_mode CHECK (((decision_mode)::text = ANY ((ARRAY['ADVISORY'::character varying, 'GATE'::character varying])::text[]))),
    CONSTRAINT ck_similarity_policy_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'ACTIVE'::character varying, 'RETIRED'::character varying])::text[]))),
    CONSTRAINT ck_similarity_policy_threshold_nonnegative CHECK (((threshold_value IS NULL) OR (threshold_value >= (0)::numeric))),
    CONSTRAINT ck_similarity_policy_version_positive CHECK ((version_no > 0))
);

CREATE TABLE stored_file (
    storage_key character varying(500) NOT NULL,
    original_name character varying(500) NOT NULL,
    media_type character varying(150) NOT NULL,
    byte_size integer NOT NULL,
    sha256 character varying(64) NOT NULL,
    scan_state character varying(20) DEFAULT 'QUARANTINED'::character varying NOT NULL,
    scanned_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_stored_file_byte_size_positive CHECK ((byte_size > 0)),
    CONSTRAINT ck_stored_file_scan_state CHECK (((scan_state)::text = ANY ((ARRAY['QUARANTINED'::character varying, 'CLEAN'::character varying, 'INFECTED'::character varying, 'FAILED'::character varying])::text[])))
);

CREATE TABLE student_profile (
    user_id uuid NOT NULL,
    student_code character varying(32) NOT NULL,
    department_id uuid NOT NULL,
    display_name character varying(255) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    class_name character varying(100),
    major_code character varying(32)
);

CREATE TABLE thesis (
    round_id uuid NOT NULL,
    topic_id uuid NOT NULL,
    registration_id uuid NOT NULL,
    department_id uuid NOT NULL,
    current_title character varying(500) NOT NULL,
    state character varying(30) DEFAULT 'ACTIVE'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_thesis_state CHECK (((state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'PROPOSAL_APPROVED'::character varying, 'IN_PROGRESS'::character varying, 'EXTENDED'::character varying, 'WITHDRAWN'::character varying, 'READY_FOR_DEFENSE'::character varying, 'DEFENDED'::character varying, 'COMPLETED'::character varying, 'ARCHIVED'::character varying])::text[])))
);

CREATE TABLE thesis_member (
    thesis_id uuid NOT NULL,
    student_id uuid NOT NULL,
    is_coordinator boolean DEFAULT false NOT NULL,
    active boolean DEFAULT true NOT NULL,
    joined_at timestamp with time zone NOT NULL,
    left_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE thesis_round (
    academic_year_id uuid NOT NULL,
    code character varying(32) NOT NULL,
    round_type character varying(20) NOT NULL,
    opens_at timestamp with time zone NOT NULL,
    closes_at timestamp with time zone NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_thesis_round_round_type CHECK (((round_type)::text = ANY ((ARRAY['MAIN'::character varying, 'SUPPLEMENTARY'::character varying])::text[]))),
    CONSTRAINT ck_thesis_round_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'OPEN'::character varying, 'CLOSED'::character varying, 'ARCHIVED'::character varying])::text[]))),
    CONSTRAINT ck_thesis_round_time_window CHECK ((closes_at > opens_at))
);

CREATE TABLE topic (
    round_id uuid NOT NULL,
    department_id uuid NOT NULL,
    proposer_user_id uuid NOT NULL,
    proposer_type character varying(20) NOT NULL,
    current_title character varying(500) NOT NULL,
    description text,
    max_students integer DEFAULT 3 NOT NULL,
    state character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    decided_by uuid,
    decided_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    code character varying(40) NOT NULL,
    receiving_lecturer_id uuid,
    CONSTRAINT ck_topic_max_students CHECK (((max_students >= 1) AND (max_students <= 3))),
    CONSTRAINT ck_topic_proposer_type CHECK (((proposer_type)::text = ANY ((ARRAY['LECTURER'::character varying, 'STUDENT'::character varying])::text[]))),
    CONSTRAINT ck_topic_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'APPROVED'::character varying, 'RETURNED'::character varying, 'REJECTED'::character varying, 'LOCKED'::character varying])::text[])))
);

CREATE TABLE topic_change_request (
    thesis_id uuid NOT NULL,
    requested_by uuid NOT NULL,
    reason text NOT NULL,
    proposed_topic_id uuid,
    proposed_title character varying(500),
    advisor_reviewed_by uuid,
    advisor_reviewed_at timestamp with time zone,
    department_decided_by uuid,
    department_decided_at timestamp with time zone,
    state character varying(30) DEFAULT 'SUBMITTED'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_topic_change_request_state CHECK (((state)::text = ANY ((ARRAY['SUBMITTED'::character varying, 'ADVISOR_REVIEWED'::character varying, 'APPROVED'::character varying, 'REJECTED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT ck_topic_change_request_target_present CHECK (((proposed_topic_id IS NOT NULL) OR (proposed_title IS NOT NULL)))
);

CREATE TABLE topic_registration (
    round_id uuid NOT NULL,
    topic_id uuid NOT NULL,
    created_by uuid NOT NULL,
    state character varying(30) DEFAULT 'DRAFT'::character varying NOT NULL,
    submitted_at timestamp with time zone,
    lecturer_decided_by uuid,
    lecturer_decided_at timestamp with time zone,
    lecturer_reason text,
    department_finalized_by uuid,
    department_finalized_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    expected_member_count integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_topic_registration_expected_member_count CHECK (((expected_member_count >= 1) AND (expected_member_count <= 3))),
    CONSTRAINT ck_topic_registration_state CHECK (((state)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'LECTURER_ACCEPTED'::character varying, 'LECTURER_REJECTED'::character varying, 'RETURNED'::character varying, 'FINALIZED'::character varying, 'CANCELLED'::character varying])::text[])))
);

CREATE TABLE topic_requirement (
    topic_id uuid NOT NULL,
    requirement_type character varying(30) NOT NULL,
    value_text text,
    preferred_gpa numeric(3,2),
    enforcement character varying(20) DEFAULT 'DESIRED'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_topic_requirement_enforcement_desired CHECK (((enforcement)::text = 'DESIRED'::text)),
    CONSTRAINT ck_topic_requirement_preferred_gpa CHECK (((preferred_gpa IS NULL) OR ((preferred_gpa >= (0)::numeric) AND (preferred_gpa <= (4)::numeric)))),
    CONSTRAINT ck_topic_requirement_requirement_type CHECK (((requirement_type)::text = ANY ((ARRAY['PREFERRED_GPA'::character varying, 'SKILL'::character varying, 'TECHNOLOGY'::character varying, 'KNOWLEDGE'::character varying, 'OTHER'::character varying])::text[])))
);

CREATE TABLE topic_title_version (
    topic_id uuid NOT NULL,
    version_no integer NOT NULL,
    title character varying(500) NOT NULL,
    changed_by uuid NOT NULL,
    change_reason text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_topic_title_version_version_positive CHECK ((version_no > 0))
);

CREATE TABLE user_account (
    external_subject character varying(255),
    base_role character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    email character varying(255),
    password_hash character varying(255),
    email_verified_at timestamp with time zone,
    CONSTRAINT ck_user_account_base_role CHECK (((base_role)::text = ANY ((ARRAY['ADMIN'::character varying, 'LECTURER'::character varying, 'STUDENT'::character varying])::text[]))),
    CONSTRAINT ck_user_account_email_normalized CHECK (((email IS NULL) OR ((email)::text = lower((email)::text)))),
    CONSTRAINT ck_user_account_identity_present CHECK (((external_subject IS NOT NULL) OR (email IS NOT NULL))),
    CONSTRAINT ck_user_account_local_credentials_pair CHECK ((((email IS NULL) AND (password_hash IS NULL)) OR ((email IS NOT NULL) AND (password_hash IS NOT NULL)))),
    CONSTRAINT ck_user_account_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'LOCKED'::character varying, 'DISABLED'::character varying])::text[])))
);

ALTER TABLE ONLY alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);

ALTER TABLE ONLY academic_year
    ADD CONSTRAINT pk_academic_year PRIMARY KEY (id);

ALTER TABLE ONLY advisor_assignment
    ADD CONSTRAINT pk_advisor_assignment PRIMARY KEY (id);

ALTER TABLE ONLY advisor_review
    ADD CONSTRAINT pk_advisor_review PRIMARY KEY (id);

ALTER TABLE ONLY audit_event
    ADD CONSTRAINT pk_audit_event PRIMARY KEY (id);

ALTER TABLE ONLY bonus_evidence
    ADD CONSTRAINT pk_bonus_evidence PRIMARY KEY (id);

ALTER TABLE ONLY council
    ADD CONSTRAINT pk_council PRIMARY KEY (id);

ALTER TABLE ONLY council_attendance
    ADD CONSTRAINT pk_council_attendance PRIMARY KEY (id);

ALTER TABLE ONLY council_member
    ADD CONSTRAINT pk_council_member PRIMARY KEY (id);

ALTER TABLE ONLY council_minute
    ADD CONSTRAINT pk_council_minute PRIMARY KEY (id);

ALTER TABLE ONLY defense_eligibility_check
    ADD CONSTRAINT pk_defense_eligibility_check PRIMARY KEY (id);

ALTER TABLE ONLY defense_session
    ADD CONSTRAINT pk_defense_session PRIMARY KEY (id);

ALTER TABLE ONLY department
    ADD CONSTRAINT pk_department PRIMARY KEY (id);

ALTER TABLE ONLY document
    ADD CONSTRAINT pk_document PRIMARY KEY (id);

ALTER TABLE ONLY document_version
    ADD CONSTRAINT pk_document_version PRIMARY KEY (id);

ALTER TABLE ONLY eligibility_exception
    ADD CONSTRAINT pk_eligibility_exception PRIMARY KEY (id);

ALTER TABLE ONLY eligibility_snapshot
    ADD CONSTRAINT pk_eligibility_snapshot PRIMARY KEY (id);

ALTER TABLE ONLY evaluation
    ADD CONSTRAINT pk_evaluation PRIMARY KEY (id);

ALTER TABLE ONLY evaluation_item
    ADD CONSTRAINT pk_evaluation_item PRIMARY KEY (id);

ALTER TABLE ONLY expertise_evidence
    ADD CONSTRAINT pk_expertise_evidence PRIMARY KEY (id);

ALTER TABLE ONLY external_procedure_outcome
    ADD CONSTRAINT pk_external_procedure_outcome PRIMARY KEY (id);

ALTER TABLE ONLY faculty
    ADD CONSTRAINT pk_faculty PRIMARY KEY (id);

ALTER TABLE ONLY final_result
    ADD CONSTRAINT pk_final_result PRIMARY KEY (id);

ALTER TABLE ONLY lecturer_expertise
    ADD CONSTRAINT pk_lecturer_expertise PRIMARY KEY (id);

ALTER TABLE ONLY lecturer_profile
    ADD CONSTRAINT pk_lecturer_profile PRIMARY KEY (id);

ALTER TABLE ONLY member_work_assignment
    ADD CONSTRAINT pk_member_work_assignment PRIMARY KEY (id);

ALTER TABLE ONLY minute_signature
    ADD CONSTRAINT pk_minute_signature PRIMARY KEY (id);

ALTER TABLE ONLY minute_version
    ADD CONSTRAINT pk_minute_version PRIMARY KEY (id);

ALTER TABLE ONLY organizational_position
    ADD CONSTRAINT pk_organizational_position PRIMARY KEY (id);

ALTER TABLE ONLY position_assignment
    ADD CONSTRAINT pk_position_assignment PRIMARY KEY (id);

ALTER TABLE ONLY progress_milestone
    ADD CONSTRAINT pk_progress_milestone PRIMARY KEY (id);

ALTER TABLE ONLY progress_report
    ADD CONSTRAINT pk_progress_report PRIMARY KEY (id);

ALTER TABLE ONLY progress_review
    ADD CONSTRAINT pk_progress_review PRIMARY KEY (id);

ALTER TABLE ONLY proposal
    ADD CONSTRAINT pk_proposal PRIMARY KEY (id);

ALTER TABLE ONLY proposal_review
    ADD CONSTRAINT pk_proposal_review PRIMARY KEY (id);

ALTER TABLE ONLY proposal_version
    ADD CONSTRAINT pk_proposal_version PRIMARY KEY (id);

ALTER TABLE ONLY registration_member
    ADD CONSTRAINT pk_registration_member PRIMARY KEY (id);

ALTER TABLE ONLY repository_item
    ADD CONSTRAINT pk_repository_item PRIMARY KEY (id);

ALTER TABLE ONLY resource_assignment
    ADD CONSTRAINT pk_resource_assignment PRIMARY KEY (id);

ALTER TABLE ONLY retrieval_audit
    ADD CONSTRAINT pk_retrieval_audit PRIMARY KEY (id);

ALTER TABLE ONLY reviewer_assignment
    ADD CONSTRAINT pk_reviewer_assignment PRIMARY KEY (id);

ALTER TABLE ONLY reviewer_review
    ADD CONSTRAINT pk_reviewer_review PRIMARY KEY (id);

ALTER TABLE ONLY round_policy
    ADD CONSTRAINT pk_round_policy PRIMARY KEY (id);

ALTER TABLE ONLY rubric_assignment
    ADD CONSTRAINT pk_rubric_assignment PRIMARY KEY (id);

ALTER TABLE ONLY rubric_criterion
    ADD CONSTRAINT pk_rubric_criterion PRIMARY KEY (id);

ALTER TABLE ONLY rubric_template
    ADD CONSTRAINT pk_rubric_template PRIMARY KEY (id);

ALTER TABLE ONLY search_index_metadata
    ADD CONSTRAINT pk_search_index_metadata PRIMARY KEY (id);

ALTER TABLE ONLY session_thesis
    ADD CONSTRAINT pk_session_thesis PRIMARY KEY (id);

ALTER TABLE ONLY signature_confirmation
    ADD CONSTRAINT pk_signature_confirmation PRIMARY KEY (id);

ALTER TABLE ONLY similarity_check
    ADD CONSTRAINT pk_similarity_check PRIMARY KEY (id);

ALTER TABLE ONLY similarity_match
    ADD CONSTRAINT pk_similarity_match PRIMARY KEY (id);

ALTER TABLE ONLY similarity_policy
    ADD CONSTRAINT pk_similarity_policy PRIMARY KEY (id);

ALTER TABLE ONLY stored_file
    ADD CONSTRAINT pk_stored_file PRIMARY KEY (id);

ALTER TABLE ONLY student_profile
    ADD CONSTRAINT pk_student_profile PRIMARY KEY (id);

ALTER TABLE ONLY thesis
    ADD CONSTRAINT pk_thesis PRIMARY KEY (id);

ALTER TABLE ONLY thesis_member
    ADD CONSTRAINT pk_thesis_member PRIMARY KEY (id);

ALTER TABLE ONLY thesis_round
    ADD CONSTRAINT pk_thesis_round PRIMARY KEY (id);

ALTER TABLE ONLY topic
    ADD CONSTRAINT pk_topic PRIMARY KEY (id);

ALTER TABLE ONLY topic_change_request
    ADD CONSTRAINT pk_topic_change_request PRIMARY KEY (id);

ALTER TABLE ONLY topic_registration
    ADD CONSTRAINT pk_topic_registration PRIMARY KEY (id);

ALTER TABLE ONLY topic_requirement
    ADD CONSTRAINT pk_topic_requirement PRIMARY KEY (id);

ALTER TABLE ONLY topic_title_version
    ADD CONSTRAINT pk_topic_title_version PRIMARY KEY (id);

ALTER TABLE ONLY user_account
    ADD CONSTRAINT pk_user_account PRIMARY KEY (id);

ALTER TABLE ONLY academic_year
    ADD CONSTRAINT uq_academic_year_code UNIQUE (code);

ALTER TABLE ONLY advisor_review
    ADD CONSTRAINT uq_advisor_review_advisor_assignment_id_thesis_member_i_0e97 UNIQUE (advisor_assignment_id, thesis_member_id, version_no);

ALTER TABLE ONLY council_attendance
    ADD CONSTRAINT uq_council_attendance_session_id_council_member_id UNIQUE (session_id, council_member_id);

ALTER TABLE ONLY council_member
    ADD CONSTRAINT uq_council_member_council_id_lecturer_id UNIQUE (council_id, lecturer_id);

ALTER TABLE ONLY council_member
    ADD CONSTRAINT uq_council_member_council_id_role_code_role_slot UNIQUE (council_id, role_code, role_slot);

ALTER TABLE ONLY council_minute
    ADD CONSTRAINT uq_council_minute_session_id_minute_no UNIQUE (session_id, minute_no);

ALTER TABLE ONLY council
    ADD CONSTRAINT uq_council_round_id_code UNIQUE (round_id, code);

ALTER TABLE ONLY defense_session
    ADD CONSTRAINT uq_defense_session_council_id_code UNIQUE (council_id, code);

ALTER TABLE ONLY department
    ADD CONSTRAINT uq_department_faculty_id_code UNIQUE (faculty_id, code);

ALTER TABLE ONLY document_version
    ADD CONSTRAINT uq_document_version_document_id_version_no UNIQUE (document_id, version_no);

ALTER TABLE ONLY eligibility_exception
    ADD CONSTRAINT uq_eligibility_exception_snapshot_id UNIQUE (snapshot_id);

ALTER TABLE ONLY eligibility_snapshot
    ADD CONSTRAINT uq_eligibility_snapshot_student_id_round_id_version UNIQUE (student_id, round_id, version);

ALTER TABLE ONLY evaluation_item
    ADD CONSTRAINT uq_evaluation_item_evaluation_id_criterion_id UNIQUE (evaluation_id, criterion_id);

ALTER TABLE ONLY evaluation
    ADD CONSTRAINT uq_evaluation_session_id_evaluator_member_id_thesis_member_id UNIQUE (session_id, evaluator_member_id, thesis_member_id);

ALTER TABLE ONLY external_procedure_outcome
    ADD CONSTRAINT uq_external_procedure_outcome_thesis_id_outcome_type_of_dc26 UNIQUE (thesis_id, outcome_type, official_ref);

ALTER TABLE ONLY faculty
    ADD CONSTRAINT uq_faculty_code UNIQUE (code);

ALTER TABLE ONLY final_result
    ADD CONSTRAINT uq_final_result_session_id_thesis_member_id UNIQUE (session_id, thesis_member_id);

ALTER TABLE ONLY lecturer_expertise
    ADD CONSTRAINT uq_lecturer_expertise_lecturer_id_version UNIQUE (lecturer_id, version);

ALTER TABLE ONLY lecturer_profile
    ADD CONSTRAINT uq_lecturer_profile_lecturer_code UNIQUE (lecturer_code);

ALTER TABLE ONLY lecturer_profile
    ADD CONSTRAINT uq_lecturer_profile_user_id UNIQUE (user_id);

ALTER TABLE ONLY member_work_assignment
    ADD CONSTRAINT uq_member_work_assignment_thesis_member_id_version_no UNIQUE (thesis_member_id, version_no);

ALTER TABLE ONLY minute_signature
    ADD CONSTRAINT uq_minute_signature_minute_version_id_signer_member_id UNIQUE (minute_version_id, signer_member_id);

ALTER TABLE ONLY minute_version
    ADD CONSTRAINT uq_minute_version_minute_id_version_no UNIQUE (minute_id, version_no);

ALTER TABLE ONLY organizational_position
    ADD CONSTRAINT uq_organizational_position_code UNIQUE (code);

ALTER TABLE ONLY progress_milestone
    ADD CONSTRAINT uq_progress_milestone_round_id_code_version_no UNIQUE (round_id, code, version_no);

ALTER TABLE ONLY progress_report
    ADD CONSTRAINT uq_progress_report_thesis_id_milestone_id_version_no UNIQUE (thesis_id, milestone_id, version_no);

ALTER TABLE ONLY progress_review
    ADD CONSTRAINT uq_progress_review_progress_report_id_reviewer_id UNIQUE (progress_report_id, reviewer_id);

ALTER TABLE ONLY proposal
    ADD CONSTRAINT uq_proposal_thesis_id UNIQUE (thesis_id);

ALTER TABLE ONLY proposal_version
    ADD CONSTRAINT uq_proposal_version_proposal_id_version_no UNIQUE (proposal_id, version_no);

ALTER TABLE ONLY registration_member
    ADD CONSTRAINT uq_registration_member_registration_id_student_id UNIQUE (registration_id, student_id);

ALTER TABLE ONLY repository_item
    ADD CONSTRAINT uq_repository_item_external_source_id UNIQUE (external_source_id);

ALTER TABLE ONLY repository_item
    ADD CONSTRAINT uq_repository_item_published_document_version_id UNIQUE (published_document_version_id);

ALTER TABLE ONLY reviewer_review
    ADD CONSTRAINT uq_reviewer_review_reviewer_assignment_id_thesis_member_2ade UNIQUE (reviewer_assignment_id, thesis_member_id, version_no);

ALTER TABLE ONLY round_policy
    ADD CONSTRAINT uq_round_policy_round_id_policy_type_version UNIQUE (round_id, policy_type, version);

ALTER TABLE ONLY rubric_criterion
    ADD CONSTRAINT uq_rubric_criterion_rubric_template_id_code UNIQUE (rubric_template_id, code);

ALTER TABLE ONLY rubric_criterion
    ADD CONSTRAINT uq_rubric_criterion_rubric_template_id_order_no UNIQUE (rubric_template_id, order_no);

ALTER TABLE ONLY rubric_template
    ADD CONSTRAINT uq_rubric_template_code_version_no UNIQUE (code, version_no);

ALTER TABLE ONLY search_index_metadata
    ADD CONSTRAINT uq_search_index_metadata_repository_item_id_index_name__53cf UNIQUE (repository_item_id, index_name, index_version);

ALTER TABLE ONLY session_thesis
    ADD CONSTRAINT uq_session_thesis_session_id_order_no UNIQUE (session_id, order_no);

ALTER TABLE ONLY session_thesis
    ADD CONSTRAINT uq_session_thesis_session_id_thesis_id UNIQUE (session_id, thesis_id);

ALTER TABLE ONLY signature_confirmation
    ADD CONSTRAINT uq_signature_confirmation_proposal_id_signature_type UNIQUE (proposal_id, signature_type);

ALTER TABLE ONLY similarity_policy
    ADD CONSTRAINT uq_similarity_policy_round_id_version_no UNIQUE (round_id, version_no);

ALTER TABLE ONLY stored_file
    ADD CONSTRAINT uq_stored_file_storage_key UNIQUE (storage_key);

ALTER TABLE ONLY student_profile
    ADD CONSTRAINT uq_student_profile_student_code UNIQUE (student_code);

ALTER TABLE ONLY student_profile
    ADD CONSTRAINT uq_student_profile_user_id UNIQUE (user_id);

ALTER TABLE ONLY thesis_member
    ADD CONSTRAINT uq_thesis_member_thesis_id_student_id UNIQUE (thesis_id, student_id);

ALTER TABLE ONLY thesis
    ADD CONSTRAINT uq_thesis_registration_id UNIQUE (registration_id);

ALTER TABLE ONLY thesis_round
    ADD CONSTRAINT uq_thesis_round_academic_year_id_code UNIQUE (academic_year_id, code);

ALTER TABLE ONLY thesis
    ADD CONSTRAINT uq_thesis_round_id_topic_id UNIQUE (round_id, topic_id);

ALTER TABLE ONLY topic
    ADD CONSTRAINT uq_topic_code UNIQUE (code);

ALTER TABLE ONLY topic_registration
    ADD CONSTRAINT uq_topic_registration_id_round_id UNIQUE (id, round_id);

ALTER TABLE ONLY topic_title_version
    ADD CONSTRAINT uq_topic_title_version_topic_id_version_no UNIQUE (topic_id, version_no);

ALTER TABLE ONLY user_account
    ADD CONSTRAINT uq_user_account_external_subject UNIQUE (external_subject);

CREATE INDEX ix_audit_event_correlation_id ON audit_event USING btree (correlation_id);

CREATE INDEX ix_audit_event_resource_id ON audit_event USING btree (resource_id);

CREATE INDEX ix_repository_item_source_type_visibility ON repository_item USING btree (source_type, visibility);

CREATE INDEX ix_retrieval_audit_correlation_id ON retrieval_audit USING btree (correlation_id);

CREATE INDEX ix_stored_file_sha256 ON stored_file USING btree (sha256);

CREATE UNIQUE INDEX uq_advisor_assignment_active_primary ON advisor_assignment USING btree (thesis_id) WHERE (((state)::text = 'ACTIVE'::text) AND ((assignment_type)::text = 'PRIMARY'::text));

CREATE UNIQUE INDEX uq_position_assignment_department_scope ON position_assignment USING btree (lecturer_id, position_id, department_id) WHERE ((department_id IS NOT NULL) AND ((state)::text = 'ACTIVE'::text));

CREATE UNIQUE INDEX uq_position_assignment_faculty_scope ON position_assignment USING btree (lecturer_id, position_id, faculty_id) WHERE ((faculty_id IS NOT NULL) AND ((state)::text = 'ACTIVE'::text));

CREATE UNIQUE INDEX uq_registration_member_one_coordinator ON registration_member USING btree (registration_id) WHERE (active AND is_coordinator);

CREATE UNIQUE INDEX uq_registration_member_student_round_active ON registration_member USING btree (student_id, round_id) WHERE active;

CREATE UNIQUE INDEX uq_resource_assignment_council_scope ON resource_assignment USING btree (assignment_type, user_id, council_id) WHERE ((council_id IS NOT NULL) AND ((state)::text = 'ACTIVE'::text));

CREATE UNIQUE INDEX uq_resource_assignment_round_scope ON resource_assignment USING btree (assignment_type, user_id, round_id) WHERE ((round_id IS NOT NULL) AND ((state)::text = 'ACTIVE'::text));

CREATE UNIQUE INDEX uq_resource_assignment_thesis_scope ON resource_assignment USING btree (assignment_type, user_id, thesis_id) WHERE ((thesis_id IS NOT NULL) AND ((state)::text = 'ACTIVE'::text));

CREATE UNIQUE INDEX uq_reviewer_assignment_proposal ON reviewer_assignment USING btree (lecturer_id, proposal_id) WHERE ((proposal_id IS NOT NULL) AND ((state)::text = 'ACTIVE'::text));

CREATE UNIQUE INDEX uq_reviewer_assignment_thesis ON reviewer_assignment USING btree (lecturer_id, thesis_id) WHERE ((thesis_id IS NOT NULL) AND ((state)::text = 'ACTIVE'::text));

CREATE UNIQUE INDEX uq_thesis_member_one_coordinator ON thesis_member USING btree (thesis_id) WHERE (active AND is_coordinator);

CREATE UNIQUE INDEX uq_user_account_email_lower ON user_account USING btree (lower((email)::text)) WHERE (email IS NOT NULL);

ALTER TABLE ONLY advisor_assignment
    ADD CONSTRAINT fk_advisor_assignment_assigned_by_user_account FOREIGN KEY (assigned_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY advisor_assignment
    ADD CONSTRAINT fk_advisor_assignment_lecturer_id_lecturer_profile FOREIGN KEY (lecturer_id) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY advisor_assignment
    ADD CONSTRAINT fk_advisor_assignment_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY advisor_review
    ADD CONSTRAINT fk_advisor_review_advisor_assignment_id_advisor_assignment FOREIGN KEY (advisor_assignment_id) REFERENCES advisor_assignment(id) ON DELETE RESTRICT;

ALTER TABLE ONLY advisor_review
    ADD CONSTRAINT fk_advisor_review_document_version_id_document_version FOREIGN KEY (document_version_id) REFERENCES document_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY advisor_review
    ADD CONSTRAINT fk_advisor_review_thesis_member_id_thesis_member FOREIGN KEY (thesis_member_id) REFERENCES thesis_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY audit_event
    ADD CONSTRAINT fk_audit_event_actor_id_user_account FOREIGN KEY (actor_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY bonus_evidence
    ADD CONSTRAINT fk_bonus_evidence_stored_file_id_stored_file FOREIGN KEY (stored_file_id) REFERENCES stored_file(id) ON DELETE RESTRICT;

ALTER TABLE ONLY bonus_evidence
    ADD CONSTRAINT fk_bonus_evidence_thesis_member_id_thesis_member FOREIGN KEY (thesis_member_id) REFERENCES thesis_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY council_attendance
    ADD CONSTRAINT fk_council_attendance_council_member_id_council_member FOREIGN KEY (council_member_id) REFERENCES council_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY council_attendance
    ADD CONSTRAINT fk_council_attendance_recorded_by_user_account FOREIGN KEY (recorded_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY council_attendance
    ADD CONSTRAINT fk_council_attendance_session_id_defense_session FOREIGN KEY (session_id) REFERENCES defense_session(id) ON DELETE RESTRICT;

ALTER TABLE ONLY council
    ADD CONSTRAINT fk_council_department_id_department FOREIGN KEY (department_id) REFERENCES department(id) ON DELETE RESTRICT;

ALTER TABLE ONLY council_member
    ADD CONSTRAINT fk_council_member_council_id_council FOREIGN KEY (council_id) REFERENCES council(id) ON DELETE RESTRICT;

ALTER TABLE ONLY council_member
    ADD CONSTRAINT fk_council_member_lecturer_id_lecturer_profile FOREIGN KEY (lecturer_id) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY council_minute
    ADD CONSTRAINT fk_council_minute_session_id_defense_session FOREIGN KEY (session_id) REFERENCES defense_session(id) ON DELETE RESTRICT;

ALTER TABLE ONLY council
    ADD CONSTRAINT fk_council_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY defense_eligibility_check
    ADD CONSTRAINT fk_defense_eligibility_check_advisor_review_id_advisor_review FOREIGN KEY (advisor_review_id) REFERENCES advisor_review(id) ON DELETE RESTRICT;

ALTER TABLE ONLY defense_eligibility_check
    ADD CONSTRAINT fk_defense_eligibility_check_checked_by_user_account FOREIGN KEY (checked_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY defense_eligibility_check
    ADD CONSTRAINT fk_defense_eligibility_check_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY defense_eligibility_check
    ADD CONSTRAINT fk_defense_eligibility_check_thesis_member_id_thesis_member FOREIGN KEY (thesis_member_id) REFERENCES thesis_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY defense_session
    ADD CONSTRAINT fk_defense_session_council_id_council FOREIGN KEY (council_id) REFERENCES council(id) ON DELETE RESTRICT;

ALTER TABLE ONLY department
    ADD CONSTRAINT fk_department_faculty_id_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE RESTRICT;

ALTER TABLE ONLY document
    ADD CONSTRAINT fk_document_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY document_version
    ADD CONSTRAINT fk_document_version_document_id_document FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE RESTRICT;

ALTER TABLE ONLY document_version
    ADD CONSTRAINT fk_document_version_stored_file_id_stored_file FOREIGN KEY (stored_file_id) REFERENCES stored_file(id) ON DELETE RESTRICT;

ALTER TABLE ONLY document_version
    ADD CONSTRAINT fk_document_version_submitted_by_student_profile FOREIGN KEY (submitted_by) REFERENCES student_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY eligibility_exception
    ADD CONSTRAINT fk_eligibility_exception_granted_by_user_account FOREIGN KEY (granted_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY eligibility_exception
    ADD CONSTRAINT fk_eligibility_exception_snapshot_id_eligibility_snapshot FOREIGN KEY (snapshot_id) REFERENCES eligibility_snapshot(id) ON DELETE RESTRICT;

ALTER TABLE ONLY eligibility_snapshot
    ADD CONSTRAINT fk_eligibility_snapshot_confirmed_by_user_account FOREIGN KEY (confirmed_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY eligibility_snapshot
    ADD CONSTRAINT fk_eligibility_snapshot_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY eligibility_snapshot
    ADD CONSTRAINT fk_eligibility_snapshot_student_id_student_profile FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY evaluation
    ADD CONSTRAINT fk_evaluation_evaluator_member_id_council_member FOREIGN KEY (evaluator_member_id) REFERENCES council_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY evaluation_item
    ADD CONSTRAINT fk_evaluation_item_bonus_evidence_id_bonus_evidence FOREIGN KEY (bonus_evidence_id) REFERENCES bonus_evidence(id) ON DELETE RESTRICT;

ALTER TABLE ONLY evaluation_item
    ADD CONSTRAINT fk_evaluation_item_criterion_id_rubric_criterion FOREIGN KEY (criterion_id) REFERENCES rubric_criterion(id) ON DELETE RESTRICT;

ALTER TABLE ONLY evaluation_item
    ADD CONSTRAINT fk_evaluation_item_evaluation_id_evaluation FOREIGN KEY (evaluation_id) REFERENCES evaluation(id) ON DELETE RESTRICT;

ALTER TABLE ONLY evaluation
    ADD CONSTRAINT fk_evaluation_rubric_assignment_id_rubric_assignment FOREIGN KEY (rubric_assignment_id) REFERENCES rubric_assignment(id) ON DELETE RESTRICT;

ALTER TABLE ONLY evaluation
    ADD CONSTRAINT fk_evaluation_session_id_defense_session FOREIGN KEY (session_id) REFERENCES defense_session(id) ON DELETE RESTRICT;

ALTER TABLE ONLY evaluation
    ADD CONSTRAINT fk_evaluation_thesis_member_id_thesis_member FOREIGN KEY (thesis_member_id) REFERENCES thesis_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY expertise_evidence
    ADD CONSTRAINT fk_expertise_evidence_expertise_id_lecturer_expertise FOREIGN KEY (expertise_id) REFERENCES lecturer_expertise(id) ON DELETE RESTRICT;

ALTER TABLE ONLY external_procedure_outcome
    ADD CONSTRAINT fk_external_procedure_outcome_evidence_file_id_stored_file FOREIGN KEY (evidence_file_id) REFERENCES stored_file(id) ON DELETE RESTRICT;

ALTER TABLE ONLY external_procedure_outcome
    ADD CONSTRAINT fk_external_procedure_outcome_recorded_by_user_account FOREIGN KEY (recorded_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY external_procedure_outcome
    ADD CONSTRAINT fk_external_procedure_outcome_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY final_result
    ADD CONSTRAINT fk_final_result_session_id_defense_session FOREIGN KEY (session_id) REFERENCES defense_session(id) ON DELETE RESTRICT;

ALTER TABLE ONLY final_result
    ADD CONSTRAINT fk_final_result_thesis_member_id_thesis_member FOREIGN KEY (thesis_member_id) REFERENCES thesis_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY lecturer_expertise
    ADD CONSTRAINT fk_lecturer_expertise_lecturer_id_lecturer_profile FOREIGN KEY (lecturer_id) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY lecturer_expertise
    ADD CONSTRAINT fk_lecturer_expertise_verified_by_user_account FOREIGN KEY (verified_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY lecturer_profile
    ADD CONSTRAINT fk_lecturer_profile_department_id_department FOREIGN KEY (department_id) REFERENCES department(id) ON DELETE RESTRICT;

ALTER TABLE ONLY lecturer_profile
    ADD CONSTRAINT fk_lecturer_profile_user_id_user_account FOREIGN KEY (user_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY member_work_assignment
    ADD CONSTRAINT fk_member_work_assignment_reviewed_by_lecturer_profile FOREIGN KEY (reviewed_by) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY member_work_assignment
    ADD CONSTRAINT fk_member_work_assignment_thesis_member_id_thesis_member FOREIGN KEY (thesis_member_id) REFERENCES thesis_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY minute_signature
    ADD CONSTRAINT fk_minute_signature_minute_version_id_minute_version FOREIGN KEY (minute_version_id) REFERENCES minute_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY minute_signature
    ADD CONSTRAINT fk_minute_signature_signer_member_id_council_member FOREIGN KEY (signer_member_id) REFERENCES council_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY minute_version
    ADD CONSTRAINT fk_minute_version_generated_by_user_account FOREIGN KEY (generated_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY minute_version
    ADD CONSTRAINT fk_minute_version_minute_id_council_minute FOREIGN KEY (minute_id) REFERENCES council_minute(id) ON DELETE RESTRICT;

ALTER TABLE ONLY minute_version
    ADD CONSTRAINT fk_minute_version_replacement_for_id_minute_version FOREIGN KEY (replacement_for_id) REFERENCES minute_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY minute_version
    ADD CONSTRAINT fk_minute_version_stored_file_id_stored_file FOREIGN KEY (stored_file_id) REFERENCES stored_file(id) ON DELETE RESTRICT;

ALTER TABLE ONLY position_assignment
    ADD CONSTRAINT fk_position_assignment_department_id_department FOREIGN KEY (department_id) REFERENCES department(id) ON DELETE RESTRICT;

ALTER TABLE ONLY position_assignment
    ADD CONSTRAINT fk_position_assignment_faculty_id_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE RESTRICT;

ALTER TABLE ONLY position_assignment
    ADD CONSTRAINT fk_position_assignment_lecturer_id_lecturer_profile FOREIGN KEY (lecturer_id) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY position_assignment
    ADD CONSTRAINT fk_position_assignment_position_id_organizational_position FOREIGN KEY (position_id) REFERENCES organizational_position(id) ON DELETE RESTRICT;

ALTER TABLE ONLY progress_milestone
    ADD CONSTRAINT fk_progress_milestone_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY progress_report
    ADD CONSTRAINT fk_progress_report_evidence_file_id_stored_file FOREIGN KEY (evidence_file_id) REFERENCES stored_file(id) ON DELETE RESTRICT;

ALTER TABLE ONLY progress_report
    ADD CONSTRAINT fk_progress_report_milestone_id_progress_milestone FOREIGN KEY (milestone_id) REFERENCES progress_milestone(id) ON DELETE RESTRICT;

ALTER TABLE ONLY progress_report
    ADD CONSTRAINT fk_progress_report_submitted_by_student_profile FOREIGN KEY (submitted_by) REFERENCES student_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY progress_report
    ADD CONSTRAINT fk_progress_report_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY progress_review
    ADD CONSTRAINT fk_progress_review_progress_report_id_progress_report FOREIGN KEY (progress_report_id) REFERENCES progress_report(id) ON DELETE RESTRICT;

ALTER TABLE ONLY progress_review
    ADD CONSTRAINT fk_progress_review_reviewer_id_lecturer_profile FOREIGN KEY (reviewer_id) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY proposal_review
    ADD CONSTRAINT fk_proposal_review_proposal_version_id_proposal_version FOREIGN KEY (proposal_version_id) REFERENCES proposal_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY proposal_review
    ADD CONSTRAINT fk_proposal_review_reviewer_assignment_id_reviewer_assignment FOREIGN KEY (reviewer_assignment_id) REFERENCES reviewer_assignment(id) ON DELETE RESTRICT;

ALTER TABLE ONLY proposal_review
    ADD CONSTRAINT fk_proposal_review_reviewer_user_id_user_account FOREIGN KEY (reviewer_user_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY proposal
    ADD CONSTRAINT fk_proposal_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY proposal_version
    ADD CONSTRAINT fk_proposal_version_proposal_id_proposal FOREIGN KEY (proposal_id) REFERENCES proposal(id) ON DELETE RESTRICT;

ALTER TABLE ONLY proposal_version
    ADD CONSTRAINT fk_proposal_version_stored_file_id_stored_file FOREIGN KEY (stored_file_id) REFERENCES stored_file(id) ON DELETE RESTRICT;

ALTER TABLE ONLY proposal_version
    ADD CONSTRAINT fk_proposal_version_submitted_by_student_profile FOREIGN KEY (submitted_by) REFERENCES student_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY registration_member
    ADD CONSTRAINT fk_registration_member_evidence_file_id_stored_file FOREIGN KEY (evidence_file_id) REFERENCES stored_file(id) ON DELETE RESTRICT;

ALTER TABLE ONLY registration_member
    ADD CONSTRAINT fk_registration_member_registration_id_round_id_topic_r_f9bb FOREIGN KEY (registration_id, round_id) REFERENCES topic_registration(id, round_id) ON DELETE RESTRICT;

ALTER TABLE ONLY registration_member
    ADD CONSTRAINT fk_registration_member_responded_by_user_id_user_account FOREIGN KEY (responded_by_user_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY registration_member
    ADD CONSTRAINT fk_registration_member_student_id_student_profile FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY repository_item
    ADD CONSTRAINT fk_repository_item_published_document_version_id_docume_db47 FOREIGN KEY (published_document_version_id) REFERENCES document_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY repository_item
    ADD CONSTRAINT fk_repository_item_stored_file_id_stored_file FOREIGN KEY (stored_file_id) REFERENCES stored_file(id) ON DELETE RESTRICT;

ALTER TABLE ONLY repository_item
    ADD CONSTRAINT fk_repository_item_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY resource_assignment
    ADD CONSTRAINT fk_resource_assignment_council_id_council FOREIGN KEY (council_id) REFERENCES council(id) ON DELETE RESTRICT;

ALTER TABLE ONLY resource_assignment
    ADD CONSTRAINT fk_resource_assignment_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY resource_assignment
    ADD CONSTRAINT fk_resource_assignment_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY resource_assignment
    ADD CONSTRAINT fk_resource_assignment_user_id_user_account FOREIGN KEY (user_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY retrieval_audit
    ADD CONSTRAINT fk_retrieval_audit_user_id_user_account FOREIGN KEY (user_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY reviewer_assignment
    ADD CONSTRAINT fk_reviewer_assignment_assigned_by_user_account FOREIGN KEY (assigned_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY reviewer_assignment
    ADD CONSTRAINT fk_reviewer_assignment_lecturer_id_lecturer_profile FOREIGN KEY (lecturer_id) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY reviewer_assignment
    ADD CONSTRAINT fk_reviewer_assignment_proposal_id_proposal FOREIGN KEY (proposal_id) REFERENCES proposal(id) ON DELETE RESTRICT;

ALTER TABLE ONLY reviewer_assignment
    ADD CONSTRAINT fk_reviewer_assignment_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY reviewer_review
    ADD CONSTRAINT fk_reviewer_review_document_version_id_document_version FOREIGN KEY (document_version_id) REFERENCES document_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY reviewer_review
    ADD CONSTRAINT fk_reviewer_review_reviewer_assignment_id_reviewer_assignment FOREIGN KEY (reviewer_assignment_id) REFERENCES reviewer_assignment(id) ON DELETE RESTRICT;

ALTER TABLE ONLY reviewer_review
    ADD CONSTRAINT fk_reviewer_review_thesis_member_id_thesis_member FOREIGN KEY (thesis_member_id) REFERENCES thesis_member(id) ON DELETE RESTRICT;

ALTER TABLE ONLY round_policy
    ADD CONSTRAINT fk_round_policy_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY rubric_assignment
    ADD CONSTRAINT fk_rubric_assignment_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY rubric_assignment
    ADD CONSTRAINT fk_rubric_assignment_rubric_template_id_rubric_template FOREIGN KEY (rubric_template_id) REFERENCES rubric_template(id) ON DELETE RESTRICT;

ALTER TABLE ONLY rubric_assignment
    ADD CONSTRAINT fk_rubric_assignment_session_id_defense_session FOREIGN KEY (session_id) REFERENCES defense_session(id) ON DELETE RESTRICT;

ALTER TABLE ONLY rubric_criterion
    ADD CONSTRAINT fk_rubric_criterion_parent_id_rubric_criterion FOREIGN KEY (parent_id) REFERENCES rubric_criterion(id) ON DELETE RESTRICT;

ALTER TABLE ONLY rubric_criterion
    ADD CONSTRAINT fk_rubric_criterion_rubric_template_id_rubric_template FOREIGN KEY (rubric_template_id) REFERENCES rubric_template(id) ON DELETE RESTRICT;

ALTER TABLE ONLY search_index_metadata
    ADD CONSTRAINT fk_search_index_metadata_document_version_id_document_version FOREIGN KEY (document_version_id) REFERENCES document_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY search_index_metadata
    ADD CONSTRAINT fk_search_index_metadata_repository_item_id_repository_item FOREIGN KEY (repository_item_id) REFERENCES repository_item(id) ON DELETE RESTRICT;

ALTER TABLE ONLY session_thesis
    ADD CONSTRAINT fk_session_thesis_session_id_defense_session FOREIGN KEY (session_id) REFERENCES defense_session(id) ON DELETE RESTRICT;

ALTER TABLE ONLY session_thesis
    ADD CONSTRAINT fk_session_thesis_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY signature_confirmation
    ADD CONSTRAINT fk_signature_confirmation_proposal_id_proposal FOREIGN KEY (proposal_id) REFERENCES proposal(id) ON DELETE RESTRICT;

ALTER TABLE ONLY signature_confirmation
    ADD CONSTRAINT fk_signature_confirmation_proposal_version_pair FOREIGN KEY (proposal_id, proposal_version_no) REFERENCES proposal_version(proposal_id, version_no) ON DELETE RESTRICT;

ALTER TABLE ONLY signature_confirmation
    ADD CONSTRAINT fk_signature_confirmation_signer_user_id_user_account FOREIGN KEY (signer_user_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY similarity_check
    ADD CONSTRAINT fk_similarity_check_document_version_id_document_version FOREIGN KEY (document_version_id) REFERENCES document_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY similarity_check
    ADD CONSTRAINT fk_similarity_check_policy_id_similarity_policy FOREIGN KEY (policy_id) REFERENCES similarity_policy(id) ON DELETE RESTRICT;

ALTER TABLE ONLY similarity_match
    ADD CONSTRAINT fk_similarity_match_check_id_similarity_check FOREIGN KEY (check_id) REFERENCES similarity_check(id) ON DELETE RESTRICT;

ALTER TABLE ONLY similarity_match
    ADD CONSTRAINT fk_similarity_match_source_document_version_id_document_version FOREIGN KEY (source_document_version_id) REFERENCES document_version(id) ON DELETE RESTRICT;

ALTER TABLE ONLY similarity_match
    ADD CONSTRAINT fk_similarity_match_source_repository_item_id_repository_item FOREIGN KEY (source_repository_item_id) REFERENCES repository_item(id) ON DELETE RESTRICT;

ALTER TABLE ONLY similarity_policy
    ADD CONSTRAINT fk_similarity_policy_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY student_profile
    ADD CONSTRAINT fk_student_profile_department_id_department FOREIGN KEY (department_id) REFERENCES department(id) ON DELETE RESTRICT;

ALTER TABLE ONLY student_profile
    ADD CONSTRAINT fk_student_profile_user_id_user_account FOREIGN KEY (user_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY thesis
    ADD CONSTRAINT fk_thesis_department_id_department FOREIGN KEY (department_id) REFERENCES department(id) ON DELETE RESTRICT;

ALTER TABLE ONLY thesis_member
    ADD CONSTRAINT fk_thesis_member_student_id_student_profile FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY thesis_member
    ADD CONSTRAINT fk_thesis_member_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY thesis
    ADD CONSTRAINT fk_thesis_registration_id_topic_registration FOREIGN KEY (registration_id) REFERENCES topic_registration(id) ON DELETE RESTRICT;

ALTER TABLE ONLY thesis_round
    ADD CONSTRAINT fk_thesis_round_academic_year_id_academic_year FOREIGN KEY (academic_year_id) REFERENCES academic_year(id) ON DELETE RESTRICT;

ALTER TABLE ONLY thesis
    ADD CONSTRAINT fk_thesis_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY thesis
    ADD CONSTRAINT fk_thesis_topic_id_topic FOREIGN KEY (topic_id) REFERENCES topic(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_change_request
    ADD CONSTRAINT fk_topic_change_request_advisor_reviewed_by_lecturer_profile FOREIGN KEY (advisor_reviewed_by) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_change_request
    ADD CONSTRAINT fk_topic_change_request_department_decided_by_user_account FOREIGN KEY (department_decided_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_change_request
    ADD CONSTRAINT fk_topic_change_request_proposed_topic_id_topic FOREIGN KEY (proposed_topic_id) REFERENCES topic(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_change_request
    ADD CONSTRAINT fk_topic_change_request_requested_by_student_profile FOREIGN KEY (requested_by) REFERENCES student_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_change_request
    ADD CONSTRAINT fk_topic_change_request_thesis_id_thesis FOREIGN KEY (thesis_id) REFERENCES thesis(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic
    ADD CONSTRAINT fk_topic_decided_by_user_account FOREIGN KEY (decided_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic
    ADD CONSTRAINT fk_topic_department_id_department FOREIGN KEY (department_id) REFERENCES department(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic
    ADD CONSTRAINT fk_topic_proposer_user_id_user_account FOREIGN KEY (proposer_user_id) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic
    ADD CONSTRAINT fk_topic_receiving_lecturer_id_lecturer_profile FOREIGN KEY (receiving_lecturer_id) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_registration
    ADD CONSTRAINT fk_topic_registration_created_by_student_profile FOREIGN KEY (created_by) REFERENCES student_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_registration
    ADD CONSTRAINT fk_topic_registration_department_finalized_by_user_account FOREIGN KEY (department_finalized_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_registration
    ADD CONSTRAINT fk_topic_registration_lecturer_decided_by_lecturer_profile FOREIGN KEY (lecturer_decided_by) REFERENCES lecturer_profile(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_registration
    ADD CONSTRAINT fk_topic_registration_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_registration
    ADD CONSTRAINT fk_topic_registration_topic_id_topic FOREIGN KEY (topic_id) REFERENCES topic(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_requirement
    ADD CONSTRAINT fk_topic_requirement_topic_id_topic FOREIGN KEY (topic_id) REFERENCES topic(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic
    ADD CONSTRAINT fk_topic_round_id_thesis_round FOREIGN KEY (round_id) REFERENCES thesis_round(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_title_version
    ADD CONSTRAINT fk_topic_title_version_changed_by_user_account FOREIGN KEY (changed_by) REFERENCES user_account(id) ON DELETE RESTRICT;

ALTER TABLE ONLY topic_title_version
    ADD CONSTRAINT fk_topic_title_version_topic_id_topic FOREIGN KEY (topic_id) REFERENCES topic(id) ON DELETE RESTRICT;

INSERT INTO alembic_version (version_num) VALUES ('20261010_0013');

-- Dữ liệu kỹ thuật Mẫu 6 DRAFT, cùng mã ổn định với migration 0006.
INSERT INTO rubric_template (id, code, name, version_no, source_ref, state) VALUES ('1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', 'MAU-06-HOIDONG', 'Mẫu 6 - Phiếu đánh giá Hội đồng', 1, 'SRC-MAU-06', 'DRAFT');
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('0dd2508a-5a90-54ac-a4b3-7cf55787708c', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', NULL, '1', 'Hình thức', 2.0, 'GROUP', 1);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('62db15a8-f465-5eca-a46f-ef739bb83a51', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', '0dd2508a-5a90-54ac-a4b3-7cf55787708c', '1.1', 'Chuyên cần', 1.0, 'NORMAL', 2);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('e7d96f4f-0818-543f-af45-8f44fcc200e1', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', '0dd2508a-5a90-54ac-a4b3-7cf55787708c', '1.2', 'Cấu trúc khóa luận/đồ án hợp lý, bố cục chặt chẽ, rõ ràng, trình bày theo đúng quy định. Đúng kỹ thuật soạn thảo văn bản, không có dấu hiệu đạo văn.', 0.5, 'NORMAL', 3);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('1556b1ae-9767-5738-a6da-09e991771b43', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', '0dd2508a-5a90-54ac-a4b3-7cf55787708c', '1.3', 'Trích dẫn và trình bày tài liệu tham khảo, hình vẽ, bảng biểu rõ ràng, đúng quy định, không có lỗi chính tả, không lỗi in ấn.', 0.5, 'NORMAL', 4);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('c4366e1d-3640-5941-aa47-bcaf5ef1a90f', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', NULL, '2', 'Nội dung', 4.0, 'GROUP', 5);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('abbd8794-1f03-5544-b3d1-51543ffca274', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', 'c4366e1d-3640-5941-aa47-bcaf5ef1a90f', '2.1', 'Nêu được tính cấp thiết của đề tài, làm rõ tổng quan các công trình nghiên cứu, xác định mục đích, nhiệm vụ, đối tượng, phạm vi, nghiên cứu rõ ràng, hợp lý.', 0.5, 'NORMAL', 6);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('7714905e-9934-5e36-8423-62f18ec79188', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', 'c4366e1d-3640-5941-aa47-bcaf5ef1a90f', '2.2', 'Nội dung nghiên cứu: Khối lượng công việc hợp lí; tư liệu phong phú, chính xác, phù hợp mục đích nghiên cứu.', 0.5, 'NORMAL', 7);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('1e288dbb-a1d2-5757-a952-4651ef02db4f', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', 'c4366e1d-3640-5941-aa47-bcaf5ef1a90f', '2.3', 'Phương pháp nghiên cứu: Biết vận dụng các phương pháp nghiên cứu phù hợp với nội dung nghiên cứu của đề tài; trình bày nội dung có hệ thống khoa học, logic.', 1.0, 'NORMAL', 8);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('5f166ff2-78d3-53e9-872f-a322c571be85', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', 'c4366e1d-3640-5941-aa47-bcaf5ef1a90f', '2.4', 'Khả năng áp dụng các giải thuật hiệu quả, số liệu chính xác; Khả năng giải quyết vấn đề, đầy đủ minh chứng khoa học; Khả năng suy luận, phân tích, tổng hợp tốt; có khả năng sáng tạo.', 1.0, 'NORMAL', 9);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('01adff2f-32e4-5eb3-ade9-0418b049c474', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', 'c4366e1d-3640-5941-aa47-bcaf5ef1a90f', '2.5', 'Kết quả nghiên cứu: - Nêu được kết quả đạt được phù hợp với mục tiêu nghiên cứu của đề tài; - Kết quả có giá trị về mặt lý luận và thực tiễn khoa học; - Có đánh giá, nhận xét kết quả, dự đoán tương lai (nếu cần).', 0.5, 'NORMAL', 10);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('d830c181-6f0b-59c1-87e1-e3fb0b4305ec', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', 'c4366e1d-3640-5941-aa47-bcaf5ef1a90f', '2.6', 'Kết luận, kiến nghị phù hợp với nội dung nghiên cứu.', 0.5, 'NORMAL', 11);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('8c6e81da-5724-5e97-9cb8-5383adb50764', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', NULL, '3', 'Demo và trả lời câu hỏi', 4.0, 'GROUP', 12);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('00d41d33-360d-5db4-a00b-3ed66b0cc129', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', '8c6e81da-5724-5e97-9cb8-5383adb50764', '3.1', 'Demo không có lỗi, không vi phạm luật an ninh mạng/luật sở hữu trí tuệ; Có quy trình sử dụng/hướng dẫn sử dụng rõ ràng; Có triển khai, có khả năng ứng dụng.', 1.0, 'NORMAL', 13);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('3a45fcb7-2cee-528c-b1d3-e9b7daeb09cd', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', '8c6e81da-5724-5e97-9cb8-5383adb50764', '3.2', 'Giao diện thân thiện, hợp lý; Các chức năng đáp ứng được yêu cầu của đề tài; Độ tin cậy, độ tương thích; Tốc độ, bảo mật, chi phí hợp lý.', 2.0, 'NORMAL', 14);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('a7397279-04c9-5a75-81a8-6e72b9156002', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', '8c6e81da-5724-5e97-9cb8-5383adb50764', '3.3', 'Thuyết trình lưu loát, slide trình chiếu rõ ràng, có sáng tạo; Trả lời đúng, đáp ứng được yêu cầu các câu hỏi đặt ra.', 1.0, 'NORMAL', 15);
INSERT INTO rubric_criterion (id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES ('6b93df99-d044-5fce-a447-383a6f10dd06', '1a4b7ef6-4f53-5627-8d1b-a54f9c0c1b1f', NULL, '4', 'Điểm thưởng (nếu có công bố kết quả nghiên cứu trên tập chí khoa học hoặc hội thảo trong và ngoài nước). Tổng điểm là 10 (kể cả điểm thưởng)', 1.0, 'BONUS', 16);

COMMIT;
