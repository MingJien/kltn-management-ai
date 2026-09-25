# Đặc tả Use Case canonical — NV4 Tuần 1

## Quy ước

Mỗi Use Case dưới đây là đơn vị triển khai/kiểm thử riêng. `Permission` luôn được kiểm ở backend theo base role + position/assignment + resource + state; UI không cấp quyền. Trường `Source/Status` phân biệt quy định, quyết định dự án và phần còn OPEN.

### UC-AUTH-001 — Đăng nhập và xác lập ngữ cảnh quyền

- **Primary Actor / Supporting Actor:** Người dùng / dịch vụ xác thực, authorization service.
- **Precondition / Trigger:** Tài khoản hoạt động / người dùng đăng nhập hoặc gọi API.
- **Input:** credential/token; request resource nếu có.
- **Main Flow:** xác thực → nạp base role → position/assignment hiệu lực → tính action theo resource/state → tạo correlation.
- **Alternative/Exception:** token lỗi `401`; không scope/action `403/404`; `ADMIN` không bypass.
- **Output / Postcondition:** identity context, effective actions và audit correlation; không đổi state nghiệp vụ.
- **Rule / Permission / Data:** BR-AUTH-001..002; chủ tài khoản; UserAccount, PositionAssignment.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 / `CONFIRMED_PROJECT_DECISION`.

### UC-ROUND-001 — Quản lý năm học và đợt KLTN

- **Primary Actor / Supporting Actor:** TBM/Trưởng khoa theo position / hệ thống.
- **Precondition / Trigger:** Có scope tổ chức / cần mở đợt chính hoặc bổ sung.
- **Input:** academic year, round code/type, time window, policy version.
- **Main Flow:** tạo năm học → tạo `MAIN/SUPPLEMENTARY` → cấu hình policy → mở/đóng đợt.
- **Alternative/Exception:** mốc không hợp lệ/chồng trái policy `422`; version conflict `409`.
- **Output / Postcondition:** round có version policy; `DRAFT → OPEN → CLOSED`.
- **Rule / Permission / Data:** BR-ROUND-001; position đúng scope; AcademicYear, ThesisRound, RoundPolicy.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919, SRC-PROJECT-MASTER-001 / `CONFIRMED_PROJECT_DECISION`; deadline là cấu hình theo round.

### UC-ELIG-001 — Khảo sát và xác nhận SV đủ điều kiện

- **Primary Actor / Supporting Actor:** SV, `ELIGIBILITY_VERIFIER` / import service, TBM/Khoa xem theo scope.
- **Precondition / Trigger:** Round tiếp nhận khảo sát / SV tự khai hoặc dữ liệu được đồng bộ.
- **Input:** tín chỉ đạt, tổng tín chỉ, GPA, tình trạng kỷ luật/truy cứu, evidence/source time.
- **Main Flow:** lưu snapshot → kiểm QĐ5964/policy version → verifier đối chiếu → confirm hoặc reject có lý do.
- **Alternative/Exception:** dữ liệu chưa xác nhận giữ `PENDING`; ngoại lệ cần decision_ref; actor cụ thể còn OPEN.
- **Output / Postcondition:** EligibilitySnapshot bất biến `CONFIRMED/REJECTED`, đủ căn cứ mở đăng ký.
- **Rule / Permission / Data:** BR-ELIG-001..002; SV chỉ sửa trước submit, verifier đúng round mới confirm; EligibilitySnapshot/Exception.
- **Source / Status:** SRC-QD-2919, SRC-QD-5964, SRC-GVHD-NV4-001 / rule `CONFIRMED`, actor được Khoa giao theo round.

### UC-EXP-001 — Khai báo chuyên môn giảng viên

- **Primary Actor / Supporting Actor:** Giảng viên / TBM `PROPOSED`.
- **Precondition / Trigger:** LecturerProfile hoạt động / giảng viên cập nhật hồ sơ.
- **Input:** lĩnh vực, từ khóa, minh chứng, version.
- **Main Flow:** tạo version → lưu evidence → công bố nhãn `SELF_DECLARED`.
- **Alternative/Exception:** verify bị từ chối nếu sai chức vụ/scope, tự verify hoặc thiếu minh chứng; evidence lỗi không đổi trạng thái verified.
- **Output / Postcondition:** hồ sơ chuyên môn versioned; `DRAFT → SELF_DECLARED`; verified chưa kích hoạt.
- **Rule / Permission / Data:** chủ hồ sơ C/U; LecturerExpertise, ExpertiseEvidence.
- **Source / Status:** SRC-GVHD-NV4-001 / phần tự khai `CONFIRMED`, verifier TBM đúng Bộ môn; Trưởng khoa/người được giao khi TBM là chủ hồ sơ.

