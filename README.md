# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Prototype React, FastAPI và PostgreSQL cho quy trình quản lý khóa luận của Khoa CN&KT.

## Trạng thái hiện tại — NV5

Đã có giao diện và API cho tài khoản/phân quyền; nhập danh sách SV/GV; đề xuất, duyệt đề tài; đăng ký cá nhân/nhóm và xác nhận thành viên; GV tiếp nhận; tạo hồ sơ khóa luận và phân công GVHD. Sau khi tiếp nhận, hệ thống có mốc tiến độ, báo cáo theo phiên bản, ghi nhận nộp trễ, gia hạn theo đợt có lý do/lịch sử và phản hồi của GVHD. Tài liệu có phiên bản, hạn nộp, quét tệp bằng ClamAV cục bộ, nhận xét gắn đúng phiên bản, tệp phản hồi và xuất bản đã duyệt có footer. Có kho biểu mẫu theo đợt, thông báo trong ứng dụng và nhật ký hoạt động.

Các luồng hội đồng/bảo vệ, chấm điểm và biên bản chính thức, rút khóa luận sau khi đã chốt, dữ liệu chuyên môn GV đã xác minh và AI hoàn chỉnh chưa thuộc phần đã hoàn tất.

## Cơ sở dữ liệu

Database runtime là PostgreSQL `kltn_management`; schema hiện tại ở Alembic head `20261028_0015`, gồm **39 bảng nghiệp vụ** và bảng kỹ thuật `alembic_version`. Đây là tập bảng chọn lọc từ mô hình 62 bảng, không phải bản 32 bảng nguyên trạng.

So với head `20261024_0006`, bốn bảng được thêm bằng migration:

- `registration_form_version`: lưu các phiên bản Mẫu 1a/1b nộp trước khi có hồ sơ khóa luận.
- `progress_review_annotation`: lưu nhận xét gắn với đúng phiên bản, nhận xét chung và tệp phản hồi.
- `official_form`: danh mục biểu mẫu/tài liệu của Khoa theo đợt và đối tượng xem.
- `official_form_version`: lịch sử phiên bản, phát hành và thu hồi tệp biểu mẫu.

`document_deadline` đã được tạo ở migration `20261022_0005`; file SQL tổng hợp trước đây bị thiếu bảng này và nay đã đồng bộ. Schema-only hiện hành: [database/official/kltn-management-schema.sql](database/official/kltn-management-schema.sql). Các thay đổi sau này tiếp tục bằng Alembic; không chạy lại schema-only trên database đang dùng.

## Chạy giao diện local

Chạy API và frontend trong hai cửa sổ PowerShell riêng:

```powershell
Set-Location 'D:\KLTN'
.\.venv\Scripts\python.exe -m tools.run_demo_api
```

```powershell
npm --prefix 'D:\KLTN\frontend' run dev
```

Mở `http://localhost:5173/`. Cấu hình thật nằm trong `.env` cục bộ; chỉ dùng `.env.example` làm mẫu.
