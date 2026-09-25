# Mô hình trạng thái và guard

Tên enum giữ tiếng Anh để dùng xuyên API/CSDL; giải thích bằng tiếng Việt. Tên state là `DERIVED` nếu nguồn chỉ xác nhận ý nghĩa chuyển tiếp.

## Topic và đăng ký

~~~mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> SUBMITTED: người đề xuất gửi
  SUBMITTED --> RETURNED: TBM trả sửa
  RETURNED --> SUBMITTED: gửi lại
  SUBMITTED --> APPROVED: TBM duyệt/chỉnh tên
  SUBMITTED --> REJECTED: TBM từ chối
  APPROVED --> LOCKED: khóa sau chốt đăng ký
~~~

~~~mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> SUBMITTED: SV gửi một topic
  SUBMITTED --> LECTURER_ACCEPTED: GVHD đồng ý
  SUBMITTED --> LECTURER_REJECTED: GVHD từ chối
  LECTURER_ACCEPTED --> FINALIZED: TBM chốt/phân công
  LECTURER_ACCEPTED --> RETURNED: TBM trả lại
  RETURNED --> SUBMITTED
  FINALIZED --> CANCELLED: kết quả đổi/rút hợp lệ
~~~

Guard submit: đủ điều kiện, một registration hoạt động/SV/round, nhóm 1–3. Finalize tạo Thesis/Member/AdvisorAssignment trong một transaction.

## Đề cương

~~~mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> SUBMITTED: SV nộp version
  SUBMITTED --> UNDER_REVIEW: GVHD/GVPB góp ý
  UNDER_REVIEW --> REVISION_REQUIRED: cần sửa
  REVISION_REQUIRED --> SUBMITTED: version mới
  UNDER_REVIEW --> ADVISOR_CONFIRMED: GVHD xác nhận
  ADVISOR_CONFIRMED --> DEPARTMENT_FINALIZED: TBM chốt
  DEPARTMENT_FINALIZED --> PRINT_READY: in bản đã chốt
  PRINT_READY --> DEAN_CONFIRMED: Trưởng khoa ký/xác nhận
~~~

Review trỏ đúng ProposalVersion; Trưởng khoa không được chuyển thẳng từ UNDER_REVIEW.

## Tiến độ và thay đổi

~~~mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> SUBMITTED: SV báo cáo
  SUBMITTED --> REVISION_REQUIRED: GVHD trả sửa
  REVISION_REQUIRED --> SUBMITTED
  SUBMITTED --> CONFIRMED: GVHD xác nhận
~~~

ChangeRequest chỉ cho `TOPIC_CHANGE`: `DRAFT → SUBMITTED → ADVISOR_REVIEWED → APPROVED/REJECTED`. Rút/gia hạn không dùng state machine phê duyệt online; chỉ tạo ExternalProcedureOutcome sau quyết định ngoài.

## DocumentVersion và SimilarityCheck

~~~mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> SUBMITTED
  SUBMITTED --> RESULT_AVAILABLE: SimilarityCheck hoàn tất
  RESULT_AVAILABLE --> REVISION_REQUESTED
  REVISION_REQUESTED --> SUPERSEDED: nộp version mới
  RESULT_AVAILABLE --> ACCEPTED: GVHD xác nhận
  SUBMITTED --> ACCEPTED: nếu policy không bắt buộc kiểm tra
  ACCEPTED --> FINAL: chốt bản cuối
~~~

~~~mermaid
stateDiagram-v2
  [*] --> QUEUED
  QUEUED --> RUNNING
  RUNNING --> COMPLETED
  RUNNING --> FAILED
  FAILED --> QUEUED: retry có quyền
~~~

`QUEUED/RUNNING/FAILED` chỉ thuộc SimilarityCheck; lỗi job không đổi DocumentVersion sang `CHECK_FAILED`. `COMPLETED` chỉ nói job đã xong. Kết luận mức tương đồng cao chỉ hợp lệ khi SimilarityPolicy ACTIVE có exact metric; không có trạng thái PLAGIARISM.

## Hội đồng, phiên và attendance

~~~mermaid
stateDiagram-v2
  [*] --> IMPORTED: nhập quyết định
  IMPORTED --> VALIDATED: đủ 5 role
  VALIDATED --> ACTIVE
  ACTIVE --> CLOSED
~~~

