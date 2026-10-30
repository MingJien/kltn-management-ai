"""Generate the current ERD and data dictionary from official ORM metadata.

This tool reads no archived SQL and does not connect to PostgreSQL.
"""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql

from backend.db.metadata import target_metadata
from tools.official_schema import SELECTED_TABLES, TABLE_INFO
from tools.validate_official_database import HEAD

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/design"

COLUMN_VI = {
    "subject_type":"Loại đối tượng của thông báo", "subject_id":"Mã đối tượng của thông báo",
    "event_code": "Mã sự kiện nghiệp vụ tạo thông báo", "message": "Nội dung thông báo theo đối tượng", "url": "Đường dẫn nội bộ tới đúng hồ sơ",
    "official_form_id": "Mã danh mục biểu mẫu/tài liệu Khoa", "document_kind": "Phân loại biểu mẫu trắng hoặc tài liệu công bố", "audience": "Đối tượng được xem", "uploaded_by": "Tài khoản tải tệp lên", "published_by": "Tài khoản phát hành", "change_reason": "Lý do cập nhật phiên bản",
    "page_number": "Số trang của tệp PDF", "x": "Tọa độ ngang chuẩn hóa từ 0 đến 1",
    "y": "Tọa độ dọc chuẩn hóa từ 0 đến 1", "location_label": "Tiêu đề mục hoặc mô tả vị trí cần sửa",
    "quoted_text": "Đoạn trích được nhận xét", "published_at": "Thời điểm gửi ghim cho nhóm sinh viên",
    "source_reference": "Căn cứ hoặc mã/số văn bản nguồn của thao tác",
    "set_by": "Người ban hành hoặc cập nhật hạn nộp",
    "form_code": "Loại đơn Mẫu 1a/1b", "registration_fingerprint": "Mã đối chiếu thành viên, tên đề tài và GV đề xuất khi nộp",
    "academic_year_id": "Mã năm học", "action": "Hành động", "active": "Còn hiệu lực",
    "actor_id": "Mã người thao tác", "after_hash": "Mã băm sau thay đổi",
    "assigned_at": "Thời điểm phân công", "assigned_by": "Mã người phân công",
    "assignment_type": "Loại phân công", "base_role": "Vai trò nền",
    "before_hash": "Mã băm trước thay đổi", "byte_size": "Kích thước tệp (byte)",
    "captured_at": "Thời điểm ghi nhận nguồn", "change_reason": "Lý do đổi tên",
    "changed_by": "Mã người đổi tên", "class_name": "Tên lớp",
    "closes_at": "Thời điểm đóng", "code": "Mã nghiệp vụ", "comment": "Nội dung nhận xét",
    "confirmed_at": "Thời điểm xác nhận", "confirmed_by": "Mã người xác nhận",
    "consent_status": "Trạng thái đồng thuận", "content_sha256": "SHA-256 nội dung bản nộp",
    "correlation_id": "Mã liên kết nhật ký", "created_at": "Thời điểm tạo",
    "created_by": "Mã người tạo", "current_title": "Tên đề tài hiện hành",
    "current_version_no": "Số phiên bản hiện hành", "decided_at": "Thời điểm quyết định",
    "decided_by": "Mã người quyết định", "decision": "Quyết định",
    "decision_reason": "Lý do quyết định", "department_finalized_at": "Thời điểm Bộ môn chốt",
    "department_finalized_by": "Mã người chốt tại Bộ môn", "department_id": "Mã bộ môn",
    "description": "Mô tả", "display_name": "Họ tên hiển thị",
    "document_id": "Mã tài liệu", "document_type": "Loại tài liệu",
    "due_at": "Hạn hoàn thành", "due_at_at_submission": "Hạn áp dụng lúc nộp", "effective_from": "Bắt đầu hiệu lực",
    "effective_to": "Kết thúc hiệu lực", "email": "Địa chỉ email",
    "email_verified_at": "Thời điểm xác minh email", "ends_on": "Ngày kết thúc",
    "enforcement": "Tính chất yêu cầu", "evidence_file_id": "Mã tệp minh chứng",
    "evidence_ref": "Tham chiếu nguồn điều kiện", "expected_member_count": "Quy mô nhóm dự kiến",
    "expected_output": "Sản phẩm dự kiến", "expected_ratio": "Tỷ lệ tiến độ dự kiến",
    "external_subject": "Định danh ngoài hệ thống", "faculty_id": "Mã khoa",
    "gpa_4": "Điểm trung bình hệ 4", "id": "Khóa chính UUID",
    "is_coordinator": "Là nhóm trưởng điều phối", "joined_at": "Thời điểm tham gia",
    "lecturer_code": "Mã giảng viên", "lecturer_decided_at": "Thời điểm GV tiếp nhận quyết định",
    "lecturer_decided_by": "Mã GV tiếp nhận quyết định", "lecturer_id": "Mã giảng viên",
    "lecturer_reason": "Lý do quyết định của GV", "left_at": "Thời điểm rời nhóm",
    "major_code": "Mã ngành", "max_students": "Sức chứa tối đa",
    "media_type": "Kiểu nội dung tệp", "milestone_id": "Mã mốc tiến độ",
    "name": "Tên đầy đủ", "occurred_at": "Thời điểm sự kiện",
    "official_ref": "Tham chiếu văn bản chính thức", "opens_at": "Thời điểm mở",
    "original_name": "Tên tệp gốc", "passed_credit_ratio": "Tỷ lệ tín chỉ đạt",
    "password_hash": "Mã băm mật khẩu", "position_id": "Mã chức vụ",
    "preferred_gpa": "GPA mong muốn", "progress_report_id": "Mã báo cáo tiến độ", "document_version_id": "Mã phiên bản tài liệu", "annotation_kind": "Loại nội dung phản hồi", "attachment_file_id": "Mã tệp giảng viên đính kèm",
    "proposal_id": "Mã hồ sơ đề cương", "proposal_version_id": "Mã phiên bản đề cương",
    "proposal_version_no": "Số phiên bản đề cương", "proposer_type": "Loại người đề xuất",
    "proposer_user_id": "Mã tài khoản đề xuất", "reason": "Lý do hoặc căn cứ",
    "receiving_lecturer_id": "Mã GV tiếp nhận", "registration_id": "Mã đăng ký",
    "recipient_user_id": "Mã tài khoản nhận thông báo", "actor_user_id": "Mã tài khoản sinh viên thực hiện",
    "kind": "Loại thông báo", "read_at": "Thời điểm đã xem", "revoked_at": "Thời điểm thu hồi",
    "reported_ratio": "Tỷ lệ tiến độ báo cáo", "requirement_type": "Loại yêu cầu",
    "resource_id": "Mã đối tượng nghiệp vụ", "resource_type": "Loại đối tượng nghiệp vụ",
    "responded_at": "Thời điểm phản hồi", "responded_by_user_id": "Mã tài khoản tự phản hồi",
    "review_comment": "Nhận xét xét duyệt", "review_scope": "Phạm vi góp ý",
    "reviewed_at": "Thời điểm nhận xét", "reviewed_by": "Mã người nhận xét",
    "reviewer_assignment_id": "Mã phân công người góp ý", "reviewer_id": "Mã GV nhận xét",
    "reviewer_user_id": "Mã tài khoản người góp ý", "round_id": "Mã đợt KLTN",
    "round_type": "Loại đợt", "row_version": "Số phiên bản bản ghi",
    "scan_state": "Trạng thái quét an toàn", "scanned_at": "Thời điểm quét",
    "sha256": "SHA-256 của tệp", "signature_type": "Loại xác nhận chữ ký",
    "signer_user_id": "Mã người ghi xác nhận", "source_type": "Loại nguồn mốc",
    "starts_on": "Ngày bắt đầu", "state": "Trạng thái nghiệp vụ",
    "status": "Trạng thái tài khoản", "storage_key": "Khóa lưu trữ nội bộ",
    "stored_file_id": "Mã tệp lưu trữ", "student_code": "Mã số sinh viên",
    "student_id": "Mã sinh viên", "submitted_at": "Thời điểm nộp",
    "submitted_by": "Mã người nộp", "summary": "Tóm tắt tiến độ",
    "thesis_id": "Mã khóa luận", "thesis_member_id": "Mã thành viên khóa luận",
    "title": "Tiêu đề", "topic_id": "Mã đề tài", "updated_at": "Thời điểm cập nhật",
    "user_id": "Mã tài khoản", "value_text": "Nội dung yêu cầu",
    "version": "Số phiên bản", "version_no": "Số phiên bản",
    "visibility": "Mức độ hiển thị", "work_description": "Công việc được giao",
}

