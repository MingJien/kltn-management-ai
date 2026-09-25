# Từ điển dữ liệu logical + physical PostgreSQL

> Canonical field dictionary đồng bộ trực tiếp từ SQLAlchemy metadata và các migration 20260920_0001 → 20260925_0007. Mọi bảng dùng UUID PK; FK nghiệp vụ ON DELETE RESTRICT; validation nghiệp vụ dùng dữ liệu synthetic; migration 0006 nạp riêng rubric Mẫu 6 DRAFT không chứa dữ liệu cá nhân.

## Quy ước

- Null/default/PK/FK/unique/check là contract physical, không phải mô tả dự kiến.
- PII gồm cả định danh gián tiếp và điểm/nhận xét theo cá nhân; không đưa dữ liệu thật vào Git/log/vector.
- CHECK cục bộ do PostgreSQL enforce; rule liên hàng xem database-rules.md.

## Danh tính, tổ chức, năm học và điều kiện

### faculty

**Mục đích:** Lưu Khoa sở hữu phạm vi KLTN.
**Trace:** REQ-AUTH-002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| code | VARCHAR(32) | NOT NULL | — | — | — | uq_faculty_code | — | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| name | VARCHAR(255) | NOT NULL | — | — | — | — | — | Tên hiển thị. | NON_PII | Physical metadata 20260920_0001 |
| active | BOOLEAN | NOT NULL | true | — | — | — | — | Thuộc tính nghiệp vụ của faculty. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### department

**Mục đích:** Lưu Bộ môn/chuyên ngành thuộc Khoa.
**Trace:** REQ-AUTH-002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| faculty_id | UUID | NOT NULL | — | — | faculty.id | uq_department_faculty_id_code | — | Tham chiếu faculty.id. | NON_PII | Physical metadata 20260920_0001 |
| code | VARCHAR(32) | NOT NULL | — | — | — | uq_department_faculty_id_code | — | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| name | VARCHAR(255) | NOT NULL | — | — | — | — | — | Tên hiển thị. | NON_PII | Physical metadata 20260920_0001 |
| major_code | VARCHAR(32) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của department. | PII | Physical metadata 20260920_0001 |
| active | BOOLEAN | NOT NULL | true | — | — | — | — | Thuộc tính nghiệp vụ của department. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### user_account

**Mục đích:** Một tài khoản định danh và base role cho mỗi người.
**Trace:** REQ-AUTH-001..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| external_subject | VARCHAR(255) | NOT NULL | — | — | — | uq_user_account_external_subject | — | Thuộc tính nghiệp vụ của user_account. | PII | Physical metadata 20260920_0001 |
| base_role | VARCHAR(20) | NOT NULL | — | — | — | — | ck_user_account_base_role | Thuộc tính nghiệp vụ của user_account. | PII | Physical metadata 20260920_0001 |
| status | VARCHAR(20) | NOT NULL | ACTIVE | — | — | — | ck_user_account_status | Trạng thái lifecycle. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### student_profile

**Mục đích:** Hồ sơ SV tối thiểu gắn account và Bộ môn.
**Trace:** REQ-AUTH-001, REQ-REG-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| user_id | UUID | NOT NULL | — | — | user_account.id | uq_student_profile_user_id | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| student_code | VARCHAR(32) | NOT NULL | — | — | — | uq_student_profile_student_code | — | Thuộc tính nghiệp vụ của student_profile. | PII | Physical metadata 20260920_0001 |
| department_id | UUID | NOT NULL | — | — | department.id | — | — | Tham chiếu department.id. | PII | Physical metadata 20260920_0001 |
| display_name | VARCHAR(255) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của student_profile. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### lecturer_profile

**Mục đích:** Hồ sơ GV tối thiểu gắn account và Bộ môn.
**Trace:** REQ-AUTH-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| user_id | UUID | NOT NULL | — | — | user_account.id | uq_lecturer_profile_user_id | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| lecturer_code | VARCHAR(32) | NOT NULL | — | — | — | uq_lecturer_profile_lecturer_code | — | Thuộc tính nghiệp vụ của lecturer_profile. | PII | Physical metadata 20260920_0001 |
| department_id | UUID | NOT NULL | — | — | department.id | — | — | Tham chiếu department.id. | PII | Physical metadata 20260920_0001 |
| display_name | VARCHAR(255) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của lecturer_profile. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### organizational_position

**Mục đích:** Danh mục vị trí TBM/Trưởng khoa, không phải base role.
**Trace:** REQ-AUTH-002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| code | VARCHAR(40) | NOT NULL | — | — | — | uq_organizational_position_code | ck_organizational_position_code | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| name | VARCHAR(255) | NOT NULL | — | — | — | — | — | Tên hiển thị. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### position_assignment

**Mục đích:** Gán vị trí tổ chức theo scope và hiệu lực.
**Trace:** REQ-AUTH-002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lecturer_id | UUID | NOT NULL | — | — | lecturer_profile.id | uq_position_assignment_faculty_scope, uq_position_assignment_department_scope | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| position_id | UUID | NOT NULL | — | — | organizational_position.id | uq_position_assignment_faculty_scope, uq_position_assignment_department_scope | — | Tham chiếu organizational_position.id. | NON_PII | Physical metadata 20260920_0001 |
| faculty_id | UUID | NULL | — | — | faculty.id | uq_position_assignment_faculty_scope | ck_position_assignment_exactly_one_scope | Tham chiếu faculty.id. | NON_PII | Physical metadata 20260920_0001 |
| department_id | UUID | NULL | — | — | department.id | uq_position_assignment_department_scope | ck_position_assignment_exactly_one_scope | Tham chiếu department.id. | NON_PII | Physical metadata 20260920_0001 |
| effective_from | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | ck_position_assignment_effective_window | Thời điểm bắt đầu hiệu lực. | NON_PII | Physical metadata 20260920_0001 |
| effective_to | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | ck_position_assignment_effective_window | Thời điểm kết thúc hiệu lực. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | ACTIVE | — | — | — | ck_position_assignment_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### resource_assignment

**Mục đích:** Gán quyền theo round/Thesis/Council, gồm verifier điều kiện.
**Trace:** REQ-ELIG-002; người Khoa được giao theo round

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| assignment_type | VARCHAR(50) | NOT NULL | — | — | — | uq_resource_assignment_round_scope, uq_resource_assignment_thesis_scope, uq_resource_assignment_council_scope | — | Thuộc tính nghiệp vụ của resource_assignment. | NON_PII | Physical metadata 20260920_0001 |
| user_id | UUID | NOT NULL | — | — | user_account.id | uq_resource_assignment_round_scope, uq_resource_assignment_thesis_scope, uq_resource_assignment_council_scope | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| round_id | UUID | NULL | — | — | thesis_round.id | uq_resource_assignment_round_scope | ck_resource_assignment_exactly_one_resource | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| thesis_id | UUID | NULL | — | — | thesis.id | uq_resource_assignment_thesis_scope | ck_resource_assignment_exactly_one_resource | Tham chiếu thesis.id. | NON_PII | Physical metadata 20260920_0001 |
| council_id | UUID | NULL | — | — | council.id | uq_resource_assignment_council_scope | ck_resource_assignment_exactly_one_resource | Tham chiếu council.id. | NON_PII | Physical metadata 20260920_0001 |
| effective_from | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | ck_resource_assignment_effective_window | Thời điểm bắt đầu hiệu lực. | NON_PII | Physical metadata 20260920_0001 |
| effective_to | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | ck_resource_assignment_effective_window | Thời điểm kết thúc hiệu lực. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | ACTIVE | — | — | — | ck_resource_assignment_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### academic_year

**Mục đích:** Năm học chứa các đợt KLTN.
**Trace:** REQ-ROUND-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| code | VARCHAR(20) | NOT NULL | — | — | — | uq_academic_year_code | — | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| starts_on | DATE | NOT NULL | — | — | — | — | ck_academic_year_date_window | Thuộc tính nghiệp vụ của academic_year. | NON_PII | Physical metadata 20260920_0001 |
| ends_on | DATE | NOT NULL | — | — | — | — | ck_academic_year_date_window | Thuộc tính nghiệp vụ của academic_year. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_academic_year_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### thesis_round

**Mục đích:** Đợt chính/bổ sung và thời gian tiếp nhận.
**Trace:** REQ-ROUND-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| academic_year_id | UUID | NOT NULL | — | — | academic_year.id | uq_thesis_round_academic_year_id_code | — | Tham chiếu academic_year.id. | NON_PII | Physical metadata 20260920_0001 |
| code | VARCHAR(32) | NOT NULL | — | — | — | uq_thesis_round_academic_year_id_code | — | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| round_type | VARCHAR(20) | NOT NULL | — | — | — | — | ck_thesis_round_round_type | Thuộc tính nghiệp vụ của thesis_round. | NON_PII | Physical metadata 20260920_0001 |
| opens_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | ck_thesis_round_time_window | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| closes_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | ck_thesis_round_time_window | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_thesis_round_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### round_policy

