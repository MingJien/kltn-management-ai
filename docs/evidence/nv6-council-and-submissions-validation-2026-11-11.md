# Kiểm chứng điều phối hồ sơ và lập hội đồng NV6

Kiểm thử ngày 11/11/2026 trên PostgreSQL với schema tạm và dữ liệu giả lập. Các lượt kiểm thử Chromium dùng tài khoản giả lập và quét tệp bằng ClamAV trong các kịch bản tải tệp thật. Mỗi lượt tự dọn schema do nó tạo.

| Phạm vi | Kết quả |
| --- | --- |
| Bản dựng TypeScript và Vite | Thành công |
| Pytest | 115 ca qua trong các nhóm hội đồng, đánh giá, thông báo, đăng ký, tài khoản, tiến độ, khóa luận và hợp đồng API |
| Chromium | Tám kịch bản qua trong lượt chạy nhóm, một kịch bản về thông báo và chọn thành viên qua trong lượt chạy lại riêng |

- Backend kiểm tra xung đột GVHD, căn cứ mời thành viên ngoài Khoa, quyền điều phối khi đã đóng đăng ký, quyền đọc bản nộp, tính điểm và xuất hồ sơ hội đồng.
- Chromium qua các luồng nộp Mẫu 1–3 và minh chứng công bố khoa học, mở thông báo tới đúng cuốn báo cáo, GVHD tiếp nhận báo cáo, Mẫu 7/8 và ghi nhận bản ký. Kịch bản hội đồng kiểm tra bộ môn demo và lựa chọn GVHD bị vô hiệu hóa sau khi chọn đề tài.
- Kiểm tra giao diện hội đồng từ 320 đến 1440 px, giữ nháp khi chuyển mục và chọn đúng sinh viên trong lịch bổ sung. Hai kịch bản nháp và lịch bổ sung dùng phản hồi mô phỏng trên trình duyệt. Luồng chốt và xuất hồ sơ chạy qua kiểm thử backend.
