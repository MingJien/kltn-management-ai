# Wireframe chức năng

Wireframe low-fidelity; nút chỉ hiển thị khi backend trả action được phép. Không dùng UI để quyết định quyền.

| ID | Màn hình | Nội dung/hành động | Trace |
| --- | --- | --- | --- |
| SCR-01 | Workspace/ngữ cảnh | Đợt, position/assignment hiện hành, hàng đợi công việc | UC-AUTH-001 |
| SCR-02 | Năm học/đợt/policy | MAIN/SUPPLEMENTARY, lịch, policy version, cảnh báo thiếu lịch đã duyệt | UC-ROUND-001 |
| SCR-03 | Điều kiện SV | Snapshot tín chỉ/GPA/trạng thái/nguồn/xác nhận | UC-ELIG-001 |
| SCR-04 | Expertise/topic | Giảng viên tự khai; topic requirements; TBM duyệt/chỉnh tên | UC-EXP-001, UC-TOPIC-001..003 |
| SCR-05 | Đăng ký/nhóm/GVHD | Một topic, 1–3 SV, lời mời PENDING/ACCEPTED/DECLINED từng người, coordinator, xét Topic SV sau đăng ký, GVHD đồng ý, TBM finalize | UC-REG-001/002, UC-ASSIGN-001 |
| SCR-06 | Workspace KLTN | Member work allocation và GVHD duyệt | UC-WORK-001 |
| SCR-07 | Đề cương | Timeline version/review; GVHD xác nhận; TBM chốt; Trưởng khoa ký; in | UC-PROP-001..004 |
| SCR-08 | Tiến độ/thay đổi | Milestone, report/review; đổi topic; ghi kết quả rút/gia hạn | UC-PROG-001/002, UC-CHANGE-001, UC-EXT-001 |
| SCR-09 | Tài liệu/tương đồng | Version, job, coverage/match/provenance, yêu cầu sửa | UC-DOC-001, UC-SIM-001 |
| SCR-10 | Hội đồng/phiên | Decision, 5 role, nhiều phiên/KLTN, không có auto Chair | UC-COUNCIL-001, UC-SESSION-001 |
| SCR-11 | Attendance/quorum | Có mặt/vắng, has score, guard Chair/Secretary/>2/5 | UC-SESSION-001 |
| SCR-12 | Nhận xét GVHD/GVPB | Form Mẫu 7/8 theo assignment/version | UC-EVAL-001 |
| SCR-13 | Chấm từng SV | Rubric, điểm của current evaluator, bonus evidence, lock | UC-EVAL-002/003 |
| SCR-14 | Biên bản | Completeness, version, void/replacement sau in trước chữ ký đầu, Chủ tịch + Thư ký ký | UC-MIN-001/002 |
| SCR-15 | Kho/báo cáo | Search/filter/view/download; export theo quyền | UC-REPO-001, UC-RPT-001 |
| SCR-16 | Chatbot RAG | Câu hỏi, answer, citation, link web, no-evidence | UC-AI-001 |

## Phác thảo quan trọng

~~~text
+ ĐĂNG KÝ ------------------------------------------------+
| Đợt | Điều kiện đã xác nhận | Topic đã chọn (chỉ 1)       |
| Thành viên 1..3 | Coordinator [chỉ điều phối]            |
| Yêu cầu GVHD: GPA mong muốn/kỹ năng/công nghệ/khác       |
| [Gửi] -> GVHD [Đồng ý/Từ chối] -> TBM [Chốt/phân công]  |
+----------------------------------------------------------+
~~~

~~~text
+ ĐỀ CƯƠNG ------------------------------------------------+
| v3 SUBMITTED | nhận xét GVHD | góp ý GVPB/HĐ             |
| Lịch sử v1/v2/v3 không ghi đè                            |
| [SV nộp lại] [GVHD xác nhận] [TBM chốt]                  |
| [Trưởng khoa ký/xác nhận] [In để ký trực tiếp]           |
+----------------------------------------------------------+
~~~

~~~text
+ PHIÊN BẢO VỆ --------------------------------------------+
| Quyết định: ... | Chair: từ quyết định | Secretary: ...  |
| Attendance: 5 thành viên; có mặt 4; quorum [ĐẠT]         |
| Danh sách nhiều KLTN/SV theo thứ tự                      |
| Không có nút “Tự chọn Chủ tịch”                           |
+----------------------------------------------------------+
~~~

~~~text
+ CHẤM CÁ NHÂN / BIÊN BẢN --------------------------------+
| SV: [thành viên cụ thể] | Người chấm: current account    |
| Tiêu chí | Max | Điểm của tôi | Tổng server-calculated   |
| [Submit] [Sửa điểm của tôi nếu giấy chưa ký]                   |
| Thư ký: [Tạo version] [Đối chiếu giấy] [Void bản in sai chưa ký] [In lại]               |
| Thư ký: [Ký/xác nhận]  Chủ tịch: [Ký/xác nhận] -> SIGNED khi đủ hai                        |
+----------------------------------------------------------+
~~~

~~~text
+ CHATBOT -------------------------------------------------+
| Câu hỏi [...] [Hỏi]                                      |
| Trả lời có căn cứ hoặc “không đủ bằng chứng”             |
| Nguồn: [Tên tài liệu] [Mở trên web]                      |
| Chatbot không duyệt, chấm, đổi trạng thái hoặc gửi file  |
+----------------------------------------------------------+
~~~

## Trạng thái UX

- 403/404 không làm lộ metadata tài nguyên.
- 409 hiển thị version/state mới nhất và yêu cầu tải lại.
- Similarity baseline hiển thị ADVISORY/POLICY_NOT_CONFIGURED và bằng chứng; không badge đậu/rớt.
- Sau in và trước chữ ký đầu, chỉ evaluator sửa điểm mình khi Thư ký đối chiếu giấy chưa ký; bản cũ VOID và in lại có mã/giờ mới. Từ chữ ký đầu form điểm và nội dung biên bản read-only, nêu audit reference.
- Form dùng label rõ, keyboard/focus hợp lý, state không chỉ biểu diễn bằng màu.

## Bổ sung màn hình theo quyết định 25/09

- SCR-05: SV chọn thành viên đủ điều kiện cùng bộ môn để lập nhóm 1–3; mỗi người được mời thấy nút tự ACCEPT/DECLINE. Nút gửi chỉ bật khi mọi thành viên active ACCEPTED. Với đề tài SV đề xuất, màn hiển thị đăng ký đã gửi và trạng thái TBM xét đề tài sau đó. Không có nút GV thêm/ghép; từ SUBMITTED danh sách chỉ đọc. React prototype /topics và /registrations hiện chưa có bước xác nhận từng người hay nhánh đề tài SV.
- SCR-14: hiển thị riêng trạng thái chữ ký Chair và Secretary của đúng Hội đồng; nút xuất đúng mẫu chỉ bật khi template version đã kiểm, sau in và trước chữ ký đầu có thể VOID/replacement sau khi Thư ký đối chiếu giấy; từ chữ ký đầu khóa sửa. Runtime export hiện BLOCKED_SOURCE_TEMPLATE.
- SCR-15 (AI): hiển thị source_type, title, provenance, score xếp hạng; báo rõ không phải tỉ lệ đạo văn. RAG trả citation/retrieval-only khi chưa có Gemini. React prototype: /ai (tìm đề tài).
- SCR-16 (nguồn ngoài): nút link-out chỉ cho URL HTTPS allowlist; chưa hiển thị khi chưa có provider được duyệt.