**Mục đích:** Policy versioned theo đợt, không hard-code deadline/tiêu chí mở rộng.
**Trace:** REQ-ROUND-001, REQ-PROG-002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | uq_round_policy_round_id_policy_type_version | — | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| policy_type | VARCHAR(50) | NOT NULL | — | — | — | uq_round_policy_round_id_policy_type_version | — | Thuộc tính nghiệp vụ của round_policy. | NON_PII | Physical metadata 20260920_0001 |
| version | INTEGER | NOT NULL | — | — | — | uq_round_policy_round_id_policy_type_version | ck_round_policy_version_positive | Số version tăng dần. | NON_PII | Physical metadata 20260920_0001 |
| config_json | JSONB | NOT NULL | application | — | — | — | — | Dữ liệu cấu hình/danh sách có schema ở application. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_round_policy_active_has_effective_at, ck_round_policy_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| effective_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | ck_round_policy_active_has_effective_at | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### eligibility_snapshot

**Mục đích:** Snapshot điều kiện đăng ký theo SV/đợt/version.
**Trace:** REQ-ELIG-001..002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| student_id | UUID | NOT NULL | — | — | student_profile.id | uq_eligibility_snapshot_student_id_round_id_version | — | Tham chiếu student_profile.id. | PII | Physical metadata 20260920_0001 |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | uq_eligibility_snapshot_student_id_round_id_version | — | Tham chiếu thesis_round.id. | PII | Physical metadata 20260920_0001 |
| version | INTEGER | NOT NULL | — | — | — | uq_eligibility_snapshot_student_id_round_id_version | ck_eligibility_snapshot_version_positive | Số version tăng dần. | PII | Physical metadata 20260920_0001 |
| passed_credit_ratio | NUMERIC(5, 4) | NOT NULL | — | — | — | — | ck_eligibility_snapshot_credit_ratio | Thuộc tính nghiệp vụ của eligibility_snapshot. | PII | Physical metadata 20260920_0001 |
| gpa_4 | NUMERIC(3, 2) | NOT NULL | — | — | — | — | ck_eligibility_snapshot_gpa | Thuộc tính nghiệp vụ của eligibility_snapshot. | PII | Physical metadata 20260920_0001 |
| discipline_status | VARCHAR(40) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của eligibility_snapshot. | PII | Physical metadata 20260920_0001 |
| criminal_case_status | VARCHAR(40) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của eligibility_snapshot. | PII | Physical metadata 20260920_0001 |
| evidence_ref | VARCHAR(500) | NOT NULL | — | — | — | — | — | Tham chiếu văn bản/minh chứng. | PII | Physical metadata 20260920_0001 |
| captured_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| confirmed_by | UUID | NULL | — | — | user_account.id | — | ck_eligibility_snapshot_decision_metadata | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| confirmed_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | ck_eligibility_snapshot_decision_metadata | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| decision_reason | TEXT | NULL | — | — | — | — | — | Lý do quyết định. | PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_eligibility_snapshot_decision_metadata, ck_eligibility_snapshot_state | Trạng thái lifecycle của aggregate/entity. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### eligibility_exception

**Mục đích:** Ngoại lệ có căn cứ chính thức cho snapshot.
**Trace:** REQ-ELIG-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| snapshot_id | UUID | NOT NULL | — | — | eligibility_snapshot.id | uq_eligibility_exception_snapshot_id | — | Tham chiếu eligibility_snapshot.id. | PII | Physical metadata 20260920_0001 |
| official_ref | VARCHAR(500) | NOT NULL | — | — | — | — | — | Tham chiếu văn bản/minh chứng. | PII | Physical metadata 20260920_0001 |
| reason | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của eligibility_exception. | PII | Physical metadata 20260920_0001 |
| granted_by | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| granted_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### lecturer_expertise

**Mục đích:** Hồ sơ chuyên môn tự khai/versioned của GV.
**Trace:** REQ-EXP-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lecturer_id | UUID | NOT NULL | — | — | lecturer_profile.id | uq_lecturer_expertise_lecturer_id_version | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| version | INTEGER | NOT NULL | — | — | — | uq_lecturer_expertise_lecturer_id_version | ck_lecturer_expertise_version_positive | Số version tăng dần. | NON_PII | Physical metadata 20260920_0001 |
| labels | JSONB | NOT NULL | application | — | — | — | — | Dữ liệu cấu hình/danh sách có schema ở application. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_lecturer_expertise_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| verified_by | UUID | NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| verified_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### expertise_evidence

**Mục đích:** Minh chứng cho hồ sơ chuyên môn.
**Trace:** REQ-EXP-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| expertise_id | UUID | NOT NULL | — | — | lecturer_expertise.id | — | — | Tham chiếu lecturer_expertise.id. | PII | Physical metadata 20260920_0001 |
| evidence_type | VARCHAR(50) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của expertise_evidence. | NON_PII | Physical metadata 20260920_0001 |
| reference | VARCHAR(500) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của expertise_evidence. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

## Đề tài, đăng ký, Thesis và assignment

### topic

**Mục đích:** Đề tài được đề xuất/duyệt trong một đợt.
**Trace:** REQ-TOPIC-001..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | — | — | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| department_id | UUID | NOT NULL | — | — | department.id | — | — | Tham chiếu department.id. | NON_PII | Physical metadata 20260920_0001 |
| proposer_user_id | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| proposer_type | VARCHAR(20) | NOT NULL | — | — | — | — | ck_topic_proposer_type | Thuộc tính nghiệp vụ của topic. | NON_PII | Physical metadata 20260920_0001 |
| current_title | VARCHAR(500) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của topic. | NON_PII | Physical metadata 20260920_0001 |
| description | TEXT | NULL | — | — | — | — | — | Mô tả. | NON_PII | Physical metadata 20260920_0001 |
| max_students | INTEGER | NOT NULL | 3 | — | — | — | ck_topic_max_students | Thuộc tính nghiệp vụ của topic. | PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_topic_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| decided_by | UUID | NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| decided_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### topic_title_version

**Mục đích:** Lịch sử chỉnh tên đề tài.
**Trace:** REQ-TOPIC-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| topic_id | UUID | NOT NULL | — | — | topic.id | uq_topic_title_version_topic_id_version_no | — | Tham chiếu topic.id. | NON_PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_topic_title_version_topic_id_version_no | ck_topic_title_version_version_positive | Số version tăng dần. | NON_PII | Physical metadata 20260920_0001 |
| title | VARCHAR(500) | NOT NULL | — | — | — | — | — | Tiêu đề/tên nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| changed_by | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| change_reason | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của topic_title_version. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### topic_requirement

**Mục đích:** Tiêu chí mong muốn của GVHD, enforcement DESIRED.
**Trace:** REQ-TOPIC-003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| topic_id | UUID | NOT NULL | — | — | topic.id | — | — | Tham chiếu topic.id. | NON_PII | Physical metadata 20260920_0001 |
| requirement_type | VARCHAR(30) | NOT NULL | — | — | — | — | ck_topic_requirement_requirement_type | Thuộc tính nghiệp vụ của topic_requirement. | NON_PII | Physical metadata 20260920_0001 |
| value_text | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của topic_requirement. | NON_PII | Physical metadata 20260920_0001 |
| preferred_gpa | NUMERIC(3, 2) | NULL | — | — | — | — | ck_topic_requirement_preferred_gpa | Thuộc tính nghiệp vụ của topic_requirement. | PII | Physical metadata 20260920_0001 |
| enforcement | VARCHAR(20) | NOT NULL | DESIRED | — | — | — | ck_topic_requirement_enforcement_desired | Thuộc tính nghiệp vụ của topic_requirement. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### topic_registration

**Mục đích:** Aggregate đăng ký một topic trong một đợt.
**Trace:** REQ-REG-001..006

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | uq_topic_registration_id_round_id | — | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| topic_id | UUID | NOT NULL | — | — | topic.id | — | — | Tham chiếu topic.id. | NON_PII | Physical metadata 20260920_0001 |
| created_by | UUID | NOT NULL | — | — | student_profile.id | — | — | Tham chiếu student_profile.id. | PII | Physical metadata 20260920_0001 |
| state | VARCHAR(30) | NOT NULL | DRAFT | — | — | — | ck_topic_registration_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| submitted_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Thời điểm submit. | NON_PII | Physical metadata 20260920_0001 |
| lecturer_decided_by | UUID | NULL | — | — | lecturer_profile.id | — | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| lecturer_decided_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| lecturer_reason | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của topic_registration. | PII | Physical metadata 20260920_0001 |
| department_finalized_by | UUID | NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| department_finalized_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | uq_topic_registration_id_round_id | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### registration_member