~~~mermaid
stateDiagram-v2
  [*] --> SCHEDULED
  SCHEDULED --> ATTENDANCE_OPEN
  ATTENDANCE_OPEN --> READY: Chair + Secretary có mặt, vắng không quá 2/5
  ATTENDANCE_OPEN --> POSTPONED: không đủ quorum
  READY --> SCORING: bảo vệ và chấm
  SCORING --> FINALIZED: điểm và biên bản hợp lệ
  FINALIZED --> CLOSED
  POSTPONED --> SCHEDULED: xếp lại lịch
~~~

Hệ thống không tự chọn Chair. Chỉ CouncilMember có attendance present mới được submit Evaluation.

## Evaluation, FinalResult và CouncilMinute

~~~mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> SUBMITTED: evaluator submit
  SUBMITTED --> CORRECTED: chính evaluator sửa trước khóa
  CORRECTED --> SUBMITTED
  SUBMITTED --> LOCKED: từ chữ ký đầu hoặc phiên đã ký/khóa
~~~

~~~mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> EXPORTED
  EXPORTED --> VOID: sai trước chữ ký đầu
  VOID --> REPLACED: tạo version thay thế
  EXPORTED --> PRINTED
  PRINTED --> VOID: sai, giấy chưa có chữ ký nào
  PRINTED --> SIGNED: đủ chữ ký Chair + Secretary đúng Hội đồng
  SIGNED --> LOCKED
~~~

- FinalResult được tính lại từ các Evaluation SUBMITTED hợp lệ trước khóa.
- Sau `PRINTED` còn được sửa/in lại nếu Thư ký đối chiếu giấy **chưa có chữ ký nào**; version cũ VOID và bản mới có mã/thời gian. Từ chữ ký đầu tiên không có transition sửa, dù aggregate còn PRINTED tới khi đủ hai chữ ký.
- Mọi transition nhạy cảm có authorization server-side, optimistic concurrency và AuditEvent.

## Thesis

~~~mermaid
stateDiagram-v2
  [*] --> ACTIVE: TBM finalize đăng ký
  ACTIVE --> PROPOSAL_APPROVED: đề cương được Trưởng khoa xác nhận
  PROPOSAL_APPROVED --> IN_PROGRESS: bắt đầu thực hiện
  IN_PROGRESS --> EXTENDED: ghi kết quả gia hạn ngoài
  EXTENDED --> IN_PROGRESS: tiếp tục theo hạn mới
  ACTIVE --> WITHDRAWN: ghi kết quả rút ngoài
  PROPOSAL_APPROVED --> WITHDRAWN: ghi kết quả rút ngoài
  IN_PROGRESS --> READY_FOR_DEFENSE: đủ điều kiện bảo vệ
  READY_FOR_DEFENSE --> DEFENDED: hoàn tất phiên
  DEFENDED --> COMPLETED: bản cuối được xác nhận/lưu trữ
  COMPLETED --> ARCHIVED: kết thúc lưu trữ nghiệp vụ
~~~

## Bảng transition canonical

