# CSDL lõi theo góp ý GV ngày 03/10/2026

[kltn-core-schema.sql](kltn-core-schema.sql) là file SQL riêng để trình bày và dựng **database mới `kltn_core`**. Bản này có **32 bảng nghiệp vụ**: 25 bảng nền theo các nhóm GV nêu, bốn bảng giữ FK/góp ý và hai bảng giữ lịch sử tên đề tài/nhật ký quyết định của luồng đã triển khai. Mốc GV nêu là “khoảng 25”, không phải danh sách 25 bảng bắt buộc. Nguồn là SQLAlchemy metadata đã đối chiếu với PostgreSQL `kltn_ai` tại Alembic `20261010_0013` (cột/kiểu/null, PK/FK/UNIQUE/CHECK/index). Mỗi bảng có đúng một `CREATE TABLE` với toàn bộ cột và ràng buộc của nó, **không có `ALTER TABLE` thêm cột ở cuối file**. File không chứa dữ liệu nghiệp vụ hoặc mật khẩu.

## Danh sách bảng và lý do giữ

| Cụm | Bảng | Vai trò |
| --- | --- | --- |
| Người dùng, đơn vị, chức vụ (7) | `faculty`, `department`, `user_account`, `student_profile`, `lecturer_profile`, `organizational_position`, `position_assignment` | SV/GV thuộc đúng bộ môn; TBM chỉ có quyền khi được phân công chức vụ còn hiệu lực. `user_account` có email, mã băm mật khẩu, trạng thái và UUID. |
| Dấu vết quyết định (1) | `audit_event` | Ghi người thực hiện, hành động, đối tượng và thời gian để giải trình việc duyệt/từ chối. |
| Năm học, đợt, điều kiện (4) | `academic_year`, `thesis_round`, `round_policy`, `eligibility_snapshot` | Chính sách/ngày theo đợt; snapshot đủ điều kiện có nguồn và người xác nhận. Cột tín chỉ/GPA cũ để trống khi nhập danh sách mới; không lưu chi tiết án tích/kỷ luật. |
| Đề tài, đăng ký, khóa luận, GVHD (8) | `topic`, `topic_title_version`, `topic_requirement`, `topic_registration`, `registration_member`, `thesis`, `thesis_member`, `advisor_assignment` | GV tạo → TBM duyệt → từng SV tự đồng ý → nhóm gửi → GV chấp nhận; tên cũ của đề tài được giữ theo phiên bản. Chốt nhóm/GVHD là bước triển khai sau. |
| Quyền theo đợt và FK nền (2) | `resource_assignment`, `council` | `resource_assignment` gán `ELIGIBILITY_VERIFIER` theo đợt. `council` chỉ để giữ FK thật của bảng assignment đa phạm vi; **không coi buổi góp ý đề cương/tiến độ là hội đồng bảo vệ**. |
| Tệp, đề cương và góp ý (5) | `stored_file`, `proposal`, `proposal_version`, `reviewer_assignment`, `proposal_review` | Lưu bản nộp theo phiên bản và GV được giao góp ý. GV góp ý chéo phải khác GVHD; backend kiểm ở use case vì cần đối chiếu nhiều bảng. |
| Tiến độ và nhận xét (3) | `progress_milestone`, `progress_report`, `progress_review` | Mốc theo đợt, báo cáo theo phiên bản, GVHD xác nhận và GV khác chỉ góp ý `COMMENT_ONLY`. |
| Tài liệu (2) | `document`, `document_version` | Quản lý tài liệu theo loại, quyền xem và phiên bản tệp; không ghi đè bản đã nộp. |

`round_policy` giữ cấu hình theo đợt, gồm số/thành phần người góp ý khi Khoa cung cấp nguồn. PostgreSQL giữ FK, UNIQUE, CHECK cơ bản. Các quy tắc nhiều bảng như “người xác nhận có assignment hiệu lực đúng đợt”, “GV góp ý chéo khác GVHD” và “từng thành viên tự xác nhận trước khi gửi” phải được backend kiểm trong transaction; chỉ có bảng không có nghĩa luồng đã chạy.

**Lưu ý 04/10:** `topic_title_version` và `audit_event` đã được thêm vào **file SQL lõi** vì luồng đề tài trên `kltn_dev` dùng chúng. `kltn_ai`/`kltn_dev` vốn đã có hai bảng này; migration 0011 thêm mã đề tài, GV tiếp nhận và liên kết minh chứng của thành viên. File lõi 32 bảng vẫn là bản trình bày/dựng database mới, chưa có migration lõi riêng hoặc xác nhận runtime có thể chuyển thẳng sang `kltn_core`.

Các bảng Mẫu 6, hội đồng bảo vệ, biên bản, tương đồng và chatbot vẫn nằm trong [schema đầy đủ 62 bảng](../kltn-schema-consolidated.sql) để mở rộng theo giai đoạn. `signature_confirmation` và những bảng biểu mẫu chuyên biệt cũng còn ở bản đầy đủ; không xóa lịch sử/mô hình đó chỉ để đạt một con số.

## Trạng thái và cách dựng database riêng

Đã chạy file trong schema PostgreSQL tạm trên `kltn_dev` và xuất `pg_dump --schema-only` để kiểm: **32 `CREATE TABLE`, 32 PK, 69 FK**, không có `ALTER TABLE`; sau đó xóa đúng schema tạm. **Database `kltn_core` chưa được tạo vật lý** vì tài khoản `kltn_app` không có quyền `CREATE DATABASE`.

1. Trong pgAdmin, kết nối bằng `PostgreSQL 17 - admin`. Nhấp phải **Databases → Create → Database...**, nhập **Database = `kltn_core`**, **Owner = `kltn_app`**, rồi **Save**.
2. Ở kết nối `PostgreSQL 17 - kltn_app`, nhấp phải **Databases → Refresh**. Nhấp phải `kltn_core` → **Query Tool**. Kiểm thanh kết nối phía trên đang ghi `kltn_core`.
3. Nhấp **Open File** (hình thư mục), chọn `D:\KLTN\database\core\kltn-core-schema.sql`, rồi F5 **một lần trên database mới, trống**. Tab Messages phải báo `COMMIT`, không có `ERROR`.
4. Mở `kltn_core → Schemas → public → Tables`, nhấp phải **Tables → Refresh**. Sẽ thấy 32 bảng. Có thể chạy `SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';` để kiểm số `32`.

File chặn chạy nếu `public` đã có bảng; tuyệt đối không chạy trên `kltn_ai`/`kltn_dev`. Alembic migrations hiện dành cho **mô hình 62 bảng**, chưa áp dụng cho `kltn_core`. Prototype hiện vẫn dùng `kltn_dev` với dữ liệu giả; muốn chuyển runtime sang database lõi thì phải hoàn thành migration/core configuration và kiểm lại API. File tái sinh bằng `D:\KLTN\.venv\Scripts\python.exe -m tools.export_core_database_sql` sau khi cập nhật mô hình và database nguồn nhất quán.

Mã đề tài có dạng `DT-2026-2027-0001`, duy nhất và không đổi khi sửa tên. `topic_requirement` giữ GPA/kỹ năng/công nghệ mong muốn; backend không dùng yêu cầu này thay điều kiện chính thức. `topic.receiving_lecturer_id` là GV tiếp nhận (chưa phải phân công GVHD chính thức). `registration_member.evidence_file_id` liên kết minh chứng riêng từng SV qua `stored_file`; nội dung tệp không lưu trong SQL và không đưa lên Git.
