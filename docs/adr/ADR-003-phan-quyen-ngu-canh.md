# ADR-003 — Phân quyền theo vai trò nền và ngữ cảnh tài nguyên

## Trạng thái

CONFIRMED_PROJECT_DECISION.

## Bối cảnh

Một người dùng dùng một tài khoản. GVHD, GVPB, Trưởng bộ môn, Trưởng khoa, Chủ tịch, Thư ký và thành viên Hội đồng thay đổi theo phân công/quyết định, không phải loại tài khoản riêng.

## Phương án

1. Tài khoản riêng cho mọi chức danh.
2. Ba base role kết hợp position, assignment và resource context.
3. Cho ADMIN bypass mọi quyền nghiệp vụ.

## Quyết định

Giữ ba base role ADMIN, LECTURER, STUDENT. Chức danh tổ chức, phân công và vai trò Hội đồng được biểu diễn bằng position/assignment/resource context có hiệu lực. Backend kiểm tra quyền, resource scope và state guard; giao diện chỉ hỗ trợ ẩn/hiện, không là lớp bảo vệ.

## Lý do

- Phản ánh thực tế một giảng viên có thể mang nhiều vai trò theo từng đợt/tài nguyên.
- Tránh nhiều account/password và tránh cấp quyền thừa.
- Bảo đảm ADMIN không tự có thẩm quyền duyệt nghiệp vụ.

## Hệ quả

- API không nhận role/assignment do client tự khẳng định.
- Mọi thao tác nhạy cảm phải trace tới assignment, CouncilMember hoặc resource ownership.
- ELIGIBILITY_VERIFIER là assignment cấu hình theo đợt cho đến khi OPEN-11 được chốt.

## Tham chiếu

- [Actor và vai trò](../01-requirements/actors-and-roles.md)
- [Ma trận phân quyền](../01-requirements/permission-matrix.md)
- [OPEN canonical](../01-requirements/open-issues.md)
