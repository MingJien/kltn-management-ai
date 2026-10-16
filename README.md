# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Ứng dụng React, FastAPI và PostgreSQL hỗ trợ tài khoản, phân quyền, danh sách sinh viên đủ điều kiện, tạo và duyệt đề tài, đăng ký cá nhân/nhóm, tiếp nhận của giảng viên, đề cương, tiến độ và tài liệu theo phiên bản. AI hiện chỉ được thử trên dữ liệu giả; chưa kết nối Gemini.

## CSDL hiện hành

PostgreSQL `kltn_management`, Alembic revision `20261015_0001_official`: 32 bảng nghiệp vụ và `alembic_version`. Cấu trúc đang dùng được quản lý bằng `backend/migrations_official/`; chỉ cập nhật database qua Alembic. [SQL schema-only](database/official/kltn-management-schema.sql) là bản cấu trúc để xem hoặc dùng trong database trống tạm thời, không chạy trên database đang dùng.

## Chạy local

Tạo `.env` từ `.env.example`, đặt `DATABASE_URL` trỏ đúng `kltn_management`, rồi cài dependencies. Ứng dụng và Alembic dùng cổng trong `DATABASE_URL`; `POSTGRES_PORT` chỉ là cổng xuất ra máy khi chạy PostgreSQL bằng Docker Compose. Nếu dùng PostgreSQL đã cài trên máy, không cần chạy container.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Chạy API và giao diện ở hai terminal:

```powershell
.\.venv\Scripts\python.exe -m tools.run_demo_api
```

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

Mở `http://localhost:5173`. Dữ liệu tài khoản thử nghiệm và cấu hình thư thật chỉ nằm trong máy local, không có trong repository.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m tools.validate_official_database
.\.venv\Scripts\python.exe -m pytest tests -q
npm run build --prefix frontend
.\.venv\Scripts\python.exe -m tools.run_e2e
```

`run_e2e` tạo schema kiểm thử ngẫu nhiên riêng trong `kltn_management`, không dùng hay xóa bảng nghiệp vụ hiện có.

## Tài liệu chính

- [API hiện hành](docs/design/api-design.md) · [OpenAPI sinh từ FastAPI](docs/design/openapi.yaml)
- [ERD hiện hành](docs/design/erd-kltn-management.md) · [ERD theo cụm](docs/design/erd-clusters/README.md)
- [Từ điển dữ liệu](docs/design/database-dictionary.md)
- [Quy trình đăng ký](docs/design/registration-workflow.md)
- [Minh chứng cấu trúc CSDL](docs/evidence/official-db-validation.md)

Repository không chứa dữ liệu thật hay cấu hình bí mật. Nội dung AI thử nghiệm dùng corpus giả cục bộ; việc gửi tài liệu cho dịch vụ AI cần theo chính sách của Khoa/Trường.
