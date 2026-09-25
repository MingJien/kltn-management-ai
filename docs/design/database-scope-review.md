# Rà soát phạm vi bảng CSDL

Baseline: SQLAlchemy metadata và migrations `20260920_0001` → `20260925_0007`. Phân loại theo nhu cầu nghiệp vụ, không phải lệnh xóa bảng. Tất cả 62 bảng được tạo trong schema hiện tại; `CORE-NOW` nghĩa là cần cho thiết kế/validation CSDL NV4, còn runtime nghiệp vụ thuộc các vòng triển khai sau. `LATER-PHASE` nghĩa là chưa có workflow kho/AI đầy đủ; một số bảng đã được dùng để thử nạp metadata/chỉ mục AI. `TECHNICAL-SUPPORT` là hạ tầng lưu tệp/audit. API/React/AI prototype hiện có; chỉ các endpoint và màn hình được nêu trong README là runtime.

| Table | Nhóm | Requirement/UC | Lý do | Dùng ngay hay sau |
| --- | --- | --- | --- | --- |
| `academic_year` | CORE-NOW | REQ-ROUND-001; UC đối chiếu tại `traceability-database.md` | Năm học chứa các đợt KLTN. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `advisor_assignment` | CORE-NOW | REQ-REG-003; UC đối chiếu tại `traceability-database.md` | Phân công GVHD chính cho Thesis. | Prototype tạo GVHD chính khi TBM chốt; workflow đầy đủ sau |
| `advisor_review` | CORE-NOW | REQ-EVAL-001; UC đối chiếu tại `traceability-database.md` | Phiếu nhận xét GVHD theo SV và document version. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `audit_event` | TECHNICAL-SUPPORT | BR-AUDIT-001; UC đối chiếu tại `traceability-database.md` | Dấu vết quyết định/mutation nhạy cảm. | Schema/DB validation ngay; service sau |
| `bonus_evidence` | CORE-NOW | REQ-EVAL-003; UC đối chiếu tại `traceability-database.md` | Minh chứng điểm thưởng của từng SV. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `council` | CORE-NOW | REQ-COUNCIL-001; UC đối chiếu tại `traceability-database.md` | Hội đồng nhập từ quyết định, theo round/Bộ môn. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `council_attendance` | CORE-NOW | REQ-COUNCIL-003; UC đối chiếu tại `traceability-database.md` | Hiện diện từng thành viên trong phiên. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `council_member` | CORE-NOW | REQ-COUNCIL-001; UC đối chiếu tại `traceability-database.md` | Thành viên/role-slot lấy từ quyết định. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `council_minute` | CORE-NOW | REQ-MIN-001..002; UC đối chiếu tại `traceability-database.md` | Aggregate biên bản của session. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `defense_eligibility_check` | CORE-NOW | REQ-DEF-001; UC đối chiếu tại `traceability-database.md` | Kết quả kiểm điều kiện bảo vệ theo từng SV. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `defense_session` | CORE-NOW | REQ-COUNCIL-002..003; UC đối chiếu tại `traceability-database.md` | Một buổi/phiên của Hội đồng. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `department` | CORE-NOW | REQ-AUTH-002; UC đối chiếu tại `traceability-database.md` | Lưu Bộ môn/chuyên ngành thuộc Khoa. | Prototype giới hạn phạm vi quyền theo Bộ môn; workflow đầy đủ sau |
| `document` | CORE-NOW | REQ-DOC-001; UC đối chiếu tại `traceability-database.md` | Container tài liệu của Thesis. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `document_version` | CORE-NOW | REQ-DOC-001; UC đối chiếu tại `traceability-database.md` | Bản nộp tài liệu bất biến. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `eligibility_exception` | CORE-NOW | REQ-ELIG-001; UC đối chiếu tại `traceability-database.md` | Ngoại lệ có căn cứ chính thức cho snapshot. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `eligibility_snapshot` | CORE-NOW | REQ-ELIG-001..002; UC đối chiếu tại `traceability-database.md` | Snapshot điều kiện đăng ký theo SV/đợt/version. | Prototype kiểm snapshot CONFIRMED trước đăng ký; workflow đầy đủ sau |
| `evaluation` | CORE-NOW | REQ-EVAL-002..003; UC đối chiếu tại `traceability-database.md` | Phiếu của một evaluator cho một SV trong phiên. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `evaluation_item` | CORE-NOW | REQ-EVAL-002..003; UC đối chiếu tại `traceability-database.md` | Điểm từng criterion trong phiếu. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `expertise_evidence` | CORE-NOW | REQ-EXP-001; UC đối chiếu tại `traceability-database.md` | Minh chứng cho hồ sơ chuyên môn. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `external_procedure_outcome` | CORE-NOW | REQ-CHANGE-002..003; UC đối chiếu tại `traceability-database.md` | Kết quả rút/gia hạn từ thủ tục ngoài. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `faculty` | CORE-NOW | REQ-AUTH-002; UC đối chiếu tại `traceability-database.md` | Lưu Khoa sở hữu phạm vi KLTN. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `final_result` | CORE-NOW | REQ-EVAL-002..003; UC đối chiếu tại `traceability-database.md` | Snapshot điểm tổng hợp riêng từng SV. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `lecturer_expertise` | CORE-NOW | REQ-EXP-001; UC đối chiếu tại `traceability-database.md` | Hồ sơ chuyên môn tự khai/versioned của GV. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `lecturer_profile` | CORE-NOW | REQ-AUTH-001; UC đối chiếu tại `traceability-database.md` | Hồ sơ GV tối thiểu gắn account và Bộ môn. | Prototype nhận diện giảng viên và TBM; workflow đầy đủ sau |
| `member_work_assignment` | CORE-NOW | REQ-REG-004; UC đối chiếu tại `traceability-database.md` | Phân công công việc versioned cho từng SV. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `minute_signature` | CORE-NOW | REQ-MIN-001; UC đối chiếu tại `traceability-database.md` | Chữ ký/xác nhận Chủ tịch và Thư ký trên version. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `minute_version` | CORE-NOW | REQ-MIN-001..002; UC đối chiếu tại `traceability-database.md` | Version/void/replacement/print/sign của biên bản. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `organizational_position` | CORE-NOW | REQ-AUTH-002; UC đối chiếu tại `traceability-database.md` | Danh mục vị trí TBM/Trưởng khoa, không phải base role. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `position_assignment` | CORE-NOW | REQ-AUTH-002; UC đối chiếu tại `traceability-database.md` | Gán vị trí tổ chức theo scope và hiệu lực. | Prototype kiểm vị trí TBM theo Bộ môn; workflow đầy đủ sau |
| `progress_milestone` | CORE-NOW | REQ-PROG-001..002; UC đối chiếu tại `traceability-database.md` | Mốc tiến độ versioned theo round/kế hoạch. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `progress_report` | CORE-NOW | REQ-PROG-001; UC đối chiếu tại `traceability-database.md` | Báo cáo tiến độ versioned của Thesis. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `progress_review` | CORE-NOW | REQ-PROG-001; UC đối chiếu tại `traceability-database.md` | GVHD nhận xét/xác nhận báo cáo tiến độ. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `proposal` | CORE-NOW | REQ-PROP-001..003; UC đối chiếu tại `traceability-database.md` | Aggregate đề cương một-một với Thesis. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `proposal_review` | CORE-NOW | REQ-PROP-002; UC đối chiếu tại `traceability-database.md` | Nhận xét trỏ đúng proposal version và assignment. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `proposal_version` | CORE-NOW | REQ-PROP-001; UC đối chiếu tại `traceability-database.md` | Mỗi lần nộp/sửa đề cương là một version bất biến. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `registration_member` | CORE-NOW | REQ-REG-001..002; UC đối chiếu tại `traceability-database.md` | Mọi SV trong đăng ký nhóm; chặn trùng SV/round và lưu phản hồi PENDING/ACCEPTED/DECLINED. | Schema 0007 có chứng cứ phản hồi; prototype chưa có từng SV tự xác nhận |
| `repository_item` | LATER-PHASE | REQ-REPO-001; UC đối chiếu tại `traceability-database.md` | Metadata KLTN quản lý hoặc nguồn học thuật/chính thức nhập có loại và provenance. | Prototype nạp metadata nguồn ngoài; workflow công bố sau |
| `resource_assignment` | CORE-NOW | REQ-ELIG-002; người Khoa được giao theo round; UC đối chiếu tại `traceability-database.md` | Gán quyền theo round/Thesis/Council, gồm verifier điều kiện. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `retrieval_audit` | LATER-PHASE | REQ-AI-002; UC đối chiếu tại `traceability-database.md` | Audit retrieval tối thiểu, không lưu raw prompt/chunk. | Schema ngay; runtime kho/AI sau |
| `reviewer_assignment` | CORE-NOW | REQ-PROP-002, REQ-EVAL-001; UC đối chiếu tại `traceability-database.md` | Phân công người review đề cương/KLTN. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `reviewer_review` | CORE-NOW | REQ-EVAL-001; UC đối chiếu tại `traceability-database.md` | Phiếu nhận xét GVPB theo SV và document version. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `round_policy` | CORE-NOW | REQ-ROUND-001, REQ-PROG-002; UC đối chiếu tại `traceability-database.md` | Policy versioned theo đợt, không hard-code deadline/tiêu chí mở rộng. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `rubric_assignment` | CORE-NOW | REQ-EVAL-003; UC đối chiếu tại `traceability-database.md` | Gắn rubric cho round hoặc session. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `rubric_criterion` | CORE-NOW | REQ-EVAL-003; UC đối chiếu tại `traceability-database.md` | Hierarchy Mẫu 6: ba nhóm 2/4/4, 12 tiêu chí con và mục thưởng tối đa 1; tổng phiếu tối đa 10. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `rubric_template` | CORE-NOW | REQ-EVAL-003; UC đối chiếu tại `traceability-database.md` | Phiên bản rubric theo Mẫu 6/policy. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `search_index_metadata` | LATER-PHASE | REQ-REPO-001, REQ-AI-001; UC đối chiếu tại `traceability-database.md` | Trạng thái index dẫn xuất, không phải source of truth. | Prototype ghi trạng thái index; workflow đầy đủ sau |
| `session_thesis` | CORE-NOW | REQ-COUNCIL-002; UC đối chiếu tại `traceability-database.md` | Xếp nhiều Thesis vào phiên theo thứ tự. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `signature_confirmation` | CORE-NOW | REQ-PROP-002..003; UC đối chiếu tại `traceability-database.md` | Metadata TBM chốt/Trưởng khoa xác nhận đề cương. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `similarity_check` | LATER-PHASE | REQ-SIM-001..003; UC đối chiếu tại `traceability-database.md` | Record một lần kiểm tra với provenance. | Schema ngay; runtime kho/AI sau |
| `similarity_match` | LATER-PHASE | REQ-SIM-001..002; UC đối chiếu tại `traceability-database.md` | Đoạn/nguồn match và score tách lexical/semantic. | Schema ngay; runtime kho/AI sau |
| `similarity_policy` | LATER-PHASE | REQ-SIM-002..003; UC đối chiếu tại `traceability-database.md` | Policy/metric tương đồng versioned và configurable. | Schema ngay; runtime kho/AI sau |
| `stored_file` | TECHNICAL-SUPPORT | REQ-DOC-001; UC đối chiếu tại `traceability-database.md` | Metadata file, checksum và trạng thái quét; không lưu bytes trong DB. | Schema/DB validation ngay; service sau |
| `student_profile` | CORE-NOW | REQ-AUTH-001, REQ-REG-001; UC đối chiếu tại `traceability-database.md` | Hồ sơ SV tối thiểu gắn account và Bộ môn. | Prototype nhận diện SV và bộ môn; workflow đầy đủ sau |
| `thesis` | CORE-NOW | REQ-REG-003; UC đối chiếu tại `traceability-database.md` | Hồ sơ KLTN hình thành sau finalization. | Prototype tạo khi TBM chốt; workflow đầy đủ sau |
| `thesis_member` | CORE-NOW | REQ-REG-002/004; UC đối chiếu tại `traceability-database.md` | Thành viên thực hiện KLTN và coordinator. | Prototype tạo thành viên khi TBM chốt; workflow đầy đủ sau |
| `thesis_round` | CORE-NOW | REQ-ROUND-001; UC đối chiếu tại `traceability-database.md` | Đợt chính/bổ sung và thời gian tiếp nhận. | Prototype kiểm cửa sổ nhận đăng ký; workflow đầy đủ sau |
| `topic` | CORE-NOW | REQ-TOPIC-001..003; UC đối chiếu tại `traceability-database.md` | Đề tài được đề xuất/duyệt trong một đợt. | Prototype chọn đề tài APPROVED và khóa khi chốt; workflow đầy đủ sau |
| `topic_change_request` | CORE-NOW | REQ-CHANGE-001; UC đối chiếu tại `traceability-database.md` | Workflow đổi đề tài trong hệ thống. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `topic_registration` | CORE-NOW | REQ-REG-001..006; UC đối chiếu tại `traceability-database.md` | Aggregate đăng ký một topic trong một đợt. | Prototype SV gửi → GV quyết định → TBM chốt; workflow đầy đủ sau |
| `topic_requirement` | CORE-NOW | REQ-TOPIC-003; UC đối chiếu tại `traceability-database.md` | Tiêu chí mong muốn của GVHD, enforcement DESIRED. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `topic_title_version` | CORE-NOW | REQ-TOPIC-001; UC đối chiếu tại `traceability-database.md` | Lịch sử chỉnh tên đề tài. | Schema/DB validation ngay; nghiệp vụ runtime sau |
| `user_account` | CORE-NOW | REQ-AUTH-001..003; UC đối chiếu tại `traceability-database.md` | Một tài khoản định danh và base role cho mỗi người. | Prototype định danh DEV/TEST; SSO production sau |

Tổng: 62 bảng (CORE-NOW 54, LATER-PHASE 6, TECHNICAL-SUPPORT 2, CANDIDATE_REMOVE 0). `alembic_version` do Alembic tạo thêm và không tính là entity nghiệp vụ.

Bảng `LATER-PHASE` vẫn có requirement và use case đã truy vết; giữ schema để không phải phá migration khi triển khai sau. Việc giữ bảng không đồng nghĩa tính năng đã chạy. Nếu requirement/UC thay đổi, đánh giá lại trước khi code service.

## Điều kiện loại bảng

Không có bảng nào đang mang `CANDIDATE_REMOVE` vì từng bảng có trace tối thiểu trong data dictionary. Khi audit sau phát hiện trace chỉ là suy đoán hoặc chức năng bị loại khỏi scope, gắn `CANDIDATE_REMOVE` và cập nhật domain/ERD/migration đồng bộ trước khi xóa; không xóa mù quáng.