**Mục đích:** Mọi SV trong đăng ký nhóm; dùng chặn trùng SV/round và lưu phản hồi tham gia riêng của từng người.
**Trace:** REQ-REG-001..002, REQ-REG-005..006

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| registration_id | UUID | NOT NULL | — | — | topic_registration.id | uq_registration_member_one_coordinator, uq_registration_member_registration_id_student_id | — | Tham chiếu topic_registration.id. | PII | Physical metadata 20260920_0001 |
| round_id | UUID | NOT NULL | — | — | topic_registration.round_id | uq_registration_member_student_round_active | — | Tham chiếu topic_registration.round_id. | PII | Physical metadata 20260920_0001 |
| student_id | UUID | NOT NULL | — | — | student_profile.id | uq_registration_member_registration_id_student_id, uq_registration_member_student_round_active | — | Tham chiếu student_profile.id. | PII | Physical metadata 20260920_0001 |
| is_coordinator | BOOLEAN | NOT NULL | false | — | — | — | — | Thuộc tính nghiệp vụ của registration_member. | PII | Physical metadata 20260920_0001 |
| active | BOOLEAN | NOT NULL | true | — | — | — | — | Thuộc tính nghiệp vụ của registration_member. | PII | Physical metadata 20260920_0001 |
| consent_status | VARCHAR(20) | NOT NULL | PENDING | — | — | — | ck_registration_member_consent_consistency | PENDING trước phản hồi; ACCEPTED/DECLINED sau khi chính SV trả lời. Service phải đối chiếu đúng tài khoản với student_id. | PII | Migration 0007 |
| responded_by_user_id | UUID | NULL | — | — | user_account.id | — | ck_registration_member_consent_consistency | Tài khoản đã tự phản hồi; chỉ có khi đã chấp nhận/từ chối. | PII | Migration 0007 |
| responded_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | ck_registration_member_consent_consistency | Thời điểm phản hồi; chỉ có khi đã chấp nhận/từ chối. | PII | Migration 0007 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### thesis

**Mục đích:** Hồ sơ KLTN hình thành sau finalization.
**Trace:** REQ-REG-003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | uq_thesis_round_id_topic_id | — | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| topic_id | UUID | NOT NULL | — | — | topic.id | uq_thesis_round_id_topic_id | — | Tham chiếu topic.id. | NON_PII | Physical metadata 20260920_0001 |
| registration_id | UUID | NOT NULL | — | — | topic_registration.id | uq_thesis_registration_id | — | Tham chiếu topic_registration.id. | NON_PII | Physical metadata 20260920_0001 |
| department_id | UUID | NOT NULL | — | — | department.id | — | — | Tham chiếu department.id. | NON_PII | Physical metadata 20260920_0001 |
| current_title | VARCHAR(500) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của thesis. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(30) | NOT NULL | ACTIVE | — | — | — | ck_thesis_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### thesis_member

**Mục đích:** Thành viên thực hiện KLTN và coordinator.
**Trace:** REQ-REG-002/004

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_id | UUID | NOT NULL | — | — | thesis.id | uq_thesis_member_one_coordinator, uq_thesis_member_thesis_id_student_id | — | Tham chiếu thesis.id. | PII | Physical metadata 20260920_0001 |
| student_id | UUID | NOT NULL | — | — | student_profile.id | uq_thesis_member_thesis_id_student_id | — | Tham chiếu student_profile.id. | PII | Physical metadata 20260920_0001 |
| is_coordinator | BOOLEAN | NOT NULL | false | — | — | — | — | Thuộc tính nghiệp vụ của thesis_member. | PII | Physical metadata 20260920_0001 |
| active | BOOLEAN | NOT NULL | true | — | — | — | — | Thuộc tính nghiệp vụ của thesis_member. | PII | Physical metadata 20260920_0001 |
| joined_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| left_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### member_work_assignment

**Mục đích:** Phân công công việc versioned cho từng SV.
**Trace:** REQ-REG-004

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_member_id | UUID | NOT NULL | — | — | thesis_member.id | uq_member_work_assignment_thesis_member_id_version_no | — | Tham chiếu thesis_member.id. | PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_member_work_assignment_thesis_member_id_version_no | ck_member_work_assignment_version_positive | Số version tăng dần. | PII | Physical metadata 20260920_0001 |
| work_description | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của member_work_assignment. | PII | Physical metadata 20260920_0001 |
| expected_output | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của member_work_assignment. | PII | Physical metadata 20260920_0001 |
| state | VARCHAR(30) | NOT NULL | DRAFT | — | — | — | ck_member_work_assignment_state | Trạng thái lifecycle của aggregate/entity. | PII | Physical metadata 20260920_0001 |
| reviewed_by | UUID | NULL | — | — | lecturer_profile.id | — | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| reviewed_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| review_comment | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của member_work_assignment. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | PII | Physical metadata 20260920_0001 |

### advisor_assignment

**Mục đích:** Phân công GVHD chính cho Thesis.
**Trace:** REQ-REG-003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_id | UUID | NOT NULL | — | — | thesis.id | uq_advisor_assignment_active_primary | — | Tham chiếu thesis.id. | NON_PII | Physical metadata 20260920_0001 |
| lecturer_id | UUID | NOT NULL | — | — | lecturer_profile.id | — | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| assignment_type | VARCHAR(20) | NOT NULL | PRIMARY | — | — | — | ck_advisor_assignment_assignment_type | Thuộc tính nghiệp vụ của advisor_assignment. | NON_PII | Physical metadata 20260920_0001 |
| assigned_by | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| effective_from | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Thời điểm bắt đầu hiệu lực. | NON_PII | Physical metadata 20260920_0001 |
| effective_to | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Thời điểm kết thúc hiệu lực. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | ACTIVE | — | — | — | ck_advisor_assignment_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### reviewer_assignment

**Mục đích:** Phân công người review đề cương/KLTN.
**Trace:** REQ-PROP-002, REQ-EVAL-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lecturer_id | UUID | NOT NULL | — | — | lecturer_profile.id | uq_reviewer_assignment_proposal, uq_reviewer_assignment_thesis | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| proposal_id | UUID | NULL | — | — | proposal.id | uq_reviewer_assignment_proposal | ck_reviewer_assignment_exactly_one_subject | Tham chiếu proposal.id. | NON_PII | Physical metadata 20260920_0001 |
| thesis_id | UUID | NULL | — | — | thesis.id | uq_reviewer_assignment_thesis | ck_reviewer_assignment_exactly_one_subject | Tham chiếu thesis.id. | NON_PII | Physical metadata 20260920_0001 |
| review_scope | VARCHAR(20) | NOT NULL | — | — | — | — | ck_reviewer_assignment_review_scope | Thuộc tính nghiệp vụ của reviewer_assignment. | PII | Physical metadata 20260920_0001 |
| assigned_by | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| assigned_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | ACTIVE | — | — | — | ck_reviewer_assignment_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

## Đề cương, tiến độ, thay đổi, tài liệu và tương đồng

### stored_file

**Mục đích:** Metadata file, checksum và trạng thái quét; không lưu bytes trong DB.
**Trace:** REQ-DOC-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| storage_key | VARCHAR(500) | NOT NULL | — | — | — | uq_stored_file_storage_key | — | Thuộc tính nghiệp vụ của stored_file. | NON_PII | Physical metadata 20260920_0001 |
| original_name | VARCHAR(500) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của stored_file. | NON_PII | Physical metadata 20260920_0001 |
| media_type | VARCHAR(150) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của stored_file. | NON_PII | Physical metadata 20260920_0001 |
| byte_size | INTEGER | NOT NULL | — | — | — | — | ck_stored_file_byte_size_positive | Thuộc tính nghiệp vụ của stored_file. | NON_PII | Physical metadata 20260920_0001 |
| sha256 | VARCHAR(64) | NOT NULL | — | — | — | — | — | Hash kiểm tra/audit; không phải nội dung thô. | NON_PII | Physical metadata 20260920_0001 |
| scan_state | VARCHAR(20) | NOT NULL | QUARANTINED | — | — | — | ck_stored_file_scan_state | Thuộc tính nghiệp vụ của stored_file. | NON_PII | Physical metadata 20260920_0001 |
| scanned_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### proposal

