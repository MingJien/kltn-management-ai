# Ma trận truy vết yêu cầu → thiết kế → kiểm thử

| Trace | Requirement / UC | Entity chính | API | Màn hình | Kiểm thử chấp nhận | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| TRC-01 | REQ-AUTH-001..003 / UC-AUTH-001 | UserAccount, PositionAssignment | `GET /me` | SCR-01 | Base role hoặc Admin đơn lẻ không thực hiện action TBM/HĐ. | CONFIRMED/DERIVED |
| TRC-02 | REQ-ROUND-001 / UC-ROUND-001 | AcademicYear, ThesisRound, RoundPolicy | `/academic-years`, `/thesis-rounds` | SCR-02 | MAIN/SUPPLEMENTARY chung mô hình; ngày mẫu không tự nhập. | CONFIRMED_PROJECT_DECISION |
| TRC-03 | REQ-ELIG-001..002 / UC-ELIG-001 | EligibilitySnapshot/Exception | `/rounds/{id}/eligibility-snapshots` | SCR-03 | Người Khoa được giao đối chiếu GPA/tín chỉ với nguồn Phòng Đào tạo và xác nhận kết quả; API chỉ mở đăng ký cho snapshot CONFIRMED. Chưa có runtime tự tính điều kiện từ GPA/tín chỉ. | CONFIRMED |
| TRC-04 | REQ-EXP-001 / UC-EXP-001 | LecturerExpertise/Evidence | `/lecturer-expertise` | SCR-04 | Hồ sơ tự khai có nhãn; TBM đúng Bộ môn kiểm chứng, tự khai của TBM do Trưởng khoa/người được giao kiểm. | CONFIRMED_PROJECT_DESIGN |
| TRC-05 | REQ-TOPIC-001..003 / UC-TOPIC-001..003 | Topic, TitleVersion, TopicRequirement | `/topics`, `/topics/{id}/requirements` | SCR-04 | TBM chỉnh tên có history; preferred GPA không auto reject. | CONFIRMED |
| TRC-06 | REQ-REG-001..006 / UC-REG-001/002 | TopicRegistration, RegistrationMember | `/topic-registrations` | SCR-05 | Một đăng ký hoạt động/SV/đợt; mỗi SV tự tham gia; bổ sung trước hạn/chỉ tiêu thì GV xét lại; không nguyện vọng 2. | CONFIRMED_PROJECT_DECISION |
| TRC-07 | REQ-REG-003..004 / UC-ASSIGN-001, UC-WORK-001 | AdvisorAssignment, MemberWorkAssignment | `/department-finalization`, `/work-assignments` | SCR-05/06 | GVHD accept/reject; TBM finalize; work allocation phải được GVHD duyệt. | CONFIRMED |
| TRC-08 | REQ-PROP-001..003 / UC-PROP-001..004 | Proposal/Version/Review/Signature | `/proposal-versions`, `/proposals/...` | SCR-07 | Resubmit tạo version; TBM chốt trước Trưởng khoa ký; có bản in. | CONFIRMED_PROJECT_DECISION |
| TRC-09 | REQ-PROG-001..002 / UC-PROG-001/002 | Milestone, ProgressReport/Review | `/milestones`, `/progress-reports` | SCR-08 | GVHD xác nhận; lịch cấu hình, không hard-code. | CONFIRMED_PROJECT_DECISION; ngày theo round |
| TRC-10 | REQ-CHANGE-001..003 / UC-CHANGE-001, UC-EXT-001 | ChangeRequest, ExternalProcedureOutcome | `/change-requests`, `/external-procedure-outcomes` | SCR-08 | Chỉ đổi topic có approval online; rút/gia hạn chỉ record outcome. | CONFIRMED |
| TRC-11 | REQ-DOC-001 / UC-DOC-001 | Document/Version/StoredFile | `/uploads`, `/documents/.../versions` | SCR-09 | Version submit bất biến; file quarantine không được tham chiếu. | DERIVED |
| TRC-12 | REQ-SIM-001..003 / UC-SIM-001 | SimilarityPolicy/Check/Match | `/similarity-checks` | SCR-09 | Không hiển thị cosine thành percent; baseline chỉ advisory; không 90% auto-gate. | CONFIRMED_PROJECT_DESIGN |
| TRC-13 | REQ-COUNCIL-001..003 / UC-COUNCIL-001, UC-SESSION-001 | Council/Member/Session/SessionThesis/Attendance | `/councils`, `/defense-sessions/...` | SCR-10/11 | Import đúng 5 role; không auto Chair; quorum theo QĐ; session có nhiều thesis. | CONFIRMED |
| TRC-14 | REQ-DEF-001 / UC-DEF-001 | DefenseEligibilityCheck, AdvisorReview | `/defense-eligibility-checks` | SCR-11/12 | Điều kiện Trường đầy đủ; tiêu chí Khoa chỉ khi policy có version. | CONFIRMED_PROJECT_DECISION; chỉ điều kiện Trường đợt này |
| TRC-15 | REQ-EVAL-001 / UC-EVAL-001 | AdvisorReview, ReviewerReview | `/advisor-reviews`, `/reviewer-reviews` | SCR-12 | Chỉ assignment đúng lập Mẫu 7/8; version hóa. | CONFIRMED |
| TRC-16 | REQ-EVAL-002..003 / UC-RUBRIC-001, UC-EVAL-002/003 | Rubric, Evaluation/Item, BonusEvidence, FinalResult | `/evaluations`, `/final-results` | SCR-13 | Chấm riêng từng SV; evaluator chỉ sửa điểm mình; avg 1 số; bonus≤1; final≤10. | CONFIRMED |
| TRC-17 | REQ-MIN-001..002 / UC-MIN-001/002 | CouncilMinute/Version/Signature | `/minutes/...` | SCR-14 | Void/replacement sau in nếu giấy chưa ai ký; từ chữ ký đầu khóa, đủ Chair + Secretary mới SIGNED. | CONFIRMED_PROJECT_DESIGN |
| TRC-18 | REQ-REPO-001 / UC-REPO-001 | RepositoryItem, SearchIndexMetadata | `/repository/documents` | SCR-15 | Search/download filter quyền; revoke chặn ngay và deindex. | CONFIRMED/DERIVED |
| TRC-19 | REQ-AI-001..002 / UC-AI-001 | SearchIndexMetadata, RetrievalAudit | `/ai/chat` | SCR-16 | Authorization trước retrieval; chunks tối thiểu; Gemini backend-only; chỉ citation/link. | CONFIRMED_PROJECT_DECISION |
| TRC-20 | REQ-RPT-001 / UC-RPT-001 | Read models từ Eligibility/Progress/Council/FinalResult | `/reports/*` | SCR-15 | Chỉ xuất trường/scope được phép; không có report vô nguồn. | DERIVED |

