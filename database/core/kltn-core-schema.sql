-- KLTN: CSDL loi theo gop y GV, uu tien tai khoan, dot, dieu kien, de tai, dang ky, khoa luan, GVHD, de cuong, tien do, tai lieu.
-- Nguon: PostgreSQL kltn_ai, Alembic 20261004_0011; doi chieu metadata truoc khi xuat.
-- Chi chay MOT LAN tren database PostgreSQL MOI, TRONG (de xuat ten: kltn_core).
-- Khong chay tren kltn_ai/kltn_dev. Khong chua du lieu sinh vien, de tai hay mat khau.
-- Ban 62 bang o kltn_ai duoc giu lam tham chieu cho cac giai doan sau.
-- council chi dong vai tro FK cho resource_assignment; KHONG dung council cho buoi gop y de cuong/tien do.

BEGIN;
SET LOCAL search_path = public;
DO $check_empty$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
    ) THEN
        RAISE EXCEPTION 'Database must be empty; do not run this file on kltn_ai or kltn_dev';
    END IF;
END $check_empty$;

-- 01. faculty
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

-- 02. department
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

-- 03. user_account
CREATE TABLE user_account (
	external_subject VARCHAR(255),
	email VARCHAR(255),
	password_hash VARCHAR(255),
	email_verified_at TIMESTAMP WITH TIME ZONE,
	base_role VARCHAR(20) NOT NULL,
	status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	CONSTRAINT pk_user_account PRIMARY KEY (id),
	CONSTRAINT ck_user_account_base_role CHECK (base_role IN ('ADMIN','LECTURER','STUDENT')),
	CONSTRAINT ck_user_account_status CHECK (status IN ('ACTIVE','LOCKED','DISABLED')),
	CONSTRAINT ck_user_account_identity_present CHECK (external_subject IS NOT NULL OR email IS NOT NULL),
	CONSTRAINT ck_user_account_local_credentials_pair CHECK ((email IS NULL AND password_hash IS NULL) OR (email IS NOT NULL AND password_hash IS NOT NULL)),
	CONSTRAINT ck_user_account_email_normalized CHECK (email IS NULL OR email = lower(email)),
	CONSTRAINT uq_user_account_external_subject UNIQUE (external_subject)
);

-- 04. audit_event
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

-- 05. student_profile
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

-- 06. lecturer_profile
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

-- 07. organizational_position
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

-- 08. position_assignment
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
	CONSTRAINT fk_position_assignment_lecturer_id_lecturer_profile FOREIGN KEY(lecturer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
	CONSTRAINT fk_position_assignment_position_id_organizational_position FOREIGN KEY(position_id) REFERENCES organizational_position (id) ON DELETE RESTRICT,
	CONSTRAINT fk_position_assignment_faculty_id_faculty FOREIGN KEY(faculty_id) REFERENCES faculty (id) ON DELETE RESTRICT,
	CONSTRAINT fk_position_assignment_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT
);

-- 09. academic_year
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

-- 10. thesis_round
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

-- 11. round_policy
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