EXAMPLES = {
    "official_form": "Khoa tạo danh mục Mẫu 2 của đợt DEMO; Mẫu 4 trắng và danh sách SV đã chốt nằm ở hai danh mục khác nhau.",
    "official_form_version": "Cán bộ được giao FORM_MANAGER nộp bản Mẫu 2 v2, quét sạch rồi phát hành; v1 giữ trong lịch sử. Danh sách XLSX đã chốt chỉ SV/GV của đúng đợt đọc được.",
    "progress_review_annotation": "GVHD ghim góp ý ở trang 2 của minh chứng lần nộp 1, tự lưu nháp riêng; khi yêu cầu sửa, SV xem đúng ghim của v1 rồi nộp v2 mà ghim không bị dịch sang tệp mới.",
    "document_deadline": "Khoa đặt hạn Mẫu 2 cho đợt DEMO; sau khi đóng có thể gia hạn và mở nhận lại, giữ nhãn trễ cũ.",
    "registration_form_version": "Nhóm DEMO nộp Mẫu 1b v1 rồi sửa thành v2 trước tiếp nhận; bản in v2 ghi rõ bản nộp chưa xác nhận Khoa duyệt.",
    "academic_year": "Tạo năm học giả DEMO-2026-2027 để mở đợt KLTN chính.",
    "advisor_assignment": "Khi GV chấp nhận nhóm DEMO, một phân công GVHD chính được tạo trong cùng giao dịch với khóa luận và thành viên.",
    "audit_event": "Ghi actor, thời điểm và lý do khi GV chấp nhận đăng ký DEMO và tạo khóa luận.",
    "department": "Bộ môn CNTT-DEMO thuộc Khoa CNKT-DEMO.",
    "department_major": "BM-KHMT chấp nhận ngành 7480101 và 7480208; mã ngành khác bị chặn khi nhập Excel.",
    "document": "Nhóm DEMO tạo hồ sơ báo cáo KLTN chỉ thành viên và GVHD được xem.",
    "document_version": "Lần nộp báo cáo thứ hai là v2, giữ nguyên v1 và SHA-256.",
    "eligibility_snapshot": "Khoa xác nhận SV-DEMO đủ điều kiện đợt chính theo danh sách nguồn; quyết định đặc biệt tạo snapshot v2 có số quyết định Hiệu trưởng.",
    "faculty": "Khoa CNKT-DEMO quản lý Bộ môn CNTT-DEMO.",
    "lecturer_profile": "GV-DEMO có tài khoản riêng và thuộc Bộ môn CNTT-DEMO.",
    "member_work_assignment": "SV-DEMO nộp phần việc làm API v1, GVHD yêu cầu sửa và SV nộp v2.",
    "organizational_position": "Mã DEPARTMENT_HEAD đại diện chức vụ Trưởng bộ môn.",
    "position_assignment": "GV-DEMO được phân công Trưởng bộ môn CNTT-DEMO trong một khoảng hiệu lực.",
    "progress_milestone": "Đợt DEMO mở mốc báo cáo lần 2 với hạn theo kế hoạch Khoa đã duyệt.",
    "progress_report": "Nhóm DEMO nộp báo cáo mốc lần 2 v1; sửa thành v2 sau góp ý.",
    "progress_review": "GVHD ghi nhận xét và CONFIRM hoặc yêu cầu sửa đúng lần nộp; COMMENT_ONLY còn trong ràng buộc để bảo toàn lịch sử cũ, không cấp quyền góp ý chéo tiến độ mới.",
    "proposal": "Khóa luận DEMO có một hồ sơ đề cương đang chờ GVHD xác nhận.",
    "proposal_review": "GVHD nhận xét đề cương v1 cần sửa; GV khác chỉ góp ý.",
    "proposal_version": "SV-DEMO nộp đề cương v2 PDF; v1 vẫn tải được và có mã băm riêng.",
    "registration_member": "Hai SV-DEMO tự xác nhận vào cùng một đăng ký trước khi gửi.",
    "resource_assignment": "Khoa giao ELIGIBILITY_VERIFIER cho GV-DEMO đúng đợt; quyền tự hết khi thu hồi.",
    "reviewer_assignment": "TBM giao GV khác GVHD góp ý đúng hồ sơ đề cương DEMO.",
    "signature_confirmation": "TBM ghi bản đề cương v2 đã chốt; Trưởng khoa ghi tham chiếu bản giấy đã ký.",
    "stored_file": "Tệp đề cương DEMO lưu khóa nội bộ và SHA-256, không tạo URL công khai.",
    "student_profile": "SV-DEMO-01 có MSSV giả và tài khoản thuộc Bộ môn CNTT-DEMO.",
    "thesis": "Sau khi chốt đăng ký DEMO, một khóa luận được tạo trong cùng transaction.",
    "thesis_member": "SV-DEMO-01 và SV-DEMO-02 thành thành viên chính thức sau chốt.",
    "thesis_round": "Năm học DEMO có đợt MAIN; SUPPLEMENTARY thêm khi Khoa mở.",
    "topic": "GV-DEMO đề xuất đề tài TOP-DEMO, TBM duyệt rồi SV đăng ký.",
    "topic_registration": "Nhóm DEMO gửi đăng ký; GV chấp nhận tạo khóa luận và GVHD chính thức; trạng thái và lịch sử được giữ.",
    "topic_requirement": "GV nêu kỹ năng Python là mong muốn; không tự chặn SV đủ điều kiện.",
    "topic_title_version": "TBM đổi tên TOP-DEMO ở v2, mã đề tài giữ nguyên.",
    "user_account": "Tài khoản demo SV-DEMO đăng nhập bằng email đã xác minh và bị chặn khi LOCKED.",
    "user_notification": "SV nhóm DEMO nộp báo cáo tiến độ; chỉ GVHD đúng đề tài và thành viên nhóm nhận thông báo. GVHD phản hồi thì cả nhóm nhận. TBM nhận đề tài chờ duyệt, không nhận tiến độ riêng.",
}