### UC-TOPIC-001 — Giảng viên đề xuất đề tài

- **Primary Actor / Supporting Actor:** Giảng viên / TBM.
- **Precondition / Trigger:** Round nhận đề xuất / giảng viên tạo topic.
- **Input:** title, department/major, mô tả, TopicRequirement mong muốn.
- **Main Flow:** lưu draft → gửi → TBM xử lý tại UC-TOPIC-003.
- **Alternative/Exception:** thiếu thông tin/trùng tiềm năng thì trả sửa; preferred GPA không auto-reject SV.
- **Output / Postcondition:** Topic `DRAFT → SUBMITTED`.
- **Rule / Permission / Data:** BR-TOPIC-001..002; proposer chỉ sửa draft/returned; Topic/TitleVersion/Requirement.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919, SRC-PROJECT-MASTER-001 / `CONFIRMED`.

### UC-TOPIC-002 — Sinh viên đề xuất đề tài

- **Primary Actor / Supporting Actor:** SV / TBM; GVHD tiềm năng chỉ xem khi được phân công.
- **Precondition / Trigger:** SV thuộc round và đủ điều kiện / không chọn topic có sẵn.
- **Input:** title, mô tả, phạm vi Bộ môn/đợt; chưa lưu GVHD đề xuất khi chưa có rule xác định.
- **Main Flow:** SV gửi đề xuất → TBM xử lý tại UC-TOPIC-003; việc GVHD đồng ý/từ chối áp dụng cho đăng ký ở UC-ASSIGN-001, không phải một state riêng của Topic.
- **Alternative/Exception:** thiếu thông tin thì TBM trả sửa; không tự tạo AdvisorAssignment.
- **Output / Postcondition:** Topic `DRAFT → SUBMITTED`.
- **Rule / Permission / Data:** BR-TOPIC-001; SV tạo, TBM đúng scope review; Topic.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919 / `CONFIRMED`.

### UC-TOPIC-003 — Duyệt và chỉnh tên đề tài

- **Primary Actor / Supporting Actor:** TBM / proposer.
- **Precondition / Trigger:** Topic `SUBMITTED` / có đề tài chờ xử lý.
- **Input:** decision, title chuẩn hóa, reason.
- **Main Flow:** kiểm scope/khả thi/trùng → tạo TopicTitleVersion nếu chỉnh → approve và mở đăng ký.
- **Alternative/Exception:** return/reject có lý do; title cũ không bị ghi đè.
- **Output / Postcondition:** `SUBMITTED → APPROVED/RETURNED/REJECTED`.
- **Rule / Permission / Data:** BR-TOPIC-001..002; chỉ TBM đúng scope approve/chỉnh; Topic, TopicTitleVersion.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919 / `CONFIRMED`.

### UC-REG-001 — Đăng ký một đề tài

- **Primary Actor / Supporting Actor:** SV / hệ thống.
- **Precondition / Trigger:** Eligibility confirmed, round/topic mở / SV chọn topic.
- **Input:** topicId, danh sách 1–3 studentId, coordinator.
- **Main Flow:** kiểm từng member chưa có active registration/round → kiểm capacity → tạo registration/member → submit.
- **Alternative/Exception:** nguyện vọng thứ hai, member trùng, >3, topic đóng hoặc không đủ điều kiện thì `409/422`.
- **Output / Postcondition:** TopicRegistration `SUBMITTED`; chưa tạo Thesis.
- **Rule / Permission / Data:** BR-REG-001..002, BR-REG-005; thành viên xác nhận tham gia theo policy; TopicRegistration/RegistrationMember.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919, SRC-MAU-01A/01B / `CONFIRMED_PROJECT_DECISION`; danh sách khóa sau SUBMITTED.

### UC-REG-002 — Xử lý đăng ký nhóm

