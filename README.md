# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Source của hệ thống quản lý khóa luận tốt nghiệp, gồm PostgreSQL, FastAPI và React. AI hiện ở mức thử nghiệm truy xuất tài liệu và tìm đề tài tương tự trên dữ liệu giả; không tự chấm đạo văn hoặc quyết định kết quả học tập.

## Chức năng đã có

- Đăng nhập bằng email/mật khẩu của tài khoản đã được cấp, duy trì phiên bằng cookie và kiểm tra quyền tại API theo vai trò, bộ môn và quan hệ với đề tài.
- Giảng viên tạo, sửa và gửi đề tài.
- Trưởng bộ môn duyệt, trả về để sửa hoặc từ chối đề tài thuộc bộ môn.
- Sinh viên tự đề xuất đề tài hoặc đăng ký đề tài đã duyệt, tham gia nhóm trong chỉ tiêu và thời hạn đăng ký.
- Giảng viên tiếp nhận hoặc từ chối đăng ký, kèm lý do khi từ chối.
- Thử nghiệm tìm đề tài tương tự và tra cứu nguồn trên corpus giả.

Tài khoản hiện dùng dữ liệu giả để kiểm thử; chưa có quy trình cấp tài khoản thật, xác minh email hoặc khôi phục mật khẩu. Phân công GVHD, tiến độ, tài liệu, hội đồng, chấm điểm, biên bản và tích hợp Gemini tiếp tục được phát triển ở các giai đoạn sau.

## Cấu trúc

| Thư mục | Nội dung |
| --- | --- |
| `backend/` | API FastAPI, nghiệp vụ, mô hình SQLAlchemy và Alembic migrations. |
| `frontend/` | Giao diện React. |
| `database/` | Schema PostgreSQL để dựng database mới và schema lõi để xem thiết kế. |
| `docs/` | Yêu cầu, thiết kế, ERD và đặc tả API. |
| `tests/` | Kiểm thử backend. |
| `tools/` | Script seed dữ liệu giả, sinh ERD và kiểm tra CSDL. |

## Chạy trên máy phát triển

1. Sao chép `.env.example` thành `.env` và điền cấu hình PostgreSQL trên máy. Không đưa `.env`, mật khẩu, dữ liệu thật hoặc tài liệu gốc lên Git.
2. Cài môi trường và nâng CSDL:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

3. Chạy API và giao diện ở hai terminal:

```powershell
.\.venv\Scripts\python.exe -m tools.run_demo_api
```

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

Mở `http://localhost:5173`. Dữ liệu và tài khoản demo chỉ tạo trên máy, không nằm trong repository.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m backend.db.validate_schema
.\.venv\Scripts\python.exe -m pytest tests -q
npm run build --prefix frontend
.\.venv\Scripts\python.exe -m tools.run_e2e
```

## Tài liệu chính

- [Yêu cầu, quy trình và phân quyền](docs/requirements/)
- [ERD và từ điển dữ liệu](docs/design/erd.md)
- [Schema lõi PostgreSQL](database/core/kltn-core-schema.sql)
- [Schema đầy đủ PostgreSQL](database/kltn-schema-consolidated.sql)
- [Đặc tả API](docs/design/openapi.yaml)
- [Luồng đề tài và đăng ký](docs/design/registration-workflow.md)
- [Thiết kế thử nghiệm AI](docs/ai/prototype.md)

## Phạm vi dữ liệu

Repository chỉ dùng dữ liệu giả và cấu hình mẫu. PostgreSQL là nguồn dữ liệu nghiệp vụ; Qdrant chỉ lưu chỉ mục truy xuất có thể tái tạo. Việc sử dụng tài liệu thật hoặc gửi nội dung cho dịch vụ AI phải theo chính sách được Khoa/Trường phê duyệt.