SEPARATION = {
    "official_form": "Danh mục có mã, đợt, loại tài liệu và đối tượng xem ổn định; không lặp danh mục trong từng tệp hay nhầm tài liệu Khoa với bài SV nộp.",
    "official_form_version": "Một danh mục có nhiều tệp bất biến và vòng đời nháp/phát hành/thu hồi riêng. stored_file chỉ lưu bytes/checksum/scan; không thay thế lịch sử phát hành nghiệp vụ.",
    "progress_review_annotation": "Một kết quả phản hồi có nhiều vị trí cần sửa. Mỗi ghim liên kết đúng một bản tiến độ, tài liệu hoặc đề cương (CHECK one_target), cùng tệp bất biến. Loại PIN lưu vị trí, SUMMARY lưu nhận xét chung riêng của từng GV, ATTACHMENT liên kết một tệp phản hồi riêng đã quét trong stored_file. CHECK ràng buộc đúng loại; partial UNIQUE giới hạn một SUMMARY cho mỗi GV/phiên bản. Nháp riêng và góp ý đã gửi có vòng đời khác quyết định duyệt; không gộp danh sách một-nhiều vào JSON/text.",
    "registration_form_version": "Đơn thuộc hồ sơ đăng ký trước khi có khóa luận. document_version thuộc khóa luận nên không thay thế được quan hệ này; mỗi bản tệp và dấu đối chiếu được giữ nguyên.",
    "academic_year": "Một năm học có nhiều đợt; không gộp lịch/loại đợt vào năm học.",
    "advisor_assignment": "GV chấp nhận đăng ký tạo ngay phân công GVHD chính thức cùng khóa luận trong một giao dịch; bảng giữ thời điểm và lịch sử phân công.",
    "audit_event": "Nhật ký nhiều sự kiện trên nhiều đối tượng; không thể thay bằng trạng thái cuối của từng bảng.",
    "document": "Một hồ sơ tài liệu có nhiều phiên bản; tách thông tin chung và bản nộp.",
    "department_major": "Một bộ môn quản lý nhiều ngành; cặp mã cần quan hệ và ràng buộc riêng, không thể dùng một cột department.major_code.",
    "document_version": "Tách khỏi document để không ghi đè bản đã nộp.",
    "eligibility_snapshot": "Theo từng SV/đợt/phiên bản; không nhét điều kiện biến đổi vào hồ sơ SV cố định.",
    "member_work_assignment": "Phần việc riêng từng SV có phiên bản/nhận xét, không phải nội dung chung của KLTN.",
    "position_assignment": "Chức vụ tổ chức theo khoa/bộ môn khác quyền nghiệp vụ theo đợt/KLTN của resource_assignment.",
    "progress_report": "Mỗi mốc có nhiều bản nộp; cần lịch sử và trạng thái riêng.",
    "progress_review": "Có thể có nhiều người nhận xét cùng báo cáo; COMMENT_ONLY khác quyền GVHD xác nhận.",
    "proposal": "Đề cương có chu trình xét duyệt riêng; không dùng document chung để giả xác nhận học thuật.",
    "proposal_review": "Nhận xét theo đúng phiên bản đề cương và phân công; khác nhận xét tiến độ.",
    "proposal_version": "Giữ file và SHA-256 của từng lần nộp, không ghi đè proposal hay document_version.",
    "registration_member": "Đồng thuận trước khi chốt khác tư cách thành viên chính thức trong thesis_member.",
    "resource_assignment": "Quyền theo tài nguyên và thời hạn không suy ra từ base_role hoặc chức vụ chung.",
    "reviewer_assignment": "Giới hạn GV được góp ý theo từng đề cương; không mặc nhiên trao quyền bằng vai trò LECTURER.",
    "signature_confirmation": "Một quyết định xác nhận trỏ đúng phiên bản đã chốt; không gộp thành cờ trên proposal.",
    "stored_file": "Tách metadata tệp vật lý khỏi hồ sơ nghiệp vụ và phiên bản để kiểm checksum/đường dẫn riêng.",
    "thesis": "KLTN chỉ hình thành sau khi đăng ký chốt; không dùng topic_registration như hồ sơ thực hiện.",
    "thesis_member": "Thành viên chính thức có lịch sử riêng, không đồng nhất với registration_member trước chốt.",
    "thesis_round": "Đợt chính/bổ sung có cửa sổ và trạng thái độc lập trong cùng năm học.",
    "topic_title_version": "Tên đổi theo lịch sử; topic giữ mã và tên hiện hành để truy vấn nhanh.",
}