- **Primary Actor / Supporting Actor:** SV/coordinator / các thành viên, hệ thống.
- **Precondition / Trigger:** Round/topic mở, eligibility CONFIRMED / SV tự lập nhóm.
- **Input:** topicId, member list 1–3; người tạo là coordinator.
- **Main Flow:** kiểm 1–3 member cùng department và chưa có active registration → SV gửi một registration chung; danh sách khóa khi SUBMITTED.
- **Alternative/Exception:** thành viên đã đăng ký nơi khác hoặc không đủ điều kiện thì không submit; không có lecturer add/merge. Cơ chế đồng thuận từng thành viên còn cần chốt.
- **Output / Postcondition:** membership snapshot gắn registration; `DRAFT → SUBMITTED`.
- **Rule / Permission / Data:** BR-REG-001..002, BR-REG-005; SV không có quyền nghiệp vụ cao hơn vì coordinator; RegistrationMember.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919 / giới hạn `CONFIRMED_PROJECT_DECISION`; không có thao tác thêm người sau gửi.

### UC-ASSIGN-001 — GVHD nhận/từ chối và TBM phân công

- **Primary Actor / Supporting Actor:** GVHD, TBM / hệ thống.
- **Precondition / Trigger:** Registration `SUBMITTED` / GVHD nhận hàng đợi.
- **Input:** lecturer decision/reason; department finalization/reason.
- **Main Flow:** GVHD accept/reject → TBM kiểm chỉ tiêu/conflict → khóa topic → finalize nguyên tử tạo Thesis, member, AdvisorAssignment.
- **Alternative/Exception:** reject trả SV; vượt chỉ tiêu/conflict/capacity/version conflict thì không finalize.
- **Output / Postcondition:** `SUBMITTED → LECTURER_ACCEPTED → FINALIZED` hoặc `SUBMITTED → LECTURER_REJECTED`; chỉ nhánh chốt tạo Thesis.
- **Rule / Permission / Data:** BR-REG-003; GVHD chỉ decision đăng ký liên quan, TBM đúng scope mới finalize; TopicRegistration, Thesis, ThesisMember, AdvisorAssignment.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001, SRC-QD-2919 / `CONFIRMED_PROJECT_DECISION`.

### UC-WORK-001 — Phân công công việc từng thành viên

- **Primary Actor / Supporting Actor:** Nhóm SV / GVHD, GVPB/HĐ xem khi đánh giá.
- **Precondition / Trigger:** Thesis đã tạo / nhóm lập hoặc sửa phân công.
- **Input:** thesisMemberId, work description, expected output, version.
- **Main Flow:** tạo version cho từng member → gửi GVHD → GVHD approve hoặc return.
- **Alternative/Exception:** thiếu member hoặc sửa bản đã duyệt thì phải tạo version mới.
- **Output / Postcondition:** WorkAssignment `APPROVED/REVISION_REQUIRED`, bản duyệt dùng làm evidence cá nhân.
- **Rule / Permission / Data:** BR-REG-004; SV tạo, GVHD đúng thesis duyệt; ThesisMember, MemberWorkAssignment.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-MAU-02 / `CONFIRMED`.

### UC-PROP-001 — Nộp và version đề cương

- **Primary Actor / Supporting Actor:** SV / file service.
- **Precondition / Trigger:** Thesis và GVHD đã phân công / SV nộp đề cương.
- **Input:** uploadId, proposal metadata, expected version.
- **Main Flow:** kiểm file/quarantine → tạo Proposal nếu chưa có → thêm ProposalVersion bất biến → submit.
- **Alternative/Exception:** file lỗi hoặc version conflict thì từ chối; không ghi đè.
- **Output / Postcondition:** Proposal `DRAFT/REVISION_REQUIRED → SUBMITTED`; version/hash được lưu.
- **Rule / Permission / Data:** BR-PROP-001, BR-DOC-001; ThesisMember mới nộp; Proposal/Version, StoredFile.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-MAU-03, SRC-QD-2919 / `CONFIRMED/DERIVED`.

### UC-PROP-002 — Nhận xét và góp ý đề cương

- **Primary Actor / Supporting Actor:** GVHD, GVPB/Hội đồng đề cương / SV.
- **Precondition / Trigger:** ProposalVersion `SUBMITTED/UNDER_REVIEW`, có assignment / reviewer mở version.
- **Input:** proposalVersionId, decision, comment, form/evidence.
- **Main Flow:** kiểm assignment → tạo review trỏ đúng version → yêu cầu sửa hoặc ghi góp ý.
- **Alternative/Exception:** version cũ vẫn xem được nhưng review phải chỉ rõ target; không assignment `403`.
- **Output / Postcondition:** Proposal `UNDER_REVIEW/REVISION_REQUIRED`; review bất biến.
- **Rule / Permission / Data:** BR-PROP-001; đúng reviewer context; ProposalVersion/Review, ReviewerAssignment.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 / `CONFIRMED_PROJECT_DECISION`.

