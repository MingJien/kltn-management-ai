# Tệp CSDL PostgreSQL

Thư mục này gom các tệp SQL để tạo CSDL mới và xem cấu trúc CSDL. Dùng đúng file theo mục đích:

| Tệp | Dùng để làm gì | Có thay đổi CSDL không? |
| --- | --- | --- |
| [core/kltn-core-schema.sql](core/kltn-core-schema.sql) | **Bản lõi 32 bảng riêng theo góp ý GV**: tài khoản, đợt, điều kiện, đề tài, đăng ký, khóa luận, GVHD, đề cương, tiến độ, tài liệu, quyền/góp ý, lịch sử tên đề tài và audit. Mỗi bảng có đủ cột và ràng buộc ngay trong `CREATE TABLE`; [cách tạo/xem](core/README.md). | Có nếu chạy trên database mới `kltn_core`, trống; không có dữ liệu nghiệp vụ. Không chạy trên `kltn_ai`/`kltn_dev`. |
| [kltn-schema-consolidated.sql](kltn-schema-consolidated.sql) | Bản `pg_dump --schema-only` đủ **62 bảng nghiệp vụ** từ `kltn_ai`, Alembic `20261004_0012`; dùng làm thiết kế tham chiếu cho giai đoạn sau. Mỗi bảng hiện đủ cột trong một `CREATE TABLE`, không có `ALTER ... ADD COLUMN`; khóa ở phần sau theo chuẩn pg_dump. | Không khi chỉ mở để xem; đây vẫn là DDL nên không chạy trên database hiện có. Không có dữ liệu. |
| [kltn-db-baseline.sql](kltn-db-baseline.sql) | Cùng cấu trúc gọn, thêm Alembic marker và rubric Mẫu 6 DRAFT; dùng để dựng database **mới, trống**. | Có: tạo bảng, khóa/ràng buộc và 18 dòng dữ liệu kỹ thuật (revision Alembic + rubric: 1 mẫu và 16 tiêu chí). Không có dữ liệu sinh viên/đề tài/hồ sơ. |
| `kltn-ai-workbench.sql` (chỉ trên máy) | Xem danh sách bảng, toàn bộ cột/kiểu dữ liệu, khóa/ràng buộc, index, view, trigger và Alembic revision. Tệp này được Git bỏ qua vì phục vụ thao tác pgAdmin cá nhân. | Không: các câu lệnh đều là `SELECT`. |
| `kltn-ai-updates.sql` (chỉ trên máy) | Một tệp soạn lệnh ALTER/UPDATE/DELETE dùng lại nhiều lần trong pgAdmin. Đã để sẵn câu kiểm tra đúng database. Tệp được Git bỏ qua vì là sổ thao tác cá nhân. | Chỉ thay đổi CSDL khi bạn chọn và chạy lệnh ghi dữ liệu cụ thể. |

## Cập nhật database dự án đang dùng

Không chạy lại `kltn-db-baseline.sql` trên `kltn_dev`, `kltn_ai` hoặc bất kỳ database đã có bảng nào. Khi thay đổi CSDL chính thức:

1. Sửa mô hình SQLAlchemy trong `backend/db/models/entities.py`.
2. Tạo migration mới trong `backend/migrations/versions/`.
3. Review migration rồi chạy `.\.venv\Scripts\python.exe -m alembic upgrade head` trên database đích.

`backend/migrations/` giữ lịch sử nâng cấp theo từng phiên bản của **mô hình đầy đủ**. Hai file SQL 62 bảng được tái sinh từ cùng schema thật bằng `.\.venv\Scripts\python.exe -m tools.export_database_sql` tại thư mục gốc (dùng pg_dump PostgreSQL 17). File lõi 32 bảng được tái sinh riêng bằng `.\.venv\Scripts\python.exe -m tools.export_core_database_sql`; không chạy migration 62 bảng trên database lõi.

**Lưu ý:** Một tệp cá nhân giúp thao tác thuận tiện, nhưng không thay được lịch sử migration. Mỗi lần ứng dụng thay đổi cấu trúc bảng/cột chính thức, Alembic cần một revision mới để máy khác nâng cấp đúng thứ tự và không chạy lại lệnh cũ. Schema head `20261004_0012` giữ `COMMENT_ONLY`, rubric Mẫu 6 DRAFT, chứng cứ từng SV tự tham gia và quy mô dự kiến `expected_member_count`, tỷ lệ tín chỉ/GPA khi có dữ liệu, kết quả điều kiện theo đợt, và cột email/mã băm cho phương án đăng nhập local; xem [đối chiếu quyết định với CSDL](../docs/design/doi-chieu-quyet-dinh-csdl.md). Các quy tắc nhiều bảng/quyền/trạng thái vẫn cần backend kiểm trong transaction.

Mã đề tài có dạng `DT-2026-2027-0001`, duy nhất và không đổi khi sửa tên. `topic_requirement` giữ GPA/kỹ năng/công nghệ mong muốn; backend không dùng yêu cầu này thay điều kiện chính thức. `topic.receiving_lecturer_id` là GV tiếp nhận (chưa phải phân công GVHD chính thức). `registration_member.evidence_file_id` liên kết minh chứng riêng từng SV qua `stored_file`; nội dung tệp không lưu trong SQL và không đưa lên Git.
