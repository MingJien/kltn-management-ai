# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Ứng dụng React, FastAPI và PostgreSQL hỗ trợ tài khoản, phân quyền, danh sách sinh viên đủ điều kiện, tạo và duyệt đề tài, đăng ký cá nhân/nhóm, tiếp nhận của giảng viên, đề cương, tiến độ và tài liệu theo phiên bản. Mẫu 2 và 3 được tải nguyên bản từ tệp chính thức do Khoa cung cấp (chỉ đọc, không đưa bản sao lên Git); hệ thống không tự dựng mẫu thay thế. Tệp đã nộp được lưu theo phiên bản và giữ nguyên bản gốc; tệp mới ở trạng thái “Đang cách ly – chưa quét” nên chưa thể tải xuống hoặc dùng để duyệt cho đến khi có máy quét tệp thật. Bản in từ mẫu chính thức chưa xuất được vì chưa có bộ sinh bản in từ mẫu; hệ thống báo chưa xuất được thay vì tạo bản giả lập. AI hiện chỉ được thử trên dữ liệu giả; chưa kết nối Gemini.

## CSDL hiện hành

PostgreSQL `kltn_management`, Alembic revision `20261022_0005`: 34 bảng nghiệp vụ và `alembic_version`. Bảng `department_major` lưu 10 cặp mã ngành–bộ môn của Khoa CN&KT để kiểm tra khi nhập Excel; các hồ sơ demo cũ được giữ nguyên. Cấu trúc đang dùng được quản lý bằng `backend/migrations_official/`; chỉ cập nhật database qua Alembic. [SQL schema-only](database/official/kltn-management-schema.sql) là bản cấu trúc để xem hoặc dùng trong database trống tạm thời, không chạy trên database đang dùng.

## Chạy local

Tạo `.env` từ `.env.example`, dùng database phát triển cục bộ và kiểm tra `DATABASE_URL` trước khi chạy migration. Ứng dụng và Alembic dùng cổng trong `DATABASE_URL`; `POSTGRES_PORT` chỉ là cổng xuất ra máy khi chạy PostgreSQL bằng Docker Compose. Nếu dùng PostgreSQL đã cài trên máy, không cần chạy container.

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

Mở `http://localhost:5173/` và dùng cùng hostname này cho các liên kết trong email để giữ cùng origin. Giữ cả API và frontend đang chạy trong hai terminal khi mở link. Nếu cổng 5173 đã bận, Vite sẽ báo lỗi thay vì chạy sang cổng khác. Mật khẩu và cấu hình thư thật chỉ nằm trong máy local, không có trong repository.
Trên máy phát triển, `KLTN_DEMO_MODE=true` trong `.env` hiện lựa chọn SV/GV/TBM giả lập tại trang đăng nhập; tài khoản kích hoạt qua email vẫn đăng nhập bằng mật khẩu.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m tools.validate_official_database
.\.venv\Scripts\python.exe -m pytest tests -q
npm run build --prefix frontend
.\.venv\Scripts\python.exe -m tools.run_e2e
```

`run_e2e` chỉ chạy khi `DATABASE_URL` trỏ một database kiểm thử riêng; script từ chối `kltn_management` để không ghi dữ liệu thử, tạo schema hay dọn dữ liệu trên database đang dùng. Khi chưa có database kiểm thử riêng, kết quả E2E được ghi BLOCKED thay vì chạy trên database nghiệp vụ.

## Tài liệu chính

- [API hiện hành](docs/design/api-design.md) · [OpenAPI sinh từ FastAPI](docs/design/openapi.yaml)
- [ERD hiện hành](docs/design/erd-kltn-management.md)
- [Từ điển dữ liệu](docs/design/database-dictionary.md)
- [Quy trình đăng ký](docs/design/registration-workflow.md)
- [Minh chứng cấu trúc CSDL](docs/evidence/official-db-validation.md)

Repository không chứa dữ liệu thật hay cấu hình bí mật. Nội dung AI thử nghiệm dùng corpus giả cục bộ; việc gửi tài liệu cho dịch vụ AI cần theo chính sách của Khoa/Trường.
