# Thiết kế kiểm tra tương đồng, kho truy hồi và AI

## Ranh giới sản phẩm

1. Similarity không đồng nghĩa plagiarism; hệ thống chỉ báo bằng chứng và “mức độ tương đồng cao”.
2. Business source có mốc 90%, nhưng exact metric/corpus/exclusion chưa chốt. Cấm map cosine 0,9 = 90%.
3. Hybrid gồm lexical + semantic; semantic chỉ tìm candidate. Document percentage phải dựa trên coverage metric đã định nghĩa/đánh giá.
4. Khi policy được Khoa chốt, vượt ngưỡng có thể chặn `FINALIZE/FINAL_SUBMISSION` và yêu cầu sửa; trước đó kết quả advisory. `OPEN-05` chặn việc kích hoạt quyết định tự động này, không chặn xây pipeline advisory.
5. Gemini được phép ở cấp project decision: authorization trước retrieval, chunks cần thiết, giảm PII, key backend-only, log an toàn. Đây không phải quy định Trường.

## Từ vựng metric

| Trường | Ý nghĩa | Có dùng làm 90%? |
| --- | --- | --- |
| semanticCandidateScore | Độ gần embedding ở cặp query/chunk, dùng xếp ứng viên | Không |
| lexicalPairScore | Mức overlap/align của cặp đoạn | Chỉ evidence |
| matchedCoveragePct | Tỷ lệ token hợp lệ thuộc union span match sau loại overlap | Chỉ khi policy duyệt công thức |
| sourceContributionPct | Phần coverage quy cho một nguồn | Giải thích report |
| overallStatus | `POLICY_NOT_CONFIGURED/LOW/REVIEW/HIGH` | Chỉ HIGH khi policy ACTIVE |

Ứng viên công thức để thực nghiệm:

`matchedCoveragePct = eligible_tokens_in_union_of_confirmed_lexical_spans / total_eligible_tokens × 100`.

`eligible_tokens`, quote/bibliography/citation/template/small-match exclusion, corpus và overlap attribution phải nằm trong SimilarityPolicy version; chưa có mặc định nghiệp vụ.

## Pipeline

~~~mermaid
flowchart TD
  A["DocumentVersion được phép"] --> B["Quarantine/scan/extract + page/offset map"]
  B --> C["Normalize/chunk/hash có version"]
  C --> D["Lexical retrieval/matching"]
  C --> E["Semantic candidate discovery"]
  D --> F["Align spans; union/deduplicate; source attribution"]
  E --> F
  F --> G["Coverage theo SimilarityPolicy"]
  G --> H["Lưu Check/Match + model/index/corpus provenance"]
  H --> I["GVHD review"]
  I -->|yêu cầu sửa| A
  I -->|xác nhận| J["Cho đi tiếp nếu policy/guard đạt"]
~~~

## Policy cần chốt cho OPEN-05

- Tên metric và công thức chính xác.
- Tokenizer/denominator.
- Corpus scope và snapshot/effective date.
- Exclusion cho trích dẫn, bibliography, template, small match.
- Threshold và action tương ứng.
- Người review và audit lý do.
- Bộ dữ liệu hiệu chỉnh có quyền sử dụng; precision/recall/F1/coverage error.
- Version, effective range và migration khi model/index đổi.

## RAG với Gemini

~~~mermaid
sequenceDiagram
  participant U as Người dùng đã xác thực
  participant A as Backend AI
  participant P as PostgreSQL
  participant Q as Qdrant
  participant G as Gemini
  U->>A: Câu hỏi
  A->>P: Resolve scope + repository item được phép
  A->>Q: Retrieval có payload filter
  Q-->>A: Chunks tối thiểu + provenance
  A->>A: Giảm PII, giới hạn context, xem text là dữ liệu không tin cậy
  A->>G: System instruction + bounded context
  G-->>A: Bản nháp trả lời
  A-->>U: Câu trả lời + citation + link web
~~~

Guardrail bắt buộc:

- Không gửi full document mặc định; không gửi chunks ngoài quyền.
- Không đưa MSSV/tên/ngày sinh/điểm vào prompt nếu không cần thiết và không được phép.
- Không dùng Vite/client để giữ API key.
- Retrieved instruction không thể thay system rule hoặc cấp tool quyền.
- AI không có command duyệt topic, phân công, chấm, ký hoặc đổi state.
- Không đủ evidence thì trả “không có nguồn xác thực phù hợp”.
- Audit giữ query hash, scope hash, item IDs, provider/outcome; không giữ nguyên body mặc định.

## Kho và index lifecycle

- Chỉ RepositoryItem `PUBLISHED` và visibility hợp lệ mới tạo SearchIndexMetadata/vector.
- Qdrant payload tối thiểu: repositoryItemId, documentVersionId, departmentId, majorCode, visibility, indexVersion; không chứa PII không cần thiết.
- Visibility revoke chặn query từ PostgreSQL ngay, sau đó outbox deindex; retry idempotent.
- Thay embedding model cần index version mới và re-embedding; không trộn không gian vector thiếu kiểm soát.

## Acceptance criteria

1. Người ngoài scope không retrieve/cite/download tài liệu hạn chế.
2. Semantic score không bao giờ mang nhãn phần trăm tài liệu.
3. Check luôn chỉ ra document/policy/model/index/corpus version.
4. Extraction/job lỗi không đổi workflow và retry không tạo quyết định trùng.
5. Khi policy chưa chốt, API/UI trả `POLICY_NOT_CONFIGURED`, không pass/fail.
6. Khi policy đã chốt và vượt ngưỡng, chỉ chặn bước được cấu hình và yêu cầu sửa; không kết luận đạo văn.
7. AI trả citation/link, không stream file và không mutate nghiệp vụ.
