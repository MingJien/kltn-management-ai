# Quy tắc nghiệp vụ — NV4

| ID | Quy tắc | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| BR-AUTH-001 | Một người chỉ dùng một `UserAccount`; base role thuộc `ADMIN/LECTURER/STUDENT`. | CONFIRMED | REQ-AUTH-001 |
| BR-AUTH-002 | Thẩm quyền nghiệp vụ = base role + position/assignment + resource + trạng thái; `ADMIN` không được bỏ qua phép kiểm tra này. | CONFIRMED_PROJECT_DECISION | REQ-AUTH-002..003 |
| BR-AUTH-003 | Tài khoản email local phải xác minh quyền sở hữu email và được liên kết hồ sơ hợp lệ trước khi truy cập nghiệp vụ; mật khẩu chỉ lưu mã băm Argon2id. Quyền SV/GV/TBM/xác nhận điều kiện do hệ thống đối chiếu và cấp, không nhận từ form đăng ký. | CONFIRMED_PROJECT_DESIGN 03/10; runtime pending | REQ-AUTH-004 |
| BR-ROUND-001 | `ThesisRound.type ∈ {MAIN, SUPPLEMENTARY}`; mỗi đợt thuộc đúng một `AcademicYear`. | CONFIRMED_PROJECT_DECISION | REQ-ROUND-001 |
| BR-ELIG-001 | Đủ điều kiện chung khi tín chỉ đạt ≥70%, GPA ≥2,50/4 và không thuộc tình trạng kỷ luật/truy cứu bị cấm; ngoại lệ do thẩm quyền quy định. | CONFIRMED | SRC-QD-5964 |
| BR-ELIG-002 | Phòng Đào tạo cung cấp dữ liệu; người được Khoa giao `ELIGIBILITY_VERIFIER` đúng đợt đối chiếu và ghi kết quả đạt/không đạt, nguồn tham chiếu, người/lúc xác nhận và lý do ngắn. Có thể lưu tỷ lệ tín chỉ và GPA đã đối chiếu để giải thích ngưỡng học vụ; hai số này được phép NULL nếu Phòng Đào tạo chỉ cung cấp kết quả chính thức. Không lưu tình trạng kỷ luật hay án tích chi tiết; không dùng tự khai để chốt. | CONFIRMED_BY_ADVISOR_2026-10-03 | REQ-ELIG-002 |
| BR-TOPIC-001 | Đề tài GV tạo chỉ mở đăng ký sau TBM duyệt. Đề tài SV đề xuất được đăng ký cá nhân trước, TBM xét sau; chỉnh tên phải lưu lịch sử. | CONFIRMED | REQ-TOPIC-001..002 |
| BR-TOPIC-002 | `preferredGpa` và yêu cầu GVHD là tiêu chí mong muốn; chỉ policy điều kiện chung mới được loại SV tự động. | CONFIRMED_PROJECT_DECISION | REQ-TOPIC-003 |
| BR-REG-001 | Mỗi SV có tối đa một đăng ký hoạt động trong một đợt và đăng ký chỉ có một topic; không có danh sách nguyện vọng xếp hạng. | CONFIRMED | REQ-REG-001 |
| BR-REG-002 | Thesis có 1–3 thành viên; tối đa một coordinator và coordinator không có quyền nghiệp vụ cao hơn thành viên. | CONFIRMED | REQ-REG-002 |
| BR-REG-003 | GVHD accept/reject; TBM mới là bên finalize topic và advisor assignment. | CONFIRMED_PROJECT_DECISION | REQ-REG-003 |
| BR-REG-004 | Mỗi thành viên phải có work allocation; GVHD duyệt trước khi dùng làm bằng chứng đánh giá cá nhân. | CONFIRMED | REQ-REG-004 |
| BR-REG-005 | Mỗi SV tự tham gia; tối đa chỉ tiêu 1–3 và trước hạn đăng ký. Bổ sung sau khi gửi/được GV nhận làm đăng ký quay về `SUBMITTED`, GV xét lại; không bổ sung sau `FINALIZED`. | CONFIRMED_PROJECT_DECISION / IMPLEMENTED | REQ-REG-005 |
| BR-REG-006 | Đề tài SV tự đề xuất được đăng ký cá nhân trước, TBM xét sau; GV tiếp nhận được TBM chọn/đổi rồi quyết định, TBM chốt. Không yêu cầu Topic.APPROVED trước đăng ký ở nhánh này. | CONFIRMED_PROJECT_DESIGN / IMPLEMENTED | REQ-TOPIC-002, REQ-REG-003, REQ-REG-006 |
| BR-PROP-001 | ProposalVersion bất biến; nhận xét trỏ đúng version; không ghi đè file đã nộp. | DERIVED | REQ-PROP-001 |
| BR-PROP-002 | Thứ tự chốt: GVHD xác nhận → TBM chốt nội dung → Trưởng khoa ký/xác nhận văn bản. | CONFIRMED_PROJECT_DECISION | REQ-PROP-002..003 |
| BR-PROG-001 | GVHD quản lý và xác nhận tiến độ Thesis được phân công. Mốc góp ý đề cương và mốc nội bộ khoảng 70% trong tháng 12 được lưu theo round/version; ngày cụ thể lấy từ kế hoạch được duyệt. | CONFIRMED_PROJECT_DECISION | REQ-PROG-001..002 |
| BR-PROG-002 | Ở lần báo cáo nội bộ 70%, GVHD khác chỉ được góp ý chéo khi có assignment đúng Thesis/đợt; nhận xét chéo không thay quyền xác nhận tiến độ của GVHD chính và không dùng Council bảo vệ để gán quyền. | CONFIRMED_PROJECT_DECISION / DERIVED_CONTROL | REQ-PROG-001 |
| BR-CHANGE-001 | Đổi đề tài chỉ hợp lệ trong cửa sổ quy định và có xác nhận cần thiết; rút/gia hạn chỉ cập nhật sau kết quả thủ tục ngoài. | CONFIRMED | REQ-CHANGE-001..003 |
| BR-DOC-001 | Mọi lần nộp tài liệu tạo `DocumentVersion`; version đã dùng cho review/check không bị sửa byte. | DERIVED | REQ-DOC-001 |
| BR-SIM-001 | “90%” là ngưỡng nghiệp vụ chưa gắn metric; cấm so sánh trực tiếp với cosine score. | CONFIRMED_PROJECT_DECISION | REQ-SIM-002 |
| BR-SIM-002 | Semantic chỉ phát hiện ứng viên; document percentage phải là coverage metric có định nghĩa, corpus, exclusion, version và kết quả đánh giá. | CONFIRMED_PROJECT_DECISION | REQ-SIM-002..003 |
| BR-SIM-003 | Kết quả tương đồng ở bản hiện tại là advisory, không tự loại hoặc chặn nộp/bảo vệ. Gate tương lai đòi policy Khoa được duyệt và đánh giá metric/corpus/ngưỡng. | CONFIRMED_PROJECT_DESIGN | REQ-SIM-003 |
| BR-REPO-001 | Search/index chỉ chứa tài liệu người dùng được phép xem; revoke visibility phải loại hoặc cập nhật index. | DERIVED | REQ-REPO-001, REQ-AI-002 |
| BR-AI-001 | Chưa kết nối Gemini. Khi triển khai, chỉ gửi câu hỏi đã lọc và đoạn từ quy định chính thức hoặc tài liệu đã công bố; không gửi tên, MSSV, điểm, kỷ luật hay báo cáo chưa công bố của người khác. Backend phải kiểm nguồn/visibility và lọc trước khi gọi; key chỉ ở backend. | CONFIRMED_BY_ADVISOR_2026-10-03 / RUNTIME_PENDING | REQ-AI-002 |
| BR-AI-002 | Chatbot trả câu trả lời, trích dẫn và link web; download do web endpoint có authorization thực hiện. | CONFIRMED | REQ-AI-001 |
| BR-COUNCIL-001 | Chỉ import/update CouncilMember từ quyết định; không tự sinh hoặc tự chọn Chair. | CONFIRMED | REQ-COUNCIL-001 |
| BR-COUNCIL-002 | Hội đồng 5 thành viên: Chair, Secretary, 2 Reviewer, Member; không mở phiên nếu vắng >2/5 hoặc vắng Chair/Secretary. | CONFIRMED | SRC-QD-2919 |
| BR-DEF-001 | Đợt hiện tại áp dụng đúng Điều 7 QĐ2919; chưa có tiêu chí bảo vệ riêng của Khoa. Policy Khoa nếu ban hành sau này phải version theo round và không được hồi tố ngầm; similarity advisory không tự loại SV. | CONFIRMED_PROJECT_DECISION | REQ-DEF-001..002 |
| BR-EVAL-001 | Evaluation duy nhất theo `(session, evaluator, thesisMember)`; chỉ chính evaluator sửa khi chưa khóa/in. | CONFIRMED | REQ-EVAL-002, REQ-MIN-001 |
| BR-EVAL-002 | Final score = trung bình số học các evaluation hợp lệ của người hiện diện/chấm, làm tròn 1 chữ số; không dùng điểm chung cho nhóm. | CONFIRMED | REQ-COUNCIL-003, REQ-EVAL-002 |
| BR-EVAL-003 | Rubric Mẫu 6 gồm ba group 2,0/4,0/4,0 với 12 tiêu chí con đúng mã/thứ tự/max point; group chỉ tổng hợp, không là điểm cộng thêm. Mục thưởng tối đa 1,0; `totalPoints ≤ 10`. FinalResult là trung bình `totalPoints` của các phiếu hợp lệ rồi làm tròn 1 chữ số; `bonusAverage` chỉ để giải thích, không cộng lần hai. | CONFIRMED baseline Mẫu 6 của dự án; khác biệt nguồn được lưu để truy vết | REQ-EVAL-003 |
| BR-MIN-001 | Sau in, trước chữ ký đầu: Thư ký đối chiếu bản giấy chưa ký; bản in sai thành VOID có lý do/audit; evaluator tự sửa phiếu, hệ thống tính lại FinalResult và tạo MinuteVersion mới liên kết bản cũ, mã phiên bản/thời gian khác để in lại. Không overwrite file cũ. | CONFIRMED_PROJECT_DECISION | REQ-MIN-001..002 |
| BR-MIN-002 | Mẫu 9 do Chair và Secretary đúng Council cùng ký. Từ chữ ký đầu tiên (kể cả bản giấy chưa nhập hệ thống) không sửa điểm/nội dung; state vẫn PRINTED đến khi đủ hai chữ ký, sau đó SIGNED. | CONFIRMED_PROJECT_DECISION | REQ-MIN-001..002, SRC-MAU-09 |
| BR-AUDIT-001 | Mọi accept/reject/finalize/sign/void/score change/visibility change phải có audit event gồm actor, time, resource, before/after và lý do. | DERIVED | Toàn bộ yêu cầu có thẩm quyền |