### UC-PROP-003 — Sửa và GVHD xác nhận đề cương

- **Primary Actor / Supporting Actor:** SV, GVHD / hệ thống.
- **Precondition / Trigger:** Proposal cần sửa hoặc đã đủ review / SV nộp lại, GVHD quyết định.
- **Input:** version mới hoặc advisor decision/reason.
- **Main Flow:** SV tạo version mới → review lại → GVHD confirm khi đạt.
- **Alternative/Exception:** còn review yêu cầu sửa hoặc không phải latest version thì không confirm.
- **Output / Postcondition:** `REVISION_REQUIRED → SUBMITTED → ADVISOR_CONFIRMED`.
- **Rule / Permission / Data:** BR-PROP-001..002; chỉ GVHD assignment hiện hành confirm; Proposal/Version/Review.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 / `CONFIRMED_PROJECT_DECISION`.

### UC-PROP-004 — TBM chốt, Trưởng khoa ký và in

- **Primary Actor / Supporting Actor:** TBM, Trưởng khoa / SV.
- **Precondition / Trigger:** Proposal `ADVISOR_CONFIRMED` / hồ sơ chờ chốt.
- **Input:** department decision/reason; dean signature confirmation; print request.
- **Main Flow:** TBM finalize nội dung → Trưởng khoa ký/xác nhận văn bản → tạo bản in ký trực tiếp.
- **Alternative/Exception:** Trưởng khoa không được bỏ qua TBM; trả sửa tạo vòng version mới.
- **Output / Postcondition:** `ADVISOR_CONFIRMED → DEPARTMENT_FINALIZED → DEAN_CONFIRMED`; printable artifact.
- **Rule / Permission / Data:** BR-PROP-002; position đúng scope; Proposal, SignatureConfirmation, ProposalVersion.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001, SRC-MAU-03 / `CONFIRMED_PROJECT_DECISION`.

### UC-PROG-001 — Lập và duyệt kế hoạch/milestone

- **Primary Actor / Supporting Actor:** SV, GVHD / actor quản lý round.
- **Precondition / Trigger:** Thesis hoạt động / SV lập kế hoạch hoặc round cấu hình checkpoint.
- **Input:** milestone title/time/expected output/source; member work reference.
- **Main Flow:** nạp milestone round → SV lập kế hoạch → GVHD review/approve.
- **Alternative/Exception:** mốc ngoài policy phải cấu hình/version; ngày mẫu không thành deadline.
- **Output / Postcondition:** kế hoạch được GVHD duyệt ở bản phân công công việc; `ProgressMilestone` chuyển `DRAFT → OPEN`, không có enum `APPROVED` cho milestone.
- **Rule / Permission / Data:** BR-PROG-001; GVHD đúng thesis duyệt; ProgressMilestone, MemberWorkAssignment.
- **Source / Status:** SRC-MAU-02, SRC-GVHD-NV4-001, SRC-HP-IN4299N / hai checkpoint `CONFIRMED_PROJECT_DECISION`; ngày theo cấu hình round.

### UC-PROG-002 — Báo cáo và nhận xét tiến độ

- **Primary Actor / Supporting Actor:** SV, GVHD / GV góp ý chéo khi được assignment.
- **Precondition / Trigger:** Milestone mở / SV nộp report.
- **Input:** summary, ratio, evidence, milestoneId.
- **Main Flow:** SV submit → GVHD review → confirm hoặc return → lưu history.
- **Alternative/Exception:** evidence lỗi/ratio không hợp lệ `422`; reviewer ngoài assignment `403`.
- **Output / Postcondition:** ProgressReport `DRAFT → SUBMITTED → CONFIRMED/REVISION_REQUIRED`; ProgressMilestone có state `OPEN/CLOSED` riêng.
- **Rule / Permission / Data:** BR-PROG-001; ProgressReport/Review/Milestone.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-MAU-02, SRC-HP-IN4299N / `CONFIRMED`.

### UC-CHANGE-001 — Đổi đề tài trên hệ thống

