# ADR-001 — Backend FastAPI theo modular monolith

## Trạng thái

PROPOSED — được dùng làm baseline thiết kế; chỉ chuyển thành quyết định triển khai khi bắt đầu backend.

## Bối cảnh

Hệ thống cần các workflow KLTN liên kết chặt: quyền ngữ cảnh, đăng ký đề tài, đề cương, tiến độ, tài liệu, Hội đồng, điểm và kho tra cứu. Chưa có requirement về độc lập triển khai hoặc tải lớn cho từng phần.

## Phương án

1. FastAPI modular monolith.
2. Microservice theo từng nghiệp vụ.
3. Một ứng dụng không có ranh giới module.

## Quyết định

Chọn FastAPI modular monolith, chia module theo ownership nghiệp vụ trong architecture.md. Mỗi module có ranh giới dữ liệu và service rõ, nhưng sử dụng cùng một deployment và PostgreSQL giao dịch.

## Lý do

- Phù hợp phạm vi KLTN, ít hạ tầng vận hành.
- Transaction liên module và authorization dễ giữ nhất quán.
- Không tự thêm Kafka, Kubernetes, Redis hoặc service phân tán khi chưa có requirement.
- Vẫn có đường tách module sau này nếu xuất hiện nhu cầu có căn cứ.

## Hệ quả

- API và migration phải giữ ownership module rõ ràng.
- Không được dùng module chung để bypass authorization hay state guard.
- Bất kỳ quyết định tách service sau này cần ADR mới và căn cứ về vận hành/tải.

## Tham chiếu

- [Yêu cầu nghiệp vụ](../01-requirements/business-requirements.md)
- [Kiến trúc hệ thống](../02-design/architecture.md)
- [Quyết định thiết kế CSDL](../02-design/database-design-decisions.md)
