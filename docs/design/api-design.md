# API hiện hành

Ứng dụng dùng PostgreSQL `kltn_management` ở revision Alembic `20261030_0017`. [OpenAPI công bố](openapi.yaml) được sinh trực tiếp từ các route FastAPI, cùng nội dung với `/openapi.json` và `/docs` khi chạy backend. Tệp này chỉ mô tả endpoint đã có mã nguồn.

## Nhóm chức năng đã có API

- Tài khoản email/mật khẩu, kích hoạt qua email, đăng nhập/đăng xuất, đổi và đặt lại mật khẩu; ADMIN hoặc giảng viên được giao ACCOUNT_MANAGER quản lý tài khoản đúng phạm vi đợt, không kiêm quyền xác nhận đủ điều kiện.
- Năm học/đợt, nhập và xác nhận danh sách sinh viên đủ điều kiện theo quyền được Khoa giao.
- GV tạo đề tài, Trưởng bộ môn xét duyệt, SV tự đăng ký/tham gia nhóm, GV tiếp nhận quyết định, Trưởng bộ môn chốt đăng ký và GVHD.
- Hồ sơ khóa luận, đề cương, tiến độ, phân công việc và tài liệu theo phiên bản. Các chức năng này đang ở mức prototype.
- Tìm đề tài tương tự và tra cứu nguồn trên dữ liệu giả; chưa gọi Gemini.
- NV6 tuần 1: phân công/thu hồi/gia hạn phản biện; phiếu Mẫu 7/8 theo từng sinh viên và bản báo cáo, nháp riêng, xuất DOCX để ký, quét bản ký rồi gửi; xét và mở xét lại điều kiện bảo vệ, lịch sử và thông báo theo tài khoản.

## Quy tắc chung

Backend kiểm quyền theo vai trò, bộ môn, đợt và tài nguyên. Các thao tác ghi cần cookie phiên, Origin hợp lệ và CSRF token theo từng route. Thao tác đổi trạng thái kiểm `If-Match`/`row_version` cùng điều kiện nghiệp vụ trong transaction. Lỗi thường dùng: `401` chưa đăng nhập, `403` thiếu quyền, `404` không tìm thấy, `409` xung đột, `422` dữ liệu không hợp lệ.

Gửi email thật cần cấu hình SMTP; khi vận hành ngoài máy cá nhân cần HTTPS. Dữ liệu cá nhân và file chỉ được trả cho người có quyền. Mật khẩu lưu dạng mã băm. Header UUID thử nghiệm chỉ hoạt động khi bật chế độ development/test.

Hội đồng bảo vệ, chấm điểm, biên bản và câu trả lời bằng Gemini chưa có API trong bản này. Thiết kế cho các giai đoạn sau không xuất hiện trong OpenAPI hiện hành.

## Giữ đặc tả khớp mã nguồn

Sau khi đổi route hoặc schema request/response, chạy `python -m tools.export_runtime_openapi` rồi `python -m tools.export_runtime_openapi --check`. Kiểm thử `tests/test_openapi_contract.py` cũng đối chiếu tệp công bố với FastAPI.

## NV6 tuần 1

Danh sách dùng `GET /api/v1/evaluations` với tìm kiếm và phân trang. Tài nguyên NV6 của một khóa luận ở `/api/v1/theses/{thesis_id}/evaluation`. `GET` trả quyền thao tác, phân công, bản báo cáo, phiếu được phép xem và kết quả xét riêng từng sinh viên. Các `POST` phân công, gia hạn, thu hồi, lập phiếu, xét điều kiện và mở xét lại kiểm `If-Match` của khóa luận; sửa nháp, xuất phiếu, tải/quét bản ký và gửi phiếu kiểm phiên bản của phiếu.

TBM thao tác trong bộ môn; GVHD và GVPB chỉ viết đúng phiếu theo phân công của mình. ADMIN không có quyền duyệt nghiệp vụ mặc định. Người phản biện chỉ tải cuốn báo cáo qua route NV6, không được xem tiến độ hay tài liệu riêng khác. Nháp chỉ người viết xem; SV chỉ đọc phiếu đã gửi và kết quả xét của chính mình. Thông báo không cấp thêm quyền truy cập.

Điều kiện bảo vệ gồm tình trạng kỷ luật theo nguồn đối chiếu, GVHD xác nhận hoàn thành và văn bản đồng ý bảo vệ đã ký. Mỗi kết quả xét giữ bản báo cáo và Mẫu 7 làm căn cứ; bản khác làm kết quả cũ cần xét lại. Không thêm ngưỡng điểm, điều kiện phản biện hay tương đồng vào điều kiện cấp Trường. Chi tiết vận hành tại [luồng NV6](nv6-review-defense-workflow.md).