- **Primary Actor / Supporting Actor:** SV / GVHD, TBM.
- **Precondition / Trigger:** Thesis active và trong cửa sổ / SV gửi yêu cầu.
- **Input:** target title/topic, reason, evidence.
- **Main Flow:** submit → GVHD review → TBM approve/reject → version title/topic/assignment liên quan.
- **Alternative/Exception:** ngoài hạn/thiếu đồng ý/conflict thì reject có lý do.
- **Output / Postcondition:** ChangeRequest `SUBMITTED → ADVISOR_REVIEWED → APPROVED/REJECTED`; history được giữ.
- **Rule / Permission / Data:** BR-CHANGE-001; ChangeRequest, TopicTitleVersion, AdvisorAssignment.
- **Source / Status:** SRC-QD-2919, SRC-GVHD-NV4-001 / `CONFIRMED`.

### UC-EXT-001 — Ghi nhận kết quả rút/gia hạn ngoài hệ thống

- **Primary Actor / Supporting Actor:** TBM/người được giao / SV, GVHD, Trưởng khoa xem.
- **Precondition / Trigger:** Có kết quả thủ tục ngoài / người có quyền cập nhật.
- **Input:** outcomeType, officialRef, effectiveAt, evidenceFile.
- **Main Flow:** tạo draft → đối chiếu chứng từ → finalize outcome → cập nhật Thesis/member/round state.
- **Alternative/Exception:** thiếu quyết định chỉ lưu draft; không có approve online.
- **Output / Postcondition:** ExternalProcedureOutcome chính thức; Thesis `WITHDRAWN/EXTENDED` phù hợp.
- **Rule / Permission / Data:** BR-CHANGE-001; ExternalProcedureOutcome, Thesis, EvidenceDocument.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919 / `CONFIRMED`.

### UC-DOC-001 — Nộp tài liệu theo version

- **Primary Actor / Supporting Actor:** SV / file service, malware scanner.
- **Precondition / Trigger:** Thesis active và cửa sổ nộp mở / SV upload-submit.
- **Input:** bytes qua upload, media type, documentType, expectedVersion.
- **Main Flow:** allowlist/size/scan/hash → tạo Document/Version bất biến → phát job similarity/index khi hợp lệ.
- **Alternative/Exception:** malware/file lỗi/quá cỡ bị quarantine/reject; retry idempotent.
- **Output / Postcondition:** DocumentVersion `SUBMITTED`; nếu queue kiểm tra thì tạo SimilarityCheck `QUEUED` riêng; audit/hash.
- **Rule / Permission / Data:** BR-DOC-001; ThesisMember nộp tài liệu thesis mình; StoredFile, Document, DocumentVersion.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919, SRC-MAU-05 / `DERIVED`.

### UC-SIM-001 — Kiểm tra tương đồng và nộp lại

- **Primary Actor / Supporting Actor:** SV, GVHD / similarity worker.
- **Precondition / Trigger:** DocumentVersion hợp lệ / submit hoặc actor có quyền queue.
- **Input:** documentVersionId; policy do server chọn.
- **Main Flow:** lexical → semantic candidate → align/coverage → report evidence → GVHD request revision hoặc accept → SV nộp version mới nếu cần.
- **Alternative/Exception:** policy chưa ACTIVE trả `POLICY_NOT_CONFIGURED` advisory; job failed có retry; không plagiarism verdict.
- **Output / Postcondition:** SimilarityCheck/Match + provenance; DocumentVersion `RESULT_AVAILABLE → REVISION_REQUESTED/ACCEPTED`.
- **Rule / Permission / Data:** BR-SIM-001..003; source match cũng phải qua quyền; SimilarityPolicy/Check/Match, DocumentVersion.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 / boundary `CONFIRMED_PROJECT_DECISION`, baseline advisory, không auto-gate.

### UC-COUNCIL-001 — Cập nhật Hội đồng từ quyết định

- **Primary Actor / Supporting Actor:** Người được Khoa ủy quyền / Trưởng khoa, hệ thống.
- **Precondition / Trigger:** Có quyết định chính thức / nhập metadata/tệp quyết định.
- **Input:** decisionRef/date, department, 5 lecturer-role assignments.
- **Main Flow:** import → kiểm đúng Chair, Secretary, 2 Reviewer, Member → kiểm trùng/conflict → xác nhận/activate.
- **Alternative/Exception:** thiếu/đúp role hoặc GVHD chấm thesis mình thì không activate; không auto Chair.
- **Output / Postcondition:** Council `IMPORTED → VALIDATED → ACTIVE`.
- **Rule / Permission / Data:** BR-COUNCIL-001..002; actor nhập theo ủy quyền, xác nhận theo position/assignment; Council/Member.
- **Source / Status:** SRC-QD-2919, SRC-GVHD-NV4-001, SRC-MAU-09 / `CONFIRMED`.

