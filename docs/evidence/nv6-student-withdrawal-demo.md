# Kiểm thử bốn sinh viên giả lập và luồng xin thôi

Ngày kiểm: 04/11/2026. Chạy trên workspace local có các thay đổi chưa commit; đồng thời đối chiếu lại trên bản sao sạch commit `5f236dc` của nhánh NV6, bổ sung riêng kịch bản kiểm thử và thay đổi bộ chạy của tác vụ này. Kết quả không chứng nhận dữ liệu thật hoặc các chức năng ngoài phạm vi kiểm thử.

- Playwright `student-withdrawal-demo.spec.ts`: **1/1 kịch bản đạt trên mỗi bản** qua trình duyệt Chromium, API, PostgreSQL và ClamAV thật. Hệ thống dùng schema ngẫu nhiên riêng do lượt kiểm tạo và chỉ xóa schema đó khi kết thúc; không sửa hồ sơ thật.
- Nhập bốn sinh viên giả, MSSV 10 chữ số, email `example.invalid`, lớp `ĐHCNTT23F-IT` và mã ngành `7480201` theo mẫu. Khi chạy với `KLTN_E2E_SAMPLE_DEPARTMENT=true`, bộ môn `BM-CNTT` và Khoa được mô phỏng trong schema riêng; không sửa danh mục thật.
- Bốn sinh viên yêu cầu, nhận link ở hộp thư giả trên máy và kích hoạt tài khoản; SMTP thật đã tắt. Cả bốn đăng ký hai đề tài do GV1 giả lập đề xuất; từng nhóm hai người gửi đăng ký và GV1 chấp nhận.
- Một tài khoản giả khác được mô phỏng thu hồi điều kiện: giao diện hiện thông báo chưa được xác nhận và khóa nút đăng ký. Tình huống này kiểm tra một nguyên nhân có thể xảy ra; không chứng minh tài khoản thực tế của người dùng đã bị thu hồi.
- Một SV gửi đơn xin thôi, GVHD xác nhận, bổ sung PDF giả lập, điều phối ghi nhận tiếp nhận rồi kết quả giả lập cho thôi. Kiểm tra SV rời hồ sơ, thành viên còn lại tiếp tục. PDF trắng và căn cứ xử lý đều là dữ liệu thử, không phải chữ ký hay quyết định ngoài đời.
- Thời hạn hiện tính theo ngày bắt đầu thực hiện được ghi cho đợt; lượt thử không xác lập GV chấp nhận đăng ký là ngày bắt đầu chính thức. Mẫu xuất đơn còn chờ Khoa duyệt và chưa nằm trong lượt này.

Chạy lại:

```powershell
$env:KLTN_E2E_ALLOW_ISOLATED_SCHEMA='true'
$env:KLTN_E2E_SAMPLE_DEPARTMENT='true'
.\.venv\Scripts\python.exe -m tools.run_e2e student-withdrawal-demo.spec.ts
```
