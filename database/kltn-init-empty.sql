-- KLTN PostgreSQL schema, Alembic revision 20260925_0005.
-- Chạy một lần trên database PostgreSQL mới và trống.
-- Không chứa dữ liệu nghiệp vụ hoặc mật khẩu.
-- Database đã có bảng phải cập nhật bằng Alembic migration, không chạy lại file này.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 20260920_0001

CREATE TABLE faculty (
    code VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT true NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_faculty PRIMARY KEY (id),
    CONSTRAINT uq_faculty_code UNIQUE (code)
);

CREATE TABLE user_account (
    external_subject VARCHAR(255) NOT NULL,
    base_role VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_user_account PRIMARY KEY (id),
    CONSTRAINT ck_user_account_base_role CHECK (base_role IN ('ADMIN','LECTURER','STUDENT')),
    CONSTRAINT ck_user_account_status CHECK (status IN ('ACTIVE','LOCKED','DISABLED')),
    CONSTRAINT uq_user_account_external_subject UNIQUE (external_subject)
);

CREATE TABLE organizational_position (
    code VARCHAR(40) NOT NULL,
    name VARCHAR(255) NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_organizational_position PRIMARY KEY (id),
    CONSTRAINT ck_organizational_position_code CHECK (code IN ('DEPARTMENT_HEAD','FACULTY_DEAN')),
    CONSTRAINT uq_organizational_position_code UNIQUE (code)
);

CREATE TABLE academic_year (
    code VARCHAR(20) NOT NULL,
    starts_on DATE NOT NULL,
    ends_on DATE NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_academic_year PRIMARY KEY (id),
    CONSTRAINT ck_academic_year_date_window CHECK (ends_on > starts_on),
    CONSTRAINT ck_academic_year_state CHECK (state IN ('DRAFT','ACTIVE','CLOSED')),
    CONSTRAINT uq_academic_year_code UNIQUE (code)
);

CREATE TABLE stored_file (
    storage_key VARCHAR(500) NOT NULL,
    original_name VARCHAR(500) NOT NULL,
    media_type VARCHAR(150) NOT NULL,
    byte_size INTEGER NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    scan_state VARCHAR(20) DEFAULT 'QUARANTINED' NOT NULL,
    scanned_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_stored_file PRIMARY KEY (id),
    CONSTRAINT ck_stored_file_byte_size_positive CHECK (byte_size > 0),
    CONSTRAINT ck_stored_file_scan_state CHECK (scan_state IN ('QUARANTINED','CLEAN','INFECTED','FAILED')),
    CONSTRAINT uq_stored_file_storage_key UNIQUE (storage_key)
);

CREATE INDEX ix_stored_file_sha256 ON stored_file (sha256);

CREATE TABLE rubric_template (
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    version_no INTEGER NOT NULL,
    source_ref VARCHAR(500) NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_rubric_template PRIMARY KEY (id),
    CONSTRAINT uq_rubric_template_code_version_no UNIQUE (code, version_no),
    CONSTRAINT ck_rubric_template_version_positive CHECK (version_no > 0),
    CONSTRAINT ck_rubric_template_state CHECK (state IN ('DRAFT','ACTIVE','RETIRED'))
);

CREATE TABLE department (
    faculty_id UUID NOT NULL,
    code VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    major_code VARCHAR(32),
    active BOOLEAN DEFAULT true NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_department PRIMARY KEY (id),
    CONSTRAINT uq_department_faculty_id_code UNIQUE (faculty_id, code),
    CONSTRAINT fk_department_faculty_id_faculty FOREIGN KEY(faculty_id) REFERENCES faculty (id) ON DELETE RESTRICT
);

CREATE TABLE thesis_round (
    academic_year_id UUID NOT NULL,
    code VARCHAR(32) NOT NULL,
    round_type VARCHAR(20) NOT NULL,
    opens_at TIMESTAMP WITH TIME ZONE NOT NULL,
    closes_at TIMESTAMP WITH TIME ZONE NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_thesis_round PRIMARY KEY (id),
    CONSTRAINT uq_thesis_round_academic_year_id_code UNIQUE (academic_year_id, code),
    CONSTRAINT ck_thesis_round_round_type CHECK (round_type IN ('MAIN','SUPPLEMENTARY')),
    CONSTRAINT ck_thesis_round_state CHECK (state IN ('DRAFT','OPEN','CLOSED','ARCHIVED')),
    CONSTRAINT ck_thesis_round_time_window CHECK (closes_at > opens_at),
    CONSTRAINT fk_thesis_round_academic_year_id_academic_year FOREIGN KEY(academic_year_id) REFERENCES academic_year (id) ON DELETE RESTRICT
);

CREATE TABLE rubric_criterion (
    rubric_template_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    label VARCHAR(500) NOT NULL,
    max_points NUMERIC(4, 2) NOT NULL,
    criterion_type VARCHAR(20) DEFAULT 'NORMAL' NOT NULL,
    order_no INTEGER NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_rubric_criterion PRIMARY KEY (id),
    CONSTRAINT uq_rubric_criterion_rubric_template_id_code UNIQUE (rubric_template_id, code),
    CONSTRAINT uq_rubric_criterion_rubric_template_id_order_no UNIQUE (rubric_template_id, order_no),
    CONSTRAINT ck_rubric_criterion_max_points CHECK (max_points > 0 AND max_points <= 10),
    CONSTRAINT ck_rubric_criterion_order_positive CHECK (order_no > 0),
    CONSTRAINT ck_rubric_criterion_criterion_type CHECK (criterion_type IN ('NORMAL','BONUS')),
    CONSTRAINT ck_rubric_criterion_bonus_max CHECK (criterion_type <> 'BONUS' OR max_points <= 1),
    CONSTRAINT fk_rubric_criterion_rubric_template_id_rubric_template FOREIGN KEY(rubric_template_id) REFERENCES rubric_template (id) ON DELETE RESTRICT
);

