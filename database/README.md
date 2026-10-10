# CSDL nộp

Repository chỉ giữ một schema CSDL dùng để trình bày phạm vi hiện tại của dự án:

| Tệp | Nội dung |
| --- | --- |
| [core/kltn-core-schema.sql](core/kltn-core-schema.sql) | Schema lõi gồm 32 bảng nghiệp vụ: tài khoản, phân quyền, đợt KLTN, điều kiện đăng ký, đề tài, đăng ký, khóa luận, GVHD, đề cương, tiến độ và tài liệu. Mỗi bảng có đầy đủ cột và ràng buộc trong một lệnh `CREATE TABLE`. |

Schema không có dữ liệu sinh viên, đề tài, hồ sơ hay mật khẩu. Mọi thay đổi cấu trúc chính thức của ứng dụng vẫn được quản lý qua Alembic migration trong `backend/migrations/`.

Chi tiết mục đích và ràng buộc của 32 bảng nằm tại [core/README.md](core/README.md).
