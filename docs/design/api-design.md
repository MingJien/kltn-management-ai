# Thiết kế REST API

## Quy ước

Phạm vi runtime ngày 04/10: GV tạo/sửa/gửi đề tài → TBM đúng bộ môn duyệt/trả/từ chối → SV lập nhóm, từng thành viên xác nhận → nhóm trưởng gửi → GV đề xuất chấp nhận/từ chối. Đăng nhập demo bằng email/mật khẩu và phiên cookie. Luồng yêu cầu dừng ở `LECTURER_ACCEPTED`; API chốt thành khóa luận do TBM đã có từ prototype trước nhưng không thuộc mốc này. Phân công GVHD tổng quát, tiến độ, tài liệu và đăng ký tài khoản dùng thật thuộc giai đoạn sau. Các endpoint tổng thể bên dưới chưa mặc nhiên là runtime.

- Base path: `/api/v1`; phiên cookie cho phương án đăng nhập email đã chọn; UUID header chỉ DEV/TEST. Bearer token trong đặc tả tổng thể là phương án thiết kế cần đồng bộ khi triển khai auth, chưa đại diện cho runtime.
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

Nguồn OpenAPI máy đọc được của API đang chạy là `/openapi.json` hoặc `/docs` do FastAPI sinh. Trong `docs/design/openapi.yaml`, operation có `x-runtime-status=IMPLEMENTED_PROTOTYPE` là endpoint thật; các operation còn lại là contract thiết kế, chưa được triển khai và một số payload/result còn generic cần khóa trước các giai đoạn sau.

| Endpoint | Input có kiểu | Output có kiểu | Guard chính |
| --- | --- | --- | --- |
| POST /auth/login, /auth/logout | Email/mật khẩu, cookie phiên | 204 | ACTIVE, email đã xác minh; sai nhiều lần bị giới hạn; cookie HttpOnly |
| GET /me/context | Cookie phiên; X-Dev-User-Id chỉ DEV/TEST | ContextOut: user, profile, phạm vi/actions | Backend tính quyền từ hồ sơ và assignment |
| GET /rounds/open | — | OpenRoundOut[] | Đợt đang mở theo thời gian |
| GET /topics, /topics/{id} | round_id/limit hoặc topic UUID | TopicOut | SV thấy đề tài GV APPROVED và đề xuất của nhóm mình; GV thấy đề tài của mình và hàng chờ TBM cùng bộ môn |
| POST /topics; PATCH /topics/{id}; POST /topics/{id}/submit | TopicCreate/Update; If-Match khi sửa/gửi | TopicOut | GV đề xuất; DRAFT/RETURNED; giữ lịch sử tiêu đề |
| POST /topics/{id}/department-decision | APPROVE/RETURN/REJECT, If-Match, lý do khi trả/từ chối | TopicOut | TBM đúng bộ môn; không tự duyệt đề tài mình; lưu audit |
| GET /eligible-students | round_id UUID | EligibleStudentOut[] | SV cùng bộ môn có snapshot CONFIRMED |
| POST /topic-registrations | RegistrationCreate: topic_id, member_student_ids[1..3] | RegistrationOut + row_version | SV tạo bản nháp, có chính mình, capacity/round/eligibility/unique; thành viên bắt đầu PENDING; confirm_creator chỉ xác nhận chính tài khoản gửi |
| GET /topic-registrations, /{id} | —/UUID | RegistrationOut[]/RegistrationOut | Thành viên; GV tiếp nhận/TBM chỉ sau khi nhóm đã gửi |
| POST /{id}/member-response | consent_status: ACCEPTED/DECLINED; user ID không nhận từ body | RegistrationOut có trạng thái từng thành viên | Chỉ chính SV đang đăng nhập; một lần khi DRAFT; lưu actor/thời điểm |
| POST /{id}/submit | — | RegistrationOut | Chỉ nhóm trưởng; mọi thành viên active đã ACCEPTED, còn đủ điều kiện và đợt còn mở; khóa nhóm |
| POST /{id}/cancel | — | RegistrationOut | Chỉ nhóm trưởng, DRAFT/RETURNED; đánh CANCELLED và giải phóng thành viên |
| POST /{id}/lecturer-decision | LecturerDecision ACCEPT/REJECT + If-Match | RegistrationOut | Chỉ GV tiếp nhận, topic APPROVED; từ chối cần lý do; không ghép thành viên |
| POST /{id}/department-finalization | If-Match | RegistrationOut + thesis_id | TBM đúng bộ môn, transaction tạo Thesis/member/advisor |
| GET /theses/{id} | UUID | ThesisOut | Thành viên/GVHD/TBM đúng scope |
| POST /ai/similar-topics | title, abstract, keywords, domain, limit | SearchResult[] có source_type/provenance | Qdrant filter visibility/scope; score chỉ ranking |
| POST /ai/chat | question | ChatOut: NO_EVIDENCE/RETRIEVAL_ONLY/citations | Không Gemini key thì answer=null |

Các lỗi validation của FastAPI dùng HTTP 422; lỗi quyền/state do service dùng 403/404/409. `If-Match` hiện là row_version nguyên; finalization lặp được nếu đã FINALIZED và cùng TBM. Đăng nhập email/mật khẩu và cookie phiên đã chạy với tài khoản giả; cấp tài khoản, xác minh email và khôi phục mật khẩu dùng thật chưa triển khai. OIDC scaffold chưa kết nối Trường.

