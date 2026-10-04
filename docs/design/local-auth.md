# Quyết định đăng nhập của hệ thống KLTN

Theo hai phương án GV đưa ra ngày 03/10/2026, giai đoạn triển khai của đồ án **chọn đăng ký/đăng nhập bằng email và mật khẩu do ứng dụng KLTN quản lý**. Ứng dụng, tài khoản và phân quyền vẫn thuộc sản phẩm do nhóm xây dựng; không cần chờ quyền tích hợp Google/Microsoft/SSO của Trường. Phương án SSO cũ giữ ở [tài liệu dự phòng](sso-deployment.md), chưa phải đăng nhập thật.

## Dữ liệu tài khoản

`user_account.email` là email đăng nhập, lưu chữ thường và duy nhất không phân biệt hoa/thường. `password_hash` chứa **mã băm Argon2id**, tuyệt đối không lưu mật khẩu gốc hoặc băm nhanh SHA-256. `email_verified_at` ghi lúc xác minh quyền sở hữu email; `status` cho phép khóa tài khoản. `external_subject` để trống với tài khoản local, giữ cho dữ liệu DEV cũ và khả năng tích hợp SSO về sau. UUID `id` vẫn là khóa nội bộ. Migration `20261003_0010` thêm cột/ràng buộc mà không xóa các tài khoản đang có. Tham khảo [khuyến nghị lưu mật khẩu của OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

**Email đăng ký không tự chứng minh người đó là SV/GV hợp lệ.** Đăng ký mới chỉ tạo danh tính chưa được cấp quyền; phải xác minh email và đối chiếu mã SV/GV/danh sách của Khoa trước khi liên kết `student_profile` hoặc `lecturer_profile`. Người dùng không tự chọn `ADMIN`, `LECTURER`, TBM, GVHD hoặc quyền xác nhận điều kiện. Admin/Khoa chỉ cấp vai trò và assignment theo dữ liệu đã xác nhận; quyền `ELIGIBILITY_VERIFIER` gán theo đợt trong `resource_assignment`.

## Luồng tài khoản và trạng thái triển khai

1. Đăng ký email + mật khẩu; chuẩn hóa email, băm Argon2id, gửi mã/link xác minh một lần có hạn dùng. Chưa xác minh thì không được vào nghiệp vụ.
2. Đối chiếu danh sách SV/GV hợp lệ rồi liên kết hồ sơ và quyền. Không dựa vào riêng hậu tố email để tự cấp vai trò.
3. Đăng nhập kiểm mã băm, trạng thái tài khoản và xác minh email; tạo phiên an toàn bằng cookie `HttpOnly`, `Secure` trên HTTPS; có giới hạn thử sai và thông báo lỗi chung.
4. Cấp lại mật khẩu bằng token một lần có hạn dùng; không gửi mật khẩu cũ/mới qua email. Đăng xuất và thu hồi phiên.

**Trạng thái 04/10:** Đăng nhập email/mật khẩu đã có API và form React; mật khẩu băm Argon2id, kiểm trạng thái ACTIVE và `email_verified_at`, giới hạn thử sai tại tiến trình API, cookie phiên `HttpOnly`/`SameSite=Lax`, đăng xuất và kiểm quyền ở backend. Năm tài khoản giả chỉ được cấp trong `kltn_dev`; người dùng không nhập UUID. Kiểm thử tự động đã chạy trên PostgreSQL.

**Chưa phải vòng đời tài khoản dùng thật:** chưa có đăng ký công khai, gửi email xác minh, đối chiếu danh sách SV/GV từ Khoa, cấp lại mật khẩu, thu hồi mọi phiên sau đổi mật khẩu và giới hạn thử sai dùng chung nhiều tiến trình. Vì đăng ký công khai không thể tự cấp vai trò SV/GV an toàn, phần này cần quy trình cấp tài khoản từ danh sách đã xác thực và dịch vụ email trước khi vận hành thật. `X-Dev-User-Id` vẫn chỉ là cơ chế kiểm thử của API ở DEV/TEST, không còn là cách đăng nhập của giao diện.
