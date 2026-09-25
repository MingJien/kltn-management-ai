# Quy tắc nghiệp vụ — NV4 Tuần 1

| ID | Quy tắc | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| BR-AUTH-001 | Một người chỉ dùng một `UserAccount`; base role thuộc `ADMIN/LECTURER/STUDENT`. | CONFIRMED | REQ-AUTH-001 |
| BR-AUTH-002 | Thẩm quyền nghiệp vụ = base role + position/assignment + resource + trạng thái; `ADMIN` không được bỏ qua phép kiểm tra này. | CONFIRMED_PROJECT_DECISION | REQ-AUTH-002..003 |
| BR-ROUND-001 | `ThesisRound.type ∈ {MAIN, SUPPLEMENTARY}`; mỗi đợt thuộc đúng một `AcademicYear`. | CONFIRMED_PROJECT_DECISION | REQ-ROUND-001 |
| BR-ELIG-001 | Đủ điều kiện chung khi tín chỉ đạt ≥70%, GPA ≥2,50/4 và không thuộc tình trạng kỷ luật/truy cứu bị cấm; ngoại lệ do thẩm quyền quy định. | CONFIRMED | SRC-QD-5964 |
| BR-ELIG-002 | Snapshot điều kiện phải lưu giá trị, nguồn, người xác nhận và thời điểm; không dùng giá trị tự khai chưa xác nhận để chốt. Người xác nhận phải có assignment `ELIGIBILITY_VERIFIER` trong đúng round; actor cụ thể còn `OPEN-11`. | DERIVED / PROPOSED_CONTROL | REQ-ELIG-002 |
| BR-TOPIC-001 | Topic chỉ mở đăng ký sau khi TBM duyệt; TBM được chỉnh tên nhưng lịch sử tên phải lưu. | CONFIRMED | REQ-TOPIC-001..002 |
| BR-TOPIC-002 | `preferredGpa` và yêu cầu GVHD là tiêu chí mong muốn; chỉ policy điều kiện chung mới được loại SV tự động. | CONFIRMED_PROJECT_DECISION | REQ-TOPIC-003 |
| BR-REG-001 | Mỗi SV có tối đa một đăng ký hoạt động trong một đợt và đăng ký chỉ có một topic; không có danh sách nguyện vọng xếp hạng. | CONFIRMED | REQ-REG-001 |
| BR-REG-002 | Thesis có 1–3 thành viên; tối đa một coordinator và coordinator không có quyền nghiệp vụ cao hơn thành viên. | CONFIRMED | REQ-REG-002 |
| BR-REG-003 | GVHD accept/reject; TBM mới là bên finalize topic và advisor assignment. | CONFIRMED_PROJECT_DECISION | REQ-REG-003 |
| BR-REG-004 | Mỗi thành viên phải có work allocation; GVHD duyệt trước khi dùng làm bằng chứng đánh giá cá nhân. | CONFIRMED | REQ-REG-004 |
| BR-REG-005 | Không cho ghép thêm SV vào đăng ký đã hình thành khi OPEN-02 chưa được chốt; chỉ cho cấu hình sau quyết định. | PROPOSED_SAFE_DEFAULT | REQ-REG-005 |
| BR-PROP-001 | ProposalVersion bất biến; nhận xét trỏ đúng version; không ghi đè file đã nộp. | DERIVED | REQ-PROP-001 |
| BR-PROP-002 | Thứ tự chốt: GVHD xác nhận → TBM chốt nội dung → Trưởng khoa ký/xác nhận văn bản. | CONFIRMED_PROJECT_DECISION | REQ-PROP-002..003 |
| BR-PROG-001 | GVHD sở hữu thao tác nhận xét/xác nhận progress; milestone theo đợt/kế hoạch, không hard-code ngày ví dụ. | CONFIRMED / DERIVED | REQ-PROG-001..002 |
| BR-CHANGE-001 | Đổi đề tài chỉ hợp lệ trong cửa sổ quy định và có xác nhận cần thiết; rút/gia hạn chỉ cập nhật sau kết quả thủ tục ngoài. | CONFIRMED | REQ-CHANGE-001..003 |
| BR-DOC-001 | Mọi lần nộp tài liệu tạo `DocumentVersion`; version đã dùng cho review/check không bị sửa byte. | DERIVED | REQ-DOC-001 |
| BR-SIM-001 | “90%” là ngưỡng nghiệp vụ chưa gắn metric; cấm so sánh trực tiếp với cosine score. | CONFIRMED_PROJECT_DECISION | REQ-SIM-002 |
| BR-SIM-002 | Semantic chỉ phát hiện ứng viên; document percentage phải là coverage metric có định nghĩa, corpus, exclusion, version và kết quả đánh giá. | CONFIRMED_PROJECT_DECISION | REQ-SIM-002..003 |
| BR-SIM-003 | Khi policy được duyệt, vượt ngưỡng có thể chặn finalize/final submission và yêu cầu sửa; thông báo chỉ nói “mức độ tương đồng cao”, không nói “đạo văn”. | CONFIRMED_PROJECT_DECISION | REQ-SIM-003 |
| BR-REPO-001 | Search/index chỉ chứa tài liệu người dùng được phép xem; revoke visibility phải loại hoặc cập nhật index. | DERIVED | REQ-REPO-001, REQ-AI-002 |
| BR-AI-001 | Authorization diễn ra trước retrieval; Gemini chỉ nhận chunks tối thiểu đã lọc PII; key chỉ ở backend; log không chứa nguyên văn nhạy cảm. | CONFIRMED_PROJECT_DECISION | REQ-AI-002 |
| BR-AI-002 | Chatbot trả câu trả lời, trích dẫn và link web; download do web endpoint có authorization thực hiện. | CONFIRMED | REQ-AI-001 |
| BR-COUNCIL-001 | Chỉ import/update CouncilMember từ quyết định; không tự sinh hoặc tự chọn Chair. | CONFIRMED | REQ-COUNCIL-001 |
| BR-COUNCIL-002 | Hội đồng 5 thành viên: Chair, Secretary, 2 Reviewer, Member; không mở phiên nếu vắng >2/5 hoặc vắng Chair/Secretary. | CONFIRMED | SRC-QD-2919 |
| BR-EVAL-001 | Evaluation duy nhất theo `(session, evaluator, thesisMember)`; chỉ chính evaluator sửa khi chưa khóa/in. | CONFIRMED | REQ-EVAL-002, REQ-MIN-001 |
| BR-EVAL-002 | Final score = trung bình số học các evaluation hợp lệ của người hiện diện/chấm, làm tròn 1 chữ số; không dùng điểm chung cho nhóm. | CONFIRMED | REQ-COUNCIL-003, REQ-EVAL-002 |
| BR-EVAL-003 | Rubric Mẫu 6 gồm ba group 2,0/4,0/4,0 với 12 tiêu chí con đúng mã/thứ tự/max point; group chỉ tổng hợp, không là điểm cộng thêm. Mục thưởng tối đa 1,0; `totalPoints ≤ 10`. FinalResult là trung bình `totalPoints` của các phiếu hợp lệ rồi làm tròn 1 chữ số; `bonusAverage` chỉ để giải thích, không cộng lần hai. | CONFIRMED baseline Mẫu 6; CONFLICT-011 OPEN trước vận hành | REQ-EVAL-003 |
| BR-MIN-001 | Minute có version; bản sai trước in chuyển `VOID`, bản thay thế liên kết bản cũ; khi `PRINTED/SIGNED` thì khóa. | CONFIRMED / PROPOSED_STATE | REQ-MIN-001..002 |
| BR-MIN-002 | Chair ký/xác nhận biên bản bảo vệ; Secretary lập/xuất. Cụm “TBM ký biên bản” chưa được gán vào biên bản bảo vệ. | CONFIRMED / OPEN_CONFLICT | CONFLICT-009 |
| BR-AUDIT-001 | Mọi accept/reject/finalize/sign/void/score change/visibility change phải có audit event gồm actor, time, resource, before/after và lý do. | DERIVED | Toàn bộ yêu cầu có thẩm quyền |

