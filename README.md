# Hệ thống quản lý khóa luận tốt nghiệp

Ứng dụng React, FastAPI và PostgreSQL phục vụ quy trình KLTN của Khoa Công nghệ và Kỹ thuật, Trường Đại học Đồng Tháp.

## Hiện trạng

- Runtime dùng PostgreSQL kltn_management; schema hiện có 43 bảng nghiệp vụ, Alembic head 20261103_0020. Cập nhật CSDL qua migration; không chạy file SQL tổng hợp lên database đang dùng.
- NV5 có giao diện và API cho tài khoản/phân quyền, danh sách SV/GV, đề tài, xét duyệt, đăng ký cá nhân/nhóm, tiếp nhận và tạo hồ sơ khóa luận/GVHD.
- Hồ sơ khóa luận hỗ trợ đề cương, mốc và báo cáo tiến độ, hạn theo loại tài liệu, phiên bản, phản hồi đúng bản nộp, đánh dấu trễ, gia hạn theo đợt, thông báo và nhật ký.
- Tệp được quét qua ClamAV cục bộ; bản chưa xác nhận an toàn bị giới hạn tải/duyệt. Kho biểu mẫu Khoa quản lý phiên bản theo đợt; danh sách SV, đề tài và GVHD có thể xuất theo khung Mẫu 4 từ dữ liệu đã chốt.
- Có luồng xin thôi KLTN trong 14 ngày đầu, giữ lịch sử và xử lý riêng từng thành viên.
- Mẫu nhận xét Mẫu 7/8 gắn với đúng sinh viên và bản báo cáo; GV gửi nhận xét trên hệ thống, xuất phiếu có footer để ký ngoài. Người được phân công tiếp nhận hồ sơ hoặc TBM ghi nhận bản giấy theo mã bản xuất và căn cứ; không yêu cầu tải bản ký lên lại.
- Có hồ sơ chuyên môn GV, phân công theo đợt và kiểm tra điều kiện bảo vệ ở mức hiện tại.

Hội đồng, lịch bảo vệ, chấm điểm chính thức, biên bản Mẫu 9, kiểm tra tương đồng và chatbot AI hoàn chỉnh chưa triển khai.

## Chạy local

Mở hai cửa sổ PowerShell:

    Set-Location 'D:\KLTN'; .\.venv\Scripts\python.exe -m tools.run_demo_api

    npm --prefix 'D:\KLTN\frontend' run dev -- --host 127.0.0.1 --port 1573 --strictPort

Mở http://127.0.0.1:1573. Cấu hình máy và mật khẩu nằm trong .env cục bộ; không đưa lên Git.

## Kiểm tra

    .\.venv\Scripts\python.exe -m tools.validate_official_database
    npm run build --prefix 'D:\KLTN\frontend'

Các kiểm thử tích hợp dùng dữ liệu giả trong schema riêng; không gửi email thật.