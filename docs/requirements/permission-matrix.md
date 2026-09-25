# Ma trận quyền nghiệp vụ

## Ký hiệu tác nhân

- `SV`: Sinh viên/ThesisMember trong phạm vi của mình.
- `GV`: Giảng viên; `GVHD`, `GVPB` chỉ có quyền khi có assignment còn hiệu lực.
- `TBM`, `TKHOA`: position còn hiệu lực đúng Bộ môn/Khoa.
- `TVHD`, `CT`, `TK`: CouncilMember, Chủ tịch, Thư ký đúng Hội đồng/phiên.
- `ELIG-V`: cán bộ Khoa được giao assignment xác nhận điều kiện theo round sau đối chiếu nguồn Phòng Đào tạo; người cụ thể do Khoa chỉ định.
- `ADMIN`: kỹ thuật nền tảng; không có business authority.
- `SYS`: hành vi tự động sau khi server đã kiểm authorization/guard.
- `—`: không có quyền. Không dùng xóa vật lý với hồ sơ nghiệp vụ; thay bằng cancel/void/deactivate có audit.

## Ma trận theo action

| Tài nguyên | View | Create | Update | Submit | Review | Approve/Reject | Assign | Score | Export | Finalize/Sign | Delete | Guard/status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EligibilitySnapshot | SV của mình; ELIG-V/TBM/TKHOA theo scope | SV/import service | SV trước submit | SV | ELIG-V | ELIG-V đúng round | — | — | người có quyền báo cáo | ELIG-V confirm | — | Chưa confirm không dùng chốt; lưu source/time/actor. |
| LecturerExpertise | chủ hồ sơ; TBM/TKHOA theo scope | GV | chủ hồ sơ tạo version | GV | TBM `PROPOSED` | TBM cùng Bộ môn; nếu hồ sơ của TBM thì Trưởng khoa/người được giao; không tự verify | — | — | — | — | — | Mặc định `SELF_DECLARED`. |
| Topic/TopicRequirement | người dùng theo round/visibility | GV hoặc SV | proposer khi draft; TBM chỉ chỉnh title có version | proposer | TBM theo Bộ môn; GVHD chỉ sau khi có assignment liên quan | TBM approve/reject | — | — | danh sách theo quyền | TBM mở/đóng đăng ký | — | Preferred GPA không là hard gate. |
| TopicRegistration/Member | thành viên; GVHD/TBM theo scope | SV | thành viên trước submit | SV/coordinator | GVHD | GVHD accept/reject; TBM finalize | TBM tạo AdvisorAssignment khi finalize | — | — | TBM finalize | — | Một active registration/SV/round; 1–3 SV; không ghép hậu đăng ký. |
| MemberWorkAssignment | member; GVHD/GVPB/HĐ theo assignment | SV/nhóm | SV tạo version trước duyệt | SV | GVHD | GVHD approve/return | — | — | — | khóa version làm evidence | — | Mỗi ThesisMember phải có bản được duyệt trước chấm. |
| Proposal/Version | thành viên; actor có assignment/position | SV | SV bằng version mới | SV | GVHD, GVPB/HĐ đề cương | GVHD confirm; TBM approve/return | ReviewerAssignment do người có thẩm quyền cấu hình | — | SV/actor có quyền in | TBM finalize; TKHOA sign/confirm | — | Không ghi đè version; TKHOA không chốt nội dung thay TBM. |
| ProgressMilestone/Report | thành viên; GVHD/TBM theo scope | actor quản lý round tạo milestone; SV tạo report | milestone trước mở; SV tạo report version mới | SV | GVHD | GVHD confirm/return | — | — | theo REQ-RPT-001 | đóng milestone theo policy | — | GVHD xác nhận tiến độ; GVHD khác góp ý nội bộ chỉ khi được phân công. Ngày/version theo round. |
| ChangeRequest TOPIC_CHANGE | SV/GVHD/TBM liên quan | SV | SV trước submit | SV | GVHD | GVHD review; TBM approve/reject | — | — | — | TBM finalize change | — | Cửa sổ hai tuần theo QĐ2919/policy round. |
| ExternalProcedureOutcome | SV/GVHD liên quan; TBM/TKHOA | TBM/người được giao | người tạo trước finalize | người ghi | TBM/TKHOA nếu văn bản yêu cầu | Không duyệt thủ tục trên hệ thống | — | — | theo quyền | ghi nhận kết quả chính thức | — | Chỉ withdrawal/extension đã giải quyết bên ngoài. |
| Document/Version | owner và actor có assignment/visibility | SV | bằng version mới | SV | GVHD/GVPB/HĐ theo scope | GVHD request revision/accept | — | — | tải qua route có quyền | final submission khi policy cho phép | — | Quarantine/hash/immutable; không storage key công khai. |
| SimilarityCheck/Match | owner, GVHD, HĐ theo scope | SYS/actor có quyền trên document | — | queue bởi SV/GVHD | GVHD | Chỉ advisory khi policy chưa ACTIVE | — | — | report theo quyền | không có auto-gate trong baseline; policy tương lai cần phê duyệt | — | Không kết luận plagiarism; nguồn match cũng phải qua quyền. |
| Council/Member | member liên quan; TBM/TKHOA | người được ủy quyền import | sửa draft theo đúng quyết định | người nhập | TKHOA/người xác nhận quyết định | xác nhận dữ liệu quyết định | vai trò chỉ từ quyết định | — | quyết định/danh sách | activate khi đủ 5 role | — | Không auto Chair; Admin chỉ hỗ trợ import kỹ thuật. |
| DefenseSession/SessionThesis | actor theo council/scope | người được phân quyền | trước attendance open | — | CT/TK | CT open/postpone sau quorum | gắn thesis theo quyết định/lịch | — | lịch theo quyền | CT/TK close theo workflow | — | Một Council nhiều session/thesis; không tự phát minh lịch. |
| CouncilAttendance | thành viên xem mình; CT/TK/TBM xem phiên | TK | TK trước open; member xác nhận mình | TK | CT | CT xác nhận quorum | — | — | — | khóa khi phiên mở | — | Vắng >2/5 hoặc vắng CT/TK thì không mở chấm. |
| AdvisorReview/ReviewerReview | tác giả; SV khi policy công bố; HĐ theo phiên | GVHD/GVPB đúng assignment | chính tác giả bằng version mới | chính tác giả | — | defense recommendation chỉ GVHD | — | — | in phiếu | khóa version được dùng | — | Mẫu 7/8; không sửa phiếu người khác. |
| RubricTemplate | TVHD/CT/TK/TBM/TKHOA theo scope | TBM/Khoa được giao | trước khi chấm | người quản lý | TBM/Khoa | activate/deactivate theo policy | gắn round/session | — | — | khóa khi chấm bắt đầu | — | Version theo Mẫu 6/QĐ2919. |
| Evaluation/EvaluationItem | evaluator xem phiếu mình; CT/TK xem completeness; SV chỉ xem kết quả đã công bố | TVHD hiện diện | chính evaluator trước lock | chính evaluator | CT/TK chỉ completeness, không đổi điểm | — | — | chính TVHD | phiếu của mình nếu được phép | SYS lock từ chữ ký đầu của minute hoặc session close; sau in chưa ký cho sửa có Thư ký đối chiếu | — | Unique session/evaluator/thesisMember; rubric max; conflict-of-interest. |
| FinalResult | SV của mình sau công bố; HĐ/TBM/TKHOA theo scope | SYS | SYS tính lại trước lock | — | TK/CT xem đối soát | — | — | — | TK xuất bảng tổng hợp | actor nghiệp vụ công bố theo quy trình | — | Trung bình total phiếu hợp lệ; bonus không cộng hai lần. |
| CouncilMinute/Version | HĐ/TBM/TKHOA theo scope | TK | TK tạo replacement trước chữ ký đầu | TK | CT | CT confirm/sign | — | — | TK export/print | CT sign; SYS lock | TK void bản sai trước chữ ký đầu, sau đối chiếu giấy | Bản đã in sửa được nếu giấy chưa ai ký: VOID version cũ, người chấm tự sửa, tính lại và in version mới có mã/thời gian/audit. Từ chữ ký đầu khóa điểm/nội dung dù state còn PRINTED; bản sao giữ nguyên version đã ký. |
| RepositoryItem | người dùng theo visibility | actor công bố được phân quyền | actor công bố trước/qua version visibility | — | — | — | — | — | người dùng tải qua web | publish/unpublish theo assignment | — | Qdrant là index dẫn xuất; revoke chặn từ PostgreSQL trước. |
| Chatbot/RetrievalAudit | người dùng xem câu trả lời của request mình; audit theo quyền | SYS | — | người dùng gửi câu hỏi | — | — | — | — | chỉ citation/link | — | — | Authorization trước retrieval; AI read-only. |
| Báo cáo | actor theo field/scope | — | — | — | — | — | — | — | actor có quyền dữ liệu nguồn | — | — | PII/điểm lọc theo scope; mọi export có audit. |

