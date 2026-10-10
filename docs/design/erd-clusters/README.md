# ERD theo cụm nghiệp vụ

Sáu ERD dưới đây trình bày các cụm bảng và quan hệ khóa ngoại của hệ thống KLTN. Một bảng có thể xuất hiện ở nhiều cụm để giải thích nghiệp vụ, nhưng vẫn là một bảng vật lý duy nhất.

## Sáu ảnh

| Cụm | Ảnh | Bảng chính | Bảng ngữ cảnh | FK nội cụm |
| --- | --- | --- | --- | ---: |
| 01 — Người dùng và phân quyền | [PNG](01-nguoi-dung-va-phan-quyen.png) · [SVG](01-nguoi-dung-va-phan-quyen.svg) | `faculty`, `department`, `user_account`, `organizational_position`, `student_profile`, `lecturer_profile`, `position_assignment`, `resource_assignment` | — | 10 |
| 02 — Đề tài, đăng ký và khóa luận | [PNG](02-de-tai-dang-ky-va-khoa-luan.png) · [SVG](02-de-tai-dang-ky-va-khoa-luan.svg) | `academic_year`, `thesis_round`, `round_policy`, `eligibility_snapshot`, `lecturer_expertise`, `expertise_evidence`, `topic`, `topic_title_version`, `eligibility_exception`, `topic_requirement`, `topic_registration`, `registration_member`, `advisor_assignment`, `thesis`, `thesis_member`, `member_work_assignment` | `lecturer_profile`, `stored_file` | 23 |
| 03 — Đề cương, tiến độ và tài liệu | [PNG](03-de-cuong-tien-do-va-tai-lieu.png) · [SVG](03-de-cuong-tien-do-va-tai-lieu.svg) | `stored_file`, `progress_milestone`, `proposal`, `proposal_version`, `reviewer_assignment`, `proposal_review`, `signature_confirmation`, `progress_report`, `progress_review`, `topic_change_request`, `external_procedure_outcome`, `document`, `document_version` | `thesis`, `advisor_assignment` | 20 |
| 04 — Tương đồng, kho tài liệu và AI | [PNG](04-tuong-dong-kho-tai-lieu-va-ai.png) · [SVG](04-tuong-dong-kho-tai-lieu-va-ai.svg) | `repository_item`, `search_index_metadata`, `similarity_policy`, `similarity_check`, `similarity_match`, `retrieval_audit`, `audit_event` | `stored_file`, `document`, `document_version`, `thesis_round` | 12 |
| 05 — Hội đồng, bảo vệ và chấm điểm | [PNG](05-hoi-dong-bao-ve-va-cham-diem.png) · [SVG](05-hoi-dong-bao-ve-va-cham-diem.svg) | `council`, `council_member`, `defense_session`, `session_thesis`, `council_attendance`, `defense_eligibility_check`, `advisor_review`, `reviewer_review`, `rubric_template`, `rubric_criterion`, `rubric_assignment`, `bonus_evidence`, `evaluation`, `evaluation_item`, `final_result` | `thesis`, `thesis_member` | 25 |
| 06 — Biên bản, chữ ký và kết quả | [PNG](06-bien-ban-chu-ky-va-ket-qua.png) · [SVG](06-bien-ban-chu-ky-va-ket-qua.svg) | `council_minute`, `minute_version`, `minute_signature`, `final_result` | `council`, `council_member`, `defense_session`, `thesis_member`, `stored_file`, `audit_event` | 10 |

Mỗi đường nối biểu diễn đúng một FK thật giữa hai bảng đang thấy. Ký hiệu **1/N** chỉ phía bảng cha và số bản ghi con; **≤1** khi cột FK thuộc khóa duy nhất. Trong ô bảng, **UK** nghĩa là cột thuộc ít nhất một UNIQUE constraint/index, kể cả khóa ghép, không khẳng định cột đó đứng một mình là duy nhất. FK ra bảng không nằm trong cụm vẫn được ghi `FK` tại cột nhưng không kéo toàn bộ dependency tree vào ảnh. Tự tham chiếu của `rubric_criterion` và `minute_version` được vẽ thành vòng lặp. `minute_signature → council_member` là FK thật; Chair/Secretary chỉ là giá trị role nghiệp vụ, không phải FK riêng.

ERD cụm là **view để trình bày**. [ERD tổng thể](../erd.md), [từ điển dữ liệu](../data-dictionary.md) và schema PostgreSQL/Alembic là nguồn tra đầy đủ mọi bảng, cột và ràng buộc. Ảnh chỉ hiện PK, FK, UNIQUE, code/version/state và một số cột nghiệp vụ; các cột audit thông dụng được ẩn để dễ đọc.