### UC-SESSION-001 — Lập phiên và attendance

- **Primary Actor / Supporting Actor:** Thư ký, Chủ tịch / thành viên Hội đồng.
- **Precondition / Trigger:** Council ACTIVE / cần xếp lịch hoặc mở phiên.
- **Input:** schedule/location, thesis list/order, attendance.
- **Main Flow:** tạo session → gắn nhiều thesis/SV → ghi attendance → CT/TK xác nhận quorum → open.
- **Alternative/Exception:** vắng >2/5 hoặc vắng CT/TK thì `POSTPONED`; member vắng không được score.
- **Output / Postcondition:** DefenseSession `SCHEDULED → ATTENDANCE_OPEN → READY/POSTPONED → SCORING`.
- **Rule / Permission / Data:** BR-COUNCIL-002; Secretary ghi, Chair xác nhận; DefenseSession, SessionThesis, CouncilAttendance.
- **Source / Status:** SRC-QD-2919, SRC-GVHD-NV4-001, SRC-MAU-04/09 / `CONFIRMED`.

### UC-DEF-001 — Kiểm tra đủ điều kiện bảo vệ

- **Primary Actor / Supporting Actor:** GVHD, actor quản lý round / hệ thống.
- **Precondition / Trigger:** Có bản KLTN hoàn thành / chuẩn bị danh sách bảo vệ.
- **Input:** discipline result, completion evidence, AdvisorReview recommendation, local policy result, similarity gate status.
- **Main Flow:** kiểm ba điều kiện Trường → áp policy Khoa nếu cấu hình → lưu từng check/reason.
- **Alternative/Exception:** local policy chưa có không tự phát minh; similarity advisory không tự chặn.
- **Output / Postcondition:** DefenseEligibilityCheck `ELIGIBLE/NOT_ELIGIBLE/PENDING_POLICY`.
- **Rule / Permission / Data:** REQ-DEF-001, BR-SIM-003; GVHD chỉ xác nhận recommendation, verifier theo scope chốt check; AdvisorReview, DocumentVersion, DefenseEligibilityCheck.
- **Source / Status:** SRC-QD-2919, SRC-MAU-07 / điều kiện Trường `CONFIRMED`, đợt hiện tại chỉ dùng điều kiện Trường; local policy nếu Khoa ban hành sau.

### UC-EVAL-001 — Lập nhận xét GVHD/GVPB

- **Primary Actor / Supporting Actor:** GVHD hoặc GVPB / SV xem khi được công bố.
- **Precondition / Trigger:** Assignment hiệu lực và document version xác định / actor mở form.
- **Input:** trường Mẫu 7 hoặc Mẫu 8, documentVersionId, decision/recommendation.
- **Main Flow:** nhập → validate theo loại form → submit version → in/ký nếu cần.
- **Alternative/Exception:** sai assignment hoặc sửa bản submitted thì phải tạo version mới.
- **Output / Postcondition:** tạo bản ghi AdvisorReview/ReviewerReview mới với `version_no` và `created_at`; các bảng này không có cột status `SUBMITTED/LOCKED`. Sau khi biên bản in/khóa, service từ chối sửa theo guard nghiệp vụ.
- **Rule / Permission / Data:** chỉ tác giả đúng assignment tạo/sửa phiếu mình; AdvisorAssignment/ReviewerAssignment, Review.
- **Source / Status:** SRC-MAU-07, SRC-MAU-08, SRC-GVHD-NV4-001 / `CONFIRMED`.

### UC-RUBRIC-001 — Gắn rubric cho đợt/phiên

