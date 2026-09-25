# Thiết kế xuất biểu mẫu chính thức

Nguồn: SRC-MAU-03, SRC-MAU-06, SRC-MAU-09, SRC-PROJECT-DEC-20260925. Mục tiêu là **đúng nội dung và đúng bố cục biểu mẫu đang áp dụng**. Tệp xuất chỉ PASS khi so sánh với mẫu nguồn đã được làm trắng và kiểm tra bản render; không dùng vài dấu cách để giả bố cục.

## Luồng chung

`Business state đã được khóa/ủy quyền` → `DTO có kiểu và nguồn từng trường` → `adapter của template + version` → `DOCX (Mẫu 3/9) hoặc XLSX (Mẫu 6)` → `PDF nếu cần` → `StoredFile(content hash, template source/version, mime)` → `AuditEvent`. Template nằm trong kho tài liệu đã phê duyệt ngoài Git; không đưa bản đã điền dữ liệu thật vào repository. Lệnh xuất phải idempotent theo aggregate/version/template version, và phải từ chối nếu quyền, trạng thái, dữ liệu bắt buộc không đạt.

## Mẫu 3 — Đề cương

| DTO | Nguồn nghiệp vụ | Kiểm tra |
| --- | --- | --- |
| title, department, major, student list | Thesis/Topic, ThesisMember, StudentProfile | Đúng version tên đề tài đã được TBM chốt |
| advisor identity | AdvisorAssignment + LecturerProfile | Assignment hiệu lực trên Thesis |
| proposal content and decision history | ProposalVersion, ProposalReview, SignatureConfirmation | Không ghi đè version; không in bản chưa đủ xác nhận |
| template_id, template_version | SRC-MAU-03 + registry nội bộ | Giữ được hash và version nguồn |

Adapter điền đúng vị trí/tables theo Mẫu 3 chính thức; PDF chỉ sau khi DOCX render và đối chiếu.

## Mẫu 6 — Phiếu chấm

| DTO | Nguồn nghiệp vụ | Kiểm tra |
| --- | --- | --- |
| evaluator role/person, student, thesis title | CouncilMember/DefenseSession/ThesisMember/Thesis | Member phải có mặt và thuộc đúng phiên |
| item_scores, comment | EvaluationItem, RubricCriterion | 3 nhóm 2/4/4; tiêu chí con theo version |
| bonus, total, recommendation | Evaluation, BonusEvidence | Bonus tối đa 1, tổng kể cả bonus tối đa 10, không cộng lại khi tính trung bình |
| template_version, rubric_version | SRC-MAU-06, RubricTemplate | CONFLICT-011 cần Khoa xác nhận hiệu lực trước chấm thật |

Tệp XLSX local có sheet “Mẫu” với công thức nhóm và tổng; có điểm ví dụ trong ô nhập, vì vậy phải làm sạch cell ví dụ và so khớp công thức/merged cells/print area trước khi dùng làm template phát hành.

## Mẫu 9 — “Biên bản họp Hội đồng chấm khóa luận tốt nghiệp/đồ án tốt nghiệp”

| DTO | Nguồn nghiệp vụ | Kiểm tra |
| --- | --- | --- |
| title, student, code/class, advisor | Thesis/ThesisMember/StudentProfile/AdvisorAssignment | Một bản biên bản theo từng SV/KLTN trong phiên |
| council decision, five members and roles | Council, CouncilMember | Quyết định thật; không tự chọn Chair |
| date/time/place, attendance and quorum | DefenseSession, CouncilAttendance | Chair + Secretary có mặt, vắng không quá 2/5 |
| opinions, conclusion, recommendation | review/minute fields | Không tự tạo lời nhận xét |
| valid ballots, score, ranking | Evaluation, FinalResult | Chỉ điểm hợp lệ, theo rubric/version |
| secretary_signature, chair_signature | MinuteSignature → CouncilMember.role | Cần **cả hai** vai trò của đúng Council; không TBM |
| template source/hash/version, minute version | SRC-MAU-09, MinuteVersion | Sau in trước chữ ký đầu: sai thì VOID bản cũ và xuất version mới có mã/thời gian; từ chữ ký đầu nội dung bất biến |

Trạng thái: `DRAFT → EXPORTED → PRINTED → SIGNED`; chỉ chuyển SIGNED khi tập role chữ ký của version hiện tại chứa SECRETARY và CHAIR, mỗi chữ ký tham chiếu thành viên được quyết định chỉ định. Số lượng row chữ ký trong DB **chưa tự bảo đảm** điều kiện này; service khi triển khai phải kiểm tra role, version và khóa ngay từ chữ ký đầu trong cùng transaction. Thư ký đối chiếu bản giấy trước khi cho phép sửa bản đã in; nếu đã có chữ ký trên giấy mà hệ thống chưa ghi thì vẫn phải từ chối.

**Trạng thái runtime:** BLOCKED_SOURCE_TEMPLATE. Binary Mẫu 9 có trên máy nhưng là 6 biên bản đã điền dữ liệu thật, không phải template trắng có field được đánh dấu. Việc sửa trực tiếp có nguy cơ giữ lại PII và tạo bản xuất sai. Cần bản mẫu trắng hiện hành hoặc bản đã được Khoa cho phép làm sạch, kèm mapping field và kiểm chứng render. Chưa tạo nút “Xuất Mẫu 9” trong React và chưa ghi PASS xuất đúng mẫu.

## Kiểm thử khi nguồn sẵn sàng

1. Dùng DTO hoàn toàn giả lập và bản template trắng được duyệt.
2. Test quyền Thư ký tạo/export; người ngoài từ chối; Chair/Secretary ký đúng role; SIGNED chỉ khi đủ hai; sửa sau in trước chữ ký đầu, khóa từ chữ ký đầu.
3. Render DOCX/XLSX ra PDF/ảnh, đối chiếu thứ tự trường, bố cục, chữ ký, số trang, vùng in, công thức, hash template.
4. Quét output không còn dữ liệu ví dụ, không đưa bản có PII lên Git.
