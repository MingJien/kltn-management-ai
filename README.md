# Hệ thống quản lý khóa luận tốt nghiệp — Khoa Công nghệ và Kỹ thuật, ĐH Đồng Tháp

## Hiện trạng

- Runtime dùng PostgreSQL `kltn_management`: 39 bảng nghiệp vụ, Alembic head `20261029_0016`. Schema là tập chọn lọc từ mô hình 62 bảng; các file SQL tham khảo 32/62 bảng được giữ nguyên.
- Đã có luồng tài khoản/phân quyền, nhập danh sách SV/GV, đề tài và xét duyệt, đăng ký cá nhân/nhóm, GV tiếp nhận và tạo hồ sơ khóa luận/GVHD.
- Hồ sơ nộp & xét duyệt gồm Mẫu 1a/1b, kế hoạch Mẫu 2, đề cương Mẫu 3, cuốn báo cáo KLTN và tài liệu hỗ trợ; có phiên bản, phản hồi đúng phiên bản, quét tệp, lịch sử và xuất bản đã duyệt có footer.
- Có mốc/báo cáo tiến độ, đánh dấu nộp trễ, gia hạn theo đợt có lý do/lịch sử, thông báo trong ứng dụng, nhật ký hoạt động và kho biểu mẫu Khoa.
- Hội đồng/bảo vệ, chấm điểm, rút khóa luận sau khi đã chốt, kiểm tra tương đồng và chatbot AI hoàn chỉnh chưa triển khai.

## Chạy local

API và giao diện chạy ở hai cửa sổ PowerShell tại thư mục dự án:

```powershell
Set-Location 'D:\KLTN'
.\.venv\Scripts\python.exe -m tools.run_demo_api
```

```powershell
npm run dev --prefix 'D:\KLTN\frontend'
```

Mở `http://localhost:5173`. Cấu hình máy và mật khẩu nằm trong `.env` cục bộ; không đưa file đó lên Git.

## Kiểm tra nhanh

```powershell
.\.venv\Scripts\python.exe -m tools.validate_official_database
npm run build --prefix 'D:\KLTN\frontend'
```

Cập nhật CSDL bằng Alembic; không chạy lại file schema tổng hợp lên database đang sử dụng.