- **Primary Actor / Supporting Actor:** Actor quản lý rubric của Khoa/TBM / Chủ tịch, Thư ký xem.
- **Precondition / Trigger:** Có template version theo Mẫu 6/QĐ / trước khi chấm.
- **Input:** rubricTemplateId/version, roundId hoặc sessionId, effective time.
- **Main Flow:** validate tổng max/criterion bonus → assign → activate → khóa khi scoring bắt đầu.
- **Alternative/Exception:** tổng cấu phần/bonus vượt policy hoặc session đã chấm thì `409/422`.
- **Output / Postcondition:** RubricAssignment `ACTIVE/LOCKED`.
- **Rule / Permission / Data:** BR-EVAL-003; actor theo assignment cấu hình, không Admin; RubricTemplate/Criterion/Assignment.
- **Source / Status:** SRC-MAU-06, SRC-QD-2919 / rubric `CONFIRMED`; actor cấu hình `PROPOSED`.

### UC-EVAL-002 — Thành viên chấm từng SV

- **Primary Actor / Supporting Actor:** Thành viên Hội đồng hiện diện / hệ thống.
- **Precondition / Trigger:** DefenseSession SCORING, quorum đạt, rubric locked, attendance present / evaluator mở phiếu.
- **Input:** thesisMemberId, rubric item points/comments, evidence reference.
- **Main Flow:** kiểm ownership/conflict/max → tính total gồm bonus criterion ≤1 và cap 10 → submit.
- **Alternative/Exception:** evaluator vắng/GVHD của thesis/điểm vượt max/phiên khóa thì từ chối; chỉ tác giả sửa trước lock.
- **Output / Postcondition:** Evaluation `DRAFT → SUBMITTED/CORRECTED → LOCKED`.
- **Rule / Permission / Data:** BR-EVAL-001..003; current CouncilMember; Evaluation/Item, RubricCriterion, BonusEvidence.
- **Source / Status:** SRC-QD-2919, SRC-MAU-06, SRC-GVHD-NV4-001 / `CONFIRMED`.

### UC-EVAL-003 — Tổng hợp điểm cá nhân

- **Primary Actor / Supporting Actor:** Hệ thống / Thư ký, Chủ tịch xem.
- **Precondition / Trigger:** Có các Evaluation hợp lệ / yêu cầu preview hoặc khóa scoring.
- **Input:** sessionId, thesisMemberId, calculation version.
- **Main Flow:** lấy phiếu của member present/hasValidScore → trung bình `totalPoints` đã gồm bonus → làm tròn 1 chữ số → lưu result.
- **Alternative/Exception:** thiếu phiếu theo policy trả incomplete, không tự điền 0; recompute trước lock tạo calculation version mới.
- **Output / Postcondition:** lưu snapshot `FinalResult` với `calculation_version` mới; bảng này không có enum trạng thái. Việc khóa/công bố đi theo biên bản, phiên và quyền xem; không đổi Evaluation.
- **Rule / Permission / Data:** BR-EVAL-002..003; read theo scope, không sửa thủ công; CouncilAttendance, Evaluation, FinalResult.
- **Source / Status:** SRC-QD-2919, SRC-HP-IN4299N, SRC-MAU-06 / `CONFIRMED`.

### UC-MIN-001 — Lập, version và xuất biên bản

- **Primary Actor / Supporting Actor:** Thư ký / hệ thống, Chủ tịch.
- **Precondition / Trigger:** Attendance và FinalResult đủ / Thư ký tạo biên bản.
- **Input:** sessionId, minute metadata, expected version.
- **Main Flow:** snapshot attendance/evaluation/result → tạo MinuteVersion → validate completeness → export draft.
- **Alternative/Exception:** thiếu phiếu/result thì không export; sai trước chữ ký đầu (kể cả đã in) chuyển VOID và tạo replacement.
- **Output / Postcondition:** CouncilMinute `DRAFT → EXPORTED` và chuỗi version.
- **Rule / Permission / Data:** BR-MIN-001..002; chỉ Secretary đúng council; CouncilMinute/Version, Attendance, FinalResult.
- **Source / Status:** SRC-QD-2919, SRC-MAU-09, SRC-GVHD-NV4-001 / `CONFIRMED`.

### UC-MIN-002 — Kiểm bản in, sửa trước chữ ký và ký khóa

