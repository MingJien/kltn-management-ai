# Quyết định thiết kế CSDL

## Quy ước trạng thái

- **CONFIRMED:** xuất phát từ nghiệp vụ/nguồn chính thức.
- **DERIVED:** cần thiết để thực thi requirement đã xác nhận.
- **PROPOSED:** lựa chọn kỹ thuật có thể thay đổi mà không đổi nghiệp vụ.

## ADR liên quan

- [ADR-001 — Backend FastAPI theo modular monolith](../decisions/ADR-001-modular-monolith.md)
- [ADR-002 — PostgreSQL là nguồn dữ liệu giao dịch chính](../decisions/ADR-002-postgresql-source-of-truth.md)
- [ADR-003 — Phân quyền theo vai trò nền và ngữ cảnh tài nguyên](../decisions/ADR-003-phan-quyen-ngu-canh.md)
- [ADR-004 — Gemini chỉ dùng ở backend cho RAG có kiểm soát](../decisions/ADR-004-rag-gemini-an-toan.md)

## Quyết định

| ID | Quyết định | Lý do và hệ quả | Status |
| --- | --- | --- | --- |
| DBD-01 | PostgreSQL `17.11-bookworm`, pin exact image, không dùng `latest` | PostgreSQL 17 được upstream hỗ trợ đến 08/11/2029; 17.11 là minor hiện hành tại thời điểm audit. Giảm rủi ro EOL sớm so với 14/15, ổn định hơn việc chọn beta 19. | PROPOSED; nguồn kỹ thuật: [PostgreSQL Versioning Policy](https://www.postgresql.org/support/versioning/) |
| DBD-02 | Docker Compose chỉ có service `postgres`, port bind `127.0.0.1:5433`, named volume `kltn_postgres_data` | Đúng phạm vi DB, không mở DB ra LAN, không bind data vào Git. Docker engine location phải được xác minh riêng; named volume không bảo đảm ổ D nếu Docker Desktop chưa cấu hình data location. | PROPOSED |
| DBD-03 | UUID làm PK; UUID do application tạo | Không lộ sequence, thuận lợi import/đồng bộ; tránh phụ thuộc extension cho default. | PROPOSED |
| DBD-04 | `varchar + CHECK` cho state/type nghiệp vụ thay PostgreSQL native enum | Cho phép migration thêm trạng thái có kiểm soát, không biến enum thành policy cứng khó đổi; CHECK vẫn chặn giá trị rác. | PROPOSED |
| DBD-05 | Mọi FK nghiệp vụ dùng `ON DELETE RESTRICT` | KLTN/điểm/biên bản cần history; xóa cascade có thể làm mất hồ sơ. State/void/revoke thay physical delete. | DERIVED |
| DBD-06 | Tách `StoredFile` khỏi `Document/Proposal/MinuteVersion` | Bytes nằm object/file storage; PostgreSQL giữ metadata, checksum, scan status và version relation. Một file chưa CLEAN không được submit. | DERIVED |
| DBD-07 | Append-only version cho đề cương, tài liệu và biên bản | Review/similarity/signature phải trỏ đúng nội dung từng thời điểm; không overwrite bản đã nộp. | DERIVED |
| DBD-08 | Denormalize `registration_member.round_id` và `active` có kiểm soát | Cần partial UNIQUE để chặn một SV ở nhiều registration hoạt động/round. Composite FK bảo đảm round khớp parent; application đồng bộ active với state. | PROPOSED control |
| DBD-09 | Count 1–3 member, topic capacity, quorum, present evaluator và điểm tổng hợp do application transaction enforce | Các rule này cần đọc/khóa nhiều bảng; trigger phức tạp làm ẩn logic. DB vẫn giữ unique/check/fk cục bộ. | DERIVED/PROPOSED |
| DBD-10 | Không PostgreSQL RLS ở baseline | Permission phụ thuộc base role + position + assignment + resource + state. Schema đã lưu đủ context; FastAPI về sau enforce. RLS chỉ cân nhắc nếu threat model/operations yêu cầu. | PROPOSED |
| DBD-11 | `JSONB` chỉ cho policy config, labels, keywords | Những cấu trúc biến thiên/versioned; core relations, điểm, members không nhét JSON. Validation schema thực hiện ở application. | PROPOSED |
| DBD-12 | Similarity policy để nullable/configurable; không CHECK 90% hoặc cosine | Baseline chỉ advisory, không có 90% gate; check record lưu metric/model/index/corpus provenance. Gate tương lai cần policy được duyệt. | CONFIRMED_PROJECT_DESIGN |
| DBD-13 | Evaluation unique theo session × evaluator CouncilMember × ThesisMember | Chấm riêng từng SV và giữ ownership; evaluator identity không nhận từ client về sau. | CONFIRMED |
| DBD-14 | RubricCriterion lưu parent_id để biểu diễn ba nhóm Mẫu 6 (2/4/4), 12 tiêu chí con và mục BONUS tối đa 1; group chỉ tổng hợp, không là điểm cộng thêm. Bonus nằm trong Evaluation.totalPoints và tổng phiếu ≤10. | Đúng cấu trúc Mẫu 6; FinalResult lấy mean total hợp lệ, không cộng lại bonus. Khác biệt nguồn với QĐ2919 được lưu source/version để truy vết; Mẫu 6 là baseline dự án, không còn chờ quyết định thiết kế. | CONFIRMED baseline thiết kế; runtime scoring pending |
| DBD-15 | FinalResult lưu snapshot tính toán có `calculation_version` | Điểm là dữ liệu quan trọng; snapshot cho audit trong khi nguồn Evaluation vẫn giữ. | DERIVED |
| DBD-16 | Minute có aggregate + version + signature riêng | MinuteVersion giữ từng tệp và liên kết bản thay thế; Chủ tịch và Thư ký cùng ký Mẫu 9. Bản in sai được VOID và tạo version/tệp/mã thời gian mới trước chữ ký đầu, có Thư ký đối chiếu và audit. Từ chữ ký đầu điểm/nội dung bất biến. | CONFIRMED_PROJECT_DECISION |
| DBD-17 | SearchIndexMetadata/ RetrievalAudit chỉ là metadata dẫn xuất | Qdrant/RAG đã có prototype trên dữ liệu giả; schema chỉ lưu metadata dẫn xuất, không lưu vector/raw prompt/secret. PostgreSQL vẫn là source of truth. | PROPOSED |
| DBD-18 | Alembic migration initial chứa DDL explicit được sinh từ metadata đã review | Các migration bất biến và review được; `alembic check` sau apply phải không có drift. Không gọi `create_all` động trong migration. | PROPOSED |
| DBD-19 | SQLAlchemy 2.x + Alembic + psycopg | Quản lý mô hình PostgreSQL và migration; cấu hình môi trường nằm ngoài source. | PROPOSED |
| DBD-20 | Không seed dữ liệu thật; validation dùng mã/tên synthetic rõ ràng | Ngăn PII vào Git/log; seed reference chỉ thêm khi thực sự cần. | DERIVED |
| DBD-21 | Lưu `consent_status`, `responded_by_user_id`, `responded_at` trên mỗi RegistrationMember | Không coi việc nhóm trưởng nhập tên là sự đồng ý của bạn khác. Migration 0007 giữ dữ liệu cũ PENDING; CHECK yêu cầu actor/time khi phản hồi. Service đối chiếu actor với StudentProfile và chỉ submit khi mọi thành viên active ACCEPTED. | CONFIRMED_PROJECT_DESIGN; service pending |
| DBD-23 | Điều kiện đăng ký giữ tỷ lệ tín chỉ/GPA có nguồn, kết quả và người xác nhận; không giữ chi tiết kỷ luật/án tích | Hai chỉ số học vụ cần giải thích ngưỡng QĐ5964, nhưng có thể NULL nếu Phòng Đào tạo chỉ cấp kết quả. Migration 0008 đã áp dụng, 0009 khôi phục hai chỉ số; dữ liệu cũ không thể suy đoán để phục hồi. | CONFIRMED_PROJECT_DESIGN 03/10 |
| DBD-24 | Chọn đăng ký/đăng nhập email và mật khẩu do ứng dụng KLTN quản lý | Không phụ thuộc quyền tích hợp SSO Trường để hoàn thành đồ án. `user_account.email` duy nhất không phân biệt hoa/thường, `password_hash` chỉ giữ mã băm, `email_verified_at` ghi xác minh; `external_subject` nullable cho tài khoản DEV/SSO cũ. Email mới không tự có quyền SV/GV/TBM; phải đối chiếu hồ sơ rồi cấp. Migration 0010 chỉ chuẩn bị CSDL, runtime xác thực còn phải làm. | CONFIRMED_PROJECT_DESIGN 03/10 |

## Quyết định nghiệp vụ và phần backend phải kiểm

| Chủ đề | Cách biểu diễn an toàn |
| --- | --- |
| Verifier expertise | `verified_by/verified_at` nullable; TBM đúng Bộ môn hoặc Trưởng khoa/người được giao khi TBM tự khai; service cấm tự verify. |
| Mốc tiến độ và ngày đợt | `ProgressMilestone` và `RoundPolicy` versioned; GVHD theo dõi, GVHD được phân công góp ý chéo ở checkpoint nội bộ. |
| Điều kiện bảo vệ đợt này | Dùng QĐ2919 Điều 7; `RoundPolicy.config_json` và `DefenseEligibilityCheck.local_policy_result` dành cho tiêu chí Khoa nếu có văn bản sau này. |
| Similarity baseline | `SimilarityPolicy.metric_code/threshold/config_json` nullable; chỉ ADVISORY, không 90% gate. |
| Bản in và chữ ký | Bản PRINTED chưa ký có thể VOID/in version mới sau Thư ký đối chiếu; từ chữ ký đầu Minute/Evaluation khóa nội dung. |
| Mẫu 9 | Chủ tịch + Thư ký ký theo CouncilMember; không gán TBM. |
| Xác nhận điều kiện | `ELIGIBILITY_VERIFIER` được Khoa giao theo round sau đối chiếu nguồn Phòng Đào tạo; không hard-code Admin/TBM. |
| Thành viên nhóm và đề tài SV | Mỗi SV tự tham gia, RegistrationMember ghi tài khoản/thời điểm; đề tài SV được đăng ký cá nhân trước khi TBM xét. API/UI đã có trên dữ liệu giả. |
| Góp ý chéo | Migration 0005 cho `COMMENT_ONLY`; service phải chỉ cho GVHD chính đổi trạng thái tiến độ, GVHD khác được giao chỉ góp ý. |

## Ranh giới migration

Alembic giữ lịch sử thay đổi từ `0001` đến head `20261010_0013`. `0012` thêm quy mô nhóm dự kiến; `0013` thêm lớp/ngành từ danh sách SV được Khoa duyệt. Schema hiện có 62 bảng nghiệp vụ và bảng `alembic_version`; bản SQL lõi 32 bảng dùng trình bày, không chạy lại trên CSDL đang dùng. Mẫu 6 đã được nạp ở trạng thái DRAFT, chưa dùng chấm thật. Thay đổi tiếp theo phải tạo migration mới.

| ID | Quyết định bổ sung | Hệ quả | Trạng thái |
| --- | --- | --- | --- |
| DBD-22 | Corpus tách nguồn vận hành/nhập/official | 0003 thêm origin/source, 0004 thêm external_source_id và source_url; tài liệu nhập không giả Thesis. | CONFIRMED_PROJECT_DECISION |
