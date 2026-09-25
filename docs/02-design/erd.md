# ERD logical + physical PostgreSQL

> ERD văn bản canonical đồng bộ từ SQLAlchemy metadata/migration 20260920_0001 → 20260924_0002. Draw.io 5 trang là ảnh thiết kế ban đầu; quan hệ mới của chữ ký với phiên bản đề cương được thể hiện tại đây và trong từ điển dữ liệu. Mỗi diagram chỉ vẽ FK nội page để đọc được; bảng quan hệ FK phía dưới gồm cả quan hệ liên trang.

## Ký hiệu

- PK: khóa chính; FK: khóa ngoại; UK: thuộc ít nhất một unique constraint/index.
- Parent ||--o{ Child: một parent có 0..N child. Parent ||--o| Child: FK child thuộc unique nên tối đa một child.
- Nullability, default, check và PII chi tiết nằm tại data-dictionary.md; invariant liên hàng tại database-rules.md.

## Danh tính, tổ chức và đợt

~~~mermaid
erDiagram
  FACULTY {
    varchar code UK
    uuid id PK
  }
  DEPARTMENT {
    uuid faculty_id FK,UK
    varchar code UK
    uuid id PK
  }
  USER_ACCOUNT {
    varchar status
    uuid id PK
    int row_version
    varchar external_subject UK
  }
  STUDENT_PROFILE {
    uuid user_id FK,UK
    uuid department_id FK
    uuid id PK
    varchar student_code UK
  }
  LECTURER_PROFILE {
    uuid user_id FK,UK
    uuid department_id FK
    uuid id PK
    varchar lecturer_code UK
  }
  ORGANIZATIONAL_POSITION {
    varchar code UK
    uuid id PK
  }
  POSITION_ASSIGNMENT {
    uuid lecturer_id FK,UK
    uuid position_id FK,UK
    uuid faculty_id FK,UK
    uuid department_id FK,UK
    varchar state
    uuid id PK
    int row_version
    timestamptz effective_from UK
  }
  ACADEMIC_YEAR {
    varchar code UK
    varchar state
    uuid id PK
    int row_version
  }
  THESIS_ROUND {
    uuid academic_year_id FK,UK
    varchar code UK
    varchar round_type
    varchar state
    uuid id PK
    int row_version
  }
  ROUND_POLICY {
    uuid round_id FK,UK
    int version UK
    varchar state
    uuid id PK
    varchar policy_type UK
  }
  RESOURCE_ASSIGNMENT {
    uuid user_id FK,UK
    uuid round_id FK,UK
    uuid thesis_id FK,UK
    uuid council_id FK,UK
    varchar state
    uuid id PK
    int row_version
    timestamptz effective_from UK
    varchar assignment_type UK
  }
  ELIGIBILITY_SNAPSHOT {
    uuid student_id FK,UK
    uuid round_id FK,UK
    int version UK
    uuid confirmed_by FK
    varchar state
    uuid id PK
  }
  ELIGIBILITY_EXCEPTION {
    uuid snapshot_id FK,UK
    uuid granted_by FK
    uuid id PK
  }
  LECTURER_EXPERTISE {
    uuid lecturer_id FK,UK
    int version UK
    varchar state
    uuid verified_by FK
    uuid id PK
    int row_version
  }
  EXPERTISE_EVIDENCE {
    uuid expertise_id FK
    uuid id PK
  }
  FACULTY ||--o{ DEPARTMENT : "faculty_id"
  DEPARTMENT ||--o{ STUDENT_PROFILE : "department_id"
  USER_ACCOUNT ||--o| STUDENT_PROFILE : "user_id"
  DEPARTMENT ||--o{ LECTURER_PROFILE : "department_id"
  USER_ACCOUNT ||--o| LECTURER_PROFILE : "user_id"
  LECTURER_PROFILE ||--o{ POSITION_ASSIGNMENT : "lecturer_id"
  ORGANIZATIONAL_POSITION ||--o{ POSITION_ASSIGNMENT : "position_id"
  DEPARTMENT ||--o{ POSITION_ASSIGNMENT : "department_id"
  FACULTY ||--o{ POSITION_ASSIGNMENT : "faculty_id"
  ACADEMIC_YEAR ||--o{ THESIS_ROUND : "academic_year_id"
  THESIS_ROUND ||--o{ ROUND_POLICY : "round_id"
  THESIS_ROUND ||--o{ RESOURCE_ASSIGNMENT : "round_id"
  USER_ACCOUNT ||--o{ RESOURCE_ASSIGNMENT : "user_id"
  STUDENT_PROFILE ||--o{ ELIGIBILITY_SNAPSHOT : "student_id"
  USER_ACCOUNT ||--o{ ELIGIBILITY_SNAPSHOT : "confirmed_by"
  THESIS_ROUND ||--o{ ELIGIBILITY_SNAPSHOT : "round_id"
  ELIGIBILITY_SNAPSHOT ||--o| ELIGIBILITY_EXCEPTION : "snapshot_id"
  USER_ACCOUNT ||--o{ ELIGIBILITY_EXCEPTION : "granted_by"
  USER_ACCOUNT ||--o{ LECTURER_EXPERTISE : "verified_by"
  LECTURER_PROFILE ||--o{ LECTURER_EXPERTISE : "lecturer_id"
  LECTURER_EXPERTISE ||--o{ EXPERTISE_EVIDENCE : "expertise_id"
~~~

## Đề tài, đăng ký và Thesis

~~~mermaid
erDiagram
  TOPIC {
    uuid round_id FK
    uuid department_id FK
    uuid proposer_user_id FK
    varchar state
    uuid decided_by FK
    uuid id PK
    int row_version
  }
  TOPIC_TITLE_VERSION {
    uuid topic_id FK,UK
    int version_no UK
    uuid changed_by FK
    uuid id PK
  }
  TOPIC_REQUIREMENT {
    uuid topic_id FK
    uuid id PK
  }
  TOPIC_REGISTRATION {
    uuid round_id FK,UK
    uuid topic_id FK
    uuid created_by FK
    varchar state
    uuid lecturer_decided_by FK
    uuid department_finalized_by FK
    uuid id PK,UK
    int row_version
  }
  REGISTRATION_MEMBER {
    uuid registration_id FK,UK
    uuid round_id FK,UK
    uuid student_id FK,UK
    uuid id PK
  }
  THESIS {
    uuid round_id FK,UK
    uuid topic_id FK,UK
    uuid registration_id FK,UK
    uuid department_id FK
    varchar state
    uuid id PK
    int row_version
  }
  THESIS_MEMBER {
    uuid thesis_id FK,UK
    uuid student_id FK,UK
    uuid id PK
  }
  MEMBER_WORK_ASSIGNMENT {
    uuid thesis_member_id FK,UK
    int version_no UK
    varchar state
    uuid reviewed_by FK
    uuid id PK
    int row_version
  }
  ADVISOR_ASSIGNMENT {
    uuid thesis_id FK,UK
    uuid lecturer_id FK
    uuid assigned_by FK
    varchar state
    uuid id PK
    int row_version
  }
  REVIEWER_ASSIGNMENT {
    uuid lecturer_id FK,UK
    uuid proposal_id FK,UK
    uuid thesis_id FK,UK
    uuid assigned_by FK
    varchar state
    uuid id PK
    int row_version
    varchar review_scope UK
  }
  TOPIC ||--o{ TOPIC_TITLE_VERSION : "topic_id"
  TOPIC ||--o{ TOPIC_REQUIREMENT : "topic_id"
  TOPIC ||--o{ TOPIC_REGISTRATION : "topic_id"
  TOPIC_REGISTRATION ||--o{ REGISTRATION_MEMBER : "registration_id"
  TOPIC_REGISTRATION ||--o{ REGISTRATION_MEMBER : "round_id"
  TOPIC_REGISTRATION ||--o| THESIS : "registration_id"
  TOPIC ||--o{ THESIS : "topic_id"
  THESIS ||--o{ THESIS_MEMBER : "thesis_id"
  THESIS_MEMBER ||--o{ MEMBER_WORK_ASSIGNMENT : "thesis_member_id"
  THESIS ||--o{ ADVISOR_ASSIGNMENT : "thesis_id"
  THESIS ||--o{ REVIEWER_ASSIGNMENT : "thesis_id"
~~~

## Đề cương, tiến độ và tài liệu

~~~mermaid
erDiagram
  STORED_FILE {
    uuid id PK
    varchar storage_key UK
  }
  PROPOSAL {
    uuid thesis_id FK,UK
    varchar state
    uuid id PK
    int row_version
  }
  PROPOSAL_VERSION {
    uuid proposal_id FK,UK
    int version_no UK
    uuid stored_file_id FK
    uuid submitted_by FK
    uuid id PK
  }
  PROPOSAL_REVIEW {
    uuid proposal_version_id FK
    uuid reviewer_assignment_id FK
    uuid reviewer_user_id FK
    uuid id PK
  }
  SIGNATURE_CONFIRMATION {
    uuid proposal_id FK,UK
    int proposal_version_no FK
    uuid signer_user_id FK
    uuid id PK
    varchar signature_type UK
  }
  PROGRESS_MILESTONE {
    uuid round_id FK,UK
    varchar code UK
    int version_no UK
    varchar state
    uuid id PK
    int row_version
  }
  PROGRESS_REPORT {
    uuid thesis_id FK,UK
    uuid milestone_id FK,UK
    int version_no UK
    uuid evidence_file_id FK
    uuid submitted_by FK
    varchar state
    uuid id PK
    int row_version
  }
  PROGRESS_REVIEW {
    uuid progress_report_id FK,UK
    uuid reviewer_id FK,UK
    uuid id PK
  }
  TOPIC_CHANGE_REQUEST {
    uuid thesis_id FK
    uuid requested_by FK
    uuid proposed_topic_id FK
    uuid advisor_reviewed_by FK
    uuid department_decided_by FK
    varchar state
    uuid id PK
    int row_version
  }
  EXTERNAL_PROCEDURE_OUTCOME {
    uuid thesis_id FK,UK
    uuid evidence_file_id FK
    uuid recorded_by FK
    uuid id PK
    varchar official_ref UK
    varchar outcome_type UK
  }
  DOCUMENT {
    uuid thesis_id FK
    varchar state
    uuid id PK
    int row_version
  }
  DOCUMENT_VERSION {
    uuid document_id FK,UK
    int version_no UK
    uuid stored_file_id FK
    uuid submitted_by FK
    varchar state
    uuid id PK
    int row_version
  }
  SIMILARITY_POLICY {
    uuid round_id FK,UK
    int version_no UK
    varchar state
    uuid id PK
  }
  SIMILARITY_CHECK {
    uuid document_version_id FK
    uuid policy_id FK
    varchar state
    uuid id PK
  }
  SIMILARITY_MATCH {
    uuid check_id FK
    uuid source_document_version_id FK
    uuid id PK
  }
  PROPOSAL ||--o{ PROPOSAL_VERSION : "proposal_id"
  STORED_FILE ||--o{ PROPOSAL_VERSION : "stored_file_id"
  PROPOSAL_VERSION ||--o{ PROPOSAL_REVIEW : "proposal_version_id"
  PROPOSAL ||--o{ SIGNATURE_CONFIRMATION : "proposal_id"
  PROPOSAL_VERSION ||--o{ SIGNATURE_CONFIRMATION : "proposal_id + proposal_version_no"
  PROGRESS_MILESTONE ||--o{ PROGRESS_REPORT : "milestone_id"
  STORED_FILE ||--o{ PROGRESS_REPORT : "evidence_file_id"
  PROGRESS_REPORT ||--o{ PROGRESS_REVIEW : "progress_report_id"
  STORED_FILE ||--o{ EXTERNAL_PROCEDURE_OUTCOME : "evidence_file_id"
  STORED_FILE ||--o{ DOCUMENT_VERSION : "stored_file_id"
  DOCUMENT ||--o{ DOCUMENT_VERSION : "document_id"
  DOCUMENT_VERSION ||--o{ SIMILARITY_CHECK : "document_version_id"
  SIMILARITY_POLICY ||--o{ SIMILARITY_CHECK : "policy_id"
  DOCUMENT_VERSION ||--o{ SIMILARITY_MATCH : "source_document_version_id"
  SIMILARITY_CHECK ||--o{ SIMILARITY_MATCH : "check_id"
~~~

## Hội đồng và điểm

~~~mermaid
erDiagram
  COUNCIL {
    uuid round_id FK,UK
    uuid department_id FK
    varchar code UK
    varchar state
    uuid id PK
    int row_version
  }
  COUNCIL_MEMBER {
    uuid council_id FK,UK
    uuid lecturer_id FK,UK
    uuid id PK
    int role_slot UK
    varchar role_code UK
  }
  DEFENSE_SESSION {
    uuid council_id FK,UK
    varchar code UK
    varchar state
    uuid id PK
    int row_version
  }
  SESSION_THESIS {
    uuid session_id FK,UK
    uuid thesis_id FK,UK
    uuid id PK
    int order_no UK
  }
  COUNCIL_ATTENDANCE {
    uuid session_id FK,UK
    uuid council_member_id FK,UK
    uuid recorded_by FK
    uuid id PK
    int row_version
  }
  DEFENSE_ELIGIBILITY_CHECK {
    uuid thesis_member_id FK
    uuid round_id FK
    uuid advisor_review_id FK
    uuid checked_by FK
    uuid id PK
  }
  ADVISOR_REVIEW {
    uuid advisor_assignment_id FK,UK
    uuid thesis_member_id FK,UK
    uuid document_version_id FK
    int version_no UK
    uuid id PK
    int row_version
  }
  REVIEWER_REVIEW {
    uuid reviewer_assignment_id FK,UK
    uuid thesis_member_id FK,UK
    uuid document_version_id FK
    int version_no UK
    uuid id PK
    int row_version
  }
  RUBRIC_TEMPLATE {
    varchar code UK
    int version_no UK
    varchar state
    uuid id PK
  }
  RUBRIC_CRITERION {
    uuid rubric_template_id FK,UK
    uuid parent_id FK
    varchar code UK
    uuid id PK
    int order_no UK
  }
  RUBRIC_ASSIGNMENT {
    uuid rubric_template_id FK
    uuid round_id FK
    uuid session_id FK
    varchar state
    uuid id PK
  }
  BONUS_EVIDENCE {
    uuid thesis_member_id FK
    uuid stored_file_id FK
    uuid id PK
  }
  EVALUATION {
    uuid session_id FK,UK
    uuid evaluator_member_id FK,UK
    uuid thesis_member_id FK,UK
    uuid rubric_assignment_id FK
    numeric total_points
    varchar status
    uuid id PK
    int row_version
  }
  EVALUATION_ITEM {
    uuid evaluation_id FK,UK
    uuid criterion_id FK,UK
    uuid bonus_evidence_id FK
    uuid id PK
  }
  FINAL_RESULT {
    uuid session_id FK,UK
    uuid thesis_member_id FK,UK
    numeric final_score
    uuid id PK
  }
  COUNCIL ||--o{ COUNCIL_MEMBER : "council_id"
  COUNCIL ||--o{ DEFENSE_SESSION : "council_id"
  DEFENSE_SESSION ||--o{ SESSION_THESIS : "session_id"
  COUNCIL_MEMBER ||--o{ COUNCIL_ATTENDANCE : "council_member_id"
  DEFENSE_SESSION ||--o{ COUNCIL_ATTENDANCE : "session_id"
  ADVISOR_REVIEW ||--o{ DEFENSE_ELIGIBILITY_CHECK : "advisor_review_id"
  RUBRIC_TEMPLATE ||--o{ RUBRIC_CRITERION : "rubric_template_id"
  RUBRIC_CRITERION ||--o{ RUBRIC_CRITERION : "parent_id"
  DEFENSE_SESSION ||--o{ RUBRIC_ASSIGNMENT : "session_id"
  RUBRIC_TEMPLATE ||--o{ RUBRIC_ASSIGNMENT : "rubric_template_id"
  RUBRIC_ASSIGNMENT ||--o{ EVALUATION : "rubric_assignment_id"
  COUNCIL_MEMBER ||--o{ EVALUATION : "evaluator_member_id"
  DEFENSE_SESSION ||--o{ EVALUATION : "session_id"
  BONUS_EVIDENCE ||--o{ EVALUATION_ITEM : "bonus_evidence_id"
  RUBRIC_CRITERION ||--o{ EVALUATION_ITEM : "criterion_id"
  EVALUATION ||--o{ EVALUATION_ITEM : "evaluation_id"
  DEFENSE_SESSION ||--o{ FINAL_RESULT : "session_id"
~~~

## Biên bản, kho và audit

~~~mermaid
erDiagram
  COUNCIL_MINUTE {
    uuid session_id FK,UK
    varchar state
    uuid id PK
    int row_version
    varchar minute_no UK
  }
  MINUTE_VERSION {
    uuid minute_id FK,UK
    int version_no UK
    uuid stored_file_id FK
    uuid generated_by FK
    varchar state
    uuid replacement_for_id FK
    uuid id PK
  }
  MINUTE_SIGNATURE {
    uuid minute_version_id FK,UK
    uuid signer_member_id FK,UK
    uuid id PK
  }
  REPOSITORY_ITEM {
    uuid thesis_id FK
    uuid published_document_version_id FK,UK
    uuid id PK
    int row_version
  }
  SEARCH_INDEX_METADATA {
    uuid repository_item_id FK,UK
    uuid document_version_id FK
    varchar state
    uuid id PK
    varchar index_name UK
    varchar index_version UK
  }
  RETRIEVAL_AUDIT {
    uuid user_id FK
    uuid id PK
  }
  AUDIT_EVENT {
    uuid actor_id FK
    uuid id PK
  }
  COUNCIL_MINUTE ||--o{ MINUTE_VERSION : "minute_id"
  MINUTE_VERSION ||--o{ MINUTE_VERSION : "replacement_for_id"
  MINUTE_VERSION ||--o{ MINUTE_SIGNATURE : "minute_version_id"
  REPOSITORY_ITEM ||--o{ SEARCH_INDEX_METADATA : "repository_item_id"
~~~

## Danh sách FK đầy đủ

| Child.field | Parent.field | Nullable | Cardinality child/parent | Constraint |
| --- | --- | --- | --- | --- |
| audit_event.actor_id | user_account.id | NULL | 0..N / 0..1 | fk_audit_event_actor_id_user_account |
| department.faculty_id | faculty.id | NOT NULL | 0..N / 1 | fk_department_faculty_id_faculty |
| retrieval_audit.user_id | user_account.id | NOT NULL | 0..N / 1 | fk_retrieval_audit_user_id_user_account |
| rubric_criterion.rubric_template_id | rubric_template.id | NOT NULL | 0..N / 1 | fk_rubric_criterion_rubric_template_id_rubric_template |
| rubric_criterion.parent_id | rubric_criterion.id | NULL | 0..N / 0..1 | fk_rubric_criterion_parent_id_rubric_criterion |
| thesis_round.academic_year_id | academic_year.id | NOT NULL | 0..N / 1 | fk_thesis_round_academic_year_id_academic_year |
| council.department_id | department.id | NOT NULL | 0..N / 1 | fk_council_department_id_department |
| council.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_council_round_id_thesis_round |
| lecturer_profile.department_id | department.id | NOT NULL | 0..N / 1 | fk_lecturer_profile_department_id_department |
| lecturer_profile.user_id | user_account.id | NOT NULL | 0..1 / 1 | fk_lecturer_profile_user_id_user_account |
| progress_milestone.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_progress_milestone_round_id_thesis_round |
| round_policy.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_round_policy_round_id_thesis_round |
| similarity_policy.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_similarity_policy_round_id_thesis_round |
| student_profile.department_id | department.id | NOT NULL | 0..N / 1 | fk_student_profile_department_id_department |
| student_profile.user_id | user_account.id | NOT NULL | 0..1 / 1 | fk_student_profile_user_id_user_account |
| topic.decided_by | user_account.id | NULL | 0..N / 0..1 | fk_topic_decided_by_user_account |
| topic.department_id | department.id | NOT NULL | 0..N / 1 | fk_topic_department_id_department |
| topic.proposer_user_id | user_account.id | NOT NULL | 0..N / 1 | fk_topic_proposer_user_id_user_account |
| topic.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_topic_round_id_thesis_round |
| council_member.council_id | council.id | NOT NULL | 0..N / 1 | fk_council_member_council_id_council |
| council_member.lecturer_id | lecturer_profile.id | NOT NULL | 0..N / 1 | fk_council_member_lecturer_id_lecturer_profile |
| defense_session.council_id | council.id | NOT NULL | 0..N / 1 | fk_defense_session_council_id_council |
| eligibility_snapshot.confirmed_by | user_account.id | NULL | 0..N / 0..1 | fk_eligibility_snapshot_confirmed_by_user_account |
| eligibility_snapshot.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_eligibility_snapshot_round_id_thesis_round |
| eligibility_snapshot.student_id | student_profile.id | NOT NULL | 0..N / 1 | fk_eligibility_snapshot_student_id_student_profile |
| lecturer_expertise.lecturer_id | lecturer_profile.id | NOT NULL | 0..N / 1 | fk_lecturer_expertise_lecturer_id_lecturer_profile |
| lecturer_expertise.verified_by | user_account.id | NULL | 0..N / 0..1 | fk_lecturer_expertise_verified_by_user_account |
| position_assignment.department_id | department.id | NULL | 0..N / 0..1 | fk_position_assignment_department_id_department |
| position_assignment.faculty_id | faculty.id | NULL | 0..N / 0..1 | fk_position_assignment_faculty_id_faculty |
| position_assignment.lecturer_id | lecturer_profile.id | NOT NULL | 0..N / 1 | fk_position_assignment_lecturer_id_lecturer_profile |
| position_assignment.position_id | organizational_position.id | NOT NULL | 0..N / 1 | fk_position_assignment_position_id_organizational_position |
| topic_registration.created_by | student_profile.id | NOT NULL | 0..N / 1 | fk_topic_registration_created_by_student_profile |
| topic_registration.department_finalized_by | user_account.id | NULL | 0..N / 0..1 | fk_topic_registration_department_finalized_by_user_account |
| topic_registration.lecturer_decided_by | lecturer_profile.id | NULL | 0..N / 0..1 | fk_topic_registration_lecturer_decided_by_lecturer_profile |
| topic_registration.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_topic_registration_round_id_thesis_round |
| topic_registration.topic_id | topic.id | NOT NULL | 0..N / 1 | fk_topic_registration_topic_id_topic |
| topic_requirement.topic_id | topic.id | NOT NULL | 0..N / 1 | fk_topic_requirement_topic_id_topic |
| topic_title_version.changed_by | user_account.id | NOT NULL | 0..N / 1 | fk_topic_title_version_changed_by_user_account |
| topic_title_version.topic_id | topic.id | NOT NULL | 0..N / 1 | fk_topic_title_version_topic_id_topic |
| council_attendance.council_member_id | council_member.id | NOT NULL | 0..N / 1 | fk_council_attendance_council_member_id_council_member |
| council_attendance.recorded_by | user_account.id | NOT NULL | 0..N / 1 | fk_council_attendance_recorded_by_user_account |
| council_attendance.session_id | defense_session.id | NOT NULL | 0..N / 1 | fk_council_attendance_session_id_defense_session |
| council_minute.session_id | defense_session.id | NOT NULL | 0..N / 1 | fk_council_minute_session_id_defense_session |
| eligibility_exception.granted_by | user_account.id | NOT NULL | 0..N / 1 | fk_eligibility_exception_granted_by_user_account |
| eligibility_exception.snapshot_id | eligibility_snapshot.id | NOT NULL | 0..1 / 1 | fk_eligibility_exception_snapshot_id_eligibility_snapshot |
| expertise_evidence.expertise_id | lecturer_expertise.id | NOT NULL | 0..N / 1 | fk_expertise_evidence_expertise_id_lecturer_expertise |
| registration_member.registration_id | topic_registration.id | NOT NULL | 0..N / 1 | fk_registration_member_registration_id_round_id_topic_registration |
| registration_member.round_id | topic_registration.round_id | NOT NULL | 0..N / 1 | fk_registration_member_registration_id_round_id_topic_registration |
| registration_member.student_id | student_profile.id | NOT NULL | 0..N / 1 | fk_registration_member_student_id_student_profile |
| rubric_assignment.round_id | thesis_round.id | NULL | 0..N / 0..1 | fk_rubric_assignment_round_id_thesis_round |
| rubric_assignment.rubric_template_id | rubric_template.id | NOT NULL | 0..N / 1 | fk_rubric_assignment_rubric_template_id_rubric_template |
| rubric_assignment.session_id | defense_session.id | NULL | 0..N / 0..1 | fk_rubric_assignment_session_id_defense_session |
| thesis.department_id | department.id | NOT NULL | 0..N / 1 | fk_thesis_department_id_department |
| thesis.registration_id | topic_registration.id | NOT NULL | 0..1 / 1 | fk_thesis_registration_id_topic_registration |
| thesis.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_thesis_round_id_thesis_round |
| thesis.topic_id | topic.id | NOT NULL | 0..N / 1 | fk_thesis_topic_id_topic |
| advisor_assignment.assigned_by | user_account.id | NOT NULL | 0..N / 1 | fk_advisor_assignment_assigned_by_user_account |
| advisor_assignment.lecturer_id | lecturer_profile.id | NOT NULL | 0..N / 1 | fk_advisor_assignment_lecturer_id_lecturer_profile |
| advisor_assignment.thesis_id | thesis.id | NOT NULL | 0..N / 1 | fk_advisor_assignment_thesis_id_thesis |
| document.thesis_id | thesis.id | NOT NULL | 0..N / 1 | fk_document_thesis_id_thesis |
| external_procedure_outcome.evidence_file_id | stored_file.id | NULL | 0..N / 0..1 | fk_external_procedure_outcome_evidence_file_id_stored_file |
| external_procedure_outcome.recorded_by | user_account.id | NOT NULL | 0..N / 1 | fk_external_procedure_outcome_recorded_by_user_account |
| external_procedure_outcome.thesis_id | thesis.id | NOT NULL | 0..N / 1 | fk_external_procedure_outcome_thesis_id_thesis |
| minute_version.generated_by | user_account.id | NOT NULL | 0..N / 1 | fk_minute_version_generated_by_user_account |
| minute_version.minute_id | council_minute.id | NOT NULL | 0..N / 1 | fk_minute_version_minute_id_council_minute |
| minute_version.replacement_for_id | minute_version.id | NULL | 0..N / 0..1 | fk_minute_version_replacement_for_id_minute_version |
| minute_version.stored_file_id | stored_file.id | NOT NULL | 0..N / 1 | fk_minute_version_stored_file_id_stored_file |
| progress_report.evidence_file_id | stored_file.id | NULL | 0..N / 0..1 | fk_progress_report_evidence_file_id_stored_file |
| progress_report.milestone_id | progress_milestone.id | NOT NULL | 0..N / 1 | fk_progress_report_milestone_id_progress_milestone |
| progress_report.submitted_by | student_profile.id | NOT NULL | 0..N / 1 | fk_progress_report_submitted_by_student_profile |
| progress_report.thesis_id | thesis.id | NOT NULL | 0..N / 1 | fk_progress_report_thesis_id_thesis |
| proposal.thesis_id | thesis.id | NOT NULL | 0..1 / 1 | fk_proposal_thesis_id_thesis |
| resource_assignment.council_id | council.id | NULL | 0..N / 0..1 | fk_resource_assignment_council_id_council |
| resource_assignment.round_id | thesis_round.id | NULL | 0..N / 0..1 | fk_resource_assignment_round_id_thesis_round |
| resource_assignment.thesis_id | thesis.id | NULL | 0..N / 0..1 | fk_resource_assignment_thesis_id_thesis |
| resource_assignment.user_id | user_account.id | NOT NULL | 0..N / 1 | fk_resource_assignment_user_id_user_account |
| session_thesis.session_id | defense_session.id | NOT NULL | 0..N / 1 | fk_session_thesis_session_id_defense_session |
| session_thesis.thesis_id | thesis.id | NOT NULL | 0..N / 1 | fk_session_thesis_thesis_id_thesis |
| thesis_member.student_id | student_profile.id | NOT NULL | 0..N / 1 | fk_thesis_member_student_id_student_profile |
| thesis_member.thesis_id | thesis.id | NOT NULL | 0..N / 1 | fk_thesis_member_thesis_id_thesis |
| topic_change_request.advisor_reviewed_by | lecturer_profile.id | NULL | 0..N / 0..1 | fk_topic_change_request_advisor_reviewed_by_lecturer_profile |
| topic_change_request.department_decided_by | user_account.id | NULL | 0..N / 0..1 | fk_topic_change_request_department_decided_by_user_account |
| topic_change_request.proposed_topic_id | topic.id | NULL | 0..N / 0..1 | fk_topic_change_request_proposed_topic_id_topic |
| topic_change_request.requested_by | student_profile.id | NOT NULL | 0..N / 1 | fk_topic_change_request_requested_by_student_profile |
| topic_change_request.thesis_id | thesis.id | NOT NULL | 0..N / 1 | fk_topic_change_request_thesis_id_thesis |
| bonus_evidence.stored_file_id | stored_file.id | NULL | 0..N / 0..1 | fk_bonus_evidence_stored_file_id_stored_file |
| bonus_evidence.thesis_member_id | thesis_member.id | NOT NULL | 0..N / 1 | fk_bonus_evidence_thesis_member_id_thesis_member |
| document_version.document_id | document.id | NOT NULL | 0..N / 1 | fk_document_version_document_id_document |
| document_version.stored_file_id | stored_file.id | NOT NULL | 0..N / 1 | fk_document_version_stored_file_id_stored_file |
| document_version.submitted_by | student_profile.id | NOT NULL | 0..N / 1 | fk_document_version_submitted_by_student_profile |
| evaluation.evaluator_member_id | council_member.id | NOT NULL | 0..N / 1 | fk_evaluation_evaluator_member_id_council_member |
| evaluation.rubric_assignment_id | rubric_assignment.id | NOT NULL | 0..N / 1 | fk_evaluation_rubric_assignment_id_rubric_assignment |
| evaluation.session_id | defense_session.id | NOT NULL | 0..N / 1 | fk_evaluation_session_id_defense_session |
| evaluation.thesis_member_id | thesis_member.id | NOT NULL | 0..N / 1 | fk_evaluation_thesis_member_id_thesis_member |
| final_result.session_id | defense_session.id | NOT NULL | 0..N / 1 | fk_final_result_session_id_defense_session |
| final_result.thesis_member_id | thesis_member.id | NOT NULL | 0..N / 1 | fk_final_result_thesis_member_id_thesis_member |
| member_work_assignment.reviewed_by | lecturer_profile.id | NULL | 0..N / 0..1 | fk_member_work_assignment_reviewed_by_lecturer_profile |
| member_work_assignment.thesis_member_id | thesis_member.id | NOT NULL | 0..N / 1 | fk_member_work_assignment_thesis_member_id_thesis_member |
| minute_signature.minute_version_id | minute_version.id | NOT NULL | 0..N / 1 | fk_minute_signature_minute_version_id_minute_version |
| minute_signature.signer_member_id | council_member.id | NOT NULL | 0..N / 1 | fk_minute_signature_signer_member_id_council_member |
| progress_review.progress_report_id | progress_report.id | NOT NULL | 0..N / 1 | fk_progress_review_progress_report_id_progress_report |
| progress_review.reviewer_id | lecturer_profile.id | NOT NULL | 0..N / 1 | fk_progress_review_reviewer_id_lecturer_profile |
| proposal_version.proposal_id | proposal.id | NOT NULL | 0..N / 1 | fk_proposal_version_proposal_id_proposal |
| proposal_version.stored_file_id | stored_file.id | NOT NULL | 0..N / 1 | fk_proposal_version_stored_file_id_stored_file |
| proposal_version.submitted_by | student_profile.id | NOT NULL | 0..N / 1 | fk_proposal_version_submitted_by_student_profile |
| reviewer_assignment.assigned_by | user_account.id | NOT NULL | 0..N / 1 | fk_reviewer_assignment_assigned_by_user_account |
| reviewer_assignment.lecturer_id | lecturer_profile.id | NOT NULL | 0..N / 1 | fk_reviewer_assignment_lecturer_id_lecturer_profile |
| reviewer_assignment.proposal_id | proposal.id | NULL | 0..N / 0..1 | fk_reviewer_assignment_proposal_id_proposal |
| reviewer_assignment.thesis_id | thesis.id | NULL | 0..N / 0..1 | fk_reviewer_assignment_thesis_id_thesis |
| signature_confirmation.proposal_id | proposal.id | NOT NULL | 0..N / 1 | fk_signature_confirmation_proposal_id_proposal |
| signature_confirmation.(proposal_id, proposal_version_no) | proposal_version.(proposal_id, version_no) | NOT NULL | 0..N / 1 | fk_signature_confirmation_proposal_version_pair |
| signature_confirmation.signer_user_id | user_account.id | NOT NULL | 0..N / 1 | fk_signature_confirmation_signer_user_id_user_account |
| advisor_review.advisor_assignment_id | advisor_assignment.id | NOT NULL | 0..N / 1 | fk_advisor_review_advisor_assignment_id_advisor_assignment |
| advisor_review.document_version_id | document_version.id | NOT NULL | 0..N / 1 | fk_advisor_review_document_version_id_document_version |
| advisor_review.thesis_member_id | thesis_member.id | NOT NULL | 0..N / 1 | fk_advisor_review_thesis_member_id_thesis_member |
| evaluation_item.bonus_evidence_id | bonus_evidence.id | NULL | 0..N / 0..1 | fk_evaluation_item_bonus_evidence_id_bonus_evidence |
| evaluation_item.criterion_id | rubric_criterion.id | NOT NULL | 0..N / 1 | fk_evaluation_item_criterion_id_rubric_criterion |
| evaluation_item.evaluation_id | evaluation.id | NOT NULL | 0..N / 1 | fk_evaluation_item_evaluation_id_evaluation |
| proposal_review.proposal_version_id | proposal_version.id | NOT NULL | 0..N / 1 | fk_proposal_review_proposal_version_id_proposal_version |
| proposal_review.reviewer_assignment_id | reviewer_assignment.id | NOT NULL | 0..N / 1 | fk_proposal_review_reviewer_assignment_id_reviewer_assignment |
| proposal_review.reviewer_user_id | user_account.id | NOT NULL | 0..N / 1 | fk_proposal_review_reviewer_user_id_user_account |
| repository_item.published_document_version_id | document_version.id | NOT NULL | 0..1 / 1 | fk_repository_item_published_document_version_id_document_version |
| repository_item.thesis_id | thesis.id | NOT NULL | 0..N / 1 | fk_repository_item_thesis_id_thesis |
| reviewer_review.document_version_id | document_version.id | NOT NULL | 0..N / 1 | fk_reviewer_review_document_version_id_document_version |
| reviewer_review.reviewer_assignment_id | reviewer_assignment.id | NOT NULL | 0..N / 1 | fk_reviewer_review_reviewer_assignment_id_reviewer_assignment |
| reviewer_review.thesis_member_id | thesis_member.id | NOT NULL | 0..N / 1 | fk_reviewer_review_thesis_member_id_thesis_member |
| similarity_check.document_version_id | document_version.id | NOT NULL | 0..N / 1 | fk_similarity_check_document_version_id_document_version |
| similarity_check.policy_id | similarity_policy.id | NULL | 0..N / 0..1 | fk_similarity_check_policy_id_similarity_policy |
| defense_eligibility_check.advisor_review_id | advisor_review.id | NULL | 0..N / 0..1 | fk_defense_eligibility_check_advisor_review_id_advisor_review |
| defense_eligibility_check.checked_by | user_account.id | NOT NULL | 0..N / 1 | fk_defense_eligibility_check_checked_by_user_account |
| defense_eligibility_check.round_id | thesis_round.id | NOT NULL | 0..N / 1 | fk_defense_eligibility_check_round_id_thesis_round |
| defense_eligibility_check.thesis_member_id | thesis_member.id | NOT NULL | 0..N / 1 | fk_defense_eligibility_check_thesis_member_id_thesis_member |
| search_index_metadata.document_version_id | document_version.id | NOT NULL | 0..N / 1 | fk_search_index_metadata_document_version_id_document_version |
| search_index_metadata.repository_item_id | repository_item.id | NOT NULL | 0..N / 1 | fk_search_index_metadata_repository_item_id_repository_item |
| similarity_match.check_id | similarity_check.id | NOT NULL | 0..N / 1 | fk_similarity_match_check_id_similarity_check |
| similarity_match.source_document_version_id | document_version.id | NULL | 0..N / 0..1 | fk_similarity_match_source_document_version_id_document_version |

## Unique/partial unique quan trọng

| Table | Columns | Loại | Tên |
| --- | --- | --- | --- |
| faculty | code | UNIQUE | uq_faculty_code |
| department | faculty_id, code | UNIQUE | uq_department_faculty_id_code |
| user_account | external_subject | UNIQUE | uq_user_account_external_subject |
| student_profile | student_code | UNIQUE | uq_student_profile_student_code |
| student_profile | user_id | UNIQUE | uq_student_profile_user_id |
| lecturer_profile | user_id | UNIQUE | uq_lecturer_profile_user_id |
| lecturer_profile | lecturer_code | UNIQUE | uq_lecturer_profile_lecturer_code |
| organizational_position | code | UNIQUE | uq_organizational_position_code |
| position_assignment | lecturer_id, position_id, faculty_id WHERE faculty_id IS NOT NULL AND state = ACTIVE | PARTIAL UNIQUE INDEX | uq_position_assignment_faculty_scope |
| position_assignment | lecturer_id, position_id, department_id WHERE department_id IS NOT NULL AND state = ACTIVE | PARTIAL UNIQUE INDEX | uq_position_assignment_department_scope |
| academic_year | code | UNIQUE | uq_academic_year_code |
| thesis_round | academic_year_id, code | UNIQUE | uq_thesis_round_academic_year_id_code |
| round_policy | round_id, policy_type, version | UNIQUE | uq_round_policy_round_id_policy_type_version |
| resource_assignment | assignment_type, user_id, round_id WHERE round_id IS NOT NULL AND state = ACTIVE | PARTIAL UNIQUE INDEX | uq_resource_assignment_round_scope |
| resource_assignment | assignment_type, user_id, thesis_id WHERE thesis_id IS NOT NULL AND state = ACTIVE | PARTIAL UNIQUE INDEX | uq_resource_assignment_thesis_scope |
| resource_assignment | assignment_type, user_id, council_id WHERE council_id IS NOT NULL AND state = ACTIVE | PARTIAL UNIQUE INDEX | uq_resource_assignment_council_scope |
| eligibility_snapshot | student_id, round_id, version | UNIQUE | uq_eligibility_snapshot_student_id_round_id_version |
| eligibility_exception | snapshot_id | UNIQUE | uq_eligibility_exception_snapshot_id |
| lecturer_expertise | lecturer_id, version | UNIQUE | uq_lecturer_expertise_lecturer_id_version |
| topic_title_version | topic_id, version_no | UNIQUE | uq_topic_title_version_topic_id_version_no |
| topic_registration | id, round_id | UNIQUE | uq_topic_registration_id_round_id |
| registration_member | registration_id, student_id | UNIQUE | uq_registration_member_registration_id_student_id |
| registration_member | registration_id | PARTIAL UNIQUE | uq_registration_member_one_coordinator |
| registration_member | student_id, round_id | PARTIAL UNIQUE | uq_registration_member_student_round_active |
| thesis | round_id, topic_id | UNIQUE | uq_thesis_round_id_topic_id |
| thesis | registration_id | UNIQUE | uq_thesis_registration_id |
| thesis_member | thesis_id, student_id | UNIQUE | uq_thesis_member_thesis_id_student_id |
| thesis_member | thesis_id | PARTIAL UNIQUE | uq_thesis_member_one_coordinator |
| member_work_assignment | thesis_member_id, version_no | UNIQUE | uq_member_work_assignment_thesis_member_id_version_no |
| advisor_assignment | thesis_id | PARTIAL UNIQUE | uq_advisor_assignment_active_primary |
| reviewer_assignment | lecturer_id, proposal_id WHERE proposal_id IS NOT NULL AND state = ACTIVE | PARTIAL UNIQUE INDEX | uq_reviewer_assignment_proposal |
| reviewer_assignment | lecturer_id, thesis_id WHERE thesis_id IS NOT NULL AND state = ACTIVE | PARTIAL UNIQUE INDEX | uq_reviewer_assignment_thesis |
| stored_file | storage_key | UNIQUE | uq_stored_file_storage_key |
| proposal | thesis_id | UNIQUE | uq_proposal_thesis_id |
| proposal_version | proposal_id, version_no | UNIQUE | uq_proposal_version_proposal_id_version_no |
| signature_confirmation | proposal_id, signature_type | UNIQUE | uq_signature_confirmation_proposal_id_signature_type |
| progress_milestone | round_id, code, version_no | UNIQUE | uq_progress_milestone_round_id_code_version_no |
| progress_report | thesis_id, milestone_id, version_no | UNIQUE | uq_progress_report_thesis_id_milestone_id_version_no |
| progress_review | progress_report_id, reviewer_id | UNIQUE | uq_progress_review_progress_report_id_reviewer_id |
| external_procedure_outcome | thesis_id, outcome_type, official_ref | UNIQUE | uq_external_procedure_outcome_thesis_id_outcome_type_official_ref |
| document_version | document_id, version_no | UNIQUE | uq_document_version_document_id_version_no |
| similarity_policy | round_id, version_no | UNIQUE | uq_similarity_policy_round_id_version_no |
| council | round_id, code | UNIQUE | uq_council_round_id_code |
| council_member | council_id, role_code, role_slot | UNIQUE | uq_council_member_council_id_role_code_role_slot |
| council_member | council_id, lecturer_id | UNIQUE | uq_council_member_council_id_lecturer_id |
| defense_session | council_id, code | UNIQUE | uq_defense_session_council_id_code |
| session_thesis | session_id, order_no | UNIQUE | uq_session_thesis_session_id_order_no |
| session_thesis | session_id, thesis_id | UNIQUE | uq_session_thesis_session_id_thesis_id |
| council_attendance | session_id, council_member_id | UNIQUE | uq_council_attendance_session_id_council_member_id |
| advisor_review | advisor_assignment_id, thesis_member_id, version_no | UNIQUE | uq_advisor_review_advisor_assignment_id_thesis_member_id_version_no |
| reviewer_review | reviewer_assignment_id, thesis_member_id, version_no | UNIQUE | uq_reviewer_review_reviewer_assignment_id_thesis_member_id_version_no |
| rubric_template | code, version_no | UNIQUE | uq_rubric_template_code_version_no |
| rubric_criterion | rubric_template_id, order_no | UNIQUE | uq_rubric_criterion_rubric_template_id_order_no |
| rubric_criterion | rubric_template_id, code | UNIQUE | uq_rubric_criterion_rubric_template_id_code |
| evaluation | session_id, evaluator_member_id, thesis_member_id | UNIQUE | uq_evaluation_session_id_evaluator_member_id_thesis_member_id |
| evaluation_item | evaluation_id, criterion_id | UNIQUE | uq_evaluation_item_evaluation_id_criterion_id |
| final_result | session_id, thesis_member_id | UNIQUE | uq_final_result_session_id_thesis_member_id |
| council_minute | session_id, minute_no | UNIQUE | uq_council_minute_session_id_minute_no |
| minute_version | minute_id, version_no | UNIQUE | uq_minute_version_minute_id_version_no |
| minute_signature | minute_version_id, signer_member_id | UNIQUE | uq_minute_signature_minute_version_id_signer_member_id |
| repository_item | published_document_version_id | UNIQUE | uq_repository_item_published_document_version_id |
| search_index_metadata | repository_item_id, index_name, index_version | UNIQUE | uq_search_index_metadata_repository_item_id_index_name_index_version |

## Cổng nhất quán

- 62 bảng trong ERD = 62 bảng SQLAlchemy = 62 bảng trong migration initial.
- Không có relation nghiệp vụ chính chỉ tồn tại trong văn bản mà thiếu FK; ngoại lệ có chủ ý là AuditEvent.resource_id đa loại.
- Count 1–3 thành viên, exact Council roles/quorum, evaluator present và aggregate score là application transaction rule, không giả là CHECK.