**Mục đích:** Aggregate đề cương một-một với Thesis.
**Trace:** REQ-PROP-001..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_id | UUID | NOT NULL | — | — | thesis.id | uq_proposal_thesis_id | — | Tham chiếu thesis.id. | NON_PII | Physical metadata 20260920_0001 |
| current_version_no | INTEGER | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của proposal. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(40) | NOT NULL | DRAFT | — | — | — | ck_proposal_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### proposal_version

**Mục đích:** Mỗi lần nộp/sửa đề cương là một version bất biến.
**Trace:** REQ-PROP-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proposal_id | UUID | NOT NULL | — | — | proposal.id | uq_proposal_version_proposal_id_version_no | — | Tham chiếu proposal.id. | NON_PII | Append-only |
| version_no | INTEGER | NOT NULL | — | — | — | uq_proposal_version_proposal_id_version_no | ck_proposal_version_version_positive | Số version tăng dần. | NON_PII | Append-only |
| stored_file_id | UUID | NOT NULL | — | — | stored_file.id | — | — | Tham chiếu stored_file.id. | NON_PII | Append-only |
| submitted_by | UUID | NOT NULL | — | — | student_profile.id | — | — | Tham chiếu student_profile.id. | PII | Append-only |
| submitted_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Thời điểm submit. | NON_PII | Append-only |
| content_sha256 | VARCHAR(64) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của proposal_version. | NON_PII | Append-only |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Append-only |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Append-only |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Append-only |

### proposal_review

**Mục đích:** Nhận xét trỏ đúng proposal version và assignment.
**Trace:** REQ-PROP-002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proposal_version_id | UUID | NOT NULL | — | — | proposal_version.id | — | — | Tham chiếu proposal_version.id. | PII | Physical metadata 20260920_0001 |
| reviewer_assignment_id | UUID | NOT NULL | — | — | reviewer_assignment.id | — | — | Tham chiếu reviewer_assignment.id. | PII | Physical metadata 20260920_0001 |
| reviewer_user_id | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| decision | VARCHAR(30) | NOT NULL | — | — | — | — | ck_proposal_review_decision | Thuộc tính nghiệp vụ của proposal_review. | PII | Physical metadata 20260920_0001 |
| comment | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của proposal_review. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### signature_confirmation

**Mục đích:** Metadata TBM chốt/Trưởng khoa xác nhận đề cương.
**Trace:** REQ-PROP-002..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proposal_id | UUID | NOT NULL | — | — | proposal.id và cặp proposal_version.(proposal_id, version_no) | uq_signature_confirmation_proposal_id_signature_type | — | Hồ sơ đề cương được ký; đi cùng proposal_version_no để trỏ đúng bản. | NON_PII | Physical metadata 20260920_0001 + FK 20260924_0002 |
| proposal_version_no | INTEGER | NOT NULL | — | — | proposal_version.(proposal_id, version_no) | — | ck_signature_confirmation_proposal_version_positive | Số phiên bản đề cương cụ thể được TBM/Trưởng khoa xác nhận; không suy ra từ bản hiện hành về sau. | NON_PII | Added in 20260924_0002; composite FK fk_signature_confirmation_proposal_version_pair |
| signature_type | VARCHAR(40) | NOT NULL | — | — | — | uq_signature_confirmation_proposal_id_signature_type | ck_signature_confirmation_signature_type | TBM chốt nội dung hoặc Trưởng khoa xác nhận/ký văn bản. | NON_PII | Physical metadata 20260920_0001 |
| signer_user_id | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| confirmed_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| official_ref | VARCHAR(500) | NULL | — | — | — | — | — | Tham chiếu văn bản/minh chứng. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### progress_milestone

**Mục đích:** Mốc tiến độ versioned theo round/kế hoạch.
**Trace:** REQ-PROG-001..002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | uq_progress_milestone_round_id_code_version_no | — | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| code | VARCHAR(50) | NOT NULL | — | — | — | uq_progress_milestone_round_id_code_version_no | — | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| title | VARCHAR(255) | NOT NULL | — | — | — | — | — | Tiêu đề/tên nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_progress_milestone_round_id_code_version_no | ck_progress_milestone_version_positive | Số version tăng dần. | NON_PII | Physical metadata 20260920_0001 |
| due_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| expected_ratio | NUMERIC(5, 2) | NULL | — | — | — | — | ck_progress_milestone_expected_ratio | Thuộc tính nghiệp vụ của progress_milestone. | NON_PII | Physical metadata 20260920_0001 |
| source_type | VARCHAR(20) | NOT NULL | — | — | — | — | ck_progress_milestone_source_type | Thuộc tính nghiệp vụ của progress_milestone. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_progress_milestone_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### progress_report

**Mục đích:** Báo cáo tiến độ versioned của Thesis.
**Trace:** REQ-PROG-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_id | UUID | NOT NULL | — | — | thesis.id | uq_progress_report_thesis_id_milestone_id_version_no | — | Tham chiếu thesis.id. | PII | Physical metadata 20260920_0001 |
| milestone_id | UUID | NOT NULL | — | — | progress_milestone.id | uq_progress_report_thesis_id_milestone_id_version_no | — | Tham chiếu progress_milestone.id. | PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_progress_report_thesis_id_milestone_id_version_no | ck_progress_report_version_positive | Số version tăng dần. | PII | Physical metadata 20260920_0001 |
| summary | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của progress_report. | PII | Physical metadata 20260920_0001 |
| reported_ratio | NUMERIC(5, 2) | NULL | — | — | — | — | ck_progress_report_reported_ratio | Thuộc tính nghiệp vụ của progress_report. | PII | Physical metadata 20260920_0001 |
| evidence_file_id | UUID | NULL | — | — | stored_file.id | — | — | Tham chiếu stored_file.id. | PII | Physical metadata 20260920_0001 |
| submitted_by | UUID | NOT NULL | — | — | student_profile.id | — | — | Tham chiếu student_profile.id. | PII | Physical metadata 20260920_0001 |
| state | VARCHAR(30) | NOT NULL | DRAFT | — | — | — | ck_progress_report_state | Trạng thái lifecycle của aggregate/entity. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | PII | Physical metadata 20260920_0001 |

### progress_review

**Mục đích:** GVHD nhận xét/xác nhận báo cáo tiến độ.
**Trace:** REQ-PROG-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| progress_report_id | UUID | NOT NULL | — | — | progress_report.id | uq_progress_review_progress_report_id_reviewer_id | — | Tham chiếu progress_report.id. | PII | Physical metadata 20260920_0001 |
| reviewer_id | UUID | NOT NULL | — | — | lecturer_profile.id | uq_progress_review_progress_report_id_reviewer_id | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| decision | VARCHAR(30) | NOT NULL | — | — | — | — | ck_progress_review_decision | `COMMENT_ONLY` là góp ý chéo, `CONFIRM`/`REVISION_REQUIRED` chỉ GVHD chính quyết định ở service. | PII | Migration 0005 |
| comment | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của progress_review. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### topic_change_request

**Mục đích:** Workflow đổi đề tài trong hệ thống.
**Trace:** REQ-CHANGE-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_id | UUID | NOT NULL | — | — | thesis.id | — | — | Tham chiếu thesis.id. | PII | Physical metadata 20260920_0001 |
| requested_by | UUID | NOT NULL | — | — | student_profile.id | — | — | Tham chiếu student_profile.id. | PII | Physical metadata 20260920_0001 |
| reason | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của topic_change_request. | PII | Physical metadata 20260920_0001 |
| proposed_topic_id | UUID | NULL | — | — | topic.id | — | ck_topic_change_request_target_present | Tham chiếu topic.id. | PII | Physical metadata 20260920_0001 |
| proposed_title | VARCHAR(500) | NULL | — | — | — | — | ck_topic_change_request_target_present | Thuộc tính nghiệp vụ của topic_change_request. | PII | Physical metadata 20260920_0001 |
| advisor_reviewed_by | UUID | NULL | — | — | lecturer_profile.id | — | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| advisor_reviewed_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| department_decided_by | UUID | NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| department_decided_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| state | VARCHAR(30) | NOT NULL | SUBMITTED | — | — | — | ck_topic_change_request_state | Trạng thái lifecycle của aggregate/entity. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | PII | Physical metadata 20260920_0001 |

### external_procedure_outcome

