# Xung đột và cách phân xử nguồn

| ID | Nguồn | Vấn đề | Cách xử lý / trạng thái |
| --- | --- | --- | --- |
| CONFLICT-001 | SRC-GVHD-NV4-001 và snapshot local | Nội dung và hash khác nhau. | Bản Drive sửa 18/09/2026 04:44 UTC là canonical; snapshot local chỉ lưu `_archive`. `RESOLVED`. |
| CONFLICT-002 | SRC-KH-2026 | Một số mốc trong kế hoạch 2026–2027 ghi năm không nhất quán. | Giữ loại mốc/công việc, không hard-code ngày; thời hạn theo đợt là cấu hình. `NON_BLOCKING_OPEN`. |
| CONFLICT-003 | SRC-MAU-04 | Sheet lịch lịch sử có ngày/năm không nhất quán. | Chỉ trích schema; dữ liệu lịch mẫu không tạo rule. `RESOLVED_FOR_DESIGN`. |
| CONFLICT-004 | SRC-MAU-02 | Có ngày 30/02/2026 và mốc của kỳ trước. | Coi là ví dụ sửa được, không là deadline. `RESOLVED_FOR_DESIGN`. |
| CONFLICT-005 | SRC-MAU-01B, SRC-GVHD-NV4-001, SRC-QD-2919 | Mẫu 1b chỉ có hai cột thành viên; nguồn mới và QĐ cho phép 1–3 SV/đề tài. | Mô hình hỗ trợ tối đa 3; biểu mẫu sinh mới phải mở rộng dòng thành viên. `RESOLVED`. |
| CONFLICT-006 | SRC-QD-2919 và SRC-QD-5964 | QĐ 2919 ghi GPA 3,20; QĐ 5964 sửa Điều 2 thành GPA 2,50 và ít nhất 70% tín chỉ đạt. | QĐ 5964 mới hơn và sửa đích danh Điều 2; dùng 2,50/4. `RESOLVED`. |
| CONFLICT-007 | SRC-HP-IN4299N | Bảng thông tin đánh dấu “Tự chọn”, phần tổng quan gọi là “bắt buộc đối với sinh viên năm cuối”. | Hệ thống dùng danh sách đủ điều kiện/đăng ký theo đợt, không suy diễn loại học phần. `NON_BLOCKING_OPEN`. |
| CONFLICT-008 | SRC-QD-TLTK-011 và SRC-MAU-05 | QĐ 885 có phạm vi trực tiếp là sau đại học và dùng APA; Mẫu 5 là hướng dẫn KLTN của Khoa, có ví dụ `[tài liệu; trang]`. | Dùng Mẫu 5 cho format KLTN hiện tại; QĐ 885 làm tham chiếu. Cần xác nhận chuẩn cuối cùng nếu tự động kiểm tra trích dẫn. `NON_BLOCKING_OPEN`. |
| CONFLICT-009 | SRC-GVHD-NV4-001, SRC-QD-2919, SRC-MAU-09 | Giải đáp có cụm “TBM ký biên bản Hội đồng”; QĐ 2919 và Mẫu 9 quy định Chủ tịch ký biên bản bảo vệ. | Chủ tịch ký biên bản bảo vệ, Thư ký lập. Chưa gán cụm của TBM cho cùng loại biên bản; có thể là biên bản chốt/đề cương khác. `OPEN`. |
| CONFLICT-010 | SRC-GVHD-NV4-001 và SRC-QD-2919 | Giải đáp tính điểm theo người hiện diện/có điểm; QĐ 2919 quy định không họp nếu vắng quá 2/5 hoặc vắng Chủ tịch/Thư ký. | Kiểm tra quorum trước, sau đó tính trung bình phiếu hợp lệ của người thực sự chấm. `RESOLVED`. |
| CONFLICT-011 | SRC-QD-2919 và SRC-MAU-06 | QĐ 2919 Điều 10 khoản 4 nêu cơ cấu tối đa 1/6/1/2 (cơ cấu/nội dung/hình thức/trình bày); Mẫu 6 Khoa đang dùng có ba nhóm 2/4/4 (hình thức/nội dung/demo và trả lời), cộng mục thưởng tối đa 1 nhưng tổng phiếu tối đa 10. | Baseline thiết kế phiếu hiện tại dùng đầy đủ hierarchy Mẫu 6 theo quyết định chủ dự án; lưu version/source của rubric. Không tuyên bố cơ cấu Mẫu 6 đã thay thế QĐ 2919 về mặt pháp lý. Cần Khoa xác nhận trước khi dùng phiếu chấm thật. `OPEN_FOR_PRODUCTION`. |

Không hợp nhất im lặng xung đột. Rule chịu ảnh hưởng phải trỏ về ID xung đột tương ứng.