## Ảnh hưởng tới Use Case và dữ liệu

| Business Rule | Use Case chịu ảnh hưởng | Entity/constraint chính |
| --- | --- | --- |
| BR-AUTH-001 | UC-AUTH-001 | UserAccount; unique identity |
| BR-AUTH-002 | Mọi UC có mutation | OrganizationalPosition, PositionAssignment, ResourceAssignment, AdvisorAssignment, CouncilMember |
| BR-ROUND-001 | UC-ROUND-001 | AcademicYear 1–N ThesisRound; round_type CHECK |
| BR-ELIG-001 | UC-ELIG-001, UC-REG-001 | EligibilitySnapshot giữ tỷ lệ tín chỉ/GPA khi có nguồn, kết quả theo đợt và người xác nhận; không lưu chi tiết kỷ luật/án tích |
| BR-ELIG-002 | UC-ELIG-001 | EligibilitySnapshot, ResourceAssignment, confirmation actor/time |
| BR-TOPIC-001 | UC-TOPIC-001..003 | Topic, TopicTitleVersion, status/version |
| BR-TOPIC-002 | UC-TOPIC-001..003, UC-REG-001 | TopicRequirement.enforcement=DESIRED |
| BR-REG-001 | UC-REG-001/002 | TopicRegistration, RegistrationMember; unique active student/round |
| BR-REG-002 | UC-REG-002, UC-ASSIGN-001 | RegistrationMember/ThesisMember; count 1..3 application+transaction, one coordinator |
| BR-REG-003 | UC-ASSIGN-001 | TopicRegistration, AdvisorAssignment, Thesis; atomic finalization |
| BR-REG-004 | UC-WORK-001, UC-EVAL-002 | MemberWorkAssignment; owner ThesisMember; review state |
| BR-REG-005 | UC-REG-002 | Không có mutation thành viên hậu SUBMITTED |
| BR-PROP-001 | UC-PROP-001..003 | ProposalVersion, ProposalReview; unique versionNo, immutable file |
| BR-PROP-002 | UC-PROP-003/004 | Proposal state, ProposalSignature; guarded sequence |
| BR-PROG-001 | UC-PROG-001/002 | ProgressMilestone theo round/version, ProgressReport, ProgressReview |
| BR-PROG-002 | UC-PROG-002 | ProgressReview theo báo cáo và reviewer; ResourceAssignment kiểm quyền góp ý chéo |
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
| BR-DEF-001 | UC-DEF-001 | DefenseEligibilityCheck; RoundPolicy chỉ khi có tiêu chí Khoa được ban hành |
| BR-EVAL-001 | UC-EVAL-002 | Evaluation unique(session, evaluator, thesisMember); ownership |
| BR-EVAL-002 | UC-EVAL-003 | Attendance, Evaluation, FinalResult; application aggregation |
| BR-EVAL-003 | UC-RUBRIC-001, UC-EVAL-002/003 | RubricCriterion, EvaluationItem, Evaluation.totalPoints CHECK |
| BR-MIN-001 | UC-MIN-001/002 | CouncilMinute, MinuteVersion, replacement relation, lock state |
| BR-MIN-002 | UC-MIN-001/002 | MinuteSignature signer CouncilMember.role=CHAIR |
| BR-AUDIT-001 | Mọi UC quyết định/mutation nhạy cảm | AuditEvent actor/resource/before/after/reason/timestamp |

