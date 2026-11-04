# Kiểm chứng NV6 tuần 2

- PostgreSQL cục bộ đã áp dụng revision `20261104_0021`. Kiểm tra cấu trúc bằng `python -m tools.validate_official_database` báo 45 bảng nghiệp vụ, 125 khóa ngoại, 105 CHECK, 37 UNIQUE và 31 chỉ mục khai báo trong model.
- `python -m pytest tests/test_withdrawals.py tests/test_nv6_defense.py tests/test_nv6_evaluation.py -q`: 30 ca đạt trên PostgreSQL. Dữ liệu giả được tạo trong giao dịch và rollback. Ca bảo vệ xác minh quyền xem, điều kiện xếp lịch, điểm danh từng sinh viên, trần điểm, việc khóa dữ liệu, đọc nội dung Mẫu 9 và giá trị Mẫu 11.
- `python -m pytest tests/test_report_similarity.py -q --tb=short`: 1 ca đạt với Tesseract 5.4 và `vie+eng`. PDF scan tiếng Việt khớp cả chữ gõ và ảnh chèn trong một DOCX tự tạo. Ca này kiểm tra luồng đối chiếu, chưa đo chất lượng OCR trên tập báo cáo thực tế.
- `npm run build --prefix frontend`: hoàn tất build frontend. Chưa chạy được hai ca Playwright xin thôi vì công cụ chạy yêu cầu ClamAV thật và daemon chưa sẵn sàng. Chưa đối chiếu trang in với biểu mẫu phát hành chính thức của Khoa.
