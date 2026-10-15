# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Ứng dụng React, FastAPI và PostgreSQL hỗ trợ quản lý đề tài, đăng ký cá nhân/nhóm, xét duyệt, phân công GVHD, đề cương, tiến độ và tài liệu theo phiên bản. Hệ thống có đăng nhập, phân quyền theo nhiệm vụ và ghi nhận lịch sử thao tác.

Schema cho CSDL nghiệp vụ chính thức `kltn_management` được quản lý bằng Alembic. Revision đầu tạo 32 bảng phục vụ giai đoạn 1; hai schema 32 và 62 bảng cũ được giữ làm tài liệu tham khảo. Phần hội đồng bảo vệ, chấm điểm và biên bản chưa triển khai; chatbot AI hiện là prototype.

Tài liệu cần đối chiếu: [schema lõi 32 bảng](database/core/kltn-core-schema.sql), [schema nguồn 62 bảng](database/kltn-schema-consolidated.sql), [schema chính thức](database/official/kltn-management-schema.sql), [đặc tả API](docs/design/api-design.md), [luồng đăng ký đề tài](docs/design/registration-workflow.md) và [video demo](docs/demo/video-luong-dang-ky-de-tai.mp4).
