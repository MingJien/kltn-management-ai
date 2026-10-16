# ERD theo cụm nghiệp vụ

Nguồn tạo: **PostgreSQL public (live, read-only)**. Database: **`kltn_management`**, schema **`public`**; PostgreSQL **17.11**; Alembic **`20261015_0001_official`**. Ngày sinh: **2026-10-16 10:54 SE Asia Standard Time**.

Sáu ảnh được liên kết bên dưới là ERD hiện hành, sinh tự động từ bảng/cột/PK/FK/UNIQUE đã introspect và đối chiếu với SQLAlchemy metadata. Kết nối PostgreSQL đặt `default_transaction_read_only=on`; script không ghi dữ liệu. Các tệp ảnh không được liên kết trong bảng dưới không thuộc bộ ERD hiện hành.

## Chạy lại bằng một lệnh

Tại thư mục gốc `D:\KLTN` (có `.env` local cho kết nối), chạy:

```powershell
python tools/generate_erd_clusters.py
```

Cài môi trường lần đầu: `py -m venv .venv`, rồi `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`. Sau đó mỗi lần tái sinh chỉ cần lệnh trên.

Nếu `python` hệ thống thiếu thư viện, script tự chuyển sang `.venv\Scripts\python.exe`. Khi PostgreSQL không kết nối được, lệnh mặc định báo lỗi; chỉ dùng `--metadata-fallback` nếu muốn sinh ảnh từ SQLAlchemy metadata và ghi rõ nguồn thay thế.

## Sáu ảnh

| Cụm | Ảnh | Bảng chính | Bảng ngữ cảnh | FK nội cụm |
| --- | --- | --- | --- | ---: |
| 01 — Người dùng và phân quyền | [PNG](01-nguoi-dung-va-phan-quyen.png) · [SVG](01-nguoi-dung-va-phan-quyen.svg) | `faculty`, `department`, `user_account`, `organizational_position`, `student_profile`, `lecturer_profile`, `position_assignment`, `resource_assignment`, `audit_event` | — | 11 |
| 02 — Năm học, đợt và điều kiện | [PNG](02-nam-hoc-dot-va-dieu-kien.png) · [SVG](02-nam-hoc-dot-va-dieu-kien.svg) | `academic_year`, `thesis_round`, `eligibility_snapshot` | — | 2 |
| 03 — Đề tài và đăng ký | [PNG](03-de-tai-va-dang-ky.png) · [SVG](03-de-tai-va-dang-ky.svg) | `topic`, `topic_title_version`, `topic_requirement`, `topic_registration`, `registration_member` | — | 4 |
| 04 — Khóa luận và GVHD | [PNG](04-khoa-luan-va-gvhd.png) · [SVG](04-khoa-luan-va-gvhd.svg) | `thesis`, `thesis_member`, `advisor_assignment`, `member_work_assignment` | — | 3 |
| 05 — Đề cương và xác nhận phiên bản | [PNG](05-de-cuong-va-ky-xac-nhan.png) · [SVG](05-de-cuong-va-ky-xac-nhan.svg) | `stored_file`, `proposal`, `proposal_version`, `reviewer_assignment`, `proposal_review`, `signature_confirmation` | — | 7 |
| 06 — Tiến độ và tài liệu | [PNG](06-tien-do-va-tai-lieu.png) · [SVG](06-tien-do-va-tai-lieu.svg) | `progress_milestone`, `progress_report`, `progress_review`, `document`, `document_version` | `stored_file` | 5 |

Mỗi đường nối biểu diễn một FK thật giữa hai bảng trong cụm. `1/N` chỉ quan hệ một-nhiều; `≤1` đánh dấu phía con có khóa duy nhất. `UK` nghĩa là cột thuộc một ràng buộc hoặc chỉ mục UNIQUE, có thể là khóa ghép. FK ra ngoài cụm vẫn được ghi ở cột nhưng không kéo toàn bộ bảng liên quan vào ảnh.

ERD cụm là các góc nhìn để trình bày. [ERD đầy đủ](../erd-kltn-management.md), [từ điển dữ liệu](../database-dictionary.md) và [SQL schema-only](../../database/official/kltn-management-schema.sql) là nguồn tra cấu trúc hiện hành. Ảnh chỉ hiển thị PK, FK, UNIQUE, trạng thái và một số cột nghiệp vụ để dễ đọc.
