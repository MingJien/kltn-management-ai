# API hiện hành

Ứng dụng dùng PostgreSQL `kltn_management` ở revision Alembic `20261015_0001_official`. [OpenAPI công bố](openapi.yaml) được sinh trực tiếp từ các route FastAPI, cùng nội dung với `/openapi.json` và `/docs` khi chạy backend. Tệp này chỉ mô tả endpoint đã có mã nguồn.

## Nhóm chức năng đã có API

- Tài khoản email/mật khẩu, kích hoạt qua email, đăng nhập/đăng xuất, đổi và đặt lại mật khẩu; ADMIN quản lý tài khoản và phân công quyền theo đợt.
- Năm học/đợt, nhập và xác nhận danh sách sinh viên đủ điều kiện theo quyền được Khoa giao.
- GV tạo đề tài, Trưởng bộ môn xét duyệt, SV tự đăng ký/tham gia nhóm, GV tiếp nhận quyết định, Trưởng bộ môn chốt đăng ký và GVHD.
- Hồ sơ khóa luận, đề cương, tiến độ, phân công việc và tài liệu theo phiên bản. Các chức năng này đang ở mức prototype.
- Tìm đề tài tương tự và tra cứu nguồn trên dữ liệu giả; chưa gọi Gemini.

## Quy tắc chung

Backend kiểm quyền theo vai trò, bộ môn, đợt và tài nguyên. Các thao tác ghi cần cookie phiên, Origin hợp lệ và CSRF token theo từng route. Thao tác đổi trạng thái kiểm `If-Match`/`row_version` cùng điều kiện nghiệp vụ trong transaction. Lỗi thường dùng: `401` chưa đăng nhập, `403` thiếu quyền, `404` không tìm thấy, `409` xung đột, `422` dữ liệu không hợp lệ.

Gửi email thật cần cấu hình SMTP; khi vận hành ngoài máy cá nhân cần HTTPS. Dữ liệu cá nhân và file chỉ được trả cho người có quyền. Mật khẩu lưu dạng mã băm. Header UUID thử nghiệm chỉ hoạt động khi bật chế độ development/test.

Hội đồng bảo vệ, chấm điểm, biên bản và câu trả lời bằng Gemini chưa có API trong bản này. Thiết kế cho các giai đoạn sau không xuất hiện trong OpenAPI hiện hành.

## Giữ đặc tả khớp mã nguồn

Sau khi đổi route hoặc schema request/response, chạy `python -m tools.export_runtime_openapi` rồi `python -m tools.export_runtime_openapi --check`. Kiểm thử `tests/test_openapi_contract.py` cũng đối chiếu tệp công bố với FastAPI.