## Ảnh hưởng tới Use Case và dữ liệu

| Business Rule | Use Case chịu ảnh hưởng | Entity/constraint chính |
| --- | --- | --- |
| BR-AUTH-001 | UC-AUTH-001 | UserAccount; unique identity |
| BR-AUTH-002 | Mọi UC có mutation | OrganizationalPosition, PositionAssignment, ResourceAssignment, AdvisorAssignment, CouncilMember |
| BR-ROUND-001 | UC-ROUND-001 | AcademicYear 1–N ThesisRound; round_type CHECK |
| BR-ELIG-001 | UC-ELIG-001, UC-REG-001 | EligibilitySnapshot; ratio/GPA CHECK; policy version |
| BR-ELIG-002 | UC-ELIG-001 | EligibilitySnapshot, ResourceAssignment, confirmation actor/time |
| BR-TOPIC-001 | UC-TOPIC-001..003 | Topic, TopicTitleVersion, status/version |
| BR-TOPIC-002 | UC-TOPIC-001..003, UC-REG-001 | TopicRequirement.enforcement=DESIRED |
| BR-REG-001 | UC-REG-001/002 | TopicRegistration, RegistrationMember; unique active student/round |
| BR-REG-002 | UC-REG-002, UC-ASSIGN-001 | RegistrationMember/ThesisMember; count 1..3 application+transaction, one coordinator |
| BR-REG-003 | UC-ASSIGN-001 | TopicRegistration, AdvisorAssignment, Thesis; atomic finalization |
| BR-REG-004 | UC-WORK-001, UC-EVAL-002 | MemberWorkAssignment; owner ThesisMember; review state |
| BR-REG-005 | UC-REG-002 | Không có mutation hậu submit khi policy chưa chốt |
| BR-PROP-001 | UC-PROP-001..003 | ProposalVersion, ProposalReview; unique versionNo, immutable file |
| BR-PROP-002 | UC-PROP-003/004 | Proposal state, ProposalSignature; guarded sequence |
| BR-PROG-001 | UC-PROG-001/002 | ProgressMilestone, ProgressReport, ProgressReview |
| BR-CHANGE-001 | UC-CHANGE-001, UC-EXT-001 | TopicChangeRequest, ExternalProcedureOutcome |
| BR-DOC-001 | UC-DOC-001, UC-SIM-001 | Document, DocumentVersion, StoredFile; unique versionNo |
| BR-SIM-001 | UC-SIM-001 | SimilarityPolicy.metricCode/version; không CHECK 90/cosine |
| BR-SIM-002 | UC-SIM-001 | SimilarityCheck/Match; scoreType, coverage/model/corpus version |
| BR-SIM-003 | UC-SIM-001 | Policy decisionMode; check result; application gate |
| BR-REPO-001 | UC-REPO-001, UC-AI-001 | RepositoryItem, SearchIndexMetadata, visibility |
| BR-AI-001 | UC-AI-001 | RetrievalAudit metadata; không lưu raw secret/chunk nhạy cảm |
| BR-AI-002 | UC-AI-001, UC-REPO-001 | Citation/link tới RepositoryItem/DocumentVersion |
| BR-COUNCIL-001 | UC-COUNCIL-001 | Council, CouncilMember, decisionRef; role slots |
| BR-COUNCIL-002 | UC-SESSION-001 | CouncilMember count/role; DefenseSession, Attendance |
| BR-EVAL-001 | UC-EVAL-002 | Evaluation unique(session, evaluator, thesisMember); ownership |
| BR-EVAL-002 | UC-EVAL-003 | Attendance, Evaluation, FinalResult; application aggregation |
| BR-EVAL-003 | UC-RUBRIC-001, UC-EVAL-002/003 | RubricCriterion, EvaluationItem, Evaluation.totalPoints CHECK |
| BR-MIN-001 | UC-MIN-001/002 | CouncilMinute, MinuteVersion, replacement relation, lock state |
| BR-MIN-002 | UC-MIN-001/002 | MinuteSignature signer CouncilMember.role=CHAIR |
| BR-AUDIT-001 | Mọi UC quyết định/mutation nhạy cảm | AuditEvent actor/resource/before/after/reason/timestamp |