**Mục đích:** Kết quả rút/gia hạn từ thủ tục ngoài.
**Trace:** REQ-CHANGE-002..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_id | UUID | NOT NULL | — | — | thesis.id | uq_external_procedure_outcome_thesis_id_outcome_type_official_ref | — | Tham chiếu thesis.id. | PII | Physical metadata 20260920_0001 |
| outcome_type | VARCHAR(20) | NOT NULL | — | — | — | uq_external_procedure_outcome_thesis_id_outcome_type_official_ref | ck_external_procedure_outcome_outcome_type | Thuộc tính nghiệp vụ của external_procedure_outcome. | PII | Physical metadata 20260920_0001 |
| official_ref | VARCHAR(500) | NOT NULL | — | — | — | uq_external_procedure_outcome_thesis_id_outcome_type_official_ref | — | Tham chiếu văn bản/minh chứng. | PII | Physical metadata 20260920_0001 |
| effective_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| evidence_file_id | UUID | NULL | — | — | stored_file.id | — | — | Tham chiếu stored_file.id. | PII | Physical metadata 20260920_0001 |
| recorded_by | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### document

**Mục đích:** Container tài liệu của Thesis.
**Trace:** REQ-DOC-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_id | UUID | NOT NULL | — | — | thesis.id | — | — | Tham chiếu thesis.id. | NON_PII | Physical metadata 20260920_0001 |
| document_type | VARCHAR(50) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của document. | NON_PII | Physical metadata 20260920_0001 |
| title | VARCHAR(500) | NOT NULL | — | — | — | — | — | Tiêu đề/tên nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| visibility | VARCHAR(20) | NOT NULL | PRIVATE | — | — | — | ck_document_visibility | Thuộc tính nghiệp vụ của document. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_document_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### document_version

**Mục đích:** Bản nộp tài liệu bất biến.
**Trace:** REQ-DOC-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| document_id | UUID | NOT NULL | — | — | document.id | uq_document_version_document_id_version_no | — | Tham chiếu document.id. | NON_PII | Append-only |
| version_no | INTEGER | NOT NULL | — | — | — | uq_document_version_document_id_version_no | ck_document_version_version_positive | Số version tăng dần. | NON_PII | Append-only |
| stored_file_id | UUID | NOT NULL | — | — | stored_file.id | — | — | Tham chiếu stored_file.id. | NON_PII | Append-only |
| submitted_by | UUID | NOT NULL | — | — | student_profile.id | — | — | Tham chiếu student_profile.id. | PII | Append-only |
| submitted_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Thời điểm submit. | NON_PII | Append-only |
| content_sha256 | VARCHAR(64) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của document_version. | NON_PII | Append-only |
| state | VARCHAR(30) | NOT NULL | DRAFT | — | — | — | ck_document_version_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Append-only |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Append-only |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Append-only |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Append-only |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Append-only |

### similarity_policy

**Mục đích:** Policy/metric tương đồng versioned và configurable.
**Trace:** REQ-SIM-002..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | uq_similarity_policy_round_id_version_no | — | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_similarity_policy_round_id_version_no | ck_similarity_policy_version_positive | Số version tăng dần. | NON_PII | Physical metadata 20260920_0001 |
| metric_code | VARCHAR(100) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_policy. | PII | Physical metadata 20260920_0001 |
| threshold_value | NUMERIC(10, 6) | NULL | — | — | — | — | ck_similarity_policy_threshold_nonnegative | Thuộc tính nghiệp vụ của similarity_policy. | NON_PII | Physical metadata 20260920_0001 |
| decision_mode | VARCHAR(20) | NOT NULL | ADVISORY | — | — | — | ck_similarity_policy_decision_mode | Thuộc tính nghiệp vụ của similarity_policy. | NON_PII | Physical metadata 20260920_0001 |
| config_json | JSONB | NOT NULL | application | — | — | — | — | Dữ liệu cấu hình/danh sách có schema ở application. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_similarity_policy_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### similarity_check

**Mục đích:** Record một lần kiểm tra với provenance.
**Trace:** REQ-SIM-001..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| document_version_id | UUID | NOT NULL | — | — | document_version.id | — | — | Tham chiếu document_version.id. | NON_PII | Physical metadata 20260920_0001 |
| policy_id | UUID | NULL | — | — | similarity_policy.id | — | — | Tham chiếu similarity_policy.id. | NON_PII | Physical metadata 20260920_0001 |
| metric_code | VARCHAR(100) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_check. | PII | Physical metadata 20260920_0001 |
| lexical_coverage_pct | NUMERIC(6, 3) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_check. | NON_PII | Physical metadata 20260920_0001 |
| semantic_candidate_score | NUMERIC(10, 6) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_check. | PII | Physical metadata 20260920_0001 |
| business_status | VARCHAR(40) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_check. | NON_PII | Physical metadata 20260920_0001 |
| model_version | VARCHAR(100) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_check. | NON_PII | Physical metadata 20260920_0001 |
| index_version | VARCHAR(100) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_check. | NON_PII | Physical metadata 20260920_0001 |
| corpus_snapshot | VARCHAR(200) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_check. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | QUEUED | — | — | — | ck_similarity_check_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| completed_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### similarity_match

**Mục đích:** Đoạn/nguồn match và score tách lexical/semantic.
**Trace:** REQ-SIM-001..002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| check_id | UUID | NOT NULL | — | — | similarity_check.id | — | — | Tham chiếu similarity_check.id. | NON_PII | Physical metadata 20260920_0001 |
| source_repository_item_id | UUID | NULL | — | — | repository_item.id | — | — | Trỏ item nguồn của kết quả match kể cả KLTN cũ hay tài liệu ngoài. | NON_PII | Migration 0003 |
| source_document_version_id | UUID | NULL | — | — | document_version.id | — | — | Tham chiếu document_version.id. | NON_PII | Physical metadata 20260920_0001 |
| source_ref | VARCHAR(500) | NOT NULL | — | — | — | — | — | Tham chiếu văn bản/minh chứng. | NON_PII | Physical metadata 20260920_0001 |
| input_start | INTEGER | NOT NULL | — | — | — | — | ck_similarity_match_input_range | Thuộc tính nghiệp vụ của similarity_match. | NON_PII | Physical metadata 20260920_0001 |
| input_end | INTEGER | NOT NULL | — | — | — | — | ck_similarity_match_input_range | Thuộc tính nghiệp vụ của similarity_match. | NON_PII | Physical metadata 20260920_0001 |
| matched_text_hash | VARCHAR(64) | NULL | — | — | — | — | — | Hash kiểm tra/audit; không phải nội dung thô. | NON_PII | Physical metadata 20260920_0001 |
| lexical_score | NUMERIC(10, 6) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_match. | PII | Physical metadata 20260920_0001 |
| semantic_score | NUMERIC(10, 6) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của similarity_match. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

## Hội đồng, bảo vệ, nhận xét và điểm

### council

**Mục đích:** Hội đồng nhập từ quyết định, theo round/Bộ môn.
**Trace:** REQ-COUNCIL-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | uq_council_round_id_code | — | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| department_id | UUID | NOT NULL | — | — | department.id | — | — | Tham chiếu department.id. | NON_PII | Physical metadata 20260920_0001 |
| code | VARCHAR(50) | NOT NULL | — | — | — | uq_council_round_id_code | — | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| decision_ref | VARCHAR(500) | NOT NULL | — | — | — | — | — | Tham chiếu văn bản/minh chứng. | NON_PII | Physical metadata 20260920_0001 |
| decision_date | DATE | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của council. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | IMPORTED | — | — | — | ck_council_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### council_member

**Mục đích:** Thành viên/role-slot lấy từ quyết định.
**Trace:** REQ-COUNCIL-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| council_id | UUID | NOT NULL | — | — | council.id | uq_council_member_council_id_lecturer_id, uq_council_member_council_id_role_code_role_slot | — | Tham chiếu council.id. | NON_PII | Physical metadata 20260920_0001 |
| lecturer_id | UUID | NOT NULL | — | — | lecturer_profile.id | uq_council_member_council_id_lecturer_id | — | Tham chiếu lecturer_profile.id. | PII | Physical metadata 20260920_0001 |
| role_code | VARCHAR(20) | NOT NULL | — | — | — | uq_council_member_council_id_role_code_role_slot | ck_council_member_role_code | Thuộc tính nghiệp vụ của council_member. | PII | Physical metadata 20260920_0001 |
| role_slot | INTEGER | NOT NULL | 1 | — | — | uq_council_member_council_id_role_code_role_slot | ck_council_member_role_slot | Thuộc tính nghiệp vụ của council_member. | NON_PII | Physical metadata 20260920_0001 |
| active | BOOLEAN | NOT NULL | true | — | — | — | ck_council_member_active_boolean | Thuộc tính nghiệp vụ của council_member. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### defense_session

**Mục đích:** Một buổi/phiên của Hội đồng.
**Trace:** REQ-COUNCIL-002..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| council_id | UUID | NOT NULL | — | — | council.id | uq_defense_session_council_id_code | — | Tham chiếu council.id. | NON_PII | Physical metadata 20260920_0001 |
| code | VARCHAR(50) | NOT NULL | — | — | — | uq_defense_session_council_id_code | — | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| scheduled_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| location | VARCHAR(255) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của defense_session. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(30) | NOT NULL | SCHEDULED | — | — | — | ck_defense_session_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### session_thesis

