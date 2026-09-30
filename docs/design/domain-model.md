# Mô hình miền KLTN — NV4 Tuần 2

## Ranh giới

- `UserAccount.baseRole` chỉ nhận `ADMIN`, `LECTURER`, `STUDENT`.
- Quyền hiệu lực = base role + vị trí tổ chức + assignment trên tài nguyên + trạng thái; mặc định từ chối.
- PostgreSQL là nguồn giao dịch chính. File storage giữ bytes; Qdrant là chỉ mục dẫn xuất; Gemini chỉ hỗ trợ trả lời có nguồn.
- Mỗi entity/API/UI bên dưới trỏ về requirement/use case. Thành phần thuần kỹ thuật được ghi `PROPOSED`.

## Aggregate và entity

| Nhóm | Entity | Trách nhiệm | Trace / trạng thái |
| --- | --- | --- | --- |
| Danh tính | UserAccount, StudentProfile, LecturerProfile | Một tài khoản/người; hồ sơ theo base role | REQ-AUTH-001, `DERIVED` schema |
| Tổ chức | Faculty, Department, OrganizationalPosition, PositionAssignment, ResourceAssignment | Scope Bộ môn/Khoa; TBM/Trưởng khoa và quyền tài nguyên theo thời hạn | REQ-AUTH-002, REQ-ELIG-002, `DERIVED` |
| Năm/đợt | AcademicYear, ThesisRound, RoundPolicy | Đợt chính/bổ sung và policy có version | REQ-ROUND-001, `CONFIRMED_PROJECT_DECISION` |
| Điều kiện | EligibilitySnapshot, EligibilityException, DefenseEligibilityCheck | Chụp bằng chứng đăng ký/bảo vệ; ngoại lệ chính thức | REQ-ELIG-001..002, REQ-DEF-001 |
| Chuyên môn | LecturerExpertise, ExpertiseEvidence | Dữ liệu tự khai/version; TBM đúng bộ môn kiểm chứng, hồ sơ TBM do Trưởng khoa/người được giao kiểm | REQ-EXP-001 |
| Đề tài | Topic, TopicTitleVersion, TopicRequirement | Đề xuất, duyệt/chỉnh tên; GPA/kỹ năng/công nghệ/kiến thức mong muốn | REQ-TOPIC-001..003 |
| Đăng ký | TopicRegistration, RegistrationMember | Một topic/SV/round; nhóm 1–3 | REQ-REG-001..006 |
| Thực hiện | Thesis, ThesisMember, MemberWorkAssignment | Hồ sơ KLTN đã chốt; phân công riêng từng SV | REQ-REG-002, REQ-REG-004 |
| Phân công GV | AdvisorAssignment, ReviewerAssignment | GVHD; GVPB đề cương/KLTN theo tài nguyên/thời gian | REQ-REG-003, REQ-PROP-002, REQ-EVAL-001 |
| Đề cương | Proposal, ProposalVersion, ProposalReview, SignatureConfirmation | Version bất biến; review; TBM chốt; Trưởng khoa ký | REQ-PROP-001..003 |
| Tiến độ | ProgressMilestone, ProgressReport, ProgressReview | Mốc cấu hình; báo cáo và nhận xét/xác nhận GVHD | REQ-PROG-001..002 |
| Thay đổi | TopicChangeRequest, ExternalProcedureOutcome | Đổi topic trong hệ thống; rút/gia hạn ghi kết quả ngoài | REQ-CHANGE-001..003 |
| Tài liệu | StoredFile, Document, DocumentVersion | Container và version bất biến | REQ-DOC-001 |
| Tương đồng | SimilarityPolicy, SimilarityCheck, SimilarityMatch | Policy/metric có version; bằng chứng lexical/semantic | REQ-SIM-001..003 |
| Hội đồng | Council, CouncilMember, DefenseSession, SessionThesis, CouncilAttendance | Hội đồng theo quyết định; nhiều phiên/KLTN; attendance/quorum | REQ-COUNCIL-001..003 |
| Nhận xét | AdvisorReview, ReviewerReview | Phiếu Mẫu 7/8 theo assignment/version | REQ-EVAL-001 |
| Chấm điểm | RubricTemplate, RubricCriterion(parent_id), RubricAssignment, Evaluation, EvaluationItem, BonusEvidence, FinalResult | Chấm từng SV; rubric Mẫu 6 gồm ba nhóm 2/4/4 và 12 tiêu chí con, group không cộng lặp; bonus ≤1, tổng phiếu ≤10; trung bình/làm tròn | REQ-EVAL-002..003; baseline Mẫu 6 đã chốt, chấm thật cần runtime và version theo đợt |
| Biên bản | CouncilMinute, MinuteVersion, MinuteSignature | Thư ký lập/version/void và ký; Chủ tịch cùng ký; khóa sau đủ hai chữ ký | REQ-MIN-001..002 |
| Kho/RAG | RepositoryItem, SearchIndexMetadata, RetrievalAudit | Metadata công bố, visibility/index version, retrieval audit | REQ-REPO-001, REQ-AI-001..002 |
| Kiểm soát | AuditEvent | Dấu vết thay đổi nhạy cảm, không chứa body/PII | BR-AUDIT-001, `PROPOSED` control |

