# Kiểm chứng NV6 ngày 12/11/2026

Đối chiếu mẫu từ `docs/BieuMau` với dữ liệu giả lập. Bốn tệp đầu ra được mở bằng Microsoft Word hoặc Excel và xuất PDF để kiểm từng trang, đối chiếu dữ liệu và kiểm phần ký.

| Bản in | Kết quả kiểm tra |
| --- | --- |
| Mẫu 6 | Phiếu thường in một trang. Đủ lớp, ngành, khóa học, 12 tiêu chí, điểm thưởng, tổng và người ký. Với nhận xét dài và cỡ chữ 14, trang đầu vẫn có điểm và chữ ký, trang tiếp theo chứa nội dung nhận xét. |
| Mẫu 9 | Hai trang với hồ sơ hai SV. Đủ mục IV và V, số phiếu và kết quả theo từng SV. Trang ký có kết quả và kiến nghị. |
| Mẫu 10 | Hồ sơ hai SV in một trang. Với 36 SV, Word in ba trang, lặp tiêu đề và giữ hai dòng kết quả cuối trên trang ký. |
| Mẫu 11 | Hồ sơ hai SV in một trang. Với 36 SV, Excel in hai trang, lặp tiêu đề bảng và giữ dữ liệu kết quả trên trang ký. XLSX giữ cột ngày sinh và dấu nhận dạng từ mẫu nguồn. |

Trên CSDL demo đang dùng, kiểm bằng tài khoản TBM. Bổ sung thông tin học vụ cho hai SV giả lập có căn cứ và xác nhận điểm khóa vẫn là 8,5 và 8,0. Bản xem biên bản tổng hợp 10 nhận xét của 5 thành viên theo hai SV. Gõ chữ bị chặn. Enter thêm ngắt dòng và Backspace gỡ ngắt dòng vừa thêm. Tải thành công Mẫu 9, 10 và 11 qua giao diện.

- Backend `pytest -q` đạt 273 ca. Sau khi sửa ngắt trang Mẫu 10 và trình bày Mẫu 6, chạy lại 12 ca xuất mẫu, nghiệp vụ hội đồng và OpenAPI, đều đạt.
- `npm run build --prefix frontend` đạt. Vite còn cảnh báo kích thước gói chính.
- `python -m tools.validate_official_database` đạt trên `kltn_management` tại Alembic head `20261112_0028`, 51 bảng nghiệp vụ, 148 FK, 123 CHECK, 38 UNIQUE và 37 index tường minh.

Các bài UI chạy qua Playwright với schema riêng cho từng bộ. Các bài hồi quy giao diện dùng API mô phỏng khi cần tái tạo trạng thái lỗi và tải chậm. Các luồng nghiệp vụ dùng API và PostgreSQL, ClamAV và hộp thư thử nghiệm. Phạm vi kiểm thử không gồm gửi liên kết kích hoạt đến hộp thư thật. Bài responsive của màn hội đồng đạt ở 320, 390, 768, 1024 và 1440 px.

Qua các lượt chạy và kiểm lại, 51 ca UI trong 28 bộ đã đạt. Bộ đăng ký có 7 ca đạt trong lần chạy cả bộ. Ca còn lại được chạy riêng sau khi cập nhật kịch bản chọn mốc chung, mở lịch sử, nộp tệp phiên bản 2 và gửi nhận xét của GVHD. Phạm vi gồm quản trị và phân quyền, danh sách SV/GV, đề tài, đăng ký và Mẫu 1, nộp và duyệt tài liệu, báo cáo tiến độ, thông báo, xin thôi, đổi đề tài và gia hạn, phản biện và điều kiện bảo vệ, giao diện hội đồng, kho mẫu và lịch sử phiên bản. Kiểm thử tích hợp backend kiểm tiếp việc lập lịch, chấm, chốt, khóa điểm và xuất mẫu.

Các điểm được sửa qua tổng duyệt:

- **Hội đồng**. Chỉ cho điểm danh SV sau giờ bắt đầu và sau khi ghi nhận thành phần đủ để mở phiên. Người lập lịch xác nhận xung đột lợi ích khi chọn hoặc đổi đề tài hay hội đồng.
- **Phản biện và điều kiện bảo vệ**. Có thể ghi nhận tình trạng kỷ luật trong khi chờ báo cáo hoặc Mẫu 7. Mục điều kiện hiển thị còn thiếu hồ sơ và yêu cầu xét lại khi nguồn thay đổi.
- **Hồ sơ nộp và điểm thưởng**. Minh chứng mới chọn từ phiên bản hỗ trợ mới nhất đã quét an toàn. Màn hồ sơ hiển thị số yêu cầu chờ xử lý cho đúng vai trò và hướng dẫn cập nhật sau khi bị yêu cầu sửa.
- **Kho mẫu và thao tác bàn phím**. Thêm thao tác đưa bộ mẫu gốc còn thiếu vào kho theo đợt. Bảng SV trong chi tiết đề tài và bảng xem trước Excel có thể lấy nét để cuộn bằng bàn phím.
