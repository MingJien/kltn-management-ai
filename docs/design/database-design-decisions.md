# Quyết định thiết kế CSDL

## Quy ước trạng thái

- **CONFIRMED:** xuất phát từ nghiệp vụ/nguồn chính thức.
- **DERIVED:** cần thiết để thực thi requirement đã xác nhận.
- **PROPOSED:** lựa chọn kỹ thuật có thể thay đổi mà không đổi nghiệp vụ.
- **OPEN:** chưa đủ căn cứ; schema phải tránh khóa cứng.

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
| DBD-14 | RubricCriterion lưu parent_id để biểu diễn ba nhóm Mẫu 6 (2/4/4), 12 tiêu chí con và mục BONUS tối đa 1; group chỉ tổng hợp, không là điểm cộng thêm. Bonus nằm trong Evaluation.totalPoints và tổng phiếu ≤10. | Đúng cấu trúc Mẫu 6; FinalResult lấy mean total hợp lệ, không cộng lại bonus. Cơ cấu QĐ2919 khác Mẫu 6: lưu source/version và yêu cầu Khoa xác nhận trước chấm thật. | CONFIRMED baseline thiết kế; production gate |
| DBD-15 | FinalResult lưu snapshot tính toán có `calculation_version` | Điểm là dữ liệu quan trọng; snapshot cho audit trong khi nguồn Evaluation vẫn giữ. | DERIVED |
| DBD-16 | Minute có aggregate + version + signature riêng | MinuteVersion giữ từng tệp và liên kết bản thay thế; Chủ tịch và Thư ký cùng ký Mẫu 9. Bản in sai được VOID và tạo version/tệp/mã thời gian mới trước chữ ký đầu, có Thư ký đối chiếu và audit. Từ chữ ký đầu điểm/nội dung bất biến. | CONFIRMED_PROJECT_DECISION |
| DBD-17 | SearchIndexMetadata/ RetrievalAudit chỉ là metadata dẫn xuất | Qdrant/RAG đã có prototype trên dữ liệu giả; schema chỉ lưu metadata dẫn xuất, không lưu vector/raw prompt/secret. PostgreSQL vẫn là source of truth. | PROPOSED |
| DBD-18 | Alembic migration initial chứa DDL explicit được sinh từ metadata đã review | Các migration bất biến và review được; `alembic check` sau apply phải không có drift. Không gọi `create_all` động trong migration. | PROPOSED |
| DBD-19 | SQLAlchemy 2.x + Alembic + psycopg trong `D:\KLTN\.venv` | Đủ cho schema/migration và prototype FastAPI. Python bundled runtime 3.12 được dùng vì Python 3.9 hệ thống lỗi venv launcher do path profile có khoảng trắng. | PROPOSED |
| DBD-20 | Không seed dữ liệu thật; validation dùng mã/tên synthetic rõ ràng | Ngăn PII vào Git/log; seed reference chỉ thêm khi thực sự cần. | DERIVED |

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
| Góp ý chéo | Migration 0005 cho `COMMENT_ONLY`; service phải chỉ cho GVHD chính đổi trạng thái tiến độ, GVHD khác được giao chỉ góp ý. |

## Ranh giới migration

Migration `0001` tạo nền, `0002` khóa chữ ký đề cương đúng version, `0003` tách nguồn corpus, `0004` lưu định danh nguồn ngoài và `0005` cho góp ý chéo `COMMENT_ONLY`, `0006` nạp 16 dòng rubric Mẫu 6 trạng thái DRAFT. Head hiện tại là `20260925_0006` với 63 bảng, đã được đối chiếu bằng SQL snapshot trên schema thử nghiệm. Migration đã áp dụng là lịch sử bất biến; thay đổi vật lý trong tương lai phải có revision mới. Các quyết định ngày 25/09 về nhóm, mốc và điều kiện bảo vệ đã có bảng/cột biểu diễn. Mẫu 6 cần một migration dữ liệu thật để mọi database mới/cũ có cùng rubric baseline, nhưng chưa tự kích hoạt chấm.

| ID | Quyết định bổ sung | Hệ quả | Trạng thái |
| --- | --- | --- | --- |
| DBD-21 | Corpus tách nguồn vận hành/nhập/official | 0003 thêm origin/source, 0004 thêm external_source_id và source_url; tài liệu nhập không giả Thesis. | CONFIRMED_PROJECT_DECISION |