## Quan hệ và bất biến

| ID | Bất biến | Cơ chế |
| --- | --- | --- |
| INV-01 | Một người dùng một account; profile khớp base role. | Unique identity subject và check constraint. |
| INV-02 | Một `AcademicYear` có nhiều round; `(year, code)` duy nhất; type `MAIN/SUPPLEMENTARY`. | Unique constraint. |
| INV-03 | `EligibilitySnapshot` giữ nguồn, thời điểm, người xác nhận; không sửa sau chốt. | Append-only/version. |
| INV-04 | `preferredGpa` không tự chặn đăng ký; hard gate chỉ từ RoundPolicy/REQ-ELIG. | Domain service tách preference/policy. |
| INV-05 | Mỗi SV, kể cả thành viên nhóm không phải người tạo, chỉ thuộc tối đa một registration hoạt động/round; một registration chỉ một topic. | `registration_member.round_id` phải khớp registration; partial unique `(student_id, round_id)` với state hoạt động + transaction. |
| INV-06 | Mỗi topic/round chỉ hình thành tối đa một Thesis; Thesis có 1–3 member, tối đa một coordinator; tổng thành viên được accept/finalize không vượt capacity tối đa 3; không thêm/đổi thành viên sau SUBMITTED theo quyết định hiện tại. | Unique `(round_id, topic_id)` trên Thesis + khóa topic khi finalize + count guard. |
| INV-07 | Mỗi ThesisMember có ít nhất một MemberWorkAssignment version trước đánh giá cá nhân. | Readiness guard. |
| INV-08 | Proposal/Document version đã submit bất biến; review/check trỏ đúng version. | Content hash + append-only version. |
| INV-09 | SimilarityCheck ghi policy/model/index/corpus snapshot; cosine không là phần trăm tài liệu. | Required provenance fields. |
| INV-10 | CouncilMember phải đúng 5 role theo quyết định; không tự sinh Chair. | Import validation. |
| INV-11 | Một session chứa nhiều KLTN qua SessionThesis; attendance theo member/session. | Join table + unique constraint. |
| INV-12 | Không mở chấm nếu vắng >2/5 hoặc vắng Chair/Secretary. | Quorum domain guard từ QĐ 2919. |
| INV-13 | Evaluation duy nhất theo session × evaluator × thesis member; chỉ evaluator sửa trước lock. | Unique + authorization/state guard. |
| INV-14 | Mỗi Evaluation total đã gồm criterion thưởng ≤1 và bị chặn ở 10. FinalResult = trung bình total của phiếu hợp lệ/người hiện diện, làm tròn 1 chữ số; không cộng thưởng lần hai. | Calculation service có version; lưu `bonusAverage` chỉ để giải thích. |
| INV-15 | MinuteVersion sai sau in nhưng trước chữ ký đầu được VOID và replacement trỏ bản cũ; từ chữ ký đầu khóa điểm/nội dung. | State guard; không có post-sign bypass. |
| INV-16 | Repository/Qdrant chỉ chứa version được phép; visibility revoke kích hoạt deindex. | Transactional outbox/reindex job `PROPOSED`. |

## Không mô hình hóa thành sự thật

- Không có base role `DEPARTMENT_HEAD`, `DEAN`, `ADVISOR`, `REVIEWER`, `CHAIR`, `SECRETARY`.
- Không có `plagiarism=true/false`.
- Không có online approval cho rút/gia hạn.
- Không có hành động tự chọn Hội đồng/Chủ tịch.
- Sửa điểm/biên bản sau in chỉ khi Thư ký xác nhận giấy chưa có chữ ký nào; từ chữ ký đầu không sửa.
- Không lưu prompt, API key, file body hoặc PII trong Qdrant/AuditEvent.

Physical model canonical gồm 62 bảng tại `backend/db/models/entities.py`; mục đích và field contract của từng bảng nằm trong `data-dictionary.md`.

RepositoryItem là corpus item chung cho MANAGED_THESIS, IMPORTED_DOCUMENT, OFFICIAL_SOURCE; không ép nguồn lịch sử thành Thesis. Source type/provenance/visibility được giữ ở PostgreSQL, Qdrant chỉ là index dẫn xuất.