## Quy tắc bổ sung ngày 25/09/2026

| ID | Quy tắc | Trạng thái | Trace |
| --- | --- | --- | --- |
| BR-ROUND-002 | KLTN_COORDINATOR là ResourceAssignment theo round; Council Secretary là CouncilMember theo council/session, quyền không kế thừa nhau. | CONFIRMED_PROJECT_DECISION | REQ-ROUND-002 |
| BR-CORPUS-001 | MANAGED_THESIS bắt buộc Thesis/DocumentVersion; IMPORTED_DOCUMENT và OFFICIAL_SOURCE không có hai FK vận hành này, phải có source_ref hoặc stored_file. | CONFIRMED_PROJECT_DECISION | REQ-CORPUS-001, migration 0003 |
| BR-CORPUS-002 | Index/search lọc visibility/scope trước khi trả hit; citation giữ source_type/title/version/provenance. | CONFIRMED_PROJECT_DECISION | REQ-CORPUS-002 |
| BR-EXPORT-001 | Mẫu 9 chỉ SIGNED sau chữ ký Chair và Secretary; trước chữ ký đầu được in lại qua version mới và audit. Sau ký chỉ cấp bản sao bất biến; export đúng mẫu cần template được kiểm. | CONFIRMED_PROJECT_DECISION | REQ-EXPORT-001 |
| BR-SIM-004 | Upload không chặn vì similarity; kết quả luôn advisory trong baseline, không có gate 90% tự động. | CONFIRMED_PROJECT_DECISION | REQ-SIM-003 |
| BR-EXT-001 | URL bên ngoài từ allowlist HTTPS server-side, không nhận URL tùy ý qua query. | CONFIRMED_PROJECT_DECISION | REQ-EXT-001 |
