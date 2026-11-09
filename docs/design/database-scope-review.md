# Phạm vi CSDL theo góp ý GV ngày 03/10/2026 (cập nhật 04/10)

Nguồn: phiếu góp ý tiến độ 30/09–07/10/2026 lưu **trên máy** tại `docs/30092026_Chien-KLTN.pdf`, đã đọc lại cả bản Drive ngày 03/10. GV đề nghị **khoảng 25 bảng lõi** theo các nhóm tài khoản, đợt, điều kiện, đề tài, đăng ký, khóa luận, GVHD, đề cương, tiến độ và tài liệu; GV không liệt kê 25 tên bảng bắt buộc. Dự án chọn 25 bảng nền, bổ sung bốn bảng giữ FK/nhận xét, hai bảng lịch sử tên/audit và một bảng yêu cầu GV: [CSDL lõi riêng 32 bảng](../../database/core/kltn-core-schema.sql). File chỉ dựng database **mới, trống**; `kltn_core` chưa được tạo. `kltn_ai` giữ mô hình 62 bảng; `kltn_dev` phục vụ demo.

Không dùng `council` để biểu diễn buổi góp ý đề cương hoặc tiến độ; bảng đó chỉ được giữ nguyên vì `resource_assignment` có FK thật tới nó. Giữ bảng cùng FK bảo đảm file chạy độc lập mà không sửa/bịa quan hệ. [Danh sách 32 bảng và cách tạo/xem](../../database/core/README.md).

## Phạm vi lõi và thứ tự triển khai

**25 bảng dưới đây do dự án chọn để đáp ứng các nhóm chức năng GV nêu**; cả 25 đều nằm trong file SQL lõi. Bốn bảng bổ sung giữ FK/ghi nhận nhận xét; `topic_title_version` và `audit_event` là hai bảng nữa để luồng đề tài đã triển khai không mất lịch sử. Tổng là 32, gồm thêm `topic_requirement` để lưu yêu cầu bổ sung của GV. Thiết kế CSDL bao quát các nhóm này; runtime hiện ưu tiên GV tạo → TBM duyệt → SV đăng ký → GV chấp nhận. Phân công GVHD, đề cương, tiến độ, tài liệu và tích hợp toàn bộ phân hệ triển khai ở bước sau; việc giữ bảng không đưa các chức năng đó vào tuần này.

| Nhóm | Bảng ưu tiên | Mục đích của giai đoạn lõi |
| --- | --- | --- |
| Người dùng và quyền (8) | `faculty`, `department`, `user_account`, `student_profile`, `lecturer_profile`, `organizational_position`, `position_assignment`, `resource_assignment` | Email/mã băm tài khoản ứng dụng, hồ sơ SV/GV, TBM đúng bộ môn và quyền xác nhận điều kiện gán theo đợt. |
| Đợt và điều kiện (4) | `academic_year`, `thesis_round`, `round_policy`, `eligibility_snapshot` | Mở đợt; giữ kết quả điều kiện theo SV/đợt, người xác nhận và tín chỉ/GPA khi có nguồn. |
| Đề tài và đăng ký (6) | `topic`, `topic_registration`, `registration_member`, `thesis`, `thesis_member`, `advisor_assignment` | GV đề xuất → TBM duyệt → nhóm SV đồng ý và đăng ký → GV chấp nhận → TBM chốt GVHD. |
| Đề cương và tiến độ (4) | `proposal`, `proposal_version`, `progress_milestone`, `progress_report` | Nộp đề cương theo phiên bản; theo dõi mốc và báo cáo tiến độ. |
| Tệp và tài liệu (3) | `stored_file`, `document`, `document_version` | Lưu metadata tệp và các bản nộp không ghi đè. |

Tổng **25 bảng nền + 4 bảng phụ thuộc/góp ý + 2 bảng lịch sử/audit + 1 bảng yêu cầu = 32 bảng lõi**. `topic_title_version` giữ từng tên cũ, người đổi và lý do; `audit_event` ghi dấu vết quyết định. Hai bảng này đã có trong mô hình đầy đủ và được luồng đề tài dùng, nên không cắt chỉ để gần mốc 25. `signature_confirmation`, hội đồng bảo vệ, chấm điểm, biên bản, similarity và chatbot vẫn nằm trong mô hình đầy đủ 62 bảng. Việc đã có bảng/ERD/API đặc tả không có nghĩa chức năng đó đã chạy.

## Lát cắt kế tiếp theo GV

Luồng ưu tiên đã có backend và React: **GV tạo/gửi đề tài → TBM đúng bộ môn duyệt → từng SV tự đăng ký → đại diện gửi → GV chấp nhận**. Một SV được gửi; bổ sung còn chỗ/trước hạn làm nhóm đã gửi/nhận trở về SUBMITTED để GV xét lại. SV đề xuất cá nhân trước, người khác chỉ tham gia sau APPROVED. Test PostgreSQL/browser đã chạy trên dữ liệu giả. Kết thúc ở LECTURER_ACCEPTED; không đồng nhất với FINALIZED/phân công GVHD chính thức. Endpoint chốt cũ được giữ, ngoài mốc này. [Luồng hiện hành](registration-workflow.md) ghi guard; giai đoạn tiếp là phân công GVHD, đề cương, tiến độ, tài liệu. Chưa kết nối Gemini.

Đợt góp ý đề cương và góp ý tiến độ lần 2 **không phải Hội đồng bảo vệ**. Số người góp ý chéo và thành phần phải lấy từ hướng dẫn Khoa/kế hoạch từng đợt; hệ thống cần cho cấu hình theo đợt và cấm người góp ý chéo tự xác nhận thay GVHD chính. Chưa hard-code số người khi chưa có nguồn chính thức.

## Cách xem schema dễ đọc

[`database/core/kltn-core-schema.sql`](../../database/core/kltn-core-schema.sql) là bản lõi để GV xem phạm vi đang tập trung: mỗi bảng một `CREATE TABLE`, gồm cả cột, PK/FK/UNIQUE/CHECK; file chỉ chạy một lần trên database **mới, trống**. Đã chạy file trên schema PostgreSQL tạm rồi `pg_dump --schema-only`: **32 bảng, 32 PK, 69 FK**, không có `ALTER TABLE`; schema tạm đã xóa. [`database/kltn-schema-consolidated.sql`](../../database/kltn-schema-consolidated.sql) là bản **schema-only 62 bảng** từ `kltn_ai` ở revision `20261004_0012`, dùng để tham khảo mở rộng. [`kltn-db-baseline.sql`](../../database/kltn-db-baseline.sql) dựng bản **đầy đủ** mới. Migration Alembic hiện dành cho mô hình 62 bảng, chưa áp dụng cho database lõi 32 bảng. Không bảng nghiệp vụ nào bị xóa khỏi bản tham chiếu.

Mã đề tài có dạng `DT-2026-2027-0001`, duy nhất và không đổi khi sửa tên. `topic_requirement` giữ GPA/kỹ năng/công nghệ mong muốn; backend không dùng yêu cầu này thay điều kiện chính thức. `topic.receiving_lecturer_id` là GV tiếp nhận (chưa phải phân công GVHD chính thức). `registration_member.evidence_file_id` liên kết minh chứng riêng từng SV qua `stored_file`; nội dung tệp không lưu trong SQL và không đưa lên Git.