## Kiểm soát phần không có căn cứ

- `RoundPolicy`, storage abstraction, outbox/reindex, optimistic concurrency và AuditEvent là `PROPOSED` kỹ thuật để thực thi requirement; không phải quy định Trường.
- Không có entity/API/screen cho auto Chair, plagiarism verdict, Admin business override, online approval rút/gia hạn hoặc sửa hậu ký.
- Các câu hỏi nghiệp vụ trong phạm vi thiết kế đã được phản ánh trong yêu cầu và quy tắc hiện hành. Trước khi vận hành hồ sơ thật, cần cấu hình người được giao xác nhận theo từng đợt và version policy/rubric áp dụng; baseline rubric của dự án đã chọn Mẫu 6.

## Truy vết bổ sung từ quyết định 25/09/2026

| Source → Requirement → Rule | Use case / quyền / state | Entity/column | API → màn hình | Test / trạng thái |
| --- | --- | --- | --- | --- |
| SRC-PROJECT-DEC-20260925 → REQ-REG-005..006 → BR-REG-005 | UC-REG-001/002; mỗi SV tự tham gia trước hạn, GV xét lại khi bổ sung | topic_registration, registration_member; unique active student/round | POST /topic-registrations + submit → SCR-05 | Kiểm thử API và browser trên dữ liệu giả cho hai nhánh đề tài |
| SRC-PROJECT-DEC-20260925 → REQ-REG-003 → BR-REG-003 | UC-ASSIGN-001; GV đề xuất quyết định; TBM position đúng scope finalize | Thesis, ThesisMember, AdvisorAssignment, row_version | POST lecturer-decision, department-finalization → SCR-05 /registrations, /theses/:id | integration test PASS, một transaction |
| SRC-PROJECT-DEC-20260925 → REQ-ROUND-002 → BR-ROUND-002 | UC-ROUND-001; KLTN_COORDINATOR theo round khác Secretary | ResourceAssignment.round_id/assignment_type; CouncilMember.role_code | context/round milestones thiết kế → SCR-02/08 | Design-only; ngày theo round |
| SRC-MAU-09 + SRC-PROJECT-DEC-20260925 → REQ-MIN-001/REQ-EXPORT-001 → BR-MIN-002/BR-EXPORT-001 | UC-MIN-001/002; Secretary + Chair, PRINTED → SIGNED khi đủ hai | MinuteSignature, CouncilMinute, StoredFile | design-only signature/export → SCR-14 | DB-37 PASS cho 2 row; role service/export chưa PASS, BLOCKED_SOURCE_TEMPLATE |
| SRC-PROJECT-DEC-20260925 → REQ-CORPUS-001/002 → BR-CORPUS-001/002 | UC-REPO-001; nguồn/visibility/scope | RepositoryItem.origin_type/source_type/external_source_id/source_url/provenance; SearchIndexMetadata | repository thiết kế; AI similar-topics → SCR-15 | DB-27..39, AI pytest PASS; retrieval mẫu giả |
| SRC-PROJECT-DEC-20260925 → REQ-SIM-003/REQ-AI-003 → BR-SIM-004 | UC-SIM-001/UC-AI-001; advisory/no upload block, retrieval-only | SimilarityCheck/Match, RepositoryItem | POST /ai/similar-topics, /ai/chat → SCR-15 | local Qdrant/embedding smoke PASS; không có metric chất lượng được kiểm trên corpus thật; baseline advisory |
| SRC-PROJECT-DEC-20260925 → REQ-EXT-001 → BR-EXT-001 | UC-EXT-001; HTTPS allowlist | config only, không cần table | GET /external-resources design-only → SCR-16 | Chưa có URL được duyệt |
