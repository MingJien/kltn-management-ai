# Thiết kế API

API dùng tiền tố `/api/v1`. Tài liệu máy đọc là [openapi.yaml](openapi.yaml); khi chạy FastAPI, `/openapi.json` và `/docs` phản ánh đúng các endpoint đã triển khai.

## Đã triển khai

- Tài khoản email/mật khẩu: kích hoạt qua liên kết email, đăng nhập/đăng xuất, đổi và đặt lại mật khẩu; phiên cookie. Gửi email thật cần cấu hình SMTP và HTTPS.
- ADMIN quản lý người dùng, phân công quyền theo đợt và tạo/sửa/mở/đóng đợt KLTN. Người được giao nhập, đối chiếu và xác nhận danh sách SV đủ điều kiện.
- GV tạo/gửi đề tài → TBM duyệt hoặc trả lại → SV tự đăng ký/tham gia nhóm → GV nhận hoặc từ chối → TBM chốt đăng ký và GVHD chính. Đề tài SV tự đề xuất được TBM xét sau khi SV gửi đăng ký.
- Tìm đề tài tương tự và tra cứu nguồn trên dữ liệu giả; chưa gọi Gemini. Các route liên quan xem [luồng đăng ký](registration-workflow.md).

## Quy tắc API

- Backend kiểm quyền theo vai trò, bộ môn, đợt và tài nguyên; giao diện không tự cấp quyền. Header UUID thử nghiệm chỉ hoạt động trong DEV/TEST.
- Thao tác đổi trạng thái kiểm `If-Match`/`row_version` và điều kiện nghiệp vụ trong transaction. Lỗi thường dùng: `401` chưa đăng nhập, `403` thiếu quyền, `404` không tìm thấy, `409` xung đột và `422` dữ liệu không hợp lệ.
- Dữ liệu cá nhân chỉ trả cho người có quyền, không công khai đường dẫn tệp; mật khẩu lưu mã băm. `/topic-registrations/{id}/member-response` là route tương thích cho bản nháp cũ, không dùng để mời thành viên mới.

## Chưa triển khai

Quản lý tiến độ, tài liệu, hội đồng, chấm điểm, xuất biên bản và Gemini còn là thiết kế cho giai đoạn sau. Endpoint được mô tả trong `openapi.yaml` phải xem `x-runtime-status`; chỉ endpoint có mã chạy trong FastAPI mới được coi là chức năng hiện có.
