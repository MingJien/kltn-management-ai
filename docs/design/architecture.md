# Kiến trúc hệ thống — modular monolith

## Quyết định nền

| Thành phần | Lựa chọn | Trạng thái / lý do |
| --- | --- | --- |
| Frontend | React + TypeScript + Vite | Baseline dự án; client không quyết định quyền. |
| Backend | FastAPI modular monolith | `PROPOSED`; đủ ranh giới module, chưa cần microservice. |
| Dữ liệu giao dịch | PostgreSQL | Nguồn chính cho state, quyền, điểm, biên bản, audit. |
| File | Storage abstraction sau backend | Bytes tách CSDL; provider triển khai chưa chốt. |
| Tìm kiếm vector | Qdrant | Chỉ mục dẫn xuất có filter quyền. |
| AI | Gemini qua backend | Chưa kết nối; tương lai chỉ nguồn chính thức/đã công bố và câu hỏi đã lọc theo góp ý GV 03/10. |
| Contract | REST JSON + OpenAPI 3.1 | Trace về use case; async cho similarity/index/export. |

## Module

| Module | Sở hữu | Không được làm |
| --- | --- | --- |
| identity_access | account, profile, position, assignment authorization | Duyệt topic/điểm/biên bản |
| rounds_eligibility | year, round, policy, eligibility | Tự tạo ngoại lệ |
| topics_registration | expertise, topic/requirement, registration, thesis/member/work assignment | Không thêm người thay SV; không bổ sung sau TBM chốt |
| proposal_progress | proposal/version/review/signature, milestone/report/change/outcome | Duyệt rút/gia hạn online |
| documents_similarity | file/document/version, policy/check/match | Kết luận đạo văn |
| councils_evaluation | council/session/attendance/reviews/rubric/evaluation/result/minute | Tự chọn Chair; sửa từ chữ ký đầu |
| repository_search | publish/visibility/search/download/index lifecycle | Truy cập storage không guard |
| ai_assistant | authorize, retrieve, minimize, Gemini, citation | Workflow mutation/download bytes |
| reporting_audit | read model/export/audit metadata | Bypass resource authorization |

## Sơ đồ thành phần

~~~mermaid
flowchart LR
  U["Người dùng"] --> FE["React/TypeScript"]
  FE --> API["FastAPI modular monolith"]
  API --> AUTH["Authorization service"]
  API --> PG[(PostgreSQL)]
  API --> FS[(File storage)]
  API --> JOB["Worker/Outbox"]
  JOB --> QD[(Qdrant)]
  API --> QD
  API -.->|chỉ khi bộ lọc nguồn/câu hỏi đạt kiểm thử| GM["Gemini API: chưa bật"]
  AUTH --> PG
~~~

## Authorization

1. Xác thực account.
2. Nạp base role, position/assignment đang hiệu lực.
3. Nạp resource scope và state.
4. Kiểm tra conflict-of-interest, assignment và guard.
5. Thực hiện transaction; ghi AuditEvent metadata.

Không tin role, faculty, score, state, storage key hoặc “allowed action” do browser gửi. List/search cũng phải filter server-side. `ADMIN` chỉ được phép thao tác kỹ thuật đã cấp, không có business bypass.

## Similarity và RAG

~~~mermaid
flowchart TD
  DV["DocumentVersion được phép"] --> EX["Scan/extract/chunk/hash"]
  EX --> LX["Lexical candidate/match"]
  EX --> SM["Semantic candidate discovery"]
  LX --> CV["Coverage theo policy version"]
  SM --> CV
  CV --> DB["Check/Match + provenance trong PostgreSQL"]
  EX -->|repository eligible| IX["Qdrant + payload filter"]
  Q["Câu hỏi đã xác thực"] --> AZ["Authorization trước retrieval"]
  AZ --> IX --> MIN["Chỉ nguồn chính thức/đã công bố + lọc câu hỏi"]
  MIN -.->|tương lai, nguồn đã công bố| GM --> ANS["Trả lời + citation + link web"]
~~~

- Business threshold và metric tách biệt; semantic score không là phần trăm tài liệu.
- Gemini hiện chưa được gọi; backend chặn provider. Khi triển khai, chỉ dùng câu hỏi đã lọc và quy định/tài liệu đã công bố. Key chỉ ở backend/secret store; không vào Vite, log hoặc Git.
- Prompt injection trong tài liệu được xem là dữ liệu không tin cậy; AI không có tool đổi nghiệp vụ.
- Log chỉ giữ request/correlation/retrieved IDs/outcome cần thiết, không giữ chunks/body mặc định.

## Tính nhất quán và lỗi

| Tình huống | Hành vi |
| --- | --- |
| Qdrant lỗi | Workflow chính tiếp tục; semantic search/RAG báo tạm unavailable. |
| Gemini lỗi/rate limit | Không bịa câu trả lời; trả trạng thái retryable/no evidence. |
| Similarity lỗi | `FAILED`, không đổi acceptance/finalization; retry có idempotency. |
| Malware/extract lỗi | File ở quarantine; không tạo version khả dụng/index. |
| Concurrency | HTTP 409 + version mới nhất; không ghi đè im lặng. |
| Visibility revoke | PostgreSQL đổi trước, outbox deindex/reindex; query filter vẫn chặn ngay. |
| Post-sign correction | Từ chữ ký đầu từ chối mọi sửa điểm/nội dung; trước chữ ký đầu Thư ký đối chiếu bản in và tạo version mới. |

## Bảo mật/vận hành

- Upload allowlist MIME/size, quarantine, malware scan, SHA-256, storage key nội bộ.
- Download chỉ sau authorization và dùng route/URL thời hạn ngắn.
- Dữ liệu nhạy cảm mã hóa theo môi trường, backup/restore kiểm thử, retention có policy.
- Metric/log không dùng PII làm label; mọi service dùng correlation ID.
- Hosting, SSO, region/provider, retention và SLA là quyết định triển khai, không giả thành nghiệp vụ.

## Runtime prototype từ 25/09/2026

Cấu trúc giữ modular monolith: `backend/api` nhận HTTP/validate DTO; `backend/services` thực thi use case và transaction; `backend/db` giữ mô hình và migration; `backend/ai` xử lý nguồn, embedding, truy xuất; `frontend` là React shell. PostgreSQL `kltn_management` giữ nghiệp vụ trong 32 bảng; Qdrant local/service giữ chỉ mục AI thử nghiệm có thể tạo lại từ corpus giả. Bản này chưa ghi metadata corpus vào PostgreSQL. Hệ thống dùng email/mật khẩu băm Argon2id; quyền SV/GV/TBM chỉ gắn sau khi đối chiếu hồ sơ. Runtime đăng nhập email/mật khẩu, kích hoạt email, đặt lại mật khẩu và cookie phiên đã được kiểm trên dữ liệu giả. Tích hợp SSO của Trường không thuộc phạm vi hiện tại. UUID header chỉ được chấp nhận khi `KLTN_ENV=development|test` và `KLTN_DEV_AUTH=true`. Xuất biểu mẫu đi qua template adapter/version như [thiết kế riêng](xuat-bieu-mau.md); hiện không có runtime export exact Mẫu 9.
