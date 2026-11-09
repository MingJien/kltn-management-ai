# Đối chiếu yêu cầu với CSDL hiện hành

Phạm vi vật lý là PostgreSQL `kltn_management`, revision `20261021_0004`: 34 bảng nghiệp vụ và `alembic_version`. Đây là đối chiếu cấu trúc; có bảng không đồng nghĩa mọi chức năng liên quan đã hoàn tất.

| Nghiệp vụ | Bảng chính | Quy tắc cần kiểm ở API/service |
| --- | --- | --- |
| Tài khoản và quyền | `user_account`, `student_profile`, `lecturer_profile`, `position_assignment`, `resource_assignment` | Kích hoạt theo hồ sơ được xác nhận; quyền theo nhiệm vụ/phạm vi, kiểm ở backend. |
| Thông báo đăng ký | `user_notification`, `topic_registration`, `topic` | Mỗi GV chỉ thấy thông báo của mình; mở hồ sơ thì đánh dấu đã xem. Nếu TBM đổi GV tiếp nhận, thông báo đề xuất cũ được thu hồi. |
| Điều kiện theo đợt | `academic_year`, `thesis_round`, `eligibility_snapshot` | Chỉ cho đăng ký khi hồ sơ được người có thẩm quyền xác nhận trong đợt mở. |
| Tạo và duyệt đề tài | `topic`, `topic_title_version`, `topic_requirement` | Kiểm quyền người tạo, phạm vi Bộ môn, trạng thái và lịch sử đổi tên. |
| Đăng ký cá nhân/nhóm | `topic_registration`, `registration_member` | Tự xác nhận từng thành viên; khóa theo hạn, sức chứa, đăng ký đang hiệu lực và trạng thái đề tài. |
| Chốt đăng ký/GVHD | `thesis`, `thesis_member`, `advisor_assignment` | Chỉ Bộ môn chốt; tạo hồ sơ khóa luận và phân công trong transaction. |
| Đề cương | `proposal`, `proposal_version`, `reviewer_assignment`, `proposal_review`, `signature_confirmation`, `stored_file` | Gắn nhận xét/xác nhận với đúng phiên bản và kiểm quyền người xem/tải. |
| Tiến độ, tài liệu | `progress_milestone`, `progress_report`, `progress_review`, `document`, `document_version` | Lưu phiên bản; GVHD xác nhận, người góp ý chéo chỉ nhận xét theo phân công. |
| Nhật ký | `audit_event` | Ghi người thao tác, thời điểm, đối tượng và căn cứ cho quyết định quan trọng. |

PK/FK/CHECK/UNIQUE được đối chiếu bằng [validator hiện hành](../../tools/validate_official_database.py). Các kiểm tra quy trình nằm trong [test API](../../tests/) và không được suy ra chỉ từ ERD. Xem [ERD](erd-kltn-management.md) và [từ điển dữ liệu](database-dictionary.md) để tra đủ cột/ràng buộc.
