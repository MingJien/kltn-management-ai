# Kiểm chứng CSDL chính thức giai đoạn 1 — 15/10/2026

**Trạng thái: EXECUTED, chưa DONE.** Revision `20261015_0001_official` đã chạy trên PostgreSQL 17 thật trong cluster kiểm thử cô lập, database đặt tên `kltn_management` tại cổng 55432. Đây là môi trường kiểm thử, không phải cluster PostgreSQL thường trực tại cổng 5432. Không sao chép dữ liệu thật và không ghi vào `kltn_ai`, `kltn_dev`, `kltn_core`.

Trên cluster thường trực, tài khoản ứng dụng truy cập được database `postgres` để kiểm tra nhưng `rolcreatedb=false`; `kltn_management` chưa tồn tại. Kết nối vai trò `postgres` yêu cầu mật khẩu quản trị chưa được cấp. Vì vậy tạo database lâu dài, upgrade trên đó và chuyển vận hành thực tế là **BLOCKED**, không được báo đã triển khai thường trực. File `.env` thật được giữ nguyên; runtime đã chặn URL sang database cũ để tránh ghi nhầm.

## Lệnh và kết quả đã chạy

Các lệnh dưới đây chạy với `DATABASE_URL` được đặt tạm trong phiên PowerShell tới database thử nghiệm cô lập. Mật khẩu nằm trong file Git bỏ qua; không đưa vào báo cáo.

| Kiểm chứng | Trạng thái | Bằng chứng/kết quả |
|---|---|---|
| 1. PostgreSQL trống → revision đầu | PASS trên cluster kiểm thử | Tạo database trống và chạy `python -m alembic -c alembic-official.ini upgrade head`; không phụ thuộc revision cũ. |
| 2. Alembic upgrade head | PASS trên cluster kiểm thử | `alembic current` → `20261015_0001_official (head)`; chạy lại upgrade không tạo thay đổi. |
| 3. Drift metadata/migration | PASS trên cluster kiểm thử | `python -m alembic -c alembic-official.ini check` → `No new upgrade operations detected.` |
| 4–5. Số bảng và bảng ngoài phạm vi | PASS trên cluster kiểm thử | `python -m tools.validate_official_database` → 32 bảng nghiệp vụ + `alembic_version`, đúng danh sách chọn, không có bảng hội đồng/chấm điểm/AI. |
| 6. PK/FK/UNIQUE/CHECK/NOT NULL/index | PASS trên cluster kiểm thử | Cùng validator so trực tiếp PostgreSQL catalog với metadata: 70 FK, 60 CHECK, 27 UNIQUE, 14 index khai báo và PK/NOT NULL mọi bảng. |
| 7. Đăng nhập, xác thực, khóa, phạm vi quyền | PASS trên cluster kiểm thử | Bộ test API; E2E cookie/session, kích hoạt và admin phân công. |
| 8–9. Đề tài GV/SV, duyệt/trả/sửa tên | PASS trên cluster kiểm thử | Bộ test API và E2E đề tài GV/SV. |
| 10. Đăng ký cá nhân/nhóm, từng người tự tham gia | PASS trên cluster kiểm thử | Test API và E2E nhóm; fixture cũ đã sửa theo cách tự xác nhận. |
| 11. Chống trùng/vượt sức chứa | PASS trên cluster kiểm thử | Test API và E2E tranh chỗ cuối. |
| 12. GV tiếp nhận/TBM chốt/GVHD chính | PASS trên cluster kiểm thử | Test API và E2E; chốt tạo thesis/member/advisor trong transaction. |
| 13. Đề cương, phiên bản, nhận xét, chốt | PASS trên cluster kiểm thử | Test API kiểm quyền, checksum, v1/v2 và bản giấy; E2E UI nộp v1 → sửa → v2 → GVHD xác nhận → TBM chốt. Ghi tham chiếu bản giấy Trưởng khoa qua API, không nhận là chữ ký số. |
| 14. Mốc, báo cáo, góp ý chéo | PASS ở API/PostgreSQL | `tests/test_core_workspace.py`; COMMENT_ONLY không thể xác nhận thay GVHD. Chưa có kịch bản trình duyệt riêng cho toàn bộ tiến độ. |
| 15. Tài liệu upload/xem/tải/phiên bản/quyền | PASS ở API/PostgreSQL | `tests/test_core_workspace.py`; checksum sai bị chặn. Chưa có kịch bản trình duyệt riêng cho toàn bộ tài liệu. |
| 16. Truy cập trái phép/trường hợp biên | PASS ở API/PostgreSQL | 53 ca backend gồm admin không duyệt nghiệp vụ, SV ngoài nhóm, GV ngoài phạm vi; E2E accessibility và lỗi đăng nhập. |
| 17. Transaction rollback khi lỗi | PASS ở API/PostgreSQL | Ca kiểm lỗi commit tài liệu và đề cương đều xóa tệp đã ghi; đăng ký lỗi không để đề tài mồ côi. |
| 18. Backend/API chạy với PostgreSQL mới | PASS trên cluster kiểm thử | Uvicorn chạy trên cổng 8001 trong E2E, kết nối database cô lập; vận hành cluster thường trực BLOCKED. |
| 19. Frontend build/luồng tích hợp | PASS trên cluster kiểm thử | `npm run build --prefix frontend`; `python -m tools.run_e2e` → **6 passed**, mỗi lượt tạo/xóa schema ngẫu nhiên chỉ thuộc test. |
| 20. Regression giai đoạn 1 | PASS trên cluster kiểm thử | `pytest tests/test_registration.py tests/test_account_roster.py tests/test_auth.py tests/test_core_workspace.py` → **54 passed**; `tests/test_official_schema.py` → **5 passed**. AI không dùng DB: **3 passed** với `--basetemp local/pytest-ai-temp`. Test AI DB cũ không chạy vì ngoài schema giai đoạn 1. |
| 21. Không phụ thuộc bảng giai đoạn sau | PASS trên cluster kiểm thử | Kiểm metadata 32 bảng và mọi FK chỉ tới tập chọn; `LegacyBase` giữ mapping prototype riêng. |

Tất cả PASS ở đây áp dụng cho dữ liệu giả trong PostgreSQL cô lập, không chứng minh môi trường vận hành thường trực hoặc nguồn dữ liệu thật của Khoa. QĐ2919 trên Drive là PDF ảnh chưa trích xuất được chữ; chỉ dùng các phần đã ghi nhận trong dự án và QĐ5964/Mẫu 1a/1b/3 đọc được. Chưa xác nhận đối chiếu đầy đủ các biểu mẫu bản giấy tại Khoa.

## Bước thủ công để triển khai thường trực

Người quản trị PostgreSQL tạo database mới, ví dụ trong PowerShell khi `psql` đã nằm trong `PATH` (lệnh hỏi mật khẩu quản trị, không ghi mật khẩu vào Git):

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -c 'CREATE DATABASE kltn_management OWNER kltn_app;'
```

Sau đó người vận hành đặt `DATABASE_URL` **trỏ đích danh** `kltn_management` bằng cơ chế bí mật tại máy, chạy:

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic-official.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c alembic-official.ini check
.\.venv\Scripts\python.exe -m tools.validate_official_database
```

Khi ba lệnh đạt, mới bật backend/frontend với URL mới, cấp tài khoản/dữ liệu Khoa theo quy trình được duyệt và kiểm lại các luồng bằng dữ liệu được phép. Không chạy seed giả trên database thường trực. Không chạy chuỗi Alembic cũ (`alembic.ini`) cho database này. Kết quả triển khai thường trực cần được ghi lại sau khi có quyền và review độc lập.
