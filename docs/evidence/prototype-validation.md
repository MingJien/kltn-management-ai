# Kiểm chứng sản phẩm hiện tại

Ngày kiểm: **04/10/2026**. Windows, PostgreSQL **17.11**, tài khoản ứng dụng `kltn_app`, cổng 5432. Schema đầy đủ trên `kltn_ai` và `kltn_dev` ở Alembic **20261004_0011**. API demo và các thử nghiệm nghiệp vụ sử dụng **kltn_dev**; dữ liệu tổng hợp, không dùng hồ sơ thật.

## Kiểm tự động

| Sản phẩm | Cách kiểm | Kết quả |
| --- | --- | --- |
| API, quyền, đăng nhập, đăng ký, AI | `python -m pytest tests -q` với DATABASE_URL trỏ kltn_dev trong tiến trình TEST | **24 PASS**; 1 cảnh báo tương thích Starlette TestClient/httpx. Dữ liệu DB trong transaction rollback. |
| Ràng buộc CSDL | `python -m backend.db.validate_schema` trên kltn_dev trong TEST | **DB-01..45 PASS**, dữ liệu tổng hợp rollback. |
| Migration từ database trống | `python -m tools.validate_migrations_disposable` | Upgrade head/check/DB validation/seed PASS trong schema riêng. Hạ 0011 bị chặn để giữ mã đề tài và liên kết minh chứng; chỉ schema thử được xóa. |
| SQL đầy đủ | `python -m tools.validate_sql_snapshot` | **63 bảng vật lý**, head 0011 trên schema thử trống; 62 bảng nghiệp vụ và alembic_version. |
| SQL lõi để nộp | `python -m tools.validate_core_sql` | **32 bảng, 32 PK, 69 FK, 0 ALTER TABLE**; đối chiếu tên cột/PK/FK với metadata, pg_dump schema-only PASS. Chỉ schema thử được xóa. |
| Frontend | `npm run build --prefix frontend` | TypeScript và Vite production build **PASS**. |
| ERD sáu cụm | `python tools/generate_erd_clusters.py` | Nguồn PostgreSQL public live **read-only**, kltn_ai revision 0011; đủ sáu PNG/SVG, kiểm mở ảnh/XML, landscape, bảng và tuyến FK không chồng lên bảng khác. |

Các file SQL được tái sinh từ schema đã chạy: [SQL lõi](../../database/core/kltn-core-schema.sql), [schema đầy đủ](../../database/kltn-schema-consolidated.sql), [baseline đầy đủ](../../database/kltn-db-baseline.sql). Mỗi bảng có một CREATE TABLE với toàn bộ cột cuối cùng; file lõi đặt cả ràng buộc trong CREATE TABLE. pg_dump chuẩn ở bản đầy đủ đặt một số constraint bên dưới, không có chuỗi ADD COLUMN sửa tiếp cấu trúc bảng.

## Luồng đã kiểm trên trình duyệt và API thật

1. GV đăng nhập bằng email/mật khẩu, tạo đề tài có sức chứa 2 SV và yêu cầu Python; gửi bộ môn.
2. TBM đúng bộ môn mở hàng chờ, sửa tên và duyệt; tên cũ còn trong lịch sử.
3. SV1 xem danh sách đã duyệt, mở form cá nhân/nhóm; form nhóm giới hạn theo sức chứa, thông tin người đăng nhập được điền sẵn.
4. SV1 chọn SV2, tự xác nhận và tạo nháp. Nhóm chưa gửi được khi SV2 chưa đồng ý. SV1 tải PDF minh chứng giả; liên kết tải được phân quyền.
5. SV2 đăng nhập tài khoản của mình và xác nhận. SV1 đăng nhập lại, gửi nhóm. GV tiếp nhận xem và chấp nhận; nhóm bị khóa thành viên.
6. SV3 tạo đề xuất riêng, chọn GV mong muốn, tự xác nhận và gửi đăng ký **trước khi** TBM duyệt. TBM xác nhận GV rồi duyệt; GV từ chối có lý do. Đăng ký giữ lịch sử và giải phóng thành viên.

Test tự động bổ sung kiểm: TBM đổi GV tiếp nhận; GV cũ không được quyết định; trả đề xuất để sửa/gửi lại; chống gửi trước đồng thuận; không xác nhận thay; capacity; round label; mã đề tài duy nhất; rollback đề xuất khi tạo nhóm lỗi; snapshot mới nhất; file sai định dạng/quá 5 MB; khóa upload sau gửi; bản nháp hủy chưa từng gửi không lộ cho GV.

## Giới hạn triển khai

- Database lõi riêng `kltn_core` chưa tạo vật lý; API hiện sử dụng mô hình đầy đủ trên kltn_dev. SQL 32 bảng là sản phẩm schema ưu tiên, chưa có migration riêng cho database lõi.
- Đăng nhập local chạy với tài khoản giả; cấp tài khoản từ danh sách Khoa, xác minh email, khôi phục mật khẩu và vận hành production còn cần triển khai.
- Minh chứng được lưu riêng ngoài Git, không gửi AI. Chưa có antivirus: trạng thái QUARANTINED, tải dạng attachment, kiểm quyền, no-store và nosniff; chưa coi file là đã quét sạch.
- GV tiếp nhận chưa phải quyết định phân công GVHD chính thức. Tiến độ/tài liệu, chấm thật và xuất Mẫu 9 chưa được chứng minh hoàn chỉnh trong đợt kiểm này.
- AI thử truy xuất trên corpus giả, chế độ RETRIEVAL_ONLY; chưa gọi Gemini, chưa đánh giá chất lượng trên KLTN thật. Điểm tìm kiếm không phải phần trăm đạo văn.

Không đưa mật khẩu, file minh chứng, dữ liệu cá nhân hoặc ảnh chụp thao tác vào repo.