**Mục đích:** Xếp nhiều Thesis vào phiên theo thứ tự.
**Trace:** REQ-COUNCIL-002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session_id | UUID | NOT NULL | — | — | defense_session.id | uq_session_thesis_session_id_order_no, uq_session_thesis_session_id_thesis_id | — | Tham chiếu defense_session.id. | NON_PII | Physical metadata 20260920_0001 |
| thesis_id | UUID | NOT NULL | — | — | thesis.id | uq_session_thesis_session_id_thesis_id | — | Tham chiếu thesis.id. | NON_PII | Physical metadata 20260920_0001 |
| order_no | INTEGER | NOT NULL | — | — | — | uq_session_thesis_session_id_order_no | ck_session_thesis_order_positive | Thuộc tính nghiệp vụ của session_thesis. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### council_attendance

**Mục đích:** Hiện diện từng thành viên trong phiên.
**Trace:** REQ-COUNCIL-003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session_id | UUID | NOT NULL | — | — | defense_session.id | uq_council_attendance_session_id_council_member_id | — | Tham chiếu defense_session.id. | PII | Physical metadata 20260920_0001 |
| council_member_id | UUID | NOT NULL | — | — | council_member.id | uq_council_attendance_session_id_council_member_id | — | Tham chiếu council_member.id. | PII | Physical metadata 20260920_0001 |
| present | BOOLEAN | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của council_attendance. | PII | Physical metadata 20260920_0001 |
| recorded_by | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| recorded_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| note | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của council_attendance. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | PII | Physical metadata 20260920_0001 |

### defense_eligibility_check

**Mục đích:** Kết quả kiểm điều kiện bảo vệ theo từng SV.
**Trace:** REQ-DEF-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_member_id | UUID | NOT NULL | — | — | thesis_member.id | — | — | Tham chiếu thesis_member.id. | PII | Physical metadata 20260920_0001 |
| round_id | UUID | NOT NULL | — | — | thesis_round.id | — | — | Tham chiếu thesis_round.id. | PII | Physical metadata 20260920_0001 |
| advisor_review_id | UUID | NULL | — | — | advisor_review.id | — | — | Tham chiếu advisor_review.id. | PII | Physical metadata 20260920_0001 |
| discipline_result | VARCHAR(40) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của defense_eligibility_check. | PII | Physical metadata 20260920_0001 |
| completion_result | VARCHAR(40) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của defense_eligibility_check. | PII | Physical metadata 20260920_0001 |
| advisor_result | VARCHAR(40) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của defense_eligibility_check. | PII | Physical metadata 20260920_0001 |
| local_policy_result | VARCHAR(40) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của defense_eligibility_check. | PII | Physical metadata 20260920_0001 |
| similarity_result | VARCHAR(40) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của defense_eligibility_check. | PII | Physical metadata 20260920_0001 |
| result | VARCHAR(30) | NOT NULL | — | — | — | — | ck_defense_eligibility_check_result | Thuộc tính nghiệp vụ của defense_eligibility_check. | PII | Physical metadata 20260920_0001 |
| reason | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của defense_eligibility_check. | PII | Physical metadata 20260920_0001 |
| checked_by | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### advisor_review

**Mục đích:** Phiếu nhận xét GVHD theo SV và document version.
**Trace:** REQ-EVAL-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| advisor_assignment_id | UUID | NOT NULL | — | — | advisor_assignment.id | uq_advisor_review_advisor_assignment_id_thesis_member_id_version_no | — | Tham chiếu advisor_assignment.id. | PII | Physical metadata 20260920_0001 |
| thesis_member_id | UUID | NOT NULL | — | — | thesis_member.id | uq_advisor_review_advisor_assignment_id_thesis_member_id_version_no | — | Tham chiếu thesis_member.id. | PII | Physical metadata 20260920_0001 |
| document_version_id | UUID | NOT NULL | — | — | document_version.id | — | — | Tham chiếu document_version.id. | PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_advisor_review_advisor_assignment_id_thesis_member_id_version_no | ck_advisor_review_version_positive | Số version tăng dần. | PII | Physical metadata 20260920_0001 |
| attitude | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của advisor_review. | PII | Physical metadata 20260920_0001 |
| content_response | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của advisor_review. | PII | Physical metadata 20260920_0001 |
| presentation | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của advisor_review. | PII | Physical metadata 20260920_0001 |
| defense_recommendation | VARCHAR(20) | NOT NULL | — | — | — | — | ck_advisor_review_defense_recommendation | Thuộc tính nghiệp vụ của advisor_review. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | PII | Physical metadata 20260920_0001 |

### reviewer_review

**Mục đích:** Phiếu nhận xét GVPB theo SV và document version.
**Trace:** REQ-EVAL-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reviewer_assignment_id | UUID | NOT NULL | — | — | reviewer_assignment.id | uq_reviewer_review_reviewer_assignment_id_thesis_member_id_version_no | — | Tham chiếu reviewer_assignment.id. | PII | Physical metadata 20260920_0001 |
| thesis_member_id | UUID | NOT NULL | — | — | thesis_member.id | uq_reviewer_review_reviewer_assignment_id_thesis_member_id_version_no | — | Tham chiếu thesis_member.id. | PII | Physical metadata 20260920_0001 |
| document_version_id | UUID | NOT NULL | — | — | document_version.id | — | — | Tham chiếu document_version.id. | PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_reviewer_review_reviewer_assignment_id_thesis_member_id_version_no | ck_reviewer_review_version_positive | Số version tăng dần. | PII | Physical metadata 20260920_0001 |
| presentation | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của reviewer_review. | PII | Physical metadata 20260920_0001 |
| research_quality | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của reviewer_review. | PII | Physical metadata 20260920_0001 |
| contribution | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của reviewer_review. | PII | Physical metadata 20260920_0001 |
| questions | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của reviewer_review. | PII | Physical metadata 20260920_0001 |
| overall | TEXT | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của reviewer_review. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | PII | Physical metadata 20260920_0001 |

### rubric_template

**Mục đích:** Phiên bản rubric theo Mẫu 6/policy.
**Trace:** REQ-EVAL-003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| code | VARCHAR(50) | NOT NULL | — | — | — | uq_rubric_template_code_version_no | — | Mã nghiệp vụ trong scope tương ứng. | PII | Physical metadata 20260920_0001 |
| name | VARCHAR(255) | NOT NULL | — | — | — | — | — | Tên hiển thị. | NON_PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_rubric_template_code_version_no | ck_rubric_template_version_positive | Số version tăng dần. | NON_PII | Physical metadata 20260920_0001 |
| source_ref | VARCHAR(500) | NOT NULL | — | — | — | — | — | Tham chiếu văn bản/minh chứng. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_rubric_template_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### rubric_criterion

**Mục đích:** Hierarchy Mẫu 6: ba nhóm 2/4/4, 12 tiêu chí con và mục thưởng tối đa 1; tổng phiếu tối đa 10.
**Trace:** REQ-EVAL-003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rubric_template_id | UUID | NOT NULL | — | — | rubric_template.id | uq_rubric_criterion_rubric_template_id_code, uq_rubric_criterion_rubric_template_id_order_no | — | Tham chiếu rubric_template.id. | NON_PII | Physical metadata 20260920_0001 |
| parent_id | UUID | NULL | — | — | rubric_criterion.id | — | ck_rubric_criterion_not_self_parent | Nhóm cha của tiêu chí con; nhóm 1/2/3 và mục thưởng có NULL. | NON_PII | SRC-MAU-06; physical metadata 20260920_0001 |
| code | VARCHAR(50) | NOT NULL | — | — | — | uq_rubric_criterion_rubric_template_id_code | — | Mã nghiệp vụ trong scope tương ứng. | NON_PII | Physical metadata 20260920_0001 |
| label | VARCHAR(500) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của rubric_criterion. | NON_PII | Physical metadata 20260920_0001 |
| max_points | NUMERIC(4, 2) | NOT NULL | — | — | — | — | ck_rubric_criterion_bonus_max, ck_rubric_criterion_max_points | Điểm tối đa của nhóm hoặc tiêu chí; nhóm chỉ tổng hợp, không cộng thêm vào phiếu. | NON_PII | Physical metadata 20260920_0001 |
| criterion_type | VARCHAR(20) | NOT NULL | NORMAL | — | — | — | ck_rubric_criterion_bonus_max, ck_rubric_criterion_criterion_type | GROUP = nhóm; NORMAL = tiêu chí con; BONUS = điểm thưởng. | NON_PII | Physical metadata 20260920_0001 |
| order_no | INTEGER | NOT NULL | — | — | — | uq_rubric_criterion_rubric_template_id_order_no | ck_rubric_criterion_order_positive | Thuộc tính nghiệp vụ của rubric_criterion. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### rubric_assignment