ROLE_GROUPS = {
    "official_form": "FORM_MANAGER được cấp rõ theo đợt mới quản lý. Admin không tự có quyền phát hành; SV/GV xem theo đối tượng và phạm vi đợt.",
    "official_form_version": "FORM_MANAGER theo đợt tải/kiểm/phát hành/thu hồi. SV/GV chỉ xem bản đã phát hành và lịch sử hợp lệ, không xem nháp hoặc danh sách ngoài đợt.",
    "progress_review_annotation": "GVHD/người góp ý được phân công tự lưu và sửa ghim nháp riêng trên bản hiện hành. Chỉ sau khi gửi kết quả, SV thành viên và người có quyền xem tài nguyên tương ứng mới thấy ghim. Không mở rộng quyền xác nhận cho người góp ý chéo.",
    "registration_form_version": "SV đang trong nhóm nộp trước hạn tiếp nhận; nhóm, GV tiếp nhận và TBM đúng phạm vi được xem/tải/xuất bản nộp. Admin kỹ thuật không có quyền đọc mặc định.",
    "academic_year": "Admin kỹ thuật cấu hình năm học; người dùng được phân quyền xem đợt tương ứng.",
    "advisor_assignment": "Trưởng bộ môn chốt GVHD; GV được đề cử có quyền nhận/từ chối thay đổi; SV và GVHD xem trong phạm vi khóa luận.",
    "audit_event": "Service ghi khi có thao tác; Trưởng bộ môn đúng phạm vi xem lịch sử khóa luận.",
    "department": "Admin kỹ thuật quản lý dữ liệu tổ chức; quyền nghiệp vụ chỉ áp dụng cho bộ môn tương ứng.",
    "department_major": "Admin kỹ thuật nạp danh mục đã đối chiếu; người nhập danh sách xem và chỉ dùng cặp mã đang hoạt động.",
    "document_version": "SV thành viên nộp bản mới; GVHD nhận xét; chỉ actor có quyền trên khóa luận được tải.",
    "faculty": "Admin kỹ thuật quản lý dữ liệu Khoa; Trưởng khoa chỉ có quyền theo phân công chức vụ còn hiệu lực.",
    "lecturer_profile": "GV xem/cập nhật hồ sơ của mình theo API; Admin quản lý tài khoản, không thay GV duyệt đề tài.",
    "member_work_assignment": "SV/nhóm ghi phần việc theo khóa luận; GVHD nhận xét đúng phạm vi.",
    "organizational_position": "Admin kỹ thuật quản lý mã chức vụ; chỉ phân công position_assignment có hiệu lực mới cấp quyền nghiệp vụ.",
    "user_account": "Admin kỹ thuật quản lý trạng thái; chính chủ đăng nhập; không cấp quyền duyệt nghiệp vụ cho Admin.",
    "eligibility_snapshot": "Người Khoa được giao ELIGIBILITY_IMPORTER/VERIFIER theo đợt; SV chỉ xem kết quả của mình.",
    "position_assignment": "Admin quản trị phân công có căn cứ; Trưởng bộ môn/Trưởng khoa thực thi quyền trong phạm vi hiệu lực.",
    "resource_assignment": "Admin quản trị phân công có căn cứ; người được giao chỉ thao tác đúng tài nguyên.",
    "topic": "GV hoặc SV đề xuất; Trưởng bộ môn đúng phạm vi xét duyệt.",
    "topic_registration": "Từng SV tự tham gia; GV tiếp nhận quyết định; Trưởng bộ môn chốt.",
    "proposal": "SV thành viên nộp; GVHD xác nhận; GV được giao góp ý; TBM chốt; Trưởng khoa ghi bản ký.",
    "proposal_version": "SV thành viên nộp bản mới sau yêu cầu sửa; GVHD/GV góp ý và người chốt xem đúng phạm vi.",
    "proposal_review": "GVHD chính xác nhận hoặc yêu cầu sửa; GV được TBM giao chỉ COMMENT; SV thành viên xem.",
    "reviewer_assignment": "Trưởng bộ môn phân công giảng viên góp ý; chỉ người được giao và người trong hồ sơ xem.",
    "signature_confirmation": "Trưởng bộ môn chốt phiên bản; Trưởng khoa ghi tham chiếu bản giấy đã ký đúng phạm vi Khoa.",
    "progress_report": "SV trong nhóm nộp và xem; chỉ GVHD đúng đề tài nhận xét/xác nhận. TBM quản lý mốc chung không đọc nội dung tiến độ.",
    "progress_milestone": "Người điều phối KLTN được giao theo đợt quản lý mốc; SV/GV xem mốc khóa luận liên quan.",
    "progress_review": "Chỉ GVHD chính nhận xét và xác nhận/yêu cầu sửa báo cáo tiến độ của nhóm mình.",
    "document": "SV thành viên nộp; GVHD xem/nhận xét; người ngoài phạm vi không xem.",
    "registration_member": "Từng sinh viên tự xác nhận tham gia; GV tiếp nhận và Trưởng bộ môn xem nhóm đúng phạm vi.",
    "stored_file": "Chỉ service tài liệu/đề cương/minh chứng ghi metadata; tải file qua API kiểm quyền, không truy cập storage trực tiếp.",
    "student_profile": "SV xem hồ sơ của mình; Khoa nhập và xác nhận nguồn danh sách theo phân công đợt.",
    "thesis": "SV thành viên, GVHD, Trưởng bộ môn và người được giao xem đúng phạm vi; GV tiếp nhận tạo khóa luận trong giao dịch; TBM có quyền theo dõi đúng bộ môn.",
    "thesis_member": "Phát sinh khi GV chấp nhận đăng ký; SV/GV liên quan xem danh sách thành viên.",
    "thesis_round": "Admin kỹ thuật cấu hình đợt; Khoa xác nhận danh sách theo phân công; SV/GV xem đợt mở.",
    "topic_requirement": "GV đề xuất yêu cầu mong muốn; Trưởng bộ môn xét đề tài; SV xem trước khi đăng ký.",
    "topic_title_version": "GV/SV đề xuất thay tên theo quy trình; Trưởng bộ môn quyết định; mọi bên liên quan xem lịch sử.",
}