-- 12. eligibility_snapshot
CREATE TABLE eligibility_snapshot (
	student_id UUID NOT NULL,
	round_id UUID NOT NULL,
	version INTEGER NOT NULL,
	passed_credit_ratio NUMERIC(5, 4),
	gpa_4 NUMERIC(3, 2),
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

-- 13. topic
CREATE TABLE topic (
	round_id UUID NOT NULL,
	code VARCHAR(40) NOT NULL,
	receiving_lecturer_id UUID,
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
	CONSTRAINT uq_topic_code UNIQUE (code),
	CONSTRAINT fk_topic_receiving_lecturer_id_lecturer_profile FOREIGN KEY(receiving_lecturer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
	CONSTRAINT fk_topic_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT,
	CONSTRAINT fk_topic_proposer_user_id_user_account FOREIGN KEY(proposer_user_id) REFERENCES user_account (id) ON DELETE RESTRICT,
	CONSTRAINT fk_topic_decided_by_user_account FOREIGN KEY(decided_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

-- 14. topic_title_version
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

-- 15. topic_requirement
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

-- 16. stored_file
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

-- 17. topic_registration
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
	CONSTRAINT ck_topic_registration_state CHECK (state IN ('DRAFT','SUBMITTED','LECTURER_ACCEPTED','LECTURER_REJECTED','RETURNED','FINALIZED','CANCELLED')),
	CONSTRAINT fk_topic_registration_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
	CONSTRAINT fk_topic_registration_topic_id_topic FOREIGN KEY(topic_id) REFERENCES topic (id) ON DELETE RESTRICT,
	CONSTRAINT fk_topic_registration_created_by_student_profile FOREIGN KEY(created_by) REFERENCES student_profile (id) ON DELETE RESTRICT,
	CONSTRAINT fk_topic_registration_lecturer_decided_by_lecturer_profile FOREIGN KEY(lecturer_decided_by) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
	CONSTRAINT fk_topic_registration_department_finalized_by_user_account FOREIGN KEY(department_finalized_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

-- 18. registration_member
CREATE TABLE registration_member (
	registration_id UUID NOT NULL,
	round_id UUID NOT NULL,
	student_id UUID NOT NULL,
	evidence_file_id UUID,
	is_coordinator BOOLEAN DEFAULT false NOT NULL,
	active BOOLEAN DEFAULT true NOT NULL,
	consent_status VARCHAR(20) DEFAULT 'PENDING' NOT NULL,
	responded_by_user_id UUID,
	responded_at TIMESTAMP WITH TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_registration_member PRIMARY KEY (id),
	CONSTRAINT fk_registration_member_registration_id_round_id_topic_r_f9bb FOREIGN KEY(registration_id, round_id) REFERENCES topic_registration (id, round_id) ON DELETE RESTRICT,
	CONSTRAINT uq_registration_member_registration_id_student_id UNIQUE (registration_id, student_id),
	CONSTRAINT ck_registration_member_consent_consistency CHECK ((consent_status = 'PENDING' AND responded_by_user_id IS NULL AND responded_at IS NULL) OR (consent_status IN ('ACCEPTED','DECLINED') AND responded_by_user_id IS NOT NULL AND responded_at IS NOT NULL)),
	CONSTRAINT fk_registration_member_student_id_student_profile FOREIGN KEY(student_id) REFERENCES student_profile (id) ON DELETE RESTRICT,
	CONSTRAINT fk_registration_member_evidence_file_id_stored_file FOREIGN KEY(evidence_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
	CONSTRAINT fk_registration_member_responded_by_user_id_user_account FOREIGN KEY(responded_by_user_id) REFERENCES user_account (id) ON DELETE RESTRICT
);

-- 19. thesis
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
	CONSTRAINT ck_thesis_state CHECK (state IN ('ACTIVE','PROPOSAL_APPROVED','IN_PROGRESS','EXTENDED','WITHDRAWN','READY_FOR_DEFENSE','DEFENDED','COMPLETED','ARCHIVED')),
	CONSTRAINT fk_thesis_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
	CONSTRAINT fk_thesis_topic_id_topic FOREIGN KEY(topic_id) REFERENCES topic (id) ON DELETE RESTRICT,
	CONSTRAINT uq_thesis_registration_id UNIQUE (registration_id),
	CONSTRAINT fk_thesis_registration_id_topic_registration FOREIGN KEY(registration_id) REFERENCES topic_registration (id) ON DELETE RESTRICT,
	CONSTRAINT fk_thesis_department_id_department FOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT
);

-- 20. thesis_member
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

-- 21. advisor_assignment
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

-- 22. council
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

-- 23. resource_assignment
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
	CONSTRAINT fk_resource_assignment_user_id_user_account FOREIGN KEY(user_id) REFERENCES user_account (id) ON DELETE RESTRICT,
	CONSTRAINT fk_resource_assignment_round_id_thesis_round FOREIGN KEY(round_id) REFERENCES thesis_round (id) ON DELETE RESTRICT,
	CONSTRAINT fk_resource_assignment_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
	CONSTRAINT fk_resource_assignment_council_id_council FOREIGN KEY(council_id) REFERENCES council (id) ON DELETE RESTRICT
);

-- 24. proposal
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

-- 25. proposal_version
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

-- 26. reviewer_assignment
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
	CONSTRAINT ck_reviewer_assignment_scope_matches_subject CHECK ((review_scope = 'PROPOSAL' AND proposal_id IS NOT NULL) OR (review_scope = 'THESIS' AND thesis_id IS NOT NULL)),
	CONSTRAINT fk_reviewer_assignment_lecturer_id_lecturer_profile FOREIGN KEY(lecturer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT,
	CONSTRAINT fk_reviewer_assignment_proposal_id_proposal FOREIGN KEY(proposal_id) REFERENCES proposal (id) ON DELETE RESTRICT,
	CONSTRAINT fk_reviewer_assignment_thesis_id_thesis FOREIGN KEY(thesis_id) REFERENCES thesis (id) ON DELETE RESTRICT,
	CONSTRAINT fk_reviewer_assignment_assigned_by_user_account FOREIGN KEY(assigned_by) REFERENCES user_account (id) ON DELETE RESTRICT
);

-- 27. proposal_review
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

-- 28. progress_milestone
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

-- 29. progress_report
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

-- 30. progress_review
CREATE TABLE progress_review (
	progress_report_id UUID NOT NULL,
	reviewer_id UUID NOT NULL,
	decision VARCHAR(30) NOT NULL,
	comment TEXT NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_progress_review PRIMARY KEY (id),
	CONSTRAINT ck_progress_review_decision CHECK (decision IN ('COMMENT_ONLY','CONFIRM','REVISION_REQUIRED')),
	CONSTRAINT uq_progress_review_progress_report_id_reviewer_id UNIQUE (progress_report_id, reviewer_id),
	CONSTRAINT fk_progress_review_progress_report_id_progress_report FOREIGN KEY(progress_report_id) REFERENCES progress_report (id) ON DELETE RESTRICT,
	CONSTRAINT fk_progress_review_reviewer_id_lecturer_profile FOREIGN KEY(reviewer_id) REFERENCES lecturer_profile (id) ON DELETE RESTRICT
);

-- 31. document
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

-- 32. document_version
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
	CONSTRAINT ck_document_version_state CHECK (state IN ('DRAFT','SUBMITTED','RESULT_AVAILABLE','REVISION_REQUESTED','ACCEPTED','FINAL','SUPERSEDED')),
	CONSTRAINT fk_document_version_document_id_document FOREIGN KEY(document_id) REFERENCES document (id) ON DELETE RESTRICT,
	CONSTRAINT fk_document_version_stored_file_id_stored_file FOREIGN KEY(stored_file_id) REFERENCES stored_file (id) ON DELETE RESTRICT,
	CONSTRAINT fk_document_version_submitted_by_student_profile FOREIGN KEY(submitted_by) REFERENCES student_profile (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_user_account_email_lower ON user_account (lower(email)) WHERE email IS NOT NULL;
CREATE INDEX ix_audit_event_correlation_id ON audit_event (correlation_id);
CREATE INDEX ix_audit_event_resource_id ON audit_event (resource_id);
CREATE UNIQUE INDEX uq_position_assignment_department_scope ON position_assignment (lecturer_id, position_id, department_id) WHERE department_id IS NOT NULL AND state = 'ACTIVE';
CREATE UNIQUE INDEX uq_position_assignment_faculty_scope ON position_assignment (lecturer_id, position_id, faculty_id) WHERE faculty_id IS NOT NULL AND state = 'ACTIVE';
CREATE INDEX ix_stored_file_sha256 ON stored_file (sha256);
CREATE UNIQUE INDEX uq_registration_member_one_coordinator ON registration_member (registration_id) WHERE active AND is_coordinator;
CREATE UNIQUE INDEX uq_registration_member_student_round_active ON registration_member (student_id, round_id) WHERE active;
CREATE UNIQUE INDEX uq_thesis_member_one_coordinator ON thesis_member (thesis_id) WHERE active AND is_coordinator;
CREATE UNIQUE INDEX uq_advisor_assignment_active_primary ON advisor_assignment (thesis_id) WHERE state = 'ACTIVE' AND assignment_type = 'PRIMARY';
CREATE UNIQUE INDEX uq_resource_assignment_council_scope ON resource_assignment (assignment_type, user_id, council_id) WHERE council_id IS NOT NULL AND state = 'ACTIVE';
CREATE UNIQUE INDEX uq_resource_assignment_round_scope ON resource_assignment (assignment_type, user_id, round_id) WHERE round_id IS NOT NULL AND state = 'ACTIVE';
CREATE UNIQUE INDEX uq_resource_assignment_thesis_scope ON resource_assignment (assignment_type, user_id, thesis_id) WHERE thesis_id IS NOT NULL AND state = 'ACTIVE';
CREATE UNIQUE INDEX uq_reviewer_assignment_proposal ON reviewer_assignment (lecturer_id, proposal_id) WHERE proposal_id IS NOT NULL AND state = 'ACTIVE';
CREATE UNIQUE INDEX uq_reviewer_assignment_thesis ON reviewer_assignment (lecturer_id, thesis_id) WHERE thesis_id IS NOT NULL AND state = 'ACTIVE';

COMMIT;
