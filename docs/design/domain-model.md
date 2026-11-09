# Mô hình miền hiện hành

Mô hình vật lý đang chạy tại PostgreSQL `kltn_management`, revision `20261021_0004`, gồm 34 bảng nghiệp vụ. Cấu trúc đầy đủ được thể hiện trong [ERD](erd-kltn-management.md) và [từ điển dữ liệu](database-dictionary.md).

| Nhóm | Bảng | Trách nhiệm |
| --- | --- | --- |
| Tài khoản và tổ chức | `user_account`, `student_profile`, `lecturer_profile`, `faculty`, `department`, `organizational_position`, `position_assignment`, `resource_assignment` | Danh tính, hồ sơ và quyền được giao theo phạm vi. |
| Năm học, đợt và điều kiện | `academic_year`, `thesis_round`, `eligibility_snapshot` | Lịch đăng ký và kết quả đủ điều kiện đã được xác nhận. |
| Đề tài và đăng ký | `topic`, `topic_title_version`, `topic_requirement`, `topic_registration`, `registration_member` | Đề xuất/duyệt đề tài; sinh viên tự đăng ký hoặc tham gia nhóm. |
| Khóa luận và GVHD | `thesis`, `thesis_member`, `advisor_assignment`, `member_work_assignment` | Hồ sơ sau khi Bộ môn chốt đăng ký, thành viên, GVHD và phần việc. |
| Đề cương và xác nhận | `stored_file`, `proposal`, `proposal_version`, `reviewer_assignment`, `proposal_review`, `signature_confirmation` | Bản nộp theo phiên bản, góp ý và xác nhận đúng phiên bản. |
| Tiến độ và tài liệu | `progress_milestone`, `progress_report`, `progress_review`, `document`, `document_version` | Mốc, báo cáo tiến độ và tài liệu theo phiên bản. |
| Dấu vết | `audit_event` | Nhật ký hành động nghiệp vụ quan trọng. |

ERD chỉ thể hiện cấu trúc đang có trong database. Bảng hoặc chức năng chưa có trong revision hiện hành không được tính là đã triển khai.