def make_dictionary() -> None:
    assert set(target_metadata.tables) == SELECTED_TABLES
    lines = ["# Từ điển dữ liệu CSDL chính thức `kltn_management`", "",
        f"Sinh từ metadata SQLAlchemy của revision Alembic `{HEAD}`; {len(SELECTED_TABLES)} bảng nghiệp vụ, không tính bảng quản lý revision `alembic_version`.",
        "", "`NULL` ở đây là ràng buộc vật lý. Mọi hành động quan trọng còn chịu kiểm tra quyền/trạng thái trong service và audit. Ví dụ đều là dữ liệu giả.", ""]
    for number, table in enumerate(sorted(target_metadata.tables.values(), key=lambda item: item.name), 1):
        title, function = TABLE_INFO[table.name]
        used = callers(table.name)
        roles = ROLE_GROUPS.get(table.name, "Chỉ actor được API/service cấp quyền theo vai trò, bộ môn/đợt/KLTN; Admin không mặc nhiên duyệt nghiệp vụ.")
        lines += [f"## {number:02d}. `{table.name}` — {title}", "",
            f"**Mục đích và lý do tồn tại:** {function}. Nếu bỏ, mất dữ liệu/quan hệ riêng của {title.lower()} hoặc không còn kiểm được lịch sử và quyền liên quan.",
            f"**Use case/API/service:** {function}; " + (", ".join(f"`{path}`" for path in used) if used else "bảng phụ trợ, chưa có truy cập trực tiếp") + ".",
            f"**Vai trò thao tác:** {roles}",
            f"**Tình huống giả:** {EXAMPLES[table.name]}",
            f"**Trạng thái sử dụng:** {'Đọc/ghi trực tiếp trong API/service' if used else 'Phụ trợ cho FK/quyền/phiên bản'}.",
            f"**Vì sao không gộp/xóa:** {SEPARATION.get(table.name, 'Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.')}",
            "", "| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |",
            "|---|---|---|---|---|---|",
        ]
        for column in table.columns:
            label = "Mã ngành" if table.name == "department_major" and column.name == "code" else COLUMN_VI[column.name]
            if table.name == "department_major" and column.name == "name":
                label = "Tên ngành"
            dtype = str(column.type.compile(dialect=postgresql.dialect()))
            default = str(column.server_default.arg) if column.server_default is not None else ("Ứng dụng sinh UUID" if column.primary_key else "Ứng dụng" if column.default is not None else "—")
            default = default.replace("|", "\\|")
            if column.primary_key:
                purpose = "Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK."
            elif column.foreign_keys:
                targets = ", ".join(sorted(f"`{fk.column.table.name}.{fk.column.name}`" for fk in column.foreign_keys))
                purpose = f"{label}; liên kết tới {targets}, giữ toàn vẹn tham chiếu."
            elif column.name == "due_at_at_submission":
                purpose = "Hạn hiệu lực tại lúc gửi; giữ nguyên kết quả đúng hạn/trễ khi Khoa gia hạn mốc sau đó. Bản cũ trước migration chỉ được khôi phục theo hạn tại lúc chuyển đổi."
            elif column.name in {"created_at", "updated_at", "occurred_at", "submitted_at", "confirmed_at", "decided_at"}:
                purpose = f"{label}; dùng đối chiếu trình tự và audit."
            elif column.name in {"state", "status", "decision", "consent_status"}:
                purpose = f"{label}; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình."
            elif column.name in {"version", "version_no", "row_version", "current_version_no"}:
                purpose = f"{label}; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời."
            else:
                purpose = f"{label}; phục vụ {function.lower()}."
            lines.append(f"| `{column.name}` | {label} | `{dtype}` | {'Cho phép' if column.nullable else 'Không'} | `{default}` | {purpose} |")
        pk = ", ".join(f"`{c.name}`" for c in table.primary_key.columns)
        fks = ["`" + ", ".join(col.name for col in constraint.columns) + "` → `" + ", ".join(f"{e.column.table.name}.{e.column.name}" for e in constraint.elements) + "`" for constraint in table.constraints if isinstance(constraint, ForeignKeyConstraint)]
        uniques = ["`" + ", ".join(c.name for c in constraint.columns) + "`" for constraint in table.constraints if isinstance(constraint, UniqueConstraint)]
        checks = ["`" + (constraint.name or "") + "`: `" + str(constraint.sqltext).replace("|", "\\|") + "`" for constraint in table.constraints if isinstance(constraint, CheckConstraint)]
        indexes = ["`" + (index.name or "") + "` (" + ", ".join(str(expr).replace("|", "\\|") for expr in index.expressions) + (") UNIQUE" if index.unique else ")") for index in table.indexes]
        lines += ["", f"**PK:** {pk}.",
            "**FK và quan hệ:** " + ("; ".join(sorted(fks)) if fks else "Không có FK") + ".",
            "**UNIQUE:** " + ("; ".join(sorted(uniques)) if uniques else "Không có ràng buộc UNIQUE riêng") + ".",
            "**CHECK:** " + ("; ".join(sorted(checks)) if checks else "Không có CHECK riêng") + ".",
            "**Index:** " + ("; ".join(sorted(indexes)) if indexes else "Chỉ index PK/UNIQUE do PostgreSQL tạo") + ".",
            ""]
    (DESIGN / "database-dictionary.md").write_text("\n".join(lines), encoding="utf-8")


