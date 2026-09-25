# Kết quả lịch sử trước migration 0003/0004

Tài liệu này giữ bằng chứng baseline ngày 24/09/2026; trạng thái hiện hành xem `prototype-validation.md`.

# Kết quả kiểm chứng CSDL PostgreSQL

Ngày kiểm chứng: 25/09/2026. Phạm vi: cấu trúc CSDL và ràng buộc đã thiết kế cho dự án KLTN. Kiểm chứng trên PostgreSQL 17.11 cài trực tiếp, không dùng hồ sơ hoặc điểm thật.

| Nội dung | Kết quả |
| --- | --- |
| Mô hình SQLAlchemy | 62 bảng, 606 cột |
| Toàn bộ bảng nhìn thấy trong PostgreSQL | 63 bảng, 607 cột nếu tính thêm `alembic_version.version_num` |
| Alembic | Revision `20260924_0002` là head trên `kltn_dev` và `kltn_ai` |
| Kiểm tra schema | `alembic check` không phát hiện thao tác nâng cấp mới trên cả hai database |
| Kiểm tra ràng buộc | DB-01 đến DB-26: **26/26 PASS** trên từng database |
| Dữ liệu sau kiểm thử | 0 dòng nghiệp vụ trên mỗi database; dữ liệu mẫu của test đã rollback |
| ERD | 8 file Draw.io parse XML; hai ERD thể hiện cột và khóa ngoại ghép của chữ ký đề cương |

Khóa ngoại `signature_confirmation(proposal_id, proposal_version_no)` tham chiếu `proposal_version(proposal_id, version_no)`; cặp cột đích có UNIQUE. Do đó xác nhận ký gắn với đúng bản đề cương, không chỉ với đề cương nói chung.

PostgreSQL trực tiếp kiểm tra PK, FK, UNIQUE, CHECK và một số unique index. Các quy tắc cần đếm nhiều dòng hoặc xác minh thẩm quyền, quorum, công thức điểm và khóa sau ký phải được thực thi ở backend trong transaction; xem [quy tắc CSDL](../design/database-rules.md). Các câu hỏi nghiệp vụ đã được chốt cho baseline thiết kế ở [quyết định hiện tại](../requirements/open-issues.md); đoạn này là kết quả lịch sử của revision 0002, không mô tả trạng thái 0005.

File [SQL tạo CSDL mới](../../database/kltn-init-empty.sql) chỉ dùng với database trống. Khi cập nhật database đã tồn tại, dùng các revision trong [Alembic migrations](../../backend/migrations/versions/) và chạy `alembic upgrade head` sau khi review.