## Enforcement bắt buộc

1. Frontend chỉ ẩn/hiện action theo `GET /me` và resource actions; backend luôn kiểm lại.
2. Permission = base role + position/assignment + resource + state + conflict-of-interest; mặc định từ chối.
3. `ADMIN` không xuất hiện trong chuỗi approve/reject/assign/score/finalize/sign.
4. Mọi accept/reject/finalize/sign/void/score correction/visibility change ghi AuditEvent.
5. API trả `403` khi đã biết tài nguyên nhưng thiếu action; có thể trả `404` khi cần tránh lộ sự tồn tại.

## Quyền làm rõ ngày 25/09/2026

| Resource/action | Chủ thể được phép | Giới hạn |
| --- | --- | --- |
| Tạo nhóm đăng ký | SV đã có eligibility CONFIRMED trong round | 1–3 SV cùng department; người tạo phải thuộc nhóm; một active registration/SV/round |
| Lecturer decision | Giảng viên đề xuất đề tài đã duyệt trong prototype; phiên bản đầy đủ sẽ dùng advisor nomination/assignment rõ ràng | Không thêm/ghép SV, không quyết định đề tài khác |
| Department finalization | TBM có PositionAssignment ACTIVE đúng department | Tạo Thesis/Member/AdvisorAssignment cùng transaction; không chốt lặp |
| Mốc đợt | ResourceAssignment KLTN_COORDINATOR đúng round | Không đồng nghĩa Secretary Council hoặc GVHD |
| Ký Mẫu 9 | CouncilMember CHAIR và SECRETARY đúng council/version | Cần đủ hai, không TBM/Admin bypass |
| Truy xuất corpus | Actor có visibility/scope tương ứng | Source type/provenance/citation đi kèm; không lộ file nội bộ |
| Xuất biểu mẫu | Actor nghiệp vụ đúng assignment/state | Adapter template chính thức; hiện runtime Mẫu 9 BLOCKED_SOURCE_TEMPLATE |
