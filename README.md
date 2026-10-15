# Quản lý khóa luận tốt nghiệp

Ứng dụng React, FastAPI và PostgreSQL hỗ trợ quản lý đề tài, đăng ký khóa luận và theo dõi quá trình thực hiện.

## Hiện trạng

- Đăng nhập email/mật khẩu, kích hoạt và khôi phục tài khoản; phân quyền theo vai trò và phân công theo đợt.
- Quản lý năm học, đợt KLTN, danh sách đủ điều kiện, đề tài, đăng ký nhóm, xét duyệt và chốt GVHD.
- Theo dõi khóa luận, thay đổi GVHD có đồng thuận, phân công công việc, mốc/báo cáo tiến độ, tài liệu theo phiên bản và lịch sử xử lý.
- AI mới là phần thử nghiệm trên dữ liệu giả. Hội đồng, chấm điểm và biên bản bảo vệ chưa nằm trong phạm vi hiện tại.

## Tài liệu bàn giao

- Danh sách 32 bảng lõi: [database/core/README.md](database/core/README.md) và [schema lõi](database/core/kltn-core-schema.sql).
- Schema gộp hiện hành đến migration `20261010_0013`: [database/kltn-schema-consolidated.sql](database/kltn-schema-consolidated.sql) (62 bảng nghiệp vụ và `alembic_version`; chỉ để xem thiết kế).
- Đặc tả API: [docs/design/openapi.yaml](docs/design/openapi.yaml).
- Video luồng đăng ký đề tài: [docs/demo/video-luong-dang-ky-de-tai.mp4](docs/demo/video-luong-dang-ky-de-tai.mp4) (Git LFS).

## Chạy bản phát triển

Tạo `.env` từ `.env.example`, cấu hình PostgreSQL, rồi chạy migration và cài frontend:

```powershell
py -m pip install -e ".[dev]"
py -m alembic upgrade head
npm ci --prefix frontend
```

Chạy `py -m tools.run_demo_api` và `npm run dev --prefix frontend` ở hai terminal; mở `http://localhost:5173`.
