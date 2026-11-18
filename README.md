# Hệ thống quản lý khóa luận tốt nghiệp

Ứng dụng React, FastAPI và PostgreSQL hỗ trợ quản lý KLTN của Khoa Công nghệ và Kỹ thuật, Trường Đại học Đồng Tháp.

## Chức năng hiện có

- Quản lý tài khoản, phân quyền theo đợt, hồ sơ sinh viên và giảng viên, đề tài, đăng ký cá nhân hoặc nhóm và tiếp nhận khóa luận.
- Theo dõi đề cương, tiến độ, tài liệu và phản hồi theo phiên bản; thông báo hạn nộp và kết quả xử lý. Hỗ trợ đổi đề tài, gia hạn và xin thôi KLTN trên hệ thống.
- Phân công phản biện, nhận xét Mẫu 7/8, xác nhận điều kiện bảo vệ và xét điểm thưởng công bố khoa học theo từng sinh viên.
- Lập hội đồng, xếp và đổi lịch, điểm danh, chấm điểm, lập biên bản, chốt kết quả và xuất Mẫu 6, 9, 10, 11 từ biểu mẫu gốc. Có xử lý bảo vệ bổ sung, đính chính sau khóa và lịch sử phát hành bản in.
- Nộp và duyệt bản hoàn thiện sau bảo vệ; tra cứu, xem và tải khóa luận trong kho nội bộ. Dashboard tổng hợp tiến độ, kết quả và tình trạng lưu kho theo đợt, bộ môn.
- Có bản thử nghiệm tìm đề tài tương tự và so sánh cặp báo cáo PDF/Word, hỗ trợ OCR khi cấu hình Tesseract. Chatbot hiện truy xuất đoạn nguồn và trích dẫn; chất lượng AI trên dữ liệu thực tế và chức năng sinh câu trả lời cần tiếp tục hoàn thiện, đánh giá.

## Ràng buộc chính

- Thao tác, tài liệu và thống kê giới hạn theo vai trò và phạm vi được giao. GVHD không tham gia hội đồng đánh giá đề tài mình hướng dẫn.
- Hồ sơ bảo vệ cần đủ điều kiện và đúng phiên bản báo cáo. Kết quả, lịch sử đính chính và bản in đã phát hành được lưu để đối chiếu. Mẫu 10/11 tổng hợp toàn đợt; Mẫu 11 cần chọn hoặc nhập mã học phần.
- Kho chỉ đưa bản đã duyệt vào tra cứu; bản thu hồi và quyết định xử lý vẫn được giữ trong lịch sử. Tệp tải lên cần được ClamAV xác nhận an toàn trước khi sử dụng.
- Gia hạn theo quyết định của Khoa, tối đa 5 tháng. Thời hạn xin thôi và các bước xác nhận áp dụng theo cấu hình và trạng thái hồ sơ trên hệ thống.
- CSDL hiện có được cập nhật bằng Alembic; không chạy lại SQL khởi tạo trên CSDL đang sử dụng. Cấu hình cục bộ và dữ liệu thật không đưa lên Git.

## Chạy local

Mở hai cửa sổ PowerShell:

    Set-Location 'D:\KLTN'; .\.venv\Scripts\python.exe -m tools.run_demo_api

    npm --prefix 'D:\KLTN\frontend' run dev -- --host 127.0.0.1 --port 1573 --strictPort

Mở http://127.0.0.1:1573. Cấu hình và mật khẩu nằm trong `.env` cục bộ.

## Kiểm tra và tài liệu

    .\.venv\Scripts\python.exe -m tools.validate_official_database
    npm run build --prefix 'D:\KLTN\frontend'

[Kiểm chứng NV6](docs/evidence/nv6-release-validation-2026-11-18.md) · [Hội đồng và bảo vệ](docs/design/nv6-defense-operations.md) · [Kho nội bộ và thống kê](docs/design/nv6-archive-reporting.md) · [Biểu mẫu](docs/design/defense-forms.md) · [AI thử nghiệm](docs/ai/prototype.md)
