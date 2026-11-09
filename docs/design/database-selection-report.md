# CSDL chính thức hiện hành

Runtime sử dụng PostgreSQL `kltn_management`, Alembic head `20261102_0019`: **43 bảng nghiệp vụ**, cộng bảng kỹ thuật `alembic_version`.

Migration `20261102_0019` thêm `thesis_withdrawal_request` theo quyết định người dùng ngày 02/11/2026. Đây là hồ sơ theo từng SV, kế thừa ý nghĩa căn cứ/ngày hiệu lực/người ghi nhận/tệp của `external_procedure_outcome` nguồn 62, bổ sung đơn và xác nhận GVHD để có luồng UI trọn vẹn. Không kéo cả bảng xử lý thủ tục tương lai vào runtime. Thêm ngày bắt đầu/căn cứ trên `thesis_round`; không lấy ngày GV tiếp nhận làm ngày bắt đầu chính thức. Đơn gửi trong 02 tuần, có GVHD xác nhận; KLTN_COORDINATOR ghi nhận kết quả đã xử lý bên ngoài với bản đơn đã quét và căn cứ. Giữ hồ sơ cũ; nhóm còn lại tiếp tục đề tài nhưng nộp đề cương mới để duyệt. UNIQUE của `signature_confirmation` chuyển sang đề cương/phiên bản/loại xác nhận, giữ mọi xác nhận cũ và cho phép duyệt phiên bản mới. Mẫu phiếu hiện là bản đề nghị in từ hệ thống, chưa phải biểu mẫu chính thức của Trường.


Migration `20261028_0013` được người dùng chấp thuận: mở rộng bảng `user_notification` bằng event_code, resource_type, resource_id, message, url; registration_id cho phép NULL với sự kiện không thuộc đăng ký, có CHECK bảo đảm payload theo kind. Thông báo gắn người nhận cụ thể; quyền truy cập được kiểm lại trước tính số chưa đọc/phân trang/đánh dấu. Không thêm bảng, không gửi email. Bảng `document_deadline` nhận thêm REPORT cho cuốn báo cáo KLTN trước bảo vệ; không dùng REPORT thay báo cáo tiến độ theo mốc. Runtime vẫn 39 bảng nghiệp vụ.

Yêu cầu riêng tư mới: nội dung tiến độ/minh chứng/nhận xét chỉ nhóm SV và GVHD chính xem. Phân công PROGRESS_REVIEWER cũ được giữ dữ liệu lịch sử nhưng không cấp quyền đọc/ghi tiến độ; TBM còn quyền quản lý mốc nếu có KLTN_COORDINATOR.

Migration `20261028_0012` bổ sung đúng hai bảng được người dùng đồng ý: `official_form` (danh mục theo đợt, loại mẫu trắng/tài liệu công bố và đối tượng xem) và `official_form_version` (tệp, phiên bản, nguồn, lý do, người và thời gian phát hành). Tái dùng `stored_file`, ClamAV, `resource_assignment` với nhiệm vụ FORM_MANAGER và `audit_event`; không thêm bảng quyền, không thay bảng tài liệu bài nộp của SV. Hai bảng mới phục vụ yêu cầu quản lý mẫu cập nhật trên UI, không có trong nguồn 62. UNIQUE một bản đang áp dụng, tệp bất biến và lịch sử thu hồi giữ khả năng đối chiếu. Tệp danh sách đã điền chỉ công bố cho SV/GV trong đợt, khác mẫu trắng tải chung.

Migration `20261026_0008` bổ sung `audit_event.source_reference` và chỉ mục thời gian để tra cứu nhật ký theo vai trò; không thêm bảng nghiệp vụ.

Migration `20261028_0011` được người dùng đồng ý ngày 28/10/2026: thêm đúng hai cột `annotation_kind` và `attachment_file_id` trong `progress_review_annotation`. Không thêm bảng, vẫn 37 bảng nghiệp vụ. PIN giữ ghim; SUMMARY tự lưu nhận xét chung lên PostgreSQL (partial UNIQUE theo GV/phiên bản); ATTACHMENT lưu liên kết tới bản PDF/DOCX GV phản hồi trong stored_file. Các CHECK kiểm đúng loại và FK. Tệp SV gốc không đổi. Tệp GV có quét ClamAV, checksum và quyền theo phiên bản; chỉ tác giả thấy nháp. Gửi kết quả công bố ghim/nhận xét chung/tệp sạch trong cùng transaction. Bản đã gửi không bị ghi đè.