CREATE TABLE retrieval_audit (
    user_id UUID NOT NULL,
    question_hash VARCHAR(64) NOT NULL,
    authorized_scope_hash VARCHAR(64) NOT NULL,
    retrieved_item_count INTEGER DEFAULT '0' NOT NULL,
    provider VARCHAR(100),
    model_version VARCHAR(100),
    outcome VARCHAR(30) NOT NULL,
    correlation_id UUID NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_retrieval_audit PRIMARY KEY (id),
    CONSTRAINT ck_retrieval_audit_outcome CHECK (outcome IN ('ANSWERED','NO_EVIDENCE','DEPENDENCY_FAILED','DENIED')),
    CONSTRAINT fk_retrieval_audit_user_id_user_account FOREIGN KEY(user_id) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE INDEX ix_retrieval_audit_correlation_id ON retrieval_audit (correlation_id);

CREATE TABLE audit_event (
    actor_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID NOT NULL,
    before_hash VARCHAR(64),
    after_hash VARCHAR(64),
    reason TEXT,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    correlation_id UUID NOT NULL,
    id UUID NOT NULL,
    CONSTRAINT pk_audit_event PRIMARY KEY (id),
    CONSTRAINT fk_audit_event_actor_id_user_account FOREIGN KEY(actor_id) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE INDEX ix_audit_event_correlation_id ON audit_event (correlation_id);

CREATE INDEX ix_audit_event_resource_id ON audit_event (resource_id);

CREATE TABLE student_profile (
    user_id UUID NOT NULL,
    student_code VARCHAR(32) NOT NULL,
    department_id UUID NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_student_profile PRIMARY KEY (id),
    CONSTRAINT uq_student_profile_user_id UNIQUE (user_id),
    CONSTRAINT fk_student_profile_user_id_user_account FOREIGN KEY(user_id) REFERENCES user_account (id) ON DELETE RESTRICT,
    CONSTRAINT uq_student_profile_student_code UNIQUE (student_code),
    CONSTRAINT fk_student_profile_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT
);

CREATE TABLE lecturer_profile (
    user_id UUID NOT NULL,
    lecturer_code VARCHAR(32) NOT NULL,
    department_id UUID NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_lecturer_profile PRIMARY KEY (id),
    CONSTRAINT uq_lecturer_profile_user_id UNIQUE (user_id),
    CONSTRAINT fk_lecturer_profile_user_id_user_account FOREIGN KEY(user_id) REFERENCES user_account (id) ON DELETE RESTRICT,
    CONSTRAINT uq_lecturer_profile_lecturer_code UNIQUE (lecturer_code),
    CONSTRAINT fk_lecturer_profile_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT
);

CREATE TABLE round_policy (
    round_id UUID NOT NULL,
    policy_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL,
    config_json JSONB NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    effective_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_round_policy PRIMARY KEY (id),
    CONSTRAINT uq_round_policy_round_id_policy_type_version UNIQUE (round_id, policy_type, version),
    CONSTRAINT ck_round_policy_version_positive CHECK (version > 0),
    CONSTRAINT ck_round_policy_state CHECK (state IN ('DRAFT','ACTIVE','RETIRED')),
    CONSTRAINT ck_round_policy_active_has_effective_at CHECK (state <> 'ACTIVE' OR effective_at IS NOT NULL),
    CONSTRAINT fk_round_policy_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT
);

CREATE TABLE topic (
    round_id UUID NOT NULL,
    department_id UUID NOT NULL,
    proposer_user_id UUID NOT NULL,
    proposer_type VARCHAR(20) NOT NULL,
    current_title VARCHAR(500) NOT NULL,
    description TEXT,
    max_students INTEGER DEFAULT '3' NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    decided_by UUID,
    decided_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_topic PRIMARY KEY (id),
    CONSTRAINT ck_topic_proposer_type CHECK (proposer_type IN ('LECTURER','STUDENT')),
    CONSTRAINT ck_topic_state CHECK (state IN ('DRAFT','SUBMITTED','APPROVED','RETURNED','REJECTED','LOCKED')),
    CONSTRAINT ck_topic_max_students CHECK (max_students BETWEEN 1 AND 3),
    CONSTRAINT fk_topic_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_proposer_user_id_user_account FOREIGN KEY(proposer_user_id) REFERENCES user_account (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_decided_by_user_account FOREIGN KEY(decided_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE progress_milestone (
    round_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    version_no INTEGER NOT NULL,
    due_at TIMESTAMP WITH TIME ZONE,
    expected_ratio NUMERIC(5, 2),
    source_type VARCHAR(20) NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_progress_milestone PRIMARY KEY (id),
    CONSTRAINT uq_progress_milestone_round_id_code_version_no UNIQUE (round_id, code, version_no),
    CONSTRAINT ck_progress_milestone_version_positive CHECK (version_no > 0),
    CONSTRAINT ck_progress_milestone_expected_ratio CHECK (expected_ratio IS NULL OR (expected_ratio >= 0 AND expected_ratio <= 100)),
    CONSTRAINT ck_progress_milestone_source_type CHECK (source_type IN ('ROUND_POLICY','STUDENT_PLAN')),
    CONSTRAINT ck_progress_milestone_state CHECK (state IN ('DRAFT','OPEN','CLOSED','CANCELLED')),
    CONSTRAINT fk_progress_milestone_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT
);

CREATE TABLE similarity_policy (
    round_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    metric_code VARCHAR(100),
    threshold_value NUMERIC(10, 6),
    decision_mode VARCHAR(20) DEFAULT 'ADVISORY' NOT NULL,
    config_json JSONB NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_similarity_policy PRIMARY KEY (id),
    CONSTRAINT uq_similarity_policy_round_id_version_no UNIQUE (round_id, version_no),
    CONSTRAINT ck_similarity_policy_version_positive CHECK (version_no > 0),
    CONSTRAINT ck_similarity_policy_decision_mode CHECK (decision_mode IN ('ADVISORY','GATE')),
    CONSTRAINT ck_similarity_policy_state CHECK (state IN ('DRAFT','ACTIVE','RETIRED')),
    CONSTRAINT ck_similarity_policy_threshold_nonnegative CHECK (threshold_value IS NULL OR threshold_value >= 0),
    CONSTRAINT fk_similarity_policy_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT
);

CREATE TABLE council (
    round_id UUID NOT NULL,
    department_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    decision_ref VARCHAR(500) NOT NULL,
    decision_date DATE NOT NULL,
    state VARCHAR(20) DEFAULT 'IMPORTED' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_council PRIMARY KEY (id),
    CONSTRAINT uq_council_round_id_code UNIQUE (round_id, code),
    CONSTRAINT ck_council_state CHECK (state IN ('IMPORTED','VALIDATED','ACTIVE','CLOSED')),
    CONSTRAINT fk_council_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_council_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT
);

CREATE TABLE position_assignment (
    lecturer_id UUID NOT NULL,
    position_id UUID NOT NULL,
    faculty_id UUID,
    department_id UUID,
    effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
    effective_to TIMESTAMP WITH TIME ZONE,
    state VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_position_assignment PRIMARY KEY (id),
    CONSTRAINT ck_position_assignment_exactly_one_scope CHECK ((faculty_id IS NOT NULL AND department_id IS NULL) OR (faculty_id IS NULL AND department_id IS NOT NULL)),
    CONSTRAINT ck_position_assignment_state CHECK (state IN ('ACTIVE','REVOKED','EXPIRED')),
    CONSTRAINT ck_position_assignment_effective_window CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT uq_position_assignment_lecturer_id_position_id_faculty__8782 UNIQUE (lecturer_id, position_id, faculty_id, department_id, effective_from),
    CONSTRAINT fk_position_assignment_lecturer_id_lecturer_profile FOREIGN KEY(lecturer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_position_assignment_position_id_organizational_position FOREIGN KEY(position_id) REFERENCES organizational_position (id) ON DELETE RESTRICT,
    CONSTRAINT fk_position_assignment_faculty_id_faculty FOREIGN KEY(faculty_id) REFERENCES faculty (id) ON DELETE RESTRICT,
    CONSTRAINT fk_position_assignment_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT
);

CREATE TABLE eligibility_snapshot (
    student_id UUID NOT NULL,
    round_id UUID NOT NULL,
    version INTEGER NOT NULL,
    passed_credit_ratio NUMERIC(5, 4) NOT NULL,
    gpa_4 NUMERIC(3, 2) NOT NULL,
    discipline_status VARCHAR(40) NOT NULL,
    criminal_case_status VARCHAR(40) NOT NULL,
    evidence_ref VARCHAR(500) NOT NULL,
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    confirmed_by UUID,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    decision_reason TEXT,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_eligibility_snapshot PRIMARY KEY (id),
    CONSTRAINT uq_eligibility_snapshot_student_id_round_id_version UNIQUE (student_id, round_id, version),
    CONSTRAINT ck_eligibility_snapshot_version_positive CHECK (version > 0),
    CONSTRAINT ck_eligibility_snapshot_credit_ratio CHECK (passed_credit_ratio >= 0 AND passed_credit_ratio <= 1),
    CONSTRAINT ck_eligibility_snapshot_gpa CHECK (gpa_4 >= 0 AND gpa_4 <= 4),
    CONSTRAINT ck_eligibility_snapshot_state CHECK (state IN ('DRAFT','SUBMITTED','CONFIRMED','REJECTED')),
    CONSTRAINT ck_eligibility_snapshot_decision_metadata CHECK (state NOT IN ('CONFIRMED','REJECTED') OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)),
    CONSTRAINT fk_eligibility_snapshot_student_id_student_profile FOREIGN KEY(student_id) REFERENCES student_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_eligibility_snapshot_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_eligibility_snapshot_confirmed_by_user_account FOREIGN KEY(confirmed_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE lecturer_expertise (
    lecturer_id UUID NOT NULL,
    version INTEGER NOT NULL,
    labels JSONB NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    verified_by UUID,
    verified_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_lecturer_expertise PRIMARY KEY (id),
    CONSTRAINT uq_lecturer_expertise_lecturer_id_version UNIQUE (lecturer_id, version),
    CONSTRAINT ck_lecturer_expertise_version_positive CHECK (version > 0),
    CONSTRAINT ck_lecturer_expertise_state CHECK (state IN ('DRAFT','SELF_DECLARED','VERIFIED','REJECTED')),
    CONSTRAINT fk_lecturer_expertise_lecturer_id_lecturer_profile FOREIGN KEY(lecturer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_lecturer_expertise_verified_by_user_account FOREIGN KEY(verified_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE topic_title_version (
    topic_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    changed_by UUID NOT NULL,
    change_reason TEXT,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_topic_title_version PRIMARY KEY (id),
    CONSTRAINT uq_topic_title_version_topic_id_version_no UNIQUE (topic_id, version_no),
    CONSTRAINT ck_topic_title_version_version_positive CHECK (version_no > 0),
    CONSTRAINT fk_topic_title_version_topic_id_topic FOREIGN KEY(topic_id) REFERENCES topic (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_title_version_changed_by_user_account FOREIGN KEY(changed_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE topic_requirement (
    topic_id UUID NOT NULL,
    requirement_type VARCHAR(30) NOT NULL,
    value_text TEXT,
    preferred_gpa NUMERIC(3, 2),
    enforcement VARCHAR(20) DEFAULT 'DESIRED' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_topic_requirement PRIMARY KEY (id),
    CONSTRAINT ck_topic_requirement_requirement_type CHECK (requirement_type IN ('PREFERRED_GPA','SKILL','TECHNOLOGY','KNOWLEDGE','OTHER')),
    CONSTRAINT ck_topic_requirement_enforcement_desired CHECK (enforcement = 'DESIRED'),
    CONSTRAINT ck_topic_requirement_preferred_gpa CHECK (preferred_gpa IS NULL OR (preferred_gpa >= 0 AND preferred_gpa <= 4)),
    CONSTRAINT fk_topic_requirement_topic_id_topic FOREIGN KEY(topic_id) REFERENCES topic (id) ON DELETE RESTRICT
);

CREATE TABLE topic_registration (
    round_id UUID NOT NULL,
    topic_id UUID NOT NULL,
    created_by UUID NOT NULL,
    state VARCHAR(30) DEFAULT 'DRAFT' NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE,
    lecturer_decided_by UUID,
    lecturer_decided_at TIMESTAMP WITH TIME ZONE,
    lecturer_reason TEXT,
    department_finalized_by UUID,
    department_finalized_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_topic_registration PRIMARY KEY (id),
    CONSTRAINT uq_topic_registration_id_round_id UNIQUE (id, round_id),
    CONSTRAINT ck_topic_registration_state CHECK (state IN ('DRAFT','SUBMITTED','LECTURER_ACCEPTED','REJECTED','FINALIZED','CANCELLED')),
    CONSTRAINT fk_topic_registration_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_registration_topic_id_topic FOREIGN KEY(topic_id) REFERENCES topic (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_registration_created_by_student_profile FOREIGN KEY(created_by) REFERENCES student_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_registration_lecturer_decided_by_lecturer_profile FOREIGN KEY(lecturer_decided_by) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_registration_department_finalized_by_user_account FOREIGN KEY(department_finalized_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE council_member (
    council_id UUID NOT NULL,
    lecturer_id UUID NOT NULL,
    role_code VARCHAR(20) NOT NULL,
    role_slot INTEGER DEFAULT '1' NOT NULL,
    active BOOLEAN DEFAULT true NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_council_member PRIMARY KEY (id),
    CONSTRAINT uq_council_member_council_id_lecturer_id UNIQUE (council_id, lecturer_id),
    CONSTRAINT uq_council_member_council_id_role_code_role_slot UNIQUE (council_id, role_code, role_slot),
    CONSTRAINT ck_council_member_role_code CHECK (role_code IN ('CHAIR','SECRETARY','REVIEWER','MEMBER')),
    CONSTRAINT ck_council_member_role_slot CHECK (role_slot BETWEEN 1 AND 2),
    CONSTRAINT ck_council_member_active_boolean CHECK (active IN (true,false)),
    CONSTRAINT fk_council_member_council_id_council FOREIGN KEY(council_id) REFERENCES council (id) ON DELETE RESTRICT,
    CONSTRAINT fk_council_member_lecturer_id_lecturer_profile FOREIGN KEY(lecturer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT
);

CREATE TABLE defense_session (
    council_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    location VARCHAR(255) NOT NULL,
    state VARCHAR(30) DEFAULT 'SCHEDULED' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_defense_session PRIMARY KEY (id),
    CONSTRAINT uq_defense_session_council_id_code UNIQUE (council_id, code),
    CONSTRAINT ck_defense_session_state CHECK (state IN ('SCHEDULED','ATTENDANCE_OPEN','READY','POSTPONED','SCORING','FINALIZED','CLOSED')),
    CONSTRAINT fk_defense_session_council_id_council FOREIGN KEY(council_id) REFERENCES council (id) ON DELETE RESTRICT
);

CREATE TABLE eligibility_exception (
    snapshot_id UUID NOT NULL,
    official_ref VARCHAR(500) NOT NULL,
    reason TEXT NOT NULL,
    granted_by UUID NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_eligibility_exception PRIMARY KEY (id),
    CONSTRAINT uq_eligibility_exception_snapshot_id UNIQUE (snapshot_id),
    CONSTRAINT fk_eligibility_exception_snapshot_id_eligibility_snapshot FOREIGN KEY(snapshot_id) REFERENCES eligibility_snapshot (id) ON DELETE RESTRICT,
    CONSTRAINT fk_eligibility_exception_granted_by_user_account FOREIGN KEY(granted_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE expertise_evidence (
    expertise_id UUID NOT NULL,
    evidence_type VARCHAR(50) NOT NULL,
    reference VARCHAR(500) NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_expertise_evidence PRIMARY KEY (id),
    CONSTRAINT fk_expertise_evidence_expertise_id_lecturer_expertise FOREIGN KEY(expertise_id) REFERENCES lecturer_expertise (id) ON DELETE RESTRICT
);

CREATE TABLE registration_member (
    registration_id UUID NOT NULL,
    round_id UUID NOT NULL,
    student_id UUID NOT NULL,
    is_coordinator BOOLEAN DEFAULT false NOT NULL,
    active BOOLEAN DEFAULT true NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_registration_member PRIMARY KEY (id),
    CONSTRAINT fk_registration_member_registration_id_round_id_topic_r_f9bb FOREIGN KEY(registration_id, round_id) REFERENCES topic_registration (id, round_id) ON DELETE RESTRICT,
    CONSTRAINT uq_registration_member_registration_id_student_id UNIQUE (registration_id, student_id),
    CONSTRAINT fk_registration_member_student_id_student_profile FOREIGN KEY(student_id) REFERENCES student_profile (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_registration_member_student_round_active ON registration_member (student_id, round_id) WHERE active;

CREATE UNIQUE INDEX uq_registration_member_one_coordinator ON registration_member (registration_id) WHERE active AND is_coordinator;

CREATE TABLE thesis (
    round_id UUID NOT NULL,
    topic_id UUID NOT NULL,
    registration_id UUID NOT NULL,
    department_id UUID NOT NULL,
    current_title VARCHAR(500) NOT NULL,
    state VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_thesis PRIMARY KEY (id),
    CONSTRAINT uq_thesis_round_id_topic_id UNIQUE (round_id, topic_id),
    CONSTRAINT ck_thesis_state CHECK (state IN ('ACTIVE','SUSPENDED','WITHDRAWN','EXTENDED','READY_FOR_DEFENSE','COMPLETED','ARCHIVED')),
    CONSTRAINT fk_thesis_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_thesis_topic_id_topic FOREIGN KEY(topic_id) REFERENCES topic (id) ON DELETE RESTRICT,
    CONSTRAINT uq_thesis_registration_id UNIQUE (registration_id),
    CONSTRAINT fk_thesis_registration_id_topic_registration FOREIGN KEY(registration_id) REFERENCES topic_registration (id) ON DELETE RESTRICT,
    CONSTRAINT fk_thesis_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT
);

CREATE TABLE council_attendance (
    session_id UUID NOT NULL,
    council_member_id UUID NOT NULL,
    present BOOLEAN NOT NULL,
    recorded_by UUID NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    note TEXT,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_council_attendance PRIMARY KEY (id),
    CONSTRAINT uq_council_attendance_session_id_council_member_id UNIQUE (session_id, council_member_id),
    CONSTRAINT fk_council_attendance_session_id_defense_session FOREIGN KEY(session_id) REFERENCES defense_session (id) ON DELETE RESTRICT,
    CONSTRAINT fk_council_attendance_council_member_id_council_member FOREIGN KEY(council_member_id) REFERENCES council_member (id) ON DELETE RESTRICT,
    CONSTRAINT fk_council_attendance_recorded_by_user_account FOREIGN KEY(recorded_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE rubric_assignment (
    rubric_template_id UUID NOT NULL,
    round_id UUID,
    session_id UUID,
    state VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_rubric_assignment PRIMARY KEY (id),
    CONSTRAINT ck_rubric_assignment_exactly_one_scope CHECK ((round_id IS NOT NULL AND session_id IS NULL) OR (round_id IS NULL AND session_id IS NOT NULL)),
    CONSTRAINT ck_rubric_assignment_state CHECK (state IN ('ACTIVE','LOCKED','RETIRED')),
    CONSTRAINT fk_rubric_assignment_rubric_template_id_rubric_template FOREIGN KEY(rubric_template_id) REFERENCES rubric_template (id) ON DELETE RESTRICT,
    CONSTRAINT fk_rubric_assignment_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_rubric_assignment_session_id_defense_session FOREIGN KEY(session_id) REFERENCES defense_session (id) ON DELETE RESTRICT
);

CREATE TABLE council_minute (
    session_id UUID NOT NULL,
    minute_no VARCHAR(100) NOT NULL,
    current_version_no INTEGER DEFAULT '0' NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    printed_at TIMESTAMP WITH TIME ZONE,
    signed_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_council_minute PRIMARY KEY (id),
    CONSTRAINT uq_council_minute_session_id_minute_no UNIQUE (session_id, minute_no),
    CONSTRAINT ck_council_minute_state CHECK (state IN ('DRAFT','EXPORTED','PRINTED','SIGNED','LOCKED','VOID','REPLACED')),
    CONSTRAINT fk_council_minute_session_id_defense_session FOREIGN KEY(session_id) REFERENCES defense_session (id) ON DELETE RESTRICT
);

CREATE TABLE resource_assignment (
    assignment_type VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL,
    round_id UUID,
    thesis_id UUID,
    council_id UUID,
    effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
    effective_to TIMESTAMP WITH TIME ZONE,
    state VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_resource_assignment PRIMARY KEY (id),
    CONSTRAINT ck_resource_assignment_exactly_one_resource CHECK ((CASE WHEN round_id IS NULL THEN 0 ELSE 1 END + CASE WHEN thesis_id IS NULL THEN 0 ELSE 1 END + CASE WHEN council_id IS NULL THEN 0 ELSE 1 END) = 1),
    CONSTRAINT ck_resource_assignment_state CHECK (state IN ('ACTIVE','REVOKED','EXPIRED')),
    CONSTRAINT ck_resource_assignment_effective_window CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT uq_resource_assignment_assignment_type_user_id_round_id_d097 UNIQUE (assignment_type, user_id, round_id, thesis_id, council_id, effective_from),
    CONSTRAINT fk_resource_assignment_user_id_user_account FOREIGN KEY(user_id) REFERENCES user_account (id) ON DELETE RESTRICT,
    CONSTRAINT fk_resource_assignment_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_resource_assignment_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT fk_resource_assignment_council_id_council FOREIGN KEY(council_id) REFERENCES council (id) ON DELETE RESTRICT
);

CREATE TABLE thesis_member (
    thesis_id UUID NOT NULL,
    student_id UUID NOT NULL,
    is_coordinator BOOLEAN DEFAULT false NOT NULL,
    active BOOLEAN DEFAULT true NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL,
    left_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_thesis_member PRIMARY KEY (id),
    CONSTRAINT uq_thesis_member_thesis_id_student_id UNIQUE (thesis_id, student_id),
    CONSTRAINT fk_thesis_member_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT fk_thesis_member_student_id_student_profile FOREIGN KEY(student_id) REFERENCES student_profile (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_thesis_member_one_coordinator ON thesis_member (thesis_id) WHERE active AND is_coordinator;

CREATE TABLE advisor_assignment (
    thesis_id UUID NOT NULL,
    lecturer_id UUID NOT NULL,
    assignment_type VARCHAR(20) DEFAULT 'PRIMARY' NOT NULL,
    assigned_by UUID NOT NULL,
    effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
    effective_to TIMESTAMP WITH TIME ZONE,
    state VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_advisor_assignment PRIMARY KEY (id),
    CONSTRAINT ck_advisor_assignment_assignment_type CHECK (assignment_type = 'PRIMARY'),
    CONSTRAINT ck_advisor_assignment_state CHECK (state IN ('ACTIVE','ENDED','REVOKED')),
    CONSTRAINT fk_advisor_assignment_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT fk_advisor_assignment_lecturer_id_lecturer_profile FOREIGN KEY(lecturer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_advisor_assignment_assigned_by_user_account FOREIGN KEY(assigned_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_advisor_assignment_active_primary ON advisor_assignment (thesis_id) WHERE state = 'ACTIVE' AND assignment_type = 'PRIMARY';

CREATE TABLE proposal (
    thesis_id UUID NOT NULL,
    current_version_no INTEGER,
    state VARCHAR(40) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_proposal PRIMARY KEY (id),
    CONSTRAINT ck_proposal_state CHECK (state IN ('DRAFT','SUBMITTED','UNDER_REVIEW','REVISION_REQUIRED','ADVISOR_CONFIRMED','DEPARTMENT_FINALIZED','DEAN_CONFIRMED','PRINT_READY')),
    CONSTRAINT uq_proposal_thesis_id UNIQUE (thesis_id),
    CONSTRAINT fk_proposal_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT
);

CREATE TABLE progress_report (
    thesis_id UUID NOT NULL,
    milestone_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    summary TEXT NOT NULL,
    reported_ratio NUMERIC(5, 2),
    evidence_file_id UUID,
    submitted_by UUID NOT NULL,
    state VARCHAR(30) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_progress_report PRIMARY KEY (id),
    CONSTRAINT uq_progress_report_thesis_id_milestone_id_version_no UNIQUE (thesis_id, milestone_id, version_no),
    CONSTRAINT ck_progress_report_version_positive CHECK (version_no > 0),
    CONSTRAINT ck_progress_report_reported_ratio CHECK (reported_ratio IS NULL OR (reported_ratio >= 0 AND reported_ratio <= 100)),
    CONSTRAINT ck_progress_report_state CHECK (state IN ('DRAFT','SUBMITTED','CONFIRMED','REVISION_REQUIRED')),
    CONSTRAINT fk_progress_report_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT fk_progress_report_milestone_id_progress_milestone FOREIGN KEY(milestone_id) REFERENCES progress_milestone (id) ON DELETE RESTRICT,
    CONSTRAINT fk_progress_report_evidence_file_id_stored_file FOREIGN KEY(evidence_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
    CONSTRAINT fk_progress_report_submitted_by_student_profile FOREIGN KEY(submitted_by) REFERENCES student_profile (id) ON DELETE RESTRICT
);

CREATE TABLE topic_change_request (
    thesis_id UUID NOT NULL,
    requested_by UUID NOT NULL,
    reason TEXT NOT NULL,
    proposed_topic_id UUID,
    proposed_title VARCHAR(500),
    advisor_reviewed_by UUID,
    advisor_reviewed_at TIMESTAMP WITH TIME ZONE,
    department_decided_by UUID,
    department_decided_at TIMESTAMP WITH TIME ZONE,
    state VARCHAR(30) DEFAULT 'SUBMITTED' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_topic_change_request PRIMARY KEY (id),
    CONSTRAINT ck_topic_change_request_state CHECK (state IN ('SUBMITTED','ADVISOR_REVIEWED','APPROVED','REJECTED','CANCELLED')),
    CONSTRAINT ck_topic_change_request_target_present CHECK (proposed_topic_id IS NOT NULL OR proposed_title IS NOT NULL),
    CONSTRAINT fk_topic_change_request_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_change_request_requested_by_student_profile FOREIGN KEY(requested_by) REFERENCES student_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_change_request_proposed_topic_id_topic FOREIGN KEY(proposed_topic_id) REFERENCES topic (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_change_request_advisor_reviewed_by_lecturer_profile FOREIGN KEY(advisor_reviewed_by) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_topic_change_request_department_decided_by_user_account FOREIGN KEY(department_decided_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE external_procedure_outcome (
    thesis_id UUID NOT NULL,
    outcome_type VARCHAR(20) NOT NULL,
    official_ref VARCHAR(500) NOT NULL,
    effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
    evidence_file_id UUID,
    recorded_by UUID NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_external_procedure_outcome PRIMARY KEY (id),
    CONSTRAINT ck_external_procedure_outcome_outcome_type CHECK (outcome_type IN ('WITHDRAWAL','EXTENSION')),
    CONSTRAINT uq_external_procedure_outcome_thesis_id_outcome_type_of_dc26 UNIQUE (thesis_id, outcome_type, official_ref),
    CONSTRAINT fk_external_procedure_outcome_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT fk_external_procedure_outcome_evidence_file_id_stored_file FOREIGN KEY(evidence_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
    CONSTRAINT fk_external_procedure_outcome_recorded_by_user_account FOREIGN KEY(recorded_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE document (
    thesis_id UUID NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    visibility VARCHAR(20) DEFAULT 'PRIVATE' NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_document PRIMARY KEY (id),
    CONSTRAINT ck_document_visibility CHECK (visibility IN ('PRIVATE','ASSIGNED','INTERNAL','PUBLISHED')),
    CONSTRAINT ck_document_state CHECK (state IN ('DRAFT','ACTIVE','ARCHIVED','REVOKED')),
    CONSTRAINT fk_document_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT
);

CREATE TABLE session_thesis (
    session_id UUID NOT NULL,
    thesis_id UUID NOT NULL,
    order_no INTEGER NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_session_thesis PRIMARY KEY (id),
    CONSTRAINT uq_session_thesis_session_id_thesis_id UNIQUE (session_id, thesis_id),
    CONSTRAINT uq_session_thesis_session_id_order_no UNIQUE (session_id, order_no),
    CONSTRAINT ck_session_thesis_order_positive CHECK (order_no > 0),
    CONSTRAINT fk_session_thesis_session_id_defense_session FOREIGN KEY(session_id) REFERENCES defense_session (id) ON DELETE RESTRICT,
    CONSTRAINT fk_session_thesis_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT
);

CREATE TABLE minute_version (
    minute_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    stored_file_id UUID NOT NULL,
    generated_by UUID NOT NULL,
    state VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    replacement_for_id UUID,
    void_reason TEXT,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_minute_version PRIMARY KEY (id),
    CONSTRAINT uq_minute_version_minute_id_version_no UNIQUE (minute_id, version_no),
    CONSTRAINT ck_minute_version_version_positive CHECK (version_no > 0),
    CONSTRAINT ck_minute_version_state CHECK (state IN ('DRAFT','EXPORTED','VOID','PRINTED','SIGNED')),
    CONSTRAINT ck_minute_version_not_self_replacement CHECK (replacement_for_id IS NULL OR replacement_for_id <> id),
    CONSTRAINT fk_minute_version_minute_id_council_minute FOREIGN KEY(minute_id) REFERENCES council_minute (id) ON DELETE RESTRICT,
    CONSTRAINT fk_minute_version_stored_file_id_stored_file FOREIGN KEY(stored_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
    CONSTRAINT fk_minute_version_generated_by_user_account FOREIGN KEY(generated_by) REFERENCES user_account (id) ON DELETE RESTRICT,
    CONSTRAINT fk_minute_version_replacement_for_id_minute_version FOREIGN KEY(replacement_for_id) REFERENCES minute_version (id) ON DELETE RESTRICT
);

CREATE TABLE member_work_assignment (
    thesis_member_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    work_description TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    state VARCHAR(30) DEFAULT 'DRAFT' NOT NULL,
    reviewed_by UUID,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_comment TEXT,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_member_work_assignment PRIMARY KEY (id),
    CONSTRAINT uq_member_work_assignment_thesis_member_id_version_no UNIQUE (thesis_member_id, version_no),
    CONSTRAINT ck_member_work_assignment_version_positive CHECK (version_no > 0),
    CONSTRAINT ck_member_work_assignment_state CHECK (state IN ('DRAFT','SUBMITTED','APPROVED','REVISION_REQUIRED')),
    CONSTRAINT fk_member_work_assignment_thesis_member_id_thesis_member FOREIGN KEY(thesis_member_id) REFERENCES thesis_member (id) ON DELETE RESTRICT,
    CONSTRAINT fk_member_work_assignment_reviewed_by_lecturer_profile FOREIGN KEY(reviewed_by) REFERENCES lecturer_profile (id) ON DELETE RESTRICT
);

CREATE TABLE reviewer_assignment (
    lecturer_id UUID NOT NULL,
    proposal_id UUID,
    thesis_id UUID,
    review_scope VARCHAR(20) NOT NULL,
    assigned_by UUID NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL,
    state VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_reviewer_assignment PRIMARY KEY (id),
    CONSTRAINT ck_reviewer_assignment_exactly_one_subject CHECK ((proposal_id IS NOT NULL AND thesis_id IS NULL) OR (proposal_id IS NULL AND thesis_id IS NOT NULL)),
    CONSTRAINT ck_reviewer_assignment_review_scope CHECK (review_scope IN ('PROPOSAL','THESIS')),
    CONSTRAINT ck_reviewer_assignment_state CHECK (state IN ('ACTIVE','COMPLETED','REVOKED')),
    CONSTRAINT uq_reviewer_assignment_lecturer_id_proposal_id_thesis_i_15ea UNIQUE (lecturer_id, proposal_id, thesis_id, review_scope),
    CONSTRAINT fk_reviewer_assignment_lecturer_id_lecturer_profile FOREIGN KEY(lecturer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
    CONSTRAINT fk_reviewer_assignment_proposal_id_proposal FOREIGN KEY(proposal_id) REFERENCES proposal (id) ON DELETE RESTRICT,
    CONSTRAINT fk_reviewer_assignment_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT fk_reviewer_assignment_assigned_by_user_account FOREIGN KEY(assigned_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE proposal_version (
    proposal_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    stored_file_id UUID NOT NULL,
    submitted_by UUID NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    content_sha256 VARCHAR(64) NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_proposal_version PRIMARY KEY (id),
    CONSTRAINT uq_proposal_version_proposal_id_version_no UNIQUE (proposal_id, version_no),
    CONSTRAINT ck_proposal_version_version_positive CHECK (version_no > 0),
    CONSTRAINT fk_proposal_version_proposal_id_proposal FOREIGN KEY(proposal_id) REFERENCES proposal (id) ON DELETE RESTRICT,
    CONSTRAINT fk_proposal_version_stored_file_id_stored_file FOREIGN KEY(stored_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
    CONSTRAINT fk_proposal_version_submitted_by_student_profile FOREIGN KEY(submitted_by) REFERENCES student_profile (id) ON DELETE RESTRICT
);

CREATE TABLE signature_confirmation (
    proposal_id UUID NOT NULL,
    signature_type VARCHAR(40) NOT NULL,
    signer_user_id UUID NOT NULL,
    confirmed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    official_ref VARCHAR(500),
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_signature_confirmation PRIMARY KEY (id),
    CONSTRAINT ck_signature_confirmation_signature_type CHECK (signature_type IN ('DEPARTMENT_FINALIZATION','DEAN_CONFIRMATION')),
    CONSTRAINT uq_signature_confirmation_proposal_id_signature_type UNIQUE (proposal_id, signature_type),
    CONSTRAINT fk_signature_confirmation_proposal_id_proposal FOREIGN KEY(proposal_id) REFERENCES proposal (id) ON DELETE RESTRICT,
    CONSTRAINT fk_signature_confirmation_signer_user_id_user_account FOREIGN KEY(signer_user_id) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE progress_review (
    progress_report_id UUID NOT NULL,
    reviewer_id UUID NOT NULL,
    decision VARCHAR(30) NOT NULL,
    comment TEXT NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_progress_review PRIMARY KEY (id),
    CONSTRAINT ck_progress_review_decision CHECK (decision IN ('CONFIRM','REVISION_REQUIRED')),
    CONSTRAINT uq_progress_review_progress_report_id_reviewer_id UNIQUE (progress_report_id, reviewer_id),
    CONSTRAINT fk_progress_review_progress_report_id_progress_report FOREIGN KEY(progress_report_id) REFERENCES progress_report (id) ON DELETE RESTRICT,
    CONSTRAINT fk_progress_review_reviewer_id_lecturer_profile FOREIGN KEY(reviewer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT
);

CREATE TABLE document_version (
    document_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    stored_file_id UUID NOT NULL,
    submitted_by UUID NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    content_sha256 VARCHAR(64) NOT NULL,
    state VARCHAR(30) DEFAULT 'DRAFT' NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_document_version PRIMARY KEY (id),
    CONSTRAINT uq_document_version_document_id_version_no UNIQUE (document_id, version_no),
    CONSTRAINT ck_document_version_version_positive CHECK (version_no > 0),
    CONSTRAINT ck_document_version_state CHECK (state IN ('DRAFT','SUBMITTED','RESULT_AVAILABLE','REVISION_REQUESTED','ACCEPTED','FINAL')),
    CONSTRAINT fk_document_version_document_id_document FOREIGN KEY(document_id) REFERENCES document (id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_version_stored_file_id_stored_file FOREIGN KEY(stored_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_version_submitted_by_student_profile FOREIGN KEY(submitted_by) REFERENCES student_profile (id) ON DELETE RESTRICT
);

CREATE TABLE bonus_evidence (
    thesis_member_id UUID NOT NULL,
    evidence_type VARCHAR(100) NOT NULL,
    reference VARCHAR(500) NOT NULL,
    stored_file_id UUID,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_bonus_evidence PRIMARY KEY (id),
    CONSTRAINT fk_bonus_evidence_thesis_member_id_thesis_member FOREIGN KEY(thesis_member_id) REFERENCES thesis_member (id) ON DELETE RESTRICT,
    CONSTRAINT fk_bonus_evidence_stored_file_id_stored_file FOREIGN KEY(stored_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT
);

CREATE TABLE evaluation (
    session_id UUID NOT NULL,
    evaluator_member_id UUID NOT NULL,
    thesis_member_id UUID NOT NULL,
    rubric_assignment_id UUID NOT NULL,
    total_points NUMERIC(4, 2) DEFAULT '0' NOT NULL,
    bonus_points NUMERIC(4, 2) DEFAULT '0' NOT NULL,
    status VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE,
    correction_reason TEXT,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_evaluation PRIMARY KEY (id),
    CONSTRAINT uq_evaluation_session_id_evaluator_member_id_thesis_member_id UNIQUE (session_id, evaluator_member_id, thesis_member_id),
    CONSTRAINT ck_evaluation_status CHECK (status IN ('DRAFT','SUBMITTED','CORRECTED','LOCKED')),
    CONSTRAINT ck_evaluation_total_points CHECK (total_points >= 0 AND total_points <= 10),
    CONSTRAINT ck_evaluation_bonus_points CHECK (bonus_points >= 0 AND bonus_points <= 1),
    CONSTRAINT ck_evaluation_bonus_within_total CHECK (bonus_points <= total_points),
    CONSTRAINT fk_evaluation_session_id_defense_session FOREIGN KEY(session_id) REFERENCES defense_session (id) ON DELETE RESTRICT,
    CONSTRAINT fk_evaluation_evaluator_member_id_council_member FOREIGN KEY(evaluator_member_id) REFERENCES council_member (id) ON DELETE RESTRICT,
    CONSTRAINT fk_evaluation_thesis_member_id_thesis_member FOREIGN KEY(thesis_member_id) REFERENCES thesis_member (id) ON DELETE RESTRICT,
    CONSTRAINT fk_evaluation_rubric_assignment_id_rubric_assignment FOREIGN KEY(rubric_assignment_id) REFERENCES rubric_assignment (id) ON DELETE RESTRICT
);

CREATE TABLE final_result (
    session_id UUID NOT NULL,
    thesis_member_id UUID NOT NULL,
    scorer_count INTEGER NOT NULL,
    average_score NUMERIC(4, 2) NOT NULL,
    bonus_average NUMERIC(4, 2) NOT NULL,
    final_score NUMERIC(3, 1) NOT NULL,
    calculation_version INTEGER NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_final_result PRIMARY KEY (id),
    CONSTRAINT uq_final_result_session_id_thesis_member_id UNIQUE (session_id, thesis_member_id),
    CONSTRAINT ck_final_result_average_score CHECK (average_score >= 0 AND average_score <= 10),
    CONSTRAINT ck_final_result_bonus_average CHECK (bonus_average >= 0 AND bonus_average <= 1),
    CONSTRAINT ck_final_result_final_score CHECK (final_score >= 0 AND final_score <= 10),
    CONSTRAINT ck_final_result_scorer_count CHECK (scorer_count > 0),
    CONSTRAINT ck_final_result_calculation_version CHECK (calculation_version > 0),
    CONSTRAINT fk_final_result_session_id_defense_session FOREIGN KEY(session_id) REFERENCES defense_session (id) ON DELETE RESTRICT,
    CONSTRAINT fk_final_result_thesis_member_id_thesis_member FOREIGN KEY(thesis_member_id) REFERENCES thesis_member (id) ON DELETE RESTRICT
);

CREATE TABLE minute_signature (
    minute_version_id UUID NOT NULL,
    signer_member_id UUID NOT NULL,
    signed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    signature_ref VARCHAR(500),
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_minute_signature PRIMARY KEY (id),
    CONSTRAINT uq_minute_signature_minute_version_id_signer_member_id UNIQUE (minute_version_id, signer_member_id),
    CONSTRAINT fk_minute_signature_minute_version_id_minute_version FOREIGN KEY(minute_version_id) REFERENCES minute_version (id) ON DELETE RESTRICT,
    CONSTRAINT fk_minute_signature_signer_member_id_council_member FOREIGN KEY(signer_member_id) REFERENCES council_member (id) ON DELETE RESTRICT
);

CREATE TABLE proposal_review (
    proposal_version_id UUID NOT NULL,
    reviewer_assignment_id UUID NOT NULL,
    reviewer_user_id UUID NOT NULL,
    decision VARCHAR(30) NOT NULL,
    comment TEXT NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_proposal_review PRIMARY KEY (id),
    CONSTRAINT ck_proposal_review_decision CHECK (decision IN ('COMMENT','REVISION_REQUIRED','CONFIRM')),
    CONSTRAINT fk_proposal_review_proposal_version_id_proposal_version FOREIGN KEY(proposal_version_id) REFERENCES proposal_version (id) ON DELETE RESTRICT,
    CONSTRAINT fk_proposal_review_reviewer_assignment_id_reviewer_assignment FOREIGN KEY(reviewer_assignment_id) REFERENCES reviewer_assignment (id) ON DELETE RESTRICT,
    CONSTRAINT fk_proposal_review_reviewer_user_id_user_account FOREIGN KEY(reviewer_user_id) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE similarity_check (
    document_version_id UUID NOT NULL,
    policy_id UUID,
    metric_code VARCHAR(100) NOT NULL,
    lexical_coverage_pct NUMERIC(6, 3),
    semantic_candidate_score NUMERIC(10, 6),
    business_status VARCHAR(40),
    model_version VARCHAR(100),
    index_version VARCHAR(100),
    corpus_snapshot VARCHAR(200),
    state VARCHAR(20) DEFAULT 'QUEUED' NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_similarity_check PRIMARY KEY (id),
    CONSTRAINT ck_similarity_check_state CHECK (state IN ('QUEUED','RUNNING','COMPLETED','FAILED')),
    CONSTRAINT fk_similarity_check_document_version_id_document_version FOREIGN KEY(document_version_id) REFERENCES document_version (id) ON DELETE RESTRICT,
    CONSTRAINT fk_similarity_check_policy_id_similarity_policy FOREIGN KEY(policy_id) REFERENCES similarity_policy (id) ON DELETE RESTRICT
);

CREATE TABLE advisor_review (
    advisor_assignment_id UUID NOT NULL,
    thesis_member_id UUID NOT NULL,
    document_version_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    attitude TEXT NOT NULL,
    content_response TEXT NOT NULL,
    presentation TEXT NOT NULL,
    defense_recommendation VARCHAR(20) NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_advisor_review PRIMARY KEY (id),
    CONSTRAINT uq_advisor_review_advisor_assignment_id_thesis_member_i_0e97 UNIQUE (advisor_assignment_id, thesis_member_id, version_no),
    CONSTRAINT ck_advisor_review_version_positive CHECK (version_no > 0),
    CONSTRAINT ck_advisor_review_defense_recommendation CHECK (defense_recommendation IN ('ALLOW','DENY')),
    CONSTRAINT fk_advisor_review_advisor_assignment_id_advisor_assignment FOREIGN KEY(advisor_assignment_id) REFERENCES advisor_assignment (id) ON DELETE RESTRICT,
    CONSTRAINT fk_advisor_review_thesis_member_id_thesis_member FOREIGN KEY(thesis_member_id) REFERENCES thesis_member (id) ON DELETE RESTRICT,
    CONSTRAINT fk_advisor_review_document_version_id_document_version FOREIGN KEY(document_version_id) REFERENCES document_version (id) ON DELETE RESTRICT
);

CREATE TABLE reviewer_review (
    reviewer_assignment_id UUID NOT NULL,
    thesis_member_id UUID NOT NULL,
    document_version_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    presentation TEXT NOT NULL,
    research_quality TEXT NOT NULL,
    contribution TEXT NOT NULL,
    questions TEXT NOT NULL,
    overall TEXT NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_reviewer_review PRIMARY KEY (id),
    CONSTRAINT uq_reviewer_review_reviewer_assignment_id_thesis_member_2ade UNIQUE (reviewer_assignment_id, thesis_member_id, version_no),
    CONSTRAINT ck_reviewer_review_version_positive CHECK (version_no > 0),
    CONSTRAINT fk_reviewer_review_reviewer_assignment_id_reviewer_assignment FOREIGN KEY(reviewer_assignment_id) REFERENCES reviewer_assignment (id) ON DELETE RESTRICT,
    CONSTRAINT fk_reviewer_review_thesis_member_id_thesis_member FOREIGN KEY(thesis_member_id) REFERENCES thesis_member (id) ON DELETE RESTRICT,
    CONSTRAINT fk_reviewer_review_document_version_id_document_version FOREIGN KEY(document_version_id) REFERENCES document_version (id) ON DELETE RESTRICT
);

CREATE TABLE evaluation_item (
    evaluation_id UUID NOT NULL,
    criterion_id UUID NOT NULL,
    points NUMERIC(4, 2) NOT NULL,
    comment TEXT,
    bonus_evidence_id UUID,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_evaluation_item PRIMARY KEY (id),
    CONSTRAINT uq_evaluation_item_evaluation_id_criterion_id UNIQUE (evaluation_id, criterion_id),
    CONSTRAINT ck_evaluation_item_points_nonnegative CHECK (points >= 0),
    CONSTRAINT fk_evaluation_item_evaluation_id_evaluation FOREIGN KEY(evaluation_id) REFERENCES evaluation (id) ON DELETE RESTRICT,
    CONSTRAINT fk_evaluation_item_criterion_id_rubric_criterion FOREIGN KEY(criterion_id) REFERENCES rubric_criterion (id) ON DELETE RESTRICT,
    CONSTRAINT fk_evaluation_item_bonus_evidence_id_bonus_evidence FOREIGN KEY(bonus_evidence_id) REFERENCES bonus_evidence (id) ON DELETE RESTRICT
);

CREATE TABLE repository_item (
    thesis_id UUID NOT NULL,
    published_document_version_id UUID NOT NULL,
    title VARCHAR(500) NOT NULL,
    abstract TEXT,
    keywords JSONB NOT NULL,
    source_type VARCHAR(50) DEFAULT 'THESIS' NOT NULL,
    visibility VARCHAR(20) DEFAULT 'INTERNAL' NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    row_version INTEGER DEFAULT '1' NOT NULL,
    CONSTRAINT pk_repository_item PRIMARY KEY (id),
    CONSTRAINT ck_repository_item_visibility CHECK (visibility IN ('INTERNAL','PUBLISHED','REVOKED')),
    CONSTRAINT fk_repository_item_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
    CONSTRAINT uq_repository_item_published_document_version_id UNIQUE (published_document_version_id),
    CONSTRAINT fk_repository_item_published_document_version_id_docume_db47 FOREIGN KEY(published_document_version_id) REFERENCES document_version (id) ON DELETE RESTRICT
);

CREATE TABLE similarity_match (
    check_id UUID NOT NULL,
    source_document_version_id UUID,
    source_ref VARCHAR(500) NOT NULL,
    input_start INTEGER NOT NULL,
    input_end INTEGER NOT NULL,
    matched_text_hash VARCHAR(64),
    lexical_score NUMERIC(10, 6),
    semantic_score NUMERIC(10, 6),
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_similarity_match PRIMARY KEY (id),
    CONSTRAINT ck_similarity_match_input_range CHECK (input_start >= 0 AND input_end > input_start),
    CONSTRAINT fk_similarity_match_check_id_similarity_check FOREIGN KEY(check_id) REFERENCES similarity_check (id) ON DELETE RESTRICT,
    CONSTRAINT fk_similarity_match_source_document_version_id_document_version FOREIGN KEY(source_document_version_id) REFERENCES document_version (id) ON DELETE RESTRICT
);

CREATE TABLE defense_eligibility_check (
    thesis_member_id UUID NOT NULL,
    round_id UUID NOT NULL,
    advisor_review_id UUID,
    discipline_result VARCHAR(40) NOT NULL,
    completion_result VARCHAR(40) NOT NULL,
    advisor_result VARCHAR(40) NOT NULL,
    local_policy_result VARCHAR(40),
    similarity_result VARCHAR(40),
    result VARCHAR(30) NOT NULL,
    reason TEXT,
    checked_by UUID NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_defense_eligibility_check PRIMARY KEY (id),
    CONSTRAINT ck_defense_eligibility_check_result CHECK (result IN ('ELIGIBLE','NOT_ELIGIBLE','PENDING_POLICY')),
    CONSTRAINT fk_defense_eligibility_check_thesis_member_id_thesis_member FOREIGN KEY(thesis_member_id) REFERENCES thesis_member (id) ON DELETE RESTRICT,
    CONSTRAINT fk_defense_eligibility_check_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
    CONSTRAINT fk_defense_eligibility_check_advisor_review_id_advisor_review FOREIGN KEY(advisor_review_id) REFERENCES advisor_review (id) ON DELETE RESTRICT,
    CONSTRAINT fk_defense_eligibility_check_checked_by_user_account FOREIGN KEY(checked_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

CREATE TABLE search_index_metadata (
    repository_item_id UUID NOT NULL,
    document_version_id UUID NOT NULL,
    index_name VARCHAR(100) NOT NULL,
    index_version VARCHAR(100) NOT NULL,
    embedding_model VARCHAR(150),
    chunking_version VARCHAR(100),
    external_point_namespace VARCHAR(200),
    state VARCHAR(20) DEFAULT 'PENDING' NOT NULL,
    indexed_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_search_index_metadata PRIMARY KEY (id),
    CONSTRAINT uq_search_index_metadata_repository_item_id_index_name__53cf UNIQUE (repository_item_id, index_name, index_version),
    CONSTRAINT ck_search_index_metadata_state CHECK (state IN ('PENDING','INDEXED','FAILED','REMOVED')),
    CONSTRAINT fk_search_index_metadata_repository_item_id_repository_item FOREIGN KEY(repository_item_id) REFERENCES repository_item (id) ON DELETE RESTRICT,
    CONSTRAINT fk_search_index_metadata_document_version_id_document_version FOREIGN KEY(document_version_id) REFERENCES document_version (id) ON DELETE RESTRICT
);

ALTER TABLE position_assignment DROP CONSTRAINT uq_position_assignment_lecturer_id_position_id_faculty__8782;

CREATE UNIQUE INDEX uq_position_assignment_faculty_scope ON position_assignment (lecturer_id, position_id, faculty_id) WHERE faculty_id IS NOT NULL AND state = 'ACTIVE';

CREATE UNIQUE INDEX uq_position_assignment_department_scope ON position_assignment (lecturer_id, position_id, department_id) WHERE department_id IS NOT NULL AND state = 'ACTIVE';

ALTER TABLE resource_assignment DROP CONSTRAINT uq_resource_assignment_assignment_type_user_id_round_id_d097;

CREATE UNIQUE INDEX uq_resource_assignment_round_scope ON resource_assignment (assignment_type, user_id, round_id) WHERE round_id IS NOT NULL AND state = 'ACTIVE';

CREATE UNIQUE INDEX uq_resource_assignment_thesis_scope ON resource_assignment (assignment_type, user_id, thesis_id) WHERE thesis_id IS NOT NULL AND state = 'ACTIVE';

CREATE UNIQUE INDEX uq_resource_assignment_council_scope ON resource_assignment (assignment_type, user_id, council_id) WHERE council_id IS NOT NULL AND state = 'ACTIVE';

ALTER TABLE reviewer_assignment DROP CONSTRAINT uq_reviewer_assignment_lecturer_id_proposal_id_thesis_i_15ea;

ALTER TABLE reviewer_assignment ADD CONSTRAINT ck_reviewer_assignment_scope_matches_subject CHECK ((review_scope = 'PROPOSAL' AND proposal_id IS NOT NULL) OR (review_scope = 'THESIS' AND thesis_id IS NOT NULL));

CREATE UNIQUE INDEX uq_reviewer_assignment_proposal ON reviewer_assignment (lecturer_id, proposal_id) WHERE proposal_id IS NOT NULL AND state = 'ACTIVE';

CREATE UNIQUE INDEX uq_reviewer_assignment_thesis ON reviewer_assignment (lecturer_id, thesis_id) WHERE thesis_id IS NOT NULL AND state = 'ACTIVE';

ALTER TABLE rubric_criterion ADD COLUMN parent_id UUID;

ALTER TABLE rubric_criterion ADD CONSTRAINT fk_rubric_criterion_parent_id_rubric_criterion FOREIGN KEY (parent_id) REFERENCES rubric_criterion (id) ON DELETE RESTRICT;

ALTER TABLE rubric_criterion ADD CONSTRAINT ck_rubric_criterion_not_self_parent CHECK (parent_id IS NULL OR parent_id <> id);

ALTER TABLE rubric_criterion DROP CONSTRAINT ck_rubric_criterion_criterion_type;

ALTER TABLE rubric_criterion ADD CONSTRAINT ck_rubric_criterion_criterion_type CHECK (criterion_type IN ('GROUP','NORMAL','BONUS'));

ALTER TABLE document_version DROP CONSTRAINT ck_document_version_state;

ALTER TABLE document_version ADD CONSTRAINT ck_document_version_state CHECK (state IN ('DRAFT','SUBMITTED','RESULT_AVAILABLE','REVISION_REQUESTED','ACCEPTED','FINAL','SUPERSEDED'));

ALTER TABLE topic_registration DROP CONSTRAINT ck_topic_registration_state;

ALTER TABLE topic_registration ADD CONSTRAINT ck_topic_registration_state CHECK (state IN ('DRAFT','SUBMITTED','LECTURER_ACCEPTED','LECTURER_REJECTED','RETURNED','FINALIZED','CANCELLED'));

ALTER TABLE thesis DROP CONSTRAINT ck_thesis_state;

ALTER TABLE thesis ADD CONSTRAINT ck_thesis_state CHECK (state IN ('ACTIVE','PROPOSAL_APPROVED','IN_PROGRESS','EXTENDED','WITHDRAWN','READY_FOR_DEFENSE','DEFENDED','COMPLETED','ARCHIVED'));

INSERT INTO alembic_version (version_num) VALUES ('20260920_0001') RETURNING alembic_version.version_num;

-- Running upgrade 20260920_0001 -> 20260924_0002

DO $$ BEGIN IF EXISTS (SELECT 1 FROM signature_confirmation) THEN RAISE EXCEPTION 'Cannot infer historical proposal version for existing signatures'; END IF; END $$;

ALTER TABLE signature_confirmation ADD COLUMN proposal_version_no INTEGER NOT NULL;

ALTER TABLE signature_confirmation ADD CONSTRAINT ck_signature_confirmation_ck_signature_confirmation_pro_6af3 CHECK (proposal_version_no > 0);

ALTER TABLE signature_confirmation ADD CONSTRAINT fk_signature_confirmation_proposal_version_pair FOREIGN KEY(proposal_id, proposal_version_no) REFERENCES proposal_version (proposal_id, version_no) ON DELETE RESTRICT;

UPDATE alembic_version SET version_num='20260924_0002' WHERE alembic_version.version_num = '20260920_0001';

-- Running upgrade 20260924_0002 -> 20260925_0003

ALTER TABLE repository_item ALTER COLUMN thesis_id DROP NOT NULL;

ALTER TABLE repository_item ALTER COLUMN published_document_version_id DROP NOT NULL;

ALTER TABLE repository_item ADD COLUMN stored_file_id UUID;

ALTER TABLE repository_item ADD COLUMN origin_type VARCHAR(30) DEFAULT 'MANAGED_THESIS' NOT NULL;

ALTER TABLE repository_item ADD COLUMN source_ref VARCHAR(500);

ALTER TABLE repository_item ADD COLUMN provenance TEXT;

ALTER TABLE repository_item ADD COLUMN source_version VARCHAR(100);

ALTER TABLE repository_item ADD CONSTRAINT fk_repository_item_stored_file_id_stored_file FOREIGN KEY(stored_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT;

ALTER TABLE repository_item ADD CONSTRAINT ck_repository_item_ck_repository_item_origin_type CHECK (origin_type IN ('MANAGED_THESIS','IMPORTED_DOCUMENT','OFFICIAL_SOURCE'));

ALTER TABLE repository_item ADD CONSTRAINT ck_repository_item_ck_repository_item_source_type CHECK (source_type IN ('THESIS','CAPSTONE_PROJECT','TERM_PROJECT','COURSE_PROJECT','REGULATION','FORM','GUIDELINE','SYNTHETIC_TEST'));

ALTER TABLE repository_item ADD CONSTRAINT ck_repository_item_ck_repository_item_origin_source_consistency CHECK ((origin_type = 'MANAGED_THESIS' AND source_type = 'THESIS' AND thesis_id IS NOT NULL AND published_document_version_id IS NOT NULL) OR (origin_type = 'IMPORTED_DOCUMENT' AND source_type IN ('THESIS','CAPSTONE_PROJECT','TERM_PROJECT','COURSE_PROJECT','SYNTHETIC_TEST') AND thesis_id IS NULL AND published_document_version_id IS NULL) OR (origin_type = 'OFFICIAL_SOURCE' AND source_type IN ('REGULATION','FORM','GUIDELINE') AND thesis_id IS NULL AND published_document_version_id IS NULL));

ALTER TABLE repository_item ADD CONSTRAINT ck_repository_item_ck_repository_item_has_source_reference CHECK (source_ref IS NOT NULL OR stored_file_id IS NOT NULL OR published_document_version_id IS NOT NULL);

CREATE INDEX ix_repository_item_source_type_visibility ON repository_item (source_type, visibility);

ALTER TABLE search_index_metadata ALTER COLUMN document_version_id DROP NOT NULL;

ALTER TABLE similarity_match ADD COLUMN source_repository_item_id UUID;

ALTER TABLE similarity_match ADD CONSTRAINT fk_similarity_match_source_repository_item_id_repository_item FOREIGN KEY(source_repository_item_id) REFERENCES repository_item (id) ON DELETE RESTRICT;

UPDATE alembic_version SET version_num='20260925_0003' WHERE alembic_version.version_num = '20260924_0002';

-- Running upgrade 20260925_0003 -> 20260925_0004

ALTER TABLE repository_item ADD COLUMN external_source_id VARCHAR(200);

ALTER TABLE repository_item ADD COLUMN source_url VARCHAR(1000);

ALTER TABLE repository_item ADD CONSTRAINT uq_repository_item_external_source_id UNIQUE (external_source_id);

ALTER TABLE repository_item ADD CONSTRAINT ck_repository_item_ck_repository_item_source_url_https CHECK (source_url IS NULL OR source_url LIKE 'https://%');

ALTER TABLE repository_item DROP CONSTRAINT ck_repository_item_ck_repository_item_has_source_reference;

ALTER TABLE repository_item ADD CONSTRAINT ck_repository_item_ck_repository_item_has_source_reference CHECK (source_ref IS NOT NULL OR source_url IS NOT NULL OR stored_file_id IS NOT NULL OR published_document_version_id IS NOT NULL);

UPDATE alembic_version SET version_num='20260925_0004' WHERE alembic_version.version_num = '20260925_0003';

-- Running upgrade 20260925_0004 -> 20260925_0005

ALTER TABLE progress_review DROP CONSTRAINT ck_progress_review_decision;

ALTER TABLE progress_review ADD CONSTRAINT ck_progress_review_decision CHECK (decision IN ('COMMENT_ONLY','CONFIRM','REVISION_REQUIRED'));

UPDATE alembic_version SET version_num='20260925_0005' WHERE alembic_version.version_num = '20260925_0004';

COMMIT;
