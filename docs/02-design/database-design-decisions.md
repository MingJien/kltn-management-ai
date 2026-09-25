# Quyết định thiết kế CSDL

## Quy ước trạng thái

- **CONFIRMED:** xuất phát từ nghiệp vụ/nguồn chính thức.
- **DERIVED:** cần thiết để thực thi requirement đã xác nhận.
- **PROPOSED:** lựa chọn kỹ thuật có thể thay đổi mà không đổi nghiệp vụ.
- **OPEN:** chưa đủ căn cứ; schema phải tránh khóa cứng.

## ADR liên quan

- [ADR-001 — Backend FastAPI theo modular monolith](../adr/ADR-001-modular-monolith.md)
- [ADR-002 — PostgreSQL là nguồn dữ liệu giao dịch chính](../adr/ADR-002-postgresql-source-of-truth.md)
- [ADR-003 — Phân quyền theo vai trò nền và ngữ cảnh tài nguyên](../adr/ADR-003-phan-quyen-ngu-canh.md)
- [ADR-004 — Gemini chỉ dùng ở backend cho RAG có kiểm soát](../adr/ADR-004-rag-gemini-an-toan.md)

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
| DBD-12 | Similarity policy để nullable/configurable; không CHECK 90% hoặc cosine | Exact metric chưa chốt; check record lưu metric/model/index/corpus provenance. | CONFIRMED_PROJECT_DECISION + OPEN-05 |
| DBD-13 | Evaluation unique theo session × evaluator CouncilMember × ThesisMember | Chấm riêng từng SV và giữ ownership; evaluator identity không nhận từ client về sau. | CONFIRMED |
| DBD-14 | RubricCriterion lưu parent_id để biểu diễn ba nhóm Mẫu 6 (2/4/4), 12 tiêu chí con và mục BONUS tối đa 1; group chỉ tổng hợp, không là điểm cộng thêm. Bonus nằm trong Evaluation.totalPoints và tổng phiếu ≤10. | Đúng cấu trúc Mẫu 6; FinalResult lấy mean total hợp lệ, không cộng lại bonus. Cơ cấu QĐ2919 khác Mẫu 6: CONFLICT-011/OPEN-12 phải xác nhận trước chấm thật. | CONFIRMED baseline thiết kế; OPEN trước production scoring |
| DBD-15 | FinalResult lưu snapshot tính toán có `calculation_version` | Điểm là dữ liệu quan trọng; snapshot cho audit trong khi nguồn Evaluation vẫn giữ. | DERIVED |
| DBD-16 | Minute có aggregate + version + signature riêng | Cho phép void/replacement trước in, link bản thay thế, Chủ tịch ký, khóa hậu ký. Không tạo workflow sửa hậu ký khi OPEN-07 chưa chốt. | CONFIRMED/OPEN |
| DBD-17 | SearchIndexMetadata/ RetrievalAudit chỉ là metadata dẫn xuất | Không triển khai Qdrant/RAG vòng này; schema không lưu vector/raw prompt/secret, PostgreSQL vẫn là source of truth. | PROPOSED |
| DBD-18 | Alembic migration initial chứa DDL explicit được sinh từ metadata đã review | Migration bất biến, review được; `alembic check` sau apply phải không có drift. Không gọi `create_all` động trong migration. | PROPOSED |
| DBD-19 | SQLAlchemy 2.x + Alembic + psycopg trong `D:\KLTN\.venv` | Đủ cho schema/migration, không cài FastAPI. Python bundled runtime 3.12 được dùng vì Python 3.9 hệ thống lỗi venv launcher do path profile có khoảng trắng. | PROPOSED |
| DBD-20 | Không seed dữ liệu thật; validation dùng mã/tên synthetic rõ ràng | Ngăn PII vào Git/log; seed reference chỉ thêm khi thực sự cần. | DERIVED |

## Vấn đề chưa chốt và cách schema giữ linh hoạt

| OPEN | Cách biểu diễn an toàn |
| --- | --- |
| OPEN-01 verifier expertise | `verified_by/verified_at` nullable; mặc định SELF_DECLARED. |
| OPEN-02 ghép SV sau đăng ký | Không có workflow mutation; member/version/history cho phép bổ sung migration sau khi policy chốt. |
| OPEN-03/06 milestone/deadline | `ProgressMilestone` và `RoundPolicy` versioned. |
| OPEN-04 điều kiện riêng Khoa | `RoundPolicy.config_json` + `DefenseEligibilityCheck.local_policy_result`. |
| OPEN-05 metric 90% | `SimilarityPolicy.metric_code/threshold/config_json` nullable, mặc định ADVISORY. |
| OPEN-07 sửa hậu ký | Minute/Evaluation khóa; không có transition bypass. |
| OPEN-08 hai loại biên bản | Biên bản bảo vệ theo Chair; không gán TBM signer khi chưa phân biệt loại. |
| OPEN-11 người xác nhận điều kiện | `ResourceAssignment` theo round; không hard-code Admin/TBM. |

## Ranh giới migration

Migration `20260920_0001_create_initial_kltn_schema` tạo 62 bảng. Revision kế tiếp `20260924_0002_bind_proposal_signature_version` bổ sung cột/FK ghép để chữ ký đề cương trỏ đúng phiên bản; nếu đã có chữ ký cũ, migration dừng thay vì tự đoán bản được ký. Mọi thay đổi tiếp theo phải có revision mới; không sửa migration đã áp dụng. Ngày 24/09/2026 hai revision đã qua upgrade/downgrade/re-upgrade trong schema kiểm thử riêng, DB-01..26 và Alembic check PASS trên PostgreSQL 17.11 native.
