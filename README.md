# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Repository này chứa **sản phẩm hiện có** của đồ án KLTN: tài liệu phân tích, thiết kế và mã nguồn nền tảng CSDL PostgreSQL. Mở các liên kết dưới đây để xem từng phần; dữ liệu hồ sơ sinh viên và tệp KLTN thật không nằm trong repository.

## Xem sản phẩm

| Nội dung | Tệp nên mở |
| --- | --- |
| Phạm vi, nguồn và điểm chưa chốt | [18 câu hỏi GVHD](docs/01-requirements/18-cau-hoi-gvhd-mapping.md), [danh mục nguồn](docs/00-sources/source-register.md), [12 vấn đề còn mở](docs/01-requirements/open-issues.md) |
| Nghiệp vụ và yêu cầu | [Yêu cầu nghiệp vụ](docs/01-requirements/business-requirements.md), [quy tắc](docs/01-requirements/business-rules.md), [quy trình](docs/01-requirements/business-process.md) |
| Người dùng và quyền | [Actor/vai trò](docs/01-requirements/actors-and-roles.md), [ma trận phân quyền](docs/01-requirements/permission-matrix.md) |
| Chức năng hệ thống | [Danh mục use case](docs/01-requirements/use-case-catalog.md), [sơ đồ use case](docs/02-design/use-case.drawio) |
| Thiết kế dữ liệu | [ERD trình bày](docs/02-design/erd-for-advisor.drawio), [ERD đầy đủ](docs/02-design/erd.md), [từ điển dữ liệu](docs/02-design/data-dictionary.md), [giải thích từng bảng/cột](docs/02-design/database-explained.md) |
| File SQL để dựng CSDL mới | [schema-postgresql.sql](database/schema-postgresql.sql) |
| Mã nguồn CSDL | [SQLAlchemy models](backend/db/models/entities.py), [Alembic migration đầu](backend/migrations/versions/20260920_0001_create_initial_kltn_schema.py), [migration tiếp theo](backend/migrations/versions/20260924_0002_bind_proposal_signature_version.py) |
| Kết quả kiểm chứng | [Kết quả kiểm chứng CSDL](docs/02-design/ket-qua-kiem-chung-csdl.md), [26 ca kiểm tra](backend/db/validate_schema.py) |
| Thiết kế API và giao diện | [API](docs/02-design/api-design.md), [OpenAPI](docs/02-design/openapi.yaml), [wireframe](docs/02-design/wireframes.md) |
| Hướng AI | [Thiết kế tương đồng](docs/03-ai/similarity-design.md), [kiến trúc hệ thống](docs/02-design/architecture.md) |

## CSDL gồm những gì?

Có **62 bảng của mô hình và 606 cột**. PostgreSQL còn có bảng kỹ thuật `alembic_version` với một cột, vì vậy pgAdmin hiện **63 bảng và 607 cột vật lý**. Hai database kiểm tra cục bộ `kltn_dev` và `kltn_ai` đều ở Alembic revision `20260924_0002`, qua **26/26 ca kiểm tra**, không phát hiện lệch model/schema và không có dòng dữ liệu nghiệp vụ sau kiểm thử.

File [schema-postgresql.sql](database/schema-postgresql.sql) là **một file SQL tạo cấu trúc trên database PostgreSQL mới, trống**. Nó chứa bảng, kiểu dữ liệu, khóa chính, khóa ngoại và các ràng buộc; không chứa dữ liệu nghiệp vụ hay mật khẩu. File truy vấn thực hành cá nhân không phải tệp nộp. Với database đã có bảng, dùng các migration Alembic để cập nhật, không chạy lại file SQL tạo mới.

## Trạng thái triển khai

- Đã hoàn thành phần phân tích nghiệp vụ, use case, phân quyền, thiết kế dữ liệu và nền tảng CSDL trong phạm vi hiện tại.
- Thiết kế API, giao diện và hướng AI đã có tài liệu; **API/giao diện/AI chưa chạy thành ứng dụng hoàn chỉnh**.
- Các điểm cần Khoa/GVHD xác nhận vẫn được đánh dấu `OPEN`, đặc biệt hiệu lực rubric Mẫu 6 so với QĐ2919 và chữ ký biên bản theo đúng loại văn bản.

## Cách dựng CSDL từ mã nguồn

Sao chép `.env.example` thành `.env` trên máy của người chạy, nhập cấu hình PostgreSQL của chính máy đó, rồi chạy `python -m alembic -c alembic.ini upgrade head`. Để kiểm tra, chạy `python -m backend.db.validate_schema`. File `.env` thật và dữ liệu PostgreSQL không được đưa lên GitHub.
