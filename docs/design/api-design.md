# Thiết kế REST API

## Quy ước

- Base path: `/api/v1`; Bearer token.
- Mọi mutation kiểm tra quyền ngữ cảnh, state, `If-Match`/version và `Idempotency-Key` khi cần.
- Lỗi chuẩn: `401` chưa xác thực; `403` thiếu quyền; `404` không tồn tại/không được lộ; `409` xung đột state/version/invariant; `422` vi phạm rule; `503` dependency lỗi.
- List/search phải filter quyền như mutation. API không nhận `baseRole`, `approved`, `scoreOwner`, `storageKey` từ client làm căn cứ tin cậy.

## Nhóm endpoint

| Nhóm | Endpoint chính | Use Case / ghi chú |
| --- | --- | --- |
| Context | `GET /me` | UC-AUTH-001; trả effective contexts/actions, không cấp quyền từ client. |
| Năm/đợt | `GET/POST /academic-years`, `GET/POST /thesis-rounds` | UC-ROUND-001. |
| Điều kiện | `POST /rounds/{id}/eligibility-snapshots`, `POST /eligibility-snapshots/{id}/confirm` | UC-ELIG-001; snapshot bất biến sau confirm. |
| Expertise | `GET/POST /lecturer-expertise`, `POST /lecturer-expertise/{id}/verify` | UC-EXP-001; verify chỉ bật theo OPEN-01/policy. |
| Topic | `GET/POST /topics`, `PATCH /topics/{id}`, `POST /topics/{id}/department-decision`, `PUT /topics/{id}/requirements` | UC-TOPIC-001..003. |
| Đăng ký | `POST /topic-registrations`, `POST /.../{id}/lecturer-decision`, `POST /.../{id}/department-finalization` | UC-REG-001/002, UC-ASSIGN-001. |
| Phân công nhóm | `GET/POST /theses/{id}/work-assignments`, `POST /work-assignments/{id}/advisor-decision` | UC-WORK-001. |
| Đề cương | `POST /theses/{id}/proposal-versions`, `POST /proposal-versions/{id}/reviews`, `POST /proposals/{id}/advisor-confirmation`, `.../department-finalization`, `.../dean-confirmation`, `GET .../print` | UC-PROP-001..004. |
| Tiến độ | `GET /rounds/{id}/milestones`, `POST /theses/{id}/progress-reports`, `POST /progress-reports/{id}/advisor-review` | UC-PROG-001/002. |
| Thay đổi | `POST /theses/{id}/change-requests`, `POST /theses/{id}/external-procedure-outcomes` | UC-CHANGE-001, UC-EXT-001; endpoint sau chỉ record outcome. |
| File/tài liệu | `POST /uploads`, `POST /theses/{id}/documents`, `POST /documents/{id}/versions` | UC-DOC-001; upload quarantine trước version. |
| Tương đồng | `POST /document-versions/{id}/similarity-checks`, `GET /similarity-checks/{id}` | UC-SIM-001; client không truyền threshold; không trả plagiarism verdict. |
| Hội đồng | `POST /councils/import-decision`, `POST /councils/{id}/defense-sessions`, `PUT /defense-sessions/{id}/theses` | UC-COUNCIL-001, UC-SESSION-001. |
| Attendance | `PUT /defense-sessions/{id}/attendance`, `POST /defense-sessions/{id}/open` | Check quorum server-side. |
| Nhận xét | `POST /theses/{id}/advisor-reviews`, `POST /theses/{id}/reviewer-reviews` | UC-EVAL-001; đúng Mẫu 7/8 và assignment. |
| Chấm | `POST /defense-sessions/{id}/evaluations`, `PATCH /evaluations/{id}`, `GET /defense-sessions/{id}/final-results` | UC-EVAL-002/003; chỉ evaluator sửa điểm mình trước khóa. |
| Biên bản | `POST /defense-sessions/{id}/minutes`, `POST /council-minutes/{id}/export`, `.../void`, `.../mark-printed`, `.../chair-confirmation` | UC-MIN-001/002; không có endpoint sửa hậu ký. |
| Kho | `GET /repository/documents`, `GET /repository/documents/{id}/download` | UC-REPO-001; route có authorization. |
| AI | `POST /ai/chat` | UC-AI-001; read-only, trả citation/link, không file bytes. |
| Báo cáo | `GET /reports/eligibility`, `/progress`, `/councils`, `/score-summary` | UC-RPT-001; field-level authorization. |

## Contract nhạy cảm

### Chấm điểm

- Request định danh `thesisMemberId`, rubric items, comment; evaluator lấy từ token + CouncilMember, không nhận từ client.
- Server kiểm attendance, session state, rubric max; lưu Evaluation riêng từng SV.
- FinalResult trả `scorerCount`, `averageScore`, `bonusScore`, `finalScore`, `calculationVersion`.

### Similarity

- Kết quả tách `lexicalCoveragePct`, `semanticCandidateScore`, matches và provenance.
- Nếu policy chưa được duyệt: `overallStatus=POLICY_NOT_CONFIGURED`; không chặn workflow.
- Khi policy ACTIVE: response có `businessThreshold`, `metricName`, `decisionEffect`; thông điệp dùng “tương đồng cao”.

### RAG

- Request chỉ gồm câu hỏi và context selector hợp lệ; backend tự resolve scope.
- Response gồm answer, citations `{repositoryItemId, documentVersionId, title, route}`, và `evidenceStatus`.
- Không trả storage key, raw prompt, raw chunks không cần thiết hoặc download URL vĩnh viễn.

File contract máy đọc: `openapi.yaml`.