- **Primary Actor / Supporting Actor:** Chủ tịch, Thư ký / hệ thống.
- **Precondition / Trigger:** MinuteVersion EXPORTED/PRINTED; Thư ký phát hiện sai khi giấy chưa ký, hoặc có chữ ký.
- **Input:** void reason/replacedVersion; printed confirmation; Chair/Secretary confirmation theo MinuteVersion.
- **Main Flow:** sau in Thư ký đối chiếu thực tế; nếu sai và giấy chưa có chữ ký, evaluator tự sửa điểm, TK VOID version cũ, hệ thống tính lại/in version mới có mã và thời gian; CT và TK đúng Hội đồng ký, chữ ký đầu khóa sửa dù state còn PRINTED, đủ hai mới SIGNED → lock.
- **Alternative/Exception:** nếu đã có bất kỳ chữ ký giấy/điện tử nào thì không sửa nội dung/điểm; bản sao dùng đúng version đã ký.
- **Output / Postcondition:** `EXPORTED/PRINTED → VOID/REPLACED → EXPORTED → PRINTED` khi chưa ai ký, hoặc `EXPORTED → PRINTED → SIGNED → LOCKED`.
- **Rule / Permission / Data:** BR-MIN-001..002; TK quản lý version và ký; CT ký; MinuteVersion/Signature/AuditEvent.
- **Source / Status:** SRC-QD-2919, SRC-MAU-09, SRC-GVHD-NV4-001 / sửa sau in trước chữ ký `CONFIRMED_PROJECT_DECISION`; sau chữ ký khóa.

### UC-REPO-001 — Công bố, tìm kiếm, xem/tải KLTN

- **Primary Actor / Supporting Actor:** Người dùng / actor công bố, repository/index service.
- **Precondition / Trigger:** Có bản KLTN vận hành đã công bố hoặc nguồn nhập/official được phép, có visibility / publish hoặc search.
- **Input:** documentVersion hoặc external_source_id + source_ref/url, origin_type, source_type, provenance, visibility; query/filter.
- **Main Flow:** validate nguồn → ghi RepositoryItem metadata → index theo quyền → search/view → download qua authorized route.
- **Alternative/Exception:** draft/PII/restricted không index; revoke chặn PostgreSQL ngay rồi deindex.
- **Output / Postcondition:** RepositoryItem/SearchIndexMetadata; file được tải khi có quyền.
- **Rule / Permission / Data:** BR-REPO-001; người dùng đã xác thực theo visibility; RepositoryItem, DocumentVersion tùy origin, SearchIndexMetadata.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-QD-2919 / nghiệp vụ `CONFIRMED`, kiểm soát kỹ thuật `DERIVED`.

### UC-AI-001 — Hỏi chatbot RAG và mở nguồn

- **Primary Actor / Supporting Actor:** Người dùng / backend RAG, Qdrant, LLMProvider tùy chọn.
- **Precondition / Trigger:** Đã xác thực / người dùng gửi câu hỏi.
- **Input:** question, context selector hợp lệ.
- **Main Flow:** resolve scope → authorization trước retrieval → filtered retrieval → chunks tối thiểu/giảm PII → nếu provider có thì sinh answer; nếu không trả RETRIEVAL_ONLY với citations/link.
- **Alternative/Exception:** không evidence thì nói không đủ dữ liệu; chưa có Gemini key trả RETRIEVAL_ONLY; Qdrant lỗi trả dependency failure, không đổi workflow; không gửi full file mặc định.
- **Output / Postcondition:** answer tùy provider + citations + web routes; RetrievalAudit metadata; không mutate nghiệp vụ.
- **Rule / Permission / Data:** BR-AI-001..002; scope như repository; RepositoryItem, SearchIndexMetadata, RetrievalAudit.
- **Source / Status:** SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 / `CONFIRMED_PROJECT_DECISION`.

### UC-RPT-001 — Xuất báo cáo có truy vết

- **Primary Actor / Supporting Actor:** Người có thẩm quyền / reporting service.
- **Precondition / Trigger:** Có scope dữ liệu / actor chọn loại báo cáo.
- **Input:** round, department, report type, filters.
- **Main Flow:** xác định field/scope → đọc read model → khử/ẩn field không được phép → export → audit.
- **Alternative/Exception:** report ngoài scope hoặc field nhạy cảm bị từ chối; báo cáo mới ngoài nguồn phải `PROPOSED`.
- **Output / Postcondition:** file/report danh sách, tiến độ, Hội đồng, điểm hoặc kho; không đổi business state.
- **Rule / Permission / Data:** BR-AUDIT-001; theo permission của dữ liệu nguồn; Eligibility/Progress/Council/FinalResult/Repository read models.
- **Source / Status:** SRC-MAU-04/10/11, SRC-HP-IN4299N / `DERIVED`.