**Mục đích:** Gắn rubric cho round hoặc session.
**Trace:** REQ-EVAL-003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rubric_template_id | UUID | NOT NULL | — | — | rubric_template.id | — | — | Tham chiếu rubric_template.id. | NON_PII | Physical metadata 20260920_0001 |
| round_id | UUID | NULL | — | — | thesis_round.id | — | ck_rubric_assignment_exactly_one_scope | Tham chiếu thesis_round.id. | NON_PII | Physical metadata 20260920_0001 |
| session_id | UUID | NULL | — | — | defense_session.id | — | ck_rubric_assignment_exactly_one_scope | Tham chiếu defense_session.id. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | ACTIVE | — | — | — | ck_rubric_assignment_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### bonus_evidence

**Mục đích:** Minh chứng điểm thưởng của từng SV.
**Trace:** REQ-EVAL-003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_member_id | UUID | NOT NULL | — | — | thesis_member.id | — | — | Tham chiếu thesis_member.id. | PII | Physical metadata 20260920_0001 |
| evidence_type | VARCHAR(100) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của bonus_evidence. | PII | Physical metadata 20260920_0001 |
| reference | VARCHAR(500) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của bonus_evidence. | PII | Physical metadata 20260920_0001 |
| stored_file_id | UUID | NULL | — | — | stored_file.id | — | — | Tham chiếu stored_file.id. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### evaluation

**Mục đích:** Phiếu của một evaluator cho một SV trong phiên.
**Trace:** REQ-EVAL-002..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session_id | UUID | NOT NULL | — | — | defense_session.id | uq_evaluation_session_id_evaluator_member_id_thesis_member_id | — | Tham chiếu defense_session.id. | PII | Physical metadata 20260920_0001 |
| evaluator_member_id | UUID | NOT NULL | — | — | council_member.id | uq_evaluation_session_id_evaluator_member_id_thesis_member_id | — | Tham chiếu council_member.id. | PII | Physical metadata 20260920_0001 |
| thesis_member_id | UUID | NOT NULL | — | — | thesis_member.id | uq_evaluation_session_id_evaluator_member_id_thesis_member_id | — | Tham chiếu thesis_member.id. | PII | Physical metadata 20260920_0001 |
| rubric_assignment_id | UUID | NOT NULL | — | — | rubric_assignment.id | — | — | Tham chiếu rubric_assignment.id. | PII | Physical metadata 20260920_0001 |
| total_points | NUMERIC(4, 2) | NOT NULL | 0 | — | — | — | ck_evaluation_bonus_within_total, ck_evaluation_total_points | Thuộc tính nghiệp vụ của evaluation. | PII | Physical metadata 20260920_0001 |
| bonus_points | NUMERIC(4, 2) | NOT NULL | 0 | — | — | — | ck_evaluation_bonus_points, ck_evaluation_bonus_within_total | Thuộc tính nghiệp vụ của evaluation. | PII | Physical metadata 20260920_0001 |
| status | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_evaluation_status | Trạng thái lifecycle. | PII | Physical metadata 20260920_0001 |
| submitted_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Thời điểm submit. | PII | Physical metadata 20260920_0001 |
| correction_reason | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của evaluation. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | PII | Physical metadata 20260920_0001 |

### evaluation_item

**Mục đích:** Điểm từng criterion trong phiếu.
**Trace:** REQ-EVAL-002..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| evaluation_id | UUID | NOT NULL | — | — | evaluation.id | uq_evaluation_item_evaluation_id_criterion_id | — | Tham chiếu evaluation.id. | PII | Physical metadata 20260920_0001 |
| criterion_id | UUID | NOT NULL | — | — | rubric_criterion.id | uq_evaluation_item_evaluation_id_criterion_id | — | Tham chiếu rubric_criterion.id. | PII | Physical metadata 20260920_0001 |
| points | NUMERIC(4, 2) | NOT NULL | — | — | — | — | ck_evaluation_item_points_nonnegative | Thuộc tính nghiệp vụ của evaluation_item. | PII | Physical metadata 20260920_0001 |
| comment | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của evaluation_item. | PII | Physical metadata 20260920_0001 |
| bonus_evidence_id | UUID | NULL | — | — | bonus_evidence.id | — | — | Tham chiếu bonus_evidence.id. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### final_result

**Mục đích:** Snapshot điểm tổng hợp riêng từng SV.
**Trace:** REQ-EVAL-002..003

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session_id | UUID | NOT NULL | — | — | defense_session.id | uq_final_result_session_id_thesis_member_id | — | Tham chiếu defense_session.id. | PII | Physical metadata 20260920_0001 |
| thesis_member_id | UUID | NOT NULL | — | — | thesis_member.id | uq_final_result_session_id_thesis_member_id | — | Tham chiếu thesis_member.id. | PII | Physical metadata 20260920_0001 |
| scorer_count | INTEGER | NOT NULL | — | — | — | — | ck_final_result_scorer_count | Thuộc tính nghiệp vụ của final_result. | PII | Physical metadata 20260920_0001 |
| average_score | NUMERIC(4, 2) | NOT NULL | — | — | — | — | ck_final_result_average_score | Thuộc tính nghiệp vụ của final_result. | PII | Physical metadata 20260920_0001 |
| bonus_average | NUMERIC(4, 2) | NOT NULL | — | — | — | — | ck_final_result_bonus_average | Thuộc tính nghiệp vụ của final_result. | PII | Physical metadata 20260920_0001 |
| final_score | NUMERIC(3, 1) | NOT NULL | — | — | — | — | ck_final_result_final_score | Thuộc tính nghiệp vụ của final_result. | PII | Physical metadata 20260920_0001 |
| calculation_version | INTEGER | NOT NULL | — | — | — | — | ck_final_result_calculation_version | Thuộc tính nghiệp vụ của final_result. | PII | Physical metadata 20260920_0001 |
| calculated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

## Biên bản, kho, index và audit

### council_minute

**Mục đích:** Aggregate biên bản của session.
**Trace:** REQ-MIN-001..002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session_id | UUID | NOT NULL | — | — | defense_session.id | uq_council_minute_session_id_minute_no | — | Tham chiếu defense_session.id. | NON_PII | Physical metadata 20260920_0001 |
| minute_no | VARCHAR(100) | NOT NULL | — | — | — | uq_council_minute_session_id_minute_no | — | Thuộc tính nghiệp vụ của council_minute. | NON_PII | Physical metadata 20260920_0001 |
| current_version_no | INTEGER | NOT NULL | 0 | — | — | — | — | Thuộc tính nghiệp vụ của council_minute. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_council_minute_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| printed_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| signed_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### minute_version

**Mục đích:** Version/void/replacement/print/sign của biên bản.
**Trace:** REQ-MIN-001..002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| minute_id | UUID | NOT NULL | — | — | council_minute.id | uq_minute_version_minute_id_version_no | — | Tham chiếu council_minute.id. | NON_PII | Physical metadata 20260920_0001 |
| version_no | INTEGER | NOT NULL | — | — | — | uq_minute_version_minute_id_version_no | ck_minute_version_version_positive | Số version tăng dần. | NON_PII | Physical metadata 20260920_0001 |
| stored_file_id | UUID | NOT NULL | — | — | stored_file.id | — | — | Tham chiếu stored_file.id. | NON_PII | Physical metadata 20260920_0001 |
| generated_by | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | DRAFT | — | — | — | ck_minute_version_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| replacement_for_id | UUID | NULL | — | — | minute_version.id | — | ck_minute_version_not_self_replacement | Tham chiếu minute_version.id. | NON_PII | Physical metadata 20260920_0001 |
| void_reason | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của minute_version. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | ck_minute_version_not_self_replacement | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### minute_signature

**Mục đích:** Chữ ký/xác nhận Chủ tịch trên version.
**Trace:** REQ-MIN-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| minute_version_id | UUID | NOT NULL | — | — | minute_version.id | uq_minute_signature_minute_version_id_signer_member_id | — | Tham chiếu minute_version.id. | PII | Physical metadata 20260920_0001 |
| signer_member_id | UUID | NOT NULL | — | — | council_member.id | uq_minute_signature_minute_version_id_signer_member_id | — | Tham chiếu council_member.id. | PII | Physical metadata 20260920_0001 |
| signed_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Physical metadata 20260920_0001 |
| signature_ref | VARCHAR(500) | NULL | — | — | — | — | — | Tham chiếu văn bản/minh chứng. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### repository_item

