# Kiểm chứng PostgreSQL hiện hành — 16/10/2026

PostgreSQL local được kiểm tra trực tiếp: database `kltn_management`, Alembic revision `20261015_0001_official`, 32 bảng nghiệp vụ và bảng `alembic_version`.

- Validator đọc catalog xác nhận khớp metadata: **70 FK, 60 CHECK, 27 UNIQUE, 14 index tường minh**.
- `alembic current` trả `20261015_0001_official (head)`; `alembic check` trả `No new upgrade operations detected.`
- ERD theo cụm được sinh từ PostgreSQL ở chế độ chỉ đọc; đủ 6 PNG/SVG.
- `pytest tests/test_official_schema.py -q`: **6 passed**.
- `pytest tests/test_account_roster.py -q`: **2 passed**.
- `npm run build --prefix frontend`: thành công.
- `python -m tools.run_e2e`: **6 passed**; chỉ tạo rồi xóa schema kiểm thử ngẫu nhiên do lượt chạy này sở hữu trong `kltn_management`.

Các lượt kiểm cấu trúc và E2E không sửa dữ liệu trong schema `public`. Kết quả này xác nhận database local và code ở worktree khi chạy; không tự động xác nhận database trên máy khác.

## Kiểm tra lại tại `D:\KLTN`

```powershell
.\.venv\Scripts\python.exe -m tools.validate_official_database
.\.venv\Scripts\python.exe -m alembic -c alembic-official.ini current
.\.venv\Scripts\python.exe -m alembic -c alembic-official.ini check
```

Database hiện hành được cập nhật qua migration chính thức trong `backend/migrations_official/`. Không chạy lại SQL schema-only trên database có dữ liệu.
