# Tệp CSDL PostgreSQL

Thư mục này gom các tệp SQL để tạo CSDL mới và xem cấu trúc CSDL. Dùng đúng file theo mục đích:

| Tệp | Dùng để làm gì | Có thay đổi CSDL không? |
| --- | --- | --- |
| [kltn-init-empty.sql](kltn-init-empty.sql) | Tạo toàn bộ schema hiện hành trên một PostgreSQL database mới, trống; Alembic head `20260925_0005`. | Có: tạo bảng, cột, khóa và ràng buộc. Chỉ chạy một lần trên database trống. |
| `kltn-ai-workbench.sql` (chỉ trên máy) | Xem danh sách bảng, toàn bộ cột/kiểu dữ liệu, khóa/ràng buộc, index, view, trigger và Alembic revision. Tệp này được Git bỏ qua vì phục vụ thao tác pgAdmin cá nhân. | Không: các câu lệnh đều là `SELECT`. |
| `kltn-ai-updates.sql` (chỉ trên máy) | Một tệp soạn lệnh ALTER/UPDATE/DELETE dùng lại nhiều lần trong pgAdmin. Đã để sẵn câu kiểm tra đúng database. Tệp được Git bỏ qua vì là sổ thao tác cá nhân. | Chỉ thay đổi CSDL khi bạn chọn và chạy lệnh ghi dữ liệu cụ thể. |

## Cập nhật database dự án đang dùng

Không chạy lại `kltn-init-empty.sql` trên `kltn_dev`, `kltn_ai` hoặc bất kỳ database đã có bảng nào. Khi thay đổi CSDL chính thức:

1. Sửa mô hình SQLAlchemy trong `backend/db/models/entities.py`.
2. Tạo migration mới trong `backend/migrations/versions/`.
3. Review migration rồi chạy `.\.venv\Scripts\python.exe -m alembic upgrade head` trên database đích.

`backend/migrations/` giữ lịch sử nâng cấp theo từng phiên bản; file SQL trong thư mục này là bản dựng mới và truy vấn xem cấu trúc. `schema-postgresql.sql` đã được hợp nhất vào `kltn-init-empty.sql` vì hai file cùng mục đích tạo schema mới; file canonical hiện ở revision mới nhất.

**Lưu ý:** Một tệp cá nhân giúp thao tác thuận tiện, nhưng không thay được lịch sử migration. Mỗi lần ứng dụng thay đổi cấu trúc bảng/cột chính thức, Alembic cần một revision mới để máy khác nâng cấp đúng thứ tự và không chạy lại lệnh cũ. Các quyết định thiết kế hiện tại đã có cấu trúc ở schema head `20260925_0005`, gồm `COMMENT_ONLY` cho góp ý chéo; xem [đối chiếu quyết định với CSDL](../docs/design/doi-chieu-quyet-dinh-csdl.md). Các quy tắc nhiều bảng/quyền/trạng thái vẫn cần backend kiểm trong transaction.