Migration `20261027_0010` mở rộng bảng ghim hiện có cho tài liệu và đề cương bằng hai FK tùy chọn; báo cáo tiến độ trở thành FK tùy chọn. CHECK `one_target` bắt buộc mỗi ghim thuộc đúng một phiên bản/tệp. Không thêm bảng, không di chuyển ghim cũ; vẫn 37 bảng nghiệp vụ. Quyền xem/nhận xét và công bố nháp trong transaction được kiểm riêng theo từng loại tài nguyên. DOCX/TXT xem trực tiếp bằng bộ dựng cục bộ trong trình duyệt, ghim theo đoạn/dòng; chỉ PDF dùng tọa độ trang.

Migration `20261027_0009` thêm đúng một bảng `progress_review_annotation`, được người dùng đồng ý ngày 27/10/2026. Mỗi ghim tham chiếu báo cáo tiến độ, GV nhận xét và tệp cụ thể; lưu trang, tọa độ chuẩn hóa, mục/đoạn trích, góp ý, trạng thái nháp/đã gửi và phiên bản chống ghi đè. Nháp chỉ chính tác giả thấy, được công bố trong cùng transaction với kết quả nhận xét. Bảng này phát sinh từ yêu cầu nhận xét theo vị trí hiện tại, không có trong 62 bảng nguồn; không thêm bảng nghiệp vụ tương lai. Vị trí xem và nhận xét tổng quát chưa gửi được lưu riêng theo tài khoản, phiên bản và trình duyệt; bản ghim đã đồng bộ được lưu PostgreSQL.

Mô hình được mở rộng bằng migration mới trên cùng CSDL, không dựng lại hoặc sao chép dữ liệu thật từ CSDL cũ. Hai SQL tham khảo 32 và 62 bảng không thuộc runtime hiện hành.

## Bổ sung Mẫu 1a/1b đã được người dùng chấp thuận ngày 26/10/2026

Thêm đúng một bảng `registration_form_version`, liên kết `topic_registration`, `stored_file` và `student_profile`. Đơn được nộp trước khi có khóa luận nên không thể dùng `document_version` vốn bắt buộc thuộc hồ sơ khóa luận.

Mỗi dòng là một bản nộp bất biến: loại mẫu, số phiên bản, người và thời gian nộp, tệp, hash nội dung và dấu đối chiếu thông tin đăng ký. Khi nhóm, tên đề tài hoặc GV đề xuất thay đổi, không cho xuất bản cũ như bản hiện hành. Bản gốc vẫn giữ để đối chiếu. Bản xuất có footer ghi rõ là bản nộp, chưa xác nhận Khoa duyệt; không tự tạo bước duyệt nghiệp vụ mới.

Bảng này là phần bổ sung phục vụ nghiệp vụ hiện tại, không được ghi nhận sai là đã có trong SQL 62 bảng nguồn. Migration `20261026_0007` chỉ thêm bảng này; giữ nguyên các revision đã áp dụng.

[SQL gộp hiện hành](../../database/official/kltn-management-schema.sql) có một lệnh tạo đầy đủ cho mỗi bảng, dùng xem cấu trúc hoặc database trống. Không chạy snapshot này lên CSDL đang dùng. [Từ điển dữ liệu](database-dictionary.md) và [ERD](erd-kltn-management.md) được đồng bộ theo metadata hiện hành.

Migration 0015 giữ nguyên 0013/0014 đã áp dụng bởi cập nhật khác; chỉ bổ sung loại WORKFLOW_NOTICE trong bảng thông báo hiện có, không thêm bảng. Runtime tiến độ riêng chỉ nhóm và GVHD chính; PROGRESS_REVIEWER cũ không cấp quyền đọc/ghi tiến độ.