def make_erd() -> None:
    assert set(target_metadata.tables) == SELECTED_TABLES
    lines = ["# ERD CSDL chính thức `kltn_management`", "",
        f"Sơ đồ chứa {len(SELECTED_TABLES)} bảng nghiệp vụ của revision `{HEAD}`; cột đầy đủ, CHECK/UNIQUE và giải nghĩa nằm trong [từ điển dữ liệu](database-dictionary.md).",
        "", "```mermaid", "erDiagram"]
    for table in sorted(target_metadata.tables.values(), key=lambda item: item.name):
        lines.append(f"    {table.name} {{")
        for column in table.columns:
            if column.primary_key or column.foreign_keys:
                dtype = "uuid" if "UUID" in str(column.type).upper() else "int"
                lines.append(f"        {dtype} {column.name} {'PK' if column.primary_key else 'FK'}")
        lines.append("    }")
    for table in sorted(target_metadata.tables.values(), key=lambda item: item.name):
        for constraint in sorted((c for c in table.constraints if isinstance(c, ForeignKeyConstraint)), key=lambda item: item.name or ""):
            parent = next(iter(constraint.elements)).column.table.name
            nullable = any(c.nullable for c in constraint.columns)
            lines.append(f"    {parent} {'o|--o{' if nullable else '||--o{'} {table.name} : {next(iter(constraint.columns)).name}")
    lines += ["```", "", "Các quan hệ tùy chọn dùng `o|`; FK bắt buộc dùng `||`. Quan hệ nhiều bản ghi dùng `o{`. Các quyền chi tiết được kiểm ở service, không suy ra từ ERD.", ""]
    (DESIGN / "erd-kltn-management.md").write_text("\n".join(lines), encoding="utf-8")


def callers(table: str) -> list[str]:
    cls = "".join(token.title() for token in table.split("_"))
    used = []
    for directory in (ROOT / "backend/api", ROOT / "backend/services"):
        for path in sorted(directory.glob("*.py")):
            content = path.read_text(encoding="utf-8")
            if re.search(r"\bm\." + cls + r"\b|\bimport\s+" + cls + r"\b", content):
                used.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return used


if __name__ == "__main__":
    make_dictionary()
    make_erd()
