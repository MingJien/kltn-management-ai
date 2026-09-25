# ADR-002 — PostgreSQL là nguồn dữ liệu giao dịch chính

## Trạng thái

PROPOSED — baseline kỹ thuật cho triển khai CSDL.

## Bối cảnh

KLTN quản lý workflow, điểm cá nhân, biên bản, version và audit. Các dữ liệu này cần constraint, transaction và history. Qdrant chỉ phục vụ tìm kiếm vector/RAG dẫn xuất.

## Phương án

1. PostgreSQL làm nguồn giao dịch chính; Qdrant là index dẫn xuất.
2. Qdrant hoặc vector database làm nguồn chính.
3. Lưu toàn bộ metadata trong object storage.

## Quyết định

PostgreSQL lưu state, quyền ngữ cảnh, metadata/version, kết quả kiểm tra và audit. File bytes đi qua storage abstraction; Qdrant chỉ nhận index/payload đã được phép và có thể tái tạo từ dữ liệu hợp lệ trong PostgreSQL.

## Lý do

- Quan hệ KLTN và constraint cần nhất quán giao dịch.
- Quyền truy cập và thay đổi visibility phải chặn ngay tại nguồn chính.
- Chỉ mục vector có thể lỗi hoặc xây lại mà không làm hỏng workflow.

## Hệ quả

- Không lưu vector, raw prompt hay secret vào PostgreSQL baseline.
- FK nghiệp vụ dùng ON DELETE RESTRICT; version được append-only nơi cần.
- Migration Alembic là artifact bất biến sau khi dùng trong môi trường chia sẻ.

## Tham chiếu

- [Quyết định thiết kế CSDL](../design/database-design-decisions.md)
- [ERD](../design/erd.md)
- [Thiết kế similarity/RAG](../ai/similarity-design.md)
