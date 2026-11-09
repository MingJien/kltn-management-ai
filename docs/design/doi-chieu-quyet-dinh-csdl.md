# Đối chiếu nghiệp vụ với CSDL đang dùng

Ngày kiểm tra gần nhất: 20/10/2026. Phạm vi vật lý là PostgreSQL `kltn_management`, revision `20261020_0002`: 32 bảng nghiệp vụ và `alembic_version`. Validator đối chiếu cột, khóa và ràng buộc với metadata chính thức.

| Nghiệp vụ hiện tại | Bảng chính | Ghi chú triển khai |
| --- | --- | --- |
| Tài khoản và phân quyền | `user_account`, `student_profile`, `lecturer_profile`, `position_assignment`, `resource_assignment` | Xác thực, phạm vi quyền và phân công được kiểm trong backend. |
| Điều kiện theo đợt | `academic_year`, `thesis_round`, `eligibility_snapshot` | Kết quả được người có thẩm quyền xác nhận theo đợt. |
| Tạo và duyệt đề tài | `topic`, `topic_title_version`, `topic_requirement` | Lưu đề tài, lịch sử đổi tên và yêu cầu bổ sung. |
| Đăng ký cá nhân/nhóm | `topic_registration`, `registration_member` | Backend kiểm hạn, sức chứa, điều kiện, thành viên và đăng ký đang hiệu lực. |
| Chốt đăng ký | `thesis`, `thesis_member`, `advisor_assignment` | Sinh hồ sơ khóa luận và GVHD sau khi Bộ môn chốt. |
| Đề cương, tiến độ, tài liệu | `proposal`, `proposal_version`, `progress_milestone`, `progress_report`, `progress_review`, `document`, `document_version`, `stored_file` | Lưu phiên bản; quyền xem và thao tác được kiểm ở API. |
| Nhật ký | `audit_event` | Lưu vết quyết định và thao tác nghiệp vụ quan trọng. |

Hội đồng, đánh giá/bảng điểm và chức năng AI chưa nằm trong revision hiện tại; các tài liệu tương ứng là nội dung thiết kế hoặc kế hoạch giai đoạn sau. Có bảng trong CSDL không đồng nghĩa mọi nghiệp vụ liên quan đã hoàn thiện.

- [ERD hiện hành](erd-kltn-management.md)
- [Từ điển dữ liệu hiện hành](database-dictionary.md)
- [SQL schema-only](../../database/official/kltn-management-schema.sql) — chỉ để xem hoặc dựng database trống; không chạy trên database đang dùng.
- [Migration chính thức](../../backend/migrations_official/) — nguồn cập nhật database hiện hành.
