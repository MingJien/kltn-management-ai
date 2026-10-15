# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

React + FastAPI + PostgreSQL. CSDL nghiệp vụ chính thức là `kltn_management`; revision đầu `20261015_0001_official` tạo 32 bảng giai đoạn 1. Hai schema 32/62 bảng cũ chỉ để đối chiếu. Runtime từ chối URL trỏ sang database cũ.

Hiện có đăng nhập và phân quyền theo phạm vi, năm học/đợt và danh sách đủ điều kiện, đề tài do GV hoặc SV đề xuất, đăng ký nhóm tự xác nhận, xét duyệt/chốt GVHD, đề cương theo phiên bản, tiến độ, tài liệu riêng tư theo phiên bản và audit. AI vẫn là prototype; hội đồng, chấm điểm và biên bản bảo vệ chưa triển khai.

Cần quản trị viên PostgreSQL tạo **một lần** database `kltn_management` và cấp quyền cho tài khoản ứng dụng. Đặt `DATABASE_URL` của phiên chạy trỏ đúng database mới; `.env` cũ trên máy không được dùng làm nguồn chuyển tự động. Trong PowerShell, sau khi đã cấu hình URL thật trong phiên hiện tại:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic -c alembic-official.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c alembic-official.ini check
.\.venv\Scripts\python.exe -m tools.validate_official_database
npm ci --prefix frontend
npm run build --prefix frontend
```

Chạy `.\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --reload` và `npm run dev --prefix frontend` ở hai terminal cùng cấu hình URL mới.

Mỗi thay đổi schema sau này tạo revision mới trong `backend/migrations_official/versions/`, không sửa revision đầu đã áp dụng. Test dữ liệu giả chỉ chạy khi đặt `KLTN_ALLOW_SYNTHETIC_SEED=true` trên database thử nghiệm cô lập.

Tài liệu: [ma trận 62 bảng và quyết định chọn](docs/design/database-selection-report.md), [từ điển đủ cột](docs/design/database-dictionary.md), [ERD](docs/design/erd-kltn-management.md), [SQL chính thức để xem](database/official/kltn-management-schema.sql), [bằng chứng kiểm thử và bước bị chặn](docs/evidence/official-db-validation.md), [API runtime](docs/design/openapi-runtime.json), [video đăng ký đề tài](docs/demo/video-luong-dang-ky-de-tai.mp4).