| Object | From | Event/action | Actor | Guard/business rule | To | Invalid transition điển hình |
| --- | --- | --- | --- | --- | --- | --- |
| Topic | DRAFT/RETURNED | submit | proposer | Đủ trường; round nhận đề xuất | SUBMITTED | APPROVED submit lại → 409 |
| Topic | SUBMITTED | return/reject/approve | TBM | Position đúng department; title change tạo version | RETURNED/REJECTED/APPROVED | Admin approve → 403 |
| Topic | APPROVED | lock after finalization | TBM | Đăng ký đã chốt hoặc policy đóng đề tài | LOCKED | LOCKED mở lại không policy → 409 |
| TopicRegistration | DRAFT | submit | SV | Eligibility confirmed; 1–3 member; unique member/round | SUBMITTED | Member có active registration khác → 409 |
| TopicRegistration | SUBMITTED | accept/reject | GVHD | Đúng candidate/assignment; capacity còn | LECTURER_ACCEPTED/LECTURER_REJECTED | TBM giả lecturer decision → 403 |
| TopicRegistration | LECTURER_ACCEPTED | finalize/return | TBM | Lock topic; unique thesis/topic/round; chỉ tiêu/conflict đạt | FINALIZED/RETURNED | Race capacity → 409 |
| TopicRegistration | RETURNED | sửa và nộp lại | SV | Còn trong đợt, version mới, eligibility còn hiệu lực | SUBMITTED | Tự chuyển FINALIZED → 403 |
| TopicRegistration | DRAFT/SUBMITTED/LECTURER_ACCEPTED/LECTURER_REJECTED/RETURNED | hủy trước chốt | SV hoặc actor được giao theo policy | Chưa tạo Thesis; lưu lý do/lịch sử | CANCELLED | Sau FINALIZED muốn rút phải ghi outcome vào Thesis → 409 |
| Thesis | — | finalize registration | TBM | Registration LECTURER_ACCEPTED | ACTIVE | Tạo trực tiếp không registration → 422 |
| Thesis | ACTIVE | proposal confirmed | Trưởng khoa sau TBM | Proposal DEAN_CONFIRMED sau DEPARTMENT_FINALIZED | PROPOSAL_APPROVED | Bỏ qua TBM/ký → 409 |
| Thesis | PROPOSAL_APPROVED | start execution | hệ thống/round | Đến thời gian và không withdrawn | IN_PROGRESS | Start khi proposal chưa đạt → 409 |
| Thesis | ACTIVE/PROPOSAL_APPROVED/IN_PROGRESS | record withdrawal | actor được giao | Có ExternalProcedureOutcome chính thức | WITHDRAWN | SV tự approve rút → 403 |
| Thesis | IN_PROGRESS | record extension | actor được giao | Có outcome, một lần và thời hạn theo QĐ/policy | EXTENDED | Gia hạn online approval → 422 |
| Thesis | EXTENDED | tiếp tục theo hạn mới | actor được giao | Outcome gia hạn còn hiệu lực | IN_PROGRESS | Hết hạn chưa có kết quả → 409 |
| Thesis | IN_PROGRESS/EXTENDED | mark ready | actor eligibility scope | DefenseEligibilityCheck ELIGIBLE; similarity gate chỉ khi policy ACTIVE | READY_FOR_DEFENSE | Advisory similarity tự chặn → 409 |
| Thesis | READY_FOR_DEFENSE | defense complete | hệ thống/CT-TK | Session đủ quorum và scoring closed | DEFENDED | Không quorum → 409 |
| Thesis | DEFENDED | archive final | actor công bố | Bản sửa cuối/GVHD xác nhận theo QĐ | COMPLETED | Draft publish → 422 |
| Thesis | COMPLETED | close lifecycle | actor được giao | Hồ sơ lưu trữ đầy đủ | ARCHIVED | ARCHIVED sửa nội dung → 409 |
| Proposal | DRAFT/REVISION_REQUIRED | submit version | SV | Latest version CLEAN | SUBMITTED | Ghi đè version → 409 |
| Proposal | SUBMITTED | open review | GVHD/GVPB | Assignment đúng version | UNDER_REVIEW | Reviewer ngoài scope → 403 |
| Proposal | UNDER_REVIEW | request revision/advisor confirm | GVHD | Review latest version | REVISION_REQUIRED/ADVISOR_CONFIRMED | Confirm version cũ → 409 |
| Proposal | ADVISOR_CONFIRMED | department finalize | TBM | Đúng scope | DEPARTMENT_FINALIZED | Dean finalize nội dung → 403 |
| Proposal | DEPARTMENT_FINALIZED | print ready | actor được giao | Bản đã chốt, version cố định | PRINT_READY | In version cũ → 409 |
| Proposal | PRINT_READY | dean confirm | Trưởng khoa | Position hiệu lực; ký/xác nhận bản đúng version | DEAN_CONFIRMED | Under review ký → 409 |
| ProgressReport | DRAFT/REVISION_REQUIRED | submit | SV | Milestone OPEN | SUBMITTED | Milestone CLOSED → 409 |
| ProgressReport | SUBMITTED | return/confirm | GVHD | AdvisorAssignment hiệu lực | REVISION_REQUIRED/CONFIRMED | GVPB không assignment → 403 |
| DocumentVersion | DRAFT | submit | SV | File CLEAN; type/size hợp lệ | SUBMITTED | Malware REJECTED → 422 |
| DocumentVersion | SUBMITTED | check completed | worker | SimilarityCheck COMPLETED; đúng version | RESULT_AVAILABLE | Client tự ghi result → 403 |
| DocumentVersion | SUBMITTED/RESULT_AVAILABLE | request revision/accept | GVHD | Đúng AdvisorAssignment; policy effect hợp lệ; có thể không yêu cầu check | REVISION_REQUESTED/ACCEPTED | Policy chưa ACTIVE tự HIGH-block → 409 |
| DocumentVersion | REVISION_REQUESTED | supersede | SV | Version mới đã submit | SUPERSEDED | Sửa bytes cũ → 409 |
| DocumentVersion | ACCEPTED | finalize | actor được giao | Đúng bản cuối và scope | FINAL | Draft thành FINAL → 409 |
| SimilarityCheck | QUEUED | start | worker | Lease/job token hợp lệ | RUNNING | Client start → 403 |
| SimilarityCheck | RUNNING | complete/fail | worker | Lưu provenance | COMPLETED/FAILED | COMPLETED sửa metric → 409 |
| SimilarityCheck | FAILED | retry | worker | Retry được cho phép; giữ log lần lỗi | QUEUED | Client tự retry qua state → 403 |
| Council | — | import | actor được ủy quyền | decisionRef/tệp có | IMPORTED | Auto-generate Council → 422 |
| Council | IMPORTED | validate | actor xác nhận | Đúng 5 người/role; conflict check | VALIDATED | Thiếu Chair/Secretary → 422 |
| Council | VALIDATED | activate | actor xác nhận | Decision còn hiệu lực | ACTIVE | Hệ thống tự chọn Chair → 422 |
| Council | ACTIVE | close | actor được giao | Các phiên liên quan đã đóng | CLOSED | Còn phiên đang chấm → 409 |
| DefenseSession | SCHEDULED | open attendance | TK | Council ACTIVE | ATTENDANCE_OPEN | Session closed → 409 |
| DefenseSession | ATTENDANCE_OPEN | confirm quorum | CT/TK | CT+TK có mặt; vắng không quá 2/5 | READY/POSTPONED | Không quorum mà READY → 422 |
| DefenseSession | POSTPONED | reschedule | CT/TK | Lịch mới, quyết định vẫn hiệu lực | SCHEDULED | Tự READY khi chưa điểm danh → 409 |
| DefenseSession | READY | open defense | CT | Thesis list và eligibility hợp lệ | SCORING | Thesis chưa eligible → 422 |
| DefenseSession | SCORING | finalize | CT/TK | Phiếu hợp lệ, FinalResult và minute đủ theo policy | FINALIZED | Thiếu phiếu bị coi 0 → 422 |
| DefenseSession | FINALIZED | close | actor được giao | Biên bản đã ký/khóa | CLOSED | Sửa điểm từ chữ ký đầu → 409 |
| Evaluation | DRAFT/CORRECTED | submit | evaluator | Present; own form; rubric max; total gồm bonus ≤10 | SUBMITTED | Thư ký nhập thay → 403 |
| Evaluation | SUBMITTED | correct | chính evaluator | Trước chữ ký đầu; Thư ký xác nhận bản giấy chưa ký nếu đã in; có reason/audit | CORRECTED | Người khác sửa → 403 |
| Evaluation | SUBMITTED | lock | hệ thống | Session/minute lock | LOCKED | LOCKED sửa → 409 |
| CouncilMinute | DRAFT | export | TK | Attendance/result completeness | EXPORTED | Thiếu result → 422 |
| CouncilMinute | EXPORTED | void | TK | Chưa có chữ ký; có reason, giấy in cũ được đối chiếu | VOID | Đã có chữ ký void → 409 |
| CouncilMinute | VOID | tạo bản thay thế | TK | Có reason và MinuteVersion mới liên kết bản sai | REPLACED | Dùng lại bản VOID để ký → 409 |
| CouncilMinute | EXPORTED | mark printed | TK | Latest non-void version | PRINTED | Version đã VOID → 409 |
| CouncilMinute | PRINTED | sign/confirm | CT hoặc TK | Cả Chair và Secretary từ quyết định ký đúng MinuteVersion; transaction kiểm đủ hai | SIGNED sau chữ ký thứ hai | Người ngoài/TBM → 403; chữ ký đầu giữ PRINTED nhưng khóa sửa |
| CouncilMinute | SIGNED | lock | hệ thống | Signature valid | LOCKED | Hậu ký sửa → 409 |

## Nguyên tắc tránh status explosion

- Job state (`QUEUED/RUNNING/FAILED`) tách khỏi business decision (`ACCEPTED/REVISION_REQUESTED`).
- Permission không được mã hóa thành status; cùng state nhưng action khác nhau theo assignment/resource.
- `PENDING_POLICY/NOT_CONFIGURED` chỉ dùng khi kết quả thực sự chưa thể quyết định, không tạo nhiều state đồng nghĩa.
- Mọi transition không liệt kê bị từ chối mặc định bằng `409`; thiếu quyền là `403/404`, vi phạm dữ liệu/rule là `422`.
