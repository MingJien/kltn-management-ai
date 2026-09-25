# Wireframe chức năng

Wireframe low-fidelity; nút chỉ hiển thị khi backend trả action được phép. Không dùng UI để quyết định quyền.

| ID | Màn hình | Nội dung/hành động | Trace |
| --- | --- | --- | --- |
| SCR-01 | Workspace/ngữ cảnh | Đợt, position/assignment hiện hành, hàng đợi công việc | UC-AUTH-001 |
| SCR-02 | Năm học/đợt/policy | MAIN/SUPPLEMENTARY, lịch, policy version, cảnh báo OPEN | UC-ROUND-001 |
| SCR-03 | Điều kiện SV | Snapshot tín chỉ/GPA/trạng thái/nguồn/xác nhận | UC-ELIG-001 |
| SCR-04 | Expertise/topic | Giảng viên tự khai; topic requirements; TBM duyệt/chỉnh tên | UC-EXP-001, UC-TOPIC-001..003 |
| SCR-05 | Đăng ký/nhóm/GVHD | Một topic, 1–3 SV, coordinator, accept/reject, TBM finalize | UC-REG-001/002, UC-ASSIGN-001 |
| SCR-06 | Workspace KLTN | Member work allocation và GVHD duyệt | UC-WORK-001 |
| SCR-07 | Đề cương | Timeline version/review; GVHD xác nhận; TBM chốt; Trưởng khoa ký; in | UC-PROP-001..004 |
| SCR-08 | Tiến độ/thay đổi | Milestone, report/review; đổi topic; ghi kết quả rút/gia hạn | UC-PROG-001/002, UC-CHANGE-001, UC-EXT-001 |
| SCR-09 | Tài liệu/tương đồng | Version, job, coverage/match/provenance, yêu cầu sửa | UC-DOC-001, UC-SIM-001 |
| SCR-10 | Hội đồng/phiên | Decision, 5 role, nhiều phiên/KLTN, không có auto Chair | UC-COUNCIL-001, UC-SESSION-001 |
| SCR-11 | Attendance/quorum | Có mặt/vắng, has score, guard Chair/Secretary/>2/5 | UC-SESSION-001 |
| SCR-12 | Nhận xét GVHD/GVPB | Form Mẫu 7/8 theo assignment/version | UC-EVAL-001 |
| SCR-13 | Chấm từng SV | Rubric, điểm của current evaluator, bonus evidence, lock | UC-EVAL-002/003 |
| SCR-14 | Biên bản | Completeness, version, void/replacement trước in, Chủ tịch ký | UC-MIN-001/002 |
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
| [Submit] [Sửa điểm của tôi trước khóa]                   |
| Thư ký: [Tạo version] [Void trước in] [In]               |
| Chủ tịch: [Ký/xác nhận] -> LOCKED                        |
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
- Similarity policy chưa chốt hiển thị `POLICY_NOT_CONFIGURED`, không badge đậu/rớt.
- Sau in/ký, form điểm và biên bản read-only, nêu audit reference.
- Form dùng label rõ, keyboard/focus hợp lý, state không chỉ biểu diễn bằng màu.
