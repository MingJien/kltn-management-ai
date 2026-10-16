# Kiểm chứng PostgreSQL hiện hành — 16/10/2026

PostgreSQL local được kiểm tra trực tiếp: database `kltn_management`, Alembic revision `20261015_0001_official`, 32 bảng nghiệp vụ và bảng `alembic_version`.

- Validator đọc catalog xác nhận khớp metadata: **70 FK, 60 CHECK, 27 UNIQUE, 14 index tường minh**.
- `alembic current` trả `20261015_0001_official (head)`; `alembic check` trả `No new upgrade operations detected.`
- ERD theo cụm được sinh từ PostgreSQL ở chế độ chỉ đọc; đủ 6 PNG/SVG.
- `pytest tests -q`: **65 passed**, 1 cảnh báo deprecation từ thư viện kiểm thử.
- `python -m tools.export_runtime_openapi --check`: **PASS**; tệp OpenAPI công bố khớp trực tiếp FastAPI (72 đường dẫn, 83 thao tác).
- `npm run build --prefix frontend`: thành công sau khi đồng bộ mã về `D:\KLTN`.
- `python -m tools.run_e2e`: **6 passed**; chỉ tạo rồi xóa schema kiểm thử ngẫu nhiên do lượt chạy này sở hữu trong `kltn_management`.
- Model runtime và chuỗi Alembic đang hoạt động chỉ định nghĩa 32 bảng chính thức; model/migration 62 bảng cũ đã được rút khỏi source đang chạy. SQL cũ được giữ riêng trên máy để tham khảo.

Các lượt kiểm cấu trúc và E2E không sửa dữ liệu trong schema `public`. Kết quả này xác nhận database local và code tại máy khi chạy; không tự động xác nhận database trên máy khác.

## Kiểm tra lại tại `D:\KLTN`

```powershell
.\.venv\Scripts\python.exe -m tools.validate_official_database
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

Database hiện hành được cập nhật qua migration chính thức trong `backend/migrations_official/`. Không chạy lại SQL schema-only trên database có dữ liệu.