## Contract thiết kế bổ sung

- `POST /topic-registrations/{registrationId}/member-response`: đã chạy trong prototype cho bản DRAFT. Không nhận user ID từ body; service tìm thành viên bằng StudentProfile của tài khoản DEV/TEST hiện hành, chỉ nhận phản hồi đầu tiên, lưu trạng thái/actor/thời điểm và không cho đổi sau SUBMITTED. Vì không có endpoint chỉnh thành viên, nhóm trưởng hủy bản nháp nếu có người từ chối hoặc chọn sai nhóm rồi tạo bản nháp mới.
- `POST /topic-registrations/{registrationId}/submit` và `/cancel`: đã chạy. Chỉ nhóm trưởng gửi/hủy; gửi cần 1–3 thành viên active đã ACCEPTED, mỗi người còn snapshot đủ điều kiện và topic/round còn mở. Hủy dùng khi DRAFT/RETURNED, giữ hàng thành viên không active để tra lại lịch sử.
- Đề tài do SV đề xuất: `POST /student-proposals` tạo đề tài và bản nháp đăng ký trong một transaction. Sau các xác nhận, nhóm gửi đăng ký **trước** khi TBM xử lý `/topics/{topicId}/department-decision`. TBM xác nhận/chọn GV tiếp nhận; khi đề tài APPROVED, GV mới nhận/từ chối. Nhánh này đã chạy và được kiểm thử; GV tiếp nhận chưa phải quyết định phân công GVHD chính thức.

- `POST /council-minutes/{minuteId}/chair-confirmation` và `.../secretary-confirmation`: MinuteSignatureRequest có minuteVersionId; chỉ đúng role trong quyết định được ký; chữ ký đầu khóa sửa dù state còn PRINTED, đủ hai mới SIGNED. DESIGN_ONLY.
- `POST /council-minutes/{minuteId}/exports`: OfficialExportRequest có templateVersion/format, result chứa storedFileId/contentHash/templateSourceId. BLOCKED_SOURCE_TEMPLATE với Mẫu 9 local đã điền.
- `GET /external-resources`: ExternalResource[] chỉ từ allowlist HTTPS server-side. DESIGN_ONLY.
- RepositoryItem contract có originType/sourceType/title/visibility/sourceRef/version/provenance. Với nhập ngoài không yêu cầu Thesis giả.

## Hợp đồng runtime đề tài và đăng ký (0011)

Nguồn API chạy thật là `/openapi.json` của FastAPI; bản đặc tả toàn miền còn chứa endpoint cho giai đoạn sau.

| API | Quyền và xử lý |
| --- | --- |
| GET /rounds/open | SV/GV; tên năm học, chỉ hiện số đợt khi có nhiều đợt cùng năm. |
| GET /lecturers | Danh sách GV hoạt động cùng bộ môn để đề nghị/xác nhận người tiếp nhận. |
| POST/PATCH /topics | GV tạo/sửa bản nháp hoặc bản trả lại; mã đề tài theo năm duy nhất, requirements có cấu trúc. SV chỉ sửa đề xuất của mình ở trạng thái cho phép. |
| POST /student-proposals | SV đại diện tạo đề tài và đăng ký trong một transaction; nhóm chọn GV mong muốn, chưa bỏ qua TBM. |
| POST /topics/{id}/department-decision | TBM đúng bộ môn duyệt/trả/từ chối; sửa tên giữ phiên bản cũ, chọn GV cùng bộ môn. Cấm tự duyệt đề tài mình tạo. |
| POST /topic-registrations | Cá nhân/nhóm tối đa sức chứa; một đăng ký hoạt động mỗi SV/đợt; điều kiện lấy phiên bản snapshot mới nhất. confirm_creator chỉ xác nhận chính người đang đăng nhập. |
| POST /topic-registrations/{id}/member-response | Mỗi SV tự xác nhận; không được xác nhận thay người khác. |
| POST /topic-registrations/{id}/submit | Đại diện gửi sau khi tất cả đồng ý; SV đề xuất gửi đăng ký trước rồi chờ TBM duyệt đề tài. |
| POST /topic-registrations/{id}/lecturer-decision | Chỉ GV tiếp nhận, đề tài phải APPROVED; từ chối cần lý do; tối đa một nhóm được chấp nhận mỗi đề tài. |
| POST /topic-registrations/{id}/evidence | Body binary, X-File-Name URL-encoded; mỗi SV chỉ tải cho mình, PDF/PNG/JPEG ≤5 MB khi DRAFT/RETURNED. |
| GET /topic-registrations/{id}/members/{student_id}/evidence | Nhóm hoặc GV tiếp nhận/TBM sau khi gửi; attachment, no-store, nosniff. Không có URL file công khai. |

GPA bổ sung của GV là tiêu chí phù hợp để GV xem minh chứng, không thay điều kiện Khoa đã xác nhận. Khi đề tài SV bị trả lại, nhóm giữ thành viên, sửa nội dung rồi gửi lại; khi bị từ chối, đăng ký kết thúc và giải phóng thành viên. Không tự biến GV tiếp nhận thành quyết định phân công GVHD chính thức ở bước này.
