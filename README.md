# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Ứng dụng React, FastAPI và PostgreSQL quản lý tài khoản, đề tài, đăng ký khóa luận, GVHD, tiến độ và tài liệu. Chatbot AI hiện ở mức prototype, dùng dữ liệu giả.

## CSDL hiện hành

PostgreSQL `kltn_management`, Alembic head `20261021_0003`: **33 bảng nghiệp vụ** và bảng kỹ thuật `alembic_version`. Cập nhật cấu trúc qua Alembic; [SQL schema-only](database/official/kltn-management-schema.sql) chỉ để xem hoặc dựng database trống tạm, không chạy trên database đang dùng. Nếu máy còn ở revision `20261015_0001_official`, chạy `.\.venv\Scripts\python.exe -m alembic upgrade head` trong PowerShell để áp dụng hai migration tiếp theo.

## Tình hình hiện tại

- UI/API có quản lý tài khoản và phân quyền, danh sách sinh viên đủ điều kiện; luồng tạo/duyệt đề tài, đăng ký cá nhân hoặc nhóm, xác nhận thành viên và giảng viên tiếp nhận/từ chối. Khi giảng viên chấp nhận, hệ thống tạo hồ sơ khóa luận, thành viên và GVHD chính trong cùng giao dịch.
- Trong hồ sơ khóa luận có thông tin GVHD và lịch sử phân công; nộp đề cương theo phiên bản, nhận xét và chốt; tạo mốc tiến độ cho đợt, nộp báo cáo, GVHD xác nhận hoặc yêu cầu sửa. Nộp trễ vẫn được nhận khi mốc còn mở và được đánh dấu `!` màu đỏ; người điều phối có thể gia hạn cả đợt kèm lý do và lịch sử.
- Tài liệu hỗ trợ nộp nhiều phiên bản, lưu mã kiểm tra, nhận xét/duyệt và tải theo quyền. Bản đề cương đủ điều kiện có thể xuất để ký ngoài với địa chỉ hệ thống, mã và thời gian; bản gốc được giữ nguyên.

Hội đồng/lịch bảo vệ, chấm điểm và biên bản chưa hoàn thiện. Chatbot chưa kết nối Gemini.

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

Mở `http://127.0.0.1:5173` và dùng cùng hostname này cho liên kết trong email để giữ đúng phiên đăng nhập. Mật khẩu và cấu hình thư thật chỉ nằm trong máy local, không có trong repository.
Trên máy phát triển, `KLTN_DEMO_MODE=true` trong `.env` hiện lựa chọn SV/GV/TBM giả lập tại trang đăng nhập; tài khoản kích hoạt qua email vẫn đăng nhập bằng mật khẩu.

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
