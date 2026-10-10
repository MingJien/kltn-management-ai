# Schema lõi 32 bảng

[kltn-core-schema.sql](kltn-core-schema.sql) là schema CSDL dùng để trình bày phạm vi hiện tại của dự án. File có 32 bảng nghiệp vụ, không có dữ liệu thật hay mật khẩu. Mỗi bảng có một lệnh `CREATE TABLE` chứa đủ cột và ràng buộc; không có `ALTER TABLE` bổ sung cột ở cuối file.

| Cụm | Bảng | Lý do giữ |
| --- | --- | --- |
| Người dùng, đơn vị, chức vụ (7) | `faculty`, `department`, `user_account`, `student_profile`, `lecturer_profile`, `organizational_position`, `position_assignment` | Xác định đúng sinh viên, giảng viên, bộ môn và thẩm quyền TBM. |
| Dấu vết quyết định (1) | `audit_event` | Ghi nhận người thực hiện, hành động, đối tượng và thời điểm để giải trình. |
| Năm học, đợt, điều kiện (4) | `academic_year`, `thesis_round`, `round_policy`, `eligibility_snapshot` | Quản lý đợt KLTN, chính sách và kết quả đủ điều kiện có căn cứ, người xác nhận. |
| Đề tài, đăng ký, khóa luận, GVHD (8) | `topic`, `topic_title_version`, `topic_requirement`, `topic_registration`, `registration_member`, `thesis`, `thesis_member`, `advisor_assignment` | Thể hiện luồng GV tạo đề tài → TBM duyệt → SV đăng ký → GV tiếp nhận; giữ lịch sử tên đề tài. |
| Quyền theo đợt và FK nền (2) | `resource_assignment`, `council` | Gán quyền theo đợt, gồm quyền xác nhận điều kiện; giữ FK nền cho phân công đa phạm vi. |
| Tệp, đề cương và góp ý (5) | `stored_file`, `proposal`, `proposal_version`, `reviewer_assignment`, `proposal_review` | Lưu tệp/bản nộp theo phiên bản và góp ý của giảng viên. |
| Tiến độ và nhận xét (3) | `progress_milestone`, `progress_report`, `progress_review` | Theo dõi mốc, báo cáo và nhận xét của GVHD/GV góp ý chéo. |
| Tài liệu (2) | `document`, `document_version` | Quản lý tài liệu theo loại, quyền xem và phiên bản. |

PostgreSQL đảm bảo PK, FK, UNIQUE và CHECK cục bộ. Các quy tắc liên bảng, quyền theo đợt và chuyển trạng thái được backend kiểm trong transaction.