**Mục đích:** Item kho có thể là KLTN đang quản lý, tài liệu học thuật nhập ngoài hoặc nguồn chính thức được phép dùng.
**Trace:** REQ-REPO-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_id | UUID | NULL | — | — | thesis.id | — | — | Tham chiếu thesis.id. | NON_PII | Physical metadata 20260920_0001 |
| published_document_version_id | UUID | NULL | — | — | document_version.id | uq_repository_item_published_document_version_id | — | Tham chiếu document_version.id. | NON_PII | Physical metadata 20260920_0001 |
| stored_file_id | UUID | NULL | — | — | stored_file.id | — | ck_repository_item_has_source_reference | Tệp lưu cục bộ nếu nguồn imported/official đã được cho phép; không commit binary. | SENSITIVE | Migration 0003 |
| origin_type | VARCHAR(30) | NOT NULL | MANAGED_THESIS | — | — | — | ck_repository_item_origin_type, ck_repository_item_origin_source_consistency | MANAGED_THESIS/IMPORTED_DOCUMENT/OFFICIAL_SOURCE; quyết định quan hệ Thesis/DocumentVersion hợp lệ. | NON_PII | Migration 0003 |
| external_source_id | VARCHAR(200) | NULL | — | — | — | uq_repository_item_external_source_id | — | ID nguồn ổn định từ manifest để upsert và rebuild index, không phải khóa Thesis. | NON_PII | Migration 0004 |
| source_url | VARCHAR(1000) | NULL | — | — | — | — | ck_repository_item_source_url_https | Link HTTPS tới nguồn được phép; không phải link tải file nội bộ. | SENSITIVE | Migration 0004 |
| source_ref | VARCHAR(500) | NULL | — | — | — | — | ck_repository_item_has_source_reference | Mã nguồn/đường dẫn tham chiếu; không dùng như URL tải công khai. | SENSITIVE | Migration 0003 |
| provenance | TEXT | NULL | — | — | — | — | — | Nguồn gốc, giấy phép, bối cảnh nhập; app kiểm tra trước khi publish. | SENSITIVE | Migration 0003 |
| source_version | VARCHAR(100) | NULL | — | — | — | — | — | Phiên bản tài liệu gốc để citation/index có thể truy hồi. | NON_PII | Migration 0003 |
| title | VARCHAR(500) | NOT NULL | — | — | — | — | — | Tiêu đề/tên nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| abstract | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của repository_item. | NON_PII | Physical metadata 20260920_0001 |
| keywords | JSONB | NOT NULL | application | — | — | — | — | Dữ liệu cấu hình/danh sách có schema ở application. | NON_PII | Physical metadata 20260920_0001 |
| source_type | VARCHAR(50) | NOT NULL | THESIS | — | — | ix_repository_item_source_type_visibility | ck_repository_item_source_type | THESIS/CAPSTONE_PROJECT/TERM_PROJECT/COURSE_PROJECT/REGULATION/FORM/GUIDELINE/SYNTHETIC_TEST. | NON_PII | Migration 0003; không trộn loại nguồn. |
| visibility | VARCHAR(20) | NOT NULL | INTERNAL | — | — | — | ck_repository_item_visibility | Thuộc tính nghiệp vụ của repository_item. | NON_PII | Physical metadata 20260920_0001 |
| published_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| revoked_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |
| row_version | INTEGER | NOT NULL | 1 | — | — | — | — | Version optimistic concurrency. | NON_PII | Physical metadata 20260920_0001 |

### search_index_metadata

**Mục đích:** Trạng thái index dẫn xuất, không phải source of truth.
**Trace:** REQ-REPO-001, REQ-AI-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| repository_item_id | UUID | NOT NULL | — | — | repository_item.id | uq_search_index_metadata_repository_item_id_index_name_index_version | — | Tham chiếu repository_item.id. | NON_PII | Physical metadata 20260920_0001 |
| document_version_id | UUID | NULL | — | — | document_version.id | — | — | Tùy chọn với nguồn imported/official; repository_item_id luôn bắt buộc. | NON_PII | Migration 0003 |
| index_name | VARCHAR(100) | NOT NULL | — | — | — | uq_search_index_metadata_repository_item_id_index_name_index_version | — | Thuộc tính nghiệp vụ của search_index_metadata. | NON_PII | Physical metadata 20260920_0001 |
| index_version | VARCHAR(100) | NOT NULL | — | — | — | uq_search_index_metadata_repository_item_id_index_name_index_version | — | Thuộc tính nghiệp vụ của search_index_metadata. | NON_PII | Physical metadata 20260920_0001 |
| embedding_model | VARCHAR(150) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của search_index_metadata. | NON_PII | Physical metadata 20260920_0001 |
| chunking_version | VARCHAR(100) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của search_index_metadata. | NON_PII | Physical metadata 20260920_0001 |
| external_point_namespace | VARCHAR(200) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của search_index_metadata. | NON_PII | Physical metadata 20260920_0001 |
| state | VARCHAR(20) | NOT NULL | PENDING | — | — | — | ck_search_index_metadata_state | Trạng thái lifecycle của aggregate/entity. | NON_PII | Physical metadata 20260920_0001 |
| indexed_at | TIMESTAMP WITH TIME ZONE | NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | NON_PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | NON_PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | NON_PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | NON_PII | Physical metadata 20260920_0001 |

### retrieval_audit

**Mục đích:** Audit retrieval tối thiểu, không lưu raw prompt/chunk.
**Trace:** REQ-AI-002

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| user_id | UUID | NOT NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Physical metadata 20260920_0001 |
| question_hash | VARCHAR(64) | NOT NULL | — | — | — | — | — | Hash kiểm tra/audit; không phải nội dung thô. | PII | Physical metadata 20260920_0001 |
| authorized_scope_hash | VARCHAR(64) | NOT NULL | — | — | — | — | — | Hash kiểm tra/audit; không phải nội dung thô. | PII | Physical metadata 20260920_0001 |
| retrieved_item_count | INTEGER | NOT NULL | 0 | — | — | — | — | Thuộc tính nghiệp vụ của retrieval_audit. | PII | Physical metadata 20260920_0001 |
| provider | VARCHAR(100) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của retrieval_audit. | PII | Physical metadata 20260920_0001 |
| model_version | VARCHAR(100) | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của retrieval_audit. | PII | Physical metadata 20260920_0001 |
| outcome | VARCHAR(30) | NOT NULL | — | — | — | — | ck_retrieval_audit_outcome | Thuộc tính nghiệp vụ của retrieval_audit. | PII | Physical metadata 20260920_0001 |
| correlation_id | UUID | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của retrieval_audit. | PII | Physical metadata 20260920_0001 |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Physical metadata 20260920_0001 |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm tạo record. | PII | Physical metadata 20260920_0001 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | now() | — | — | — | — | Thời điểm cập nhật gần nhất. | PII | Physical metadata 20260920_0001 |

### audit_event

**Mục đích:** Dấu vết quyết định/mutation nhạy cảm.
**Trace:** BR-AUDIT-001

| Field | PostgreSQL type | Null? | Default | PK | FK | Unique/index | Check | Meaning | PII | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| actor_id | UUID | NULL | — | — | user_account.id | — | — | Tham chiếu user_account.id. | PII | Append-only |
| action | VARCHAR(100) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của audit_event. | PII | Append-only |
| resource_type | VARCHAR(100) | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của audit_event. | PII | Append-only |
| resource_id | UUID | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của audit_event. | PII | Append-only |
| before_hash | VARCHAR(64) | NULL | — | — | — | — | — | Hash kiểm tra/audit; không phải nội dung thô. | PII | Append-only |
| after_hash | VARCHAR(64) | NULL | — | — | — | — | — | Hash kiểm tra/audit; không phải nội dung thô. | PII | Append-only |
| reason | TEXT | NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của audit_event. | PII | Append-only |
| occurred_at | TIMESTAMP WITH TIME ZONE | NOT NULL | — | — | — | — | — | Mốc thời gian nghiệp vụ. | PII | Append-only |
| correlation_id | UUID | NOT NULL | — | — | — | — | — | Thuộc tính nghiệp vụ của audit_event. | PII | Append-only |
| id | UUID | NOT NULL | application | Có | — | — | — | Khóa chính UUID. | PII | Append-only |

## Kiểm soát đồng bộ

- Tổng số bảng: 62.
- Tổng số field: 617 (sau migration 20260925_0007).
- Migration và model là nguồn physical; thay đổi schema phải cập nhật migration mới và tái sinh tài liệu.
- Không có field plagiarism verdict; threshold similarity không hard-code 90%.
