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
| Expertise | `GET/POST /lecturer-expertise`, `POST /lecturer-expertise/{id}/verify` | UC-EXP-001; verify theo TBM đúng Bộ môn; nếu tự kiểm thì Trưởng khoa/người được giao. |
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
| Biên bản | `POST /defense-sessions/{id}/minutes`, `POST /council-minutes/{id}/export`, `.../void`, `.../mark-printed`, `.../chair-confirmation` | UC-MIN-001/002; sửa sau in trước chữ ký đầu qua evaluator correction + minute replacement; không có endpoint sửa sau ký. |
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
- Response gồm answer, citations `{repositoryItemId, sourceId, sourceType, originType, sourceVersion, provenance, title, route}`, và `evidenceStatus`.
- Không trả storage key, raw prompt, raw chunks không cần thiết hoặc download URL vĩnh viễn.

File contract máy đọc: `openapi.yaml`.

## Hợp đồng prototype đang chạy

Nguồn OpenAPI máy đọc được: `docs/prototype/openapi-runtime.json` sinh từ FastAPI. Trong `docs/design/openapi.yaml`, operation có `x-runtime-status=IMPLEMENTED_PROTOTYPE` là endpoint thật; các operation còn lại là contract thiết kế, chưa được triển khai và một số payload/result còn generic cần khóa trước các giai đoạn sau.

| Endpoint | Input có kiểu | Output có kiểu | Guard chính |
| --- | --- | --- | --- |
| GET /me/context | X-Dev-User-Id trong DEV/TEST | ContextOut: user_id, base_role, profile IDs, actions | Không bật ngoài DEV/TEST |
| GET /topics, /topics/{id} | round_id/limit hoặc topic UUID | TopicOut | Chỉ APPROVED trong prototype |
| GET /eligible-students | round_id UUID | EligibleStudentOut[] | SV cùng bộ môn có snapshot CONFIRMED |
| POST /topic-registrations | RegistrationCreate: topic_id, member_student_ids[1..3] | RegistrationOut + row_version | SV tạo bản nháp, có chính mình, capacity/round/eligibility/unique; thành viên bắt đầu PENDING |
| GET /topic-registrations, /{id} | —/UUID | RegistrationOut[]/RegistrationOut | Thành viên, GV đề xuất hoặc TBM theo scope |
| POST /{id}/member-response | consent_status: ACCEPTED/DECLINED; user ID không nhận từ body | RegistrationOut có trạng thái từng thành viên | Chỉ chính SV đang đăng nhập; một lần khi DRAFT; lưu actor/thời điểm |
| POST /{id}/submit | — | RegistrationOut | Chỉ nhóm trưởng; mọi thành viên active đã ACCEPTED, còn đủ điều kiện và đợt còn mở; khóa nhóm |
| POST /{id}/cancel | — | RegistrationOut | Chỉ nhóm trưởng, chỉ DRAFT; đánh CANCELLED và giải phóng thành viên |
| POST /{id}/lecturer-decision | LecturerDecision ACCEPT/REJECT + If-Match | RegistrationOut | Chỉ GV đề xuất topic; không ghép thành viên |
| POST /{id}/department-finalization | If-Match | RegistrationOut + thesis_id | TBM đúng bộ môn, transaction tạo Thesis/member/advisor |
| GET /theses/{id} | UUID | ThesisOut | Thành viên/GVHD/TBM đúng scope |
| POST /ai/similar-topics | title, abstract, keywords, domain, limit | SearchResult[] có source_type/provenance | Qdrant filter visibility/scope; score chỉ ranking |
| POST /ai/chat | question | ChatOut: NO_EVIDENCE/RETRIEVAL_ONLY/citations | Không Gemini key thì answer=null |

Các lỗi validation của FastAPI dùng HTTP 422; lỗi quyền/state do service dùng 403/404/409. `If-Match` hiện là row_version nguyên; finalization lặp được nếu đã FINALIZED và cùng TBM. Đây là API prototype, chưa là hợp đồng production SSO.

## Contract thiết kế bổ sung

- `POST /topic-registrations/{registrationId}/member-response`: đã chạy trong prototype cho bản DRAFT. Không nhận user ID từ body; service tìm thành viên bằng StudentProfile của tài khoản DEV/TEST hiện hành, chỉ nhận phản hồi đầu tiên, lưu trạng thái/actor/thời điểm và không cho đổi sau SUBMITTED. Vì không có endpoint chỉnh thành viên, nhóm trưởng hủy bản nháp nếu có người từ chối hoặc chọn sai nhóm rồi tạo bản nháp mới.
- `POST /topic-registrations/{registrationId}/submit` và `/cancel`: đã chạy. Chỉ nhóm trưởng gửi/hủy; gửi cần 1–3 thành viên active đã ACCEPTED, mỗi người còn snapshot đủ điều kiện và topic/round còn mở. Hủy chỉ dùng khi DRAFT, giữ hàng thành viên không active để tra lại lịch sử.
- Đề tài do SV đề xuất: `POST /topics` tạo đề tài của SV cùng bản nháp đăng ký; sau các xác nhận, nhóm gửi đăng ký **trước** khi TBM xử lý `/topics/{topicId}/department-decision`. Khi TBM APPROVED, giảng viên được phân công mới nhận/từ chối; TBM finalize sau khi GV đồng ý. Guard `Topic.APPROVED` của `POST /topic-registrations` hiện chỉ là lát cắt prototype cho đề tài GV, cần tách nhánh trước runtime thật. **DESIGN_ONLY**.

- `POST /council-minutes/{minuteId}/chair-confirmation` và `.../secretary-confirmation`: MinuteSignatureRequest có minuteVersionId; chỉ đúng role trong quyết định được ký; chữ ký đầu khóa sửa dù state còn PRINTED, đủ hai mới SIGNED. DESIGN_ONLY.
- `POST /council-minutes/{minuteId}/exports`: OfficialExportRequest có templateVersion/format, result chứa storedFileId/contentHash/templateSourceId. BLOCKED_SOURCE_TEMPLATE với Mẫu 9 local đã điền.
- `GET /external-resources`: ExternalResource[] chỉ từ allowlist HTTPS server-side. DESIGN_ONLY.
- RepositoryItem contract có originType/sourceType/title/visibility/sourceRef/version/provenance. Với nhập ngoài không yêu cầu Thesis giả.
