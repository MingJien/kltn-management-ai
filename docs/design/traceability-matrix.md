# Ma trận truy vết Tuần 1 → Tuần 2

| Trace | Requirement / UC | Entity chính | API | Màn hình | Kiểm thử chấp nhận | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| TRC-01 | REQ-AUTH-001..003 / UC-AUTH-001 | UserAccount, PositionAssignment | `GET /me` | SCR-01 | Base role hoặc Admin đơn lẻ không thực hiện action TBM/HĐ. | CONFIRMED/DERIVED |
| TRC-02 | REQ-ROUND-001 / UC-ROUND-001 | AcademicYear, ThesisRound, RoundPolicy | `/academic-years`, `/thesis-rounds` | SCR-02 | MAIN/SUPPLEMENTARY chung mô hình; ngày mẫu không tự nhập. | CONFIRMED_PROJECT_DECISION |
| TRC-03 | REQ-ELIG-001..002 / UC-ELIG-001 | EligibilitySnapshot/Exception | `/rounds/{id}/eligibility-snapshots` | SCR-03 | GPA 2,49 hoặc credit <70% bị chặn nếu không có ngoại lệ; snapshot có nguồn. | CONFIRMED |
| TRC-04 | REQ-EXP-001 / UC-EXP-001 | LecturerExpertise/Evidence | `/lecturer-expertise` | SCR-04 | Hồ sơ tự khai có nhãn; verify chỉ bật khi policy. | OPEN-01/PROPOSED |
| TRC-05 | REQ-TOPIC-001..003 / UC-TOPIC-001..003 | Topic, TitleVersion, TopicRequirement | `/topics`, `/topics/{id}/requirements` | SCR-04 | TBM chỉnh tên có history; preferred GPA không auto reject. | CONFIRMED |
| TRC-06 | REQ-REG-001..005 / UC-REG-001/002 | TopicRegistration, RegistrationMember | `/topic-registrations` | SCR-05 | Một active registration/SV/round; 1–3 SV; không nguyện vọng 2; không ghép hậu đăng ký mặc định. | CONFIRMED + OPEN-02 |
| TRC-07 | REQ-REG-003..004 / UC-ASSIGN-001, UC-WORK-001 | AdvisorAssignment, MemberWorkAssignment | `/department-finalization`, `/work-assignments` | SCR-05/06 | GVHD accept/reject; TBM finalize; work allocation phải được GVHD duyệt. | CONFIRMED |
| TRC-08 | REQ-PROP-001..003 / UC-PROP-001..004 | Proposal/Version/Review/Signature | `/proposal-versions`, `/proposals/...` | SCR-07 | Resubmit tạo version; TBM chốt trước Trưởng khoa ký; có bản in. | CONFIRMED_PROJECT_DECISION |
| TRC-09 | REQ-PROG-001..002 / UC-PROG-001/002 | Milestone, ProgressReport/Review | `/milestones`, `/progress-reports` | SCR-08 | GVHD xác nhận; lịch cấu hình, không hard-code. | CONFIRMED + OPEN-03/06 |
| TRC-10 | REQ-CHANGE-001..003 / UC-CHANGE-001, UC-EXT-001 | ChangeRequest, ExternalProcedureOutcome | `/change-requests`, `/external-procedure-outcomes` | SCR-08 | Chỉ đổi topic có approval online; rút/gia hạn chỉ record outcome. | CONFIRMED |
| TRC-11 | REQ-DOC-001 / UC-DOC-001 | Document/Version/StoredFile | `/uploads`, `/documents/.../versions` | SCR-09 | Version submit bất biến; file quarantine không được tham chiếu. | DERIVED |
| TRC-12 | REQ-SIM-001..003 / UC-SIM-001 | SimilarityPolicy/Check/Match | `/similarity-checks` | SCR-09 | Không hiển thị cosine thành percent; chưa có metric thì advisory; high chỉ nói tương đồng cao. | PROJECT_DECISION + OPEN-05 |
| TRC-13 | REQ-COUNCIL-001..003 / UC-COUNCIL-001, UC-SESSION-001 | Council/Member/Session/SessionThesis/Attendance | `/councils`, `/defense-sessions/...` | SCR-10/11 | Import đúng 5 role; không auto Chair; quorum theo QĐ; session có nhiều thesis. | CONFIRMED |
| TRC-14 | REQ-DEF-001 / UC-DEF-001 | DefenseEligibilityCheck, AdvisorReview | `/defense-eligibility-checks` | SCR-11/12 | Điều kiện Trường đầy đủ; tiêu chí Khoa chỉ khi policy có version. | CONFIRMED + OPEN-04 |
| TRC-15 | REQ-EVAL-001 / UC-EVAL-001 | AdvisorReview, ReviewerReview | `/advisor-reviews`, `/reviewer-reviews` | SCR-12 | Chỉ assignment đúng lập Mẫu 7/8; version hóa. | CONFIRMED |
| TRC-16 | REQ-EVAL-002..003 / UC-RUBRIC-001, UC-EVAL-002/003 | Rubric, Evaluation/Item, BonusEvidence, FinalResult | `/evaluations`, `/final-results` | SCR-13 | Chấm riêng từng SV; evaluator chỉ sửa điểm mình; avg 1 số; bonus≤1; final≤10. | CONFIRMED |
| TRC-17 | REQ-MIN-001..002 / UC-MIN-001/002 | CouncilMinute/Version/Signature | `/minutes/...` | SCR-14 | Void/replacement trước in; Chair ký; sau in/ký không endpoint sửa. | CONFIRMED + OPEN-07/08 |
| TRC-18 | REQ-REPO-001 / UC-REPO-001 | RepositoryItem, SearchIndexMetadata | `/repository/documents` | SCR-15 | Search/download filter quyền; revoke chặn ngay và deindex. | CONFIRMED/DERIVED |
| TRC-19 | REQ-AI-001..002 / UC-AI-001 | SearchIndexMetadata, RetrievalAudit | `/ai/chat` | SCR-16 | Authorization trước retrieval; chunks tối thiểu; Gemini backend-only; chỉ citation/link. | CONFIRMED_PROJECT_DECISION |
| TRC-20 | REQ-RPT-001 / UC-RPT-001 | Read models từ Eligibility/Progress/Council/FinalResult | `/reports/*` | SCR-15 | Chỉ xuất trường/scope được phép; không có report vô nguồn. | DERIVED |

## Kiểm soát phần không có căn cứ

- `RoundPolicy`, storage abstraction, outbox/reindex, optimistic concurrency và AuditEvent là `PROPOSED` kỹ thuật để thực thi requirement; không phải quy định Trường.
- Không có entity/API/screen cho auto Chair, plagiarism verdict, Admin business override, online approval rút/gia hạn hoặc sửa hậu ký.
- OPEN-01..10 đều có safe default trong `open-issues.md`; không cản logical design.
