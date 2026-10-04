# Thiết kế kiểm tra tương đồng, kho truy hồi và AI

## Ranh giới sản phẩm

1. Similarity không đồng nghĩa plagiarism; hệ thống chỉ báo bằng chứng và “mức độ tương đồng cao”.
2. Nguồn có nhắc mốc 90% nhưng không định nghĩa metric/corpus/exclusion; bản hiện tại **không dùng mốc này để chặn**. Cấm map cosine 0,9 = 90%.
3. Hybrid gồm lexical + semantic; semantic chỉ tìm candidate. Document percentage phải dựa trên coverage metric đã định nghĩa/đánh giá.
4. Baseline sản phẩm là ADVISORY: GVHD xem bằng chứng, SV sửa/nộp version mới; không có auto-gate ở upload, final submission hay bảo vệ. Gate tương lai là yêu cầu mới cần Khoa duyệt policy và thử nghiệm độ chính xác.
5. Theo góp ý GV 03/10, Gemini chưa được kết nối. Thiết kế tương lai chỉ gửi câu hỏi đã lọc và đoạn từ quy định chính thức hoặc tài liệu đã công bố; không gửi tên, MSSV, điểm, kỷ luật hay báo cáo chưa công bố của người khác. Trước khi có bộ lọc kiểm chứng được, không gọi provider.

## Từ vựng metric

| Trường | Ý nghĩa | Có dùng làm 90%? |
| --- | --- | --- |
| semanticCandidateScore | Độ gần embedding ở cặp query/chunk, dùng xếp ứng viên | Không |
| lexicalPairScore | Mức overlap/align của cặp đoạn | Chỉ evidence |
| matchedCoveragePct | Tỷ lệ token hợp lệ thuộc union span match sau loại overlap | Chỉ báo cáo nếu công thức/version được công bố rõ |
| sourceContributionPct | Phần coverage quy cho một nguồn | Giải thích report |
| overallStatus | `POLICY_NOT_CONFIGURED/LOW/REVIEW/HIGH` | Không dùng LOW/HIGH để tự ra quyết định trong baseline |

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

## Điều kiện cho một policy chặn tự động trong tương lai

- Tên metric và công thức chính xác.
- Tokenizer/denominator.
- Corpus scope và snapshot/effective date.
- Exclusion cho trích dẫn, bibliography, template, small match.
- Threshold và action tương ứng.
- Người review và audit lý do.
- Bộ dữ liệu hiệu chỉnh có quyền sử dụng; precision/recall/F1/coverage error.
- Version, effective range và migration khi model/index đổi.

## RAG với Gemini — thiết kế tương lai, chưa bật

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
  Q-->>A: Trích đoạn + provenance
  A->>A: Chỉ quy định chính thức/tài liệu đã công bố; lọc PII trong câu hỏi và đoạn
  A->>G: System instruction + bounded context
  G-->>A: Bản nháp trả lời
  A-->>U: Câu trả lời + citation + link web
~~~

Guardrail bắt buộc:

- Không gửi full document, tài liệu nội bộ chưa công bố hoặc chunk ngoài quyền, kể cả khi người hỏi được xem trong web.
- Không gửi tên, MSSV, ngày sinh, điểm, kỷ luật/án tích hoặc báo cáo chưa công bố của người khác.
- Không dùng Vite/client để giữ API key.
- Retrieved instruction không thể thay system rule hoặc cấp tool quyền.
- AI không có command duyệt topic, phân công, chấm, ký hoặc đổi state.
- Không đủ evidence thì trả “không có nguồn xác thực phù hợp”.
- Audit giữ query hash, scope hash, item IDs, provider/outcome; không giữ nguyên body mặc định.

## Kho và index lifecycle

- Prototype cho phép nguồn `PUBLISHED` và `INTERNAL` được index theo phạm vi được cấp; `REVOKED` bị gỡ khỏi Qdrant. Workflow xuất bản chính thức về sau phải quyết định nguồn nào được index.
- Qdrant payload tối thiểu: repositoryItemId, documentVersionId, departmentId, majorCode, visibility, indexVersion; không chứa PII không cần thiết.
- Prototype lệnh index xử lý revoke bằng deindex ngay và đánh dấu `REMOVED` cho các phiên bản metadata cũ. Outbox/retry bền vững là thiết kế cho giai đoạn sau, chưa có runtime.
- Thay embedding model cần index version mới và re-embedding; không trộn không gian vector thiếu kiểm soát.

## Acceptance criteria

1. Người ngoài scope không retrieve/cite/download tài liệu hạn chế.
2. Semantic score không bao giờ mang nhãn phần trăm tài liệu.
3. Check luôn chỉ ra document/policy/model/index/corpus version.
4. Extraction/job lỗi không đổi workflow và retry không tạo quyết định trùng.
5. Khi policy chưa chốt, API/UI trả `POLICY_NOT_CONFIGURED`, không pass/fail.
6. Khi policy đã chốt và vượt ngưỡng, chỉ chặn bước được cấu hình và yêu cầu sửa; không kết luận đạo văn.
7. AI trả citation/link, không stream file và không mutate nghiệp vụ.

## Quyết định 25/09/2026 cho luồng nộp và prototype

Tải file hợp lệ phải được ghi thành DocumentVersion trước; SimilarityCheck chạy sau upload và không trả kết quả chặn ở bước tiếp nhận. Báo cáo phân biệt lexical evidence, semantic candidate ranking và matched coverage chỉ khi có công thức được đánh giá. Hiện `advisory_similarity` là POC trên topic metadata, không phải kiểm tra đạo văn toàn văn. Không dùng score 0,9 làm “90% giống”. Nếu tương lai Khoa phê duyệt policy và bộ kiểm thử, chỉ xét gate cho FINAL_SUBMISSION/READY_FOR_DEFENSE được nêu rõ trong policy/version; sinh viên vẫn có thể nộp version mới. Đây là thay đổi phạm vi tương lai, không là lỗ hổng của baseline advisory.
