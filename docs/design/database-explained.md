# Giải thích CSDL PostgreSQL cho người mới

Tài liệu này giải thích **vì sao có từng bảng và từng cột nghiệp vụ**. [Từ điển dữ liệu](data-dictionary.md) là nơi tra kiểu PostgreSQL, `NULL`, mặc định, khóa, chỉ mục và `CHECK` chính xác. Tên cột ở đây là tên thật sau hai migration `20260920_0001` → `20260924_0002`; các cột dùng chung được giải thích một lần ở dưới. Schema có **62 bảng của mô hình, 606 cột** (gồm bảng lõi, phần mở rộng dự kiến và bảng hỗ trợ). PostgreSQL còn có bảng kỹ thuật `alembic_version` để ghi migration đã áp dụng: pgAdmin vì thế hiện **63 bảng và 607 cột vật lý** khi đếm cả `alembic_version.version_num`; con số 606 trong từ điển chỉ tính 62 bảng của mô hình.

## Đọc schema như thế nào

- Một **bảng** lưu một loại sự vật hoặc một sự kiện: `topic` là đề tài, `topic_registration` là lần đăng ký, `thesis` là khóa luận được hình thành sau khi chốt.
- `id` là khóa chính UUID. Cột kết thúc bằng `_id` thường là khóa ngoại trỏ tới `id` của bảng khác. Ví dụ `topic.round_id` nối đề tài với đợt KLTN.
- `created_at` ghi lúc tạo dòng; `updated_at` ghi lần cập nhật gần nhất. `row_version` là số phiên bản phục vụ kiểm tra sửa đồng thời **ở tầng ứng dụng**; bản thân PostgreSQL hiện chỉ đặt mặc định `1`, không tự tăng nó. Không dùng cột này làm số phiên bản tệp.
- `version`/`version_no` là số phiên bản nội dung hoặc chính sách trong phạm vi bảng cha. Các bảng `*_version` giữ lịch sử; không ghi đè tệp đã nộp.
- `state`/`status` là trạng thái quy trình. Chúng được lưu bằng `VARCHAR` và nhiều bảng có `CHECK`; thứ tự chuyển trạng thái, người có quyền chuyển và điều kiện trước/sau vẫn cần backend kiểm tra.
- Cột `*_by` là người thực hiện/xác nhận, `*_at` là thời điểm, `*_ref` là mã hoặc tham chiếu chứng từ. Chúng giúp trả lời **ai đã làm gì, khi nào, căn cứ vào đâu**.
- `stored_file` chỉ lưu thông tin tệp; nội dung nhị phân để ở kho tệp. `sha256`/`content_sha256` giúp đối chiếu đúng bản. Không lưu mật khẩu, khóa Gemini, prompt thô, bảng điểm thật hoặc tệp KLTN thật trong repo.

## 1. Danh tính, tổ chức, đợt và điều kiện

### `faculty` — Khoa

Tách Khoa ra để Bộ môn, chức vụ và dữ liệu KLTN có phạm vi rõ. `code`: mã Khoa duy nhất; `name`: tên hiển thị; `active`: Khoa còn được sử dụng. Có các cột chung `id`, `created_at`, `updated_at`.

### `department` — Bộ môn

Một Khoa có nhiều Bộ môn. `faculty_id`: Khoa chủ quản; `code`: mã Bộ môn, duy nhất **trong Khoa**; `name`: tên Bộ môn; `major_code`: mã ngành/chuyên ngành khi có; `active`: còn hoạt động. `id`, `created_at`, `updated_at` là cột chung.

### `user_account` — tài khoản đăng nhập

Tài khoản nền tảng chỉ có `ADMIN`, `LECTURER`, `STUDENT`; chức vụ và phân công được lưu riêng để một giảng viên có thể mang nhiều trách nhiệm theo thời điểm. `external_subject`: định danh ổn định từ hệ thống xác thực, không phải mật khẩu; `base_role`: một trong ba loại tài khoản; `status`: `ACTIVE`/`LOCKED`/`DISABLED`. Dùng thêm `id`, `created_at`, `updated_at`, `row_version`.

### `student_profile` — hồ sơ sinh viên

`user_id`: tài khoản tương ứng, duy nhất để một tài khoản không có hai hồ sơ SV; `student_code`: mã SV, là dữ liệu cá nhân cần bảo vệ; `department_id`: Bộ môn/ngành quản lý; `display_name`: tên hiển thị, cũng là dữ liệu cá nhân. Có `id`, `created_at`, `updated_at`.

### `lecturer_profile` — hồ sơ giảng viên

`user_id`: tài khoản tương ứng, duy nhất; `lecturer_code`: mã GV; `department_id`: Bộ môn công tác; `display_name`: tên GV. Có `id`, `created_at`, `updated_at`. Hồ sơ này không tự cấp quyền TBM, Trưởng khoa hay GVHD.

### `organizational_position` — danh mục chức vụ

`code`: loại chức vụ (`DEPARTMENT_HEAD`, `FACULTY_DEAN`); `name`: tên dễ đọc. Có `id`, `created_at`, `updated_at`. Tách danh mục khỏi người giữ chức vụ để thay người không phải sửa loại chức vụ.

### `position_assignment` — ai giữ chức vụ nào, ở đâu và khi nào

`lecturer_id`: GV được bổ nhiệm; `position_id`: chức vụ; `faculty_id` hoặc `department_id`: **đúng một** phạm vi Khoa/Bộ môn; `effective_from`, `effective_to`: khoảng hiệu lực; `state`: còn hiệu lực hay đã kết thúc. Có `id`, `created_at`, `updated_at`, `row_version`. Partial unique index ngăn hai phân công `ACTIVE` trùng người/chức vụ/phạm vi; quyền duyệt vẫn cần kiểm thời điểm và đối tượng ở backend.

### `resource_assignment` — quyền theo hồ sơ cụ thể

`assignment_type`: loại nhiệm vụ, như xác nhận điều kiện; `user_id`: người được giao; `round_id`, `thesis_id`, `council_id`: **đúng một** tài nguyên được giao; `effective_from`, `effective_to`: thời hạn; `state`: hiệu lực. Có `id`, `created_at`, `updated_at`, `row_version`. Cách này giữ câu hỏi GVHD chưa rõ về người xác nhận điều kiện ở mức cấu hình, không mặc định Admin hoặc TBM có quyền.

### `academic_year` — năm học

`code`: mã năm học; `starts_on`, `ends_on`: ngày bắt đầu/kết thúc; `state`: trạng thái mở/quản lý năm học. Có `id`, `created_at`, `updated_at`, `row_version`. Một năm học chứa được đợt chính và đợt bổ sung.

### `thesis_round` — đợt KLTN

`academic_year_id`: năm học cha; `code`: mã đợt duy nhất trong năm; `round_type`: chính (`MAIN`) hoặc bổ sung (`SUPPLEMENTARY`); `opens_at`, `closes_at`: cửa sổ thời gian; `state`: trạng thái đợt. Có `id`, `created_at`, `updated_at`, `row_version`. Không tạo hai quy trình khác nhau cho hai loại đợt.

### `round_policy` — chính sách theo đợt

`round_id`: đợt áp dụng; `policy_type`: loại chính sách; `version`: phiên bản của loại chính sách; `config_json`: thông số có thể thay đổi theo đợt; `state`: nháp/hiệu lực; `effective_at`: thời điểm có hiệu lực. Có `id`, `created_at`, `updated_at`. Các ngưỡng điều kiện và lịch chưa chốt nằm ở đây thay vì khóa cứng trong `CHECK`; backend phải xác thực cấu trúc JSON và chính sách được chọn.

### `eligibility_snapshot` — ảnh chụp điều kiện đăng ký của một SV

`student_id`, `round_id`: SV và đợt được xét; `version`: lần ghi nhận; `passed_credit_ratio`: tỷ lệ tín chỉ đã đạt; `gpa_4`: GPA hệ 4; `discipline_status`, `criminal_case_status`: thông tin điều kiện theo quy định; `evidence_ref`: tham chiếu minh chứng; `captured_at`: lúc ghi nhận; `confirmed_by`, `confirmed_at`: người/lúc xác nhận nếu đã có thẩm quyền; `decision_reason`: lý do quyết định; `state`: trạng thái xét. Có `id`, `created_at`, `updated_at`. Lưu snapshot để sau này thay đổi học vụ không làm mất căn cứ quyết định cũ.

### `eligibility_exception` — ngoại lệ có văn bản

`snapshot_id`: lần xét được ngoại lệ; `official_ref`: văn bản chấp thuận; `reason`: lý do; `granted_by`, `granted_at`: người và thời điểm cấp. Có `id`, `created_at`, `updated_at`. Ngoại lệ không được hiểu là tự bỏ qua các ngưỡng ở tầng ứng dụng.

### `lecturer_expertise` — chuyên môn GV tự khai

`lecturer_id`: GV sở hữu; `version`: lần khai báo; `labels`: lĩnh vực/từ khóa có cấu trúc linh hoạt; `state`: trạng thái, mặc định nên coi là tự khai; `verified_by`, `verified_at`: để trống đến khi người có thẩm quyền xác nhận được làm rõ. Có `id`, `created_at`, `updated_at`, `row_version`. Không quảng cáo dữ liệu tự khai là đã được Khoa kiểm chứng.

### `expertise_evidence` — căn cứ cho chuyên môn

`expertise_id`: phiên bản chuyên môn liên quan; `evidence_type`: loại căn cứ; `reference`: đường dẫn/mã tài liệu. Có `id`, `created_at`, `updated_at`. Tách minh chứng để một lần khai có nhiều căn cứ.

## 2. Đề tài, đăng ký, nhóm và phân công

### `topic` — đề tài được đề xuất/công bố

`round_id`: đợt; `department_id`: Bộ môn phụ trách; `proposer_user_id`: người đề xuất; `proposer_type`: nguồn đề xuất; `current_title`: tiêu đề đang dùng; `description`: mô tả; `max_students`: sức chứa từ 1 đến 3; `state`: tiến trình xét; `decided_by`, `decided_at`: người/lúc duyệt. Có `id`, `created_at`, `updated_at`, `row_version`. Đề tài có thể tồn tại trước khi có SV đăng ký.

### `topic_title_version` — lịch sử đổi tên đề tài

`topic_id`: đề tài; `version_no`: lần đổi; `title`: tên tại lần đó; `changed_by`: người sửa; `change_reason`: lý do. Có `id`, `created_at`, `updated_at`. Giữ tên cũ để chứng từ và lịch sử không bị sai khi đổi tên.

### `topic_requirement` — mong muốn của GVHD đối với người đăng ký

`topic_id`: đề tài; `requirement_type`: loại mong muốn; `value_text`: mô tả như kỹ năng/công nghệ; `preferred_gpa`: GPA mong muốn nếu có; `enforcement`: `DESIRED`, không tự động loại SV. Có `id`, `created_at`, `updated_at`. Điều kiện đủ KLTN chung nằm ở policy/snapshot, khác yêu cầu ưu tiên của từng GVHD.

### `topic_registration` — một lần gửi đăng ký một đề tài

`round_id`, `topic_id`: đợt và **một** đề tài; `created_by`: người khởi tạo; `state`: nháp/đã gửi/được GVHD xử lý/TBM chốt; `submitted_at`: lúc gửi; `lecturer_decided_by`, `lecturer_decided_at`, `lecturer_reason`: quyết định đồng ý/từ chối và lý do của GVHD; `department_finalized_by`, `department_finalized_at`: người/lúc TBM chốt. Có `id`, `created_at`, `updated_at`, `row_version`. Không có cột thứ tự nguyện vọng vì GVHD xác nhận mỗi SV chỉ đăng ký một đề tài hoạt động trong đợt.

### `registration_member` — SV thuộc đăng ký nhóm

`registration_id`: đăng ký; `round_id`: đợt được sao lại để áp unique theo SV/đợt, composite FK giữ khớp đăng ký; `student_id`: SV; `is_coordinator`: nhóm trưởng điều phối, không là chủ nhiệm học thuật; `active`: còn thuộc đăng ký hoạt động. Có `id`, `created_at`, `updated_at`. Backend phải đồng bộ `active` khi hủy/từ chối; DB không tự đếm đủ 1–3 người.

### `thesis` — khóa luận đã được hình thành

`round_id`, `topic_id`: đợt và đề tài chốt; `registration_id`: đăng ký nguồn; `department_id`: Bộ môn quản lý; `current_title`: tên hiện hành; `state`: vòng đời khóa luận. Có `id`, `created_at`, `updated_at`, `row_version`. Tách `thesis` khỏi `topic` vì một đề tài được duyệt chưa đồng nghĩa đã có khóa luận được giao.

### `thesis_member` — SV chính thức trong khóa luận

`thesis_id`, `student_id`: khóa luận và SV; `is_coordinator`: nhóm trưởng; `active`: còn tham gia; `joined_at`, `left_at`: mốc vào/rời nhóm. Có `id`, `created_at`, `updated_at`. Điểm và kết quả sẽ trỏ tới **thành viên**, không trỏ chung tới nhóm.

### `member_work_assignment` — phần việc của từng SV

`thesis_member_id`: người được giao; `version_no`: bản phân công; `work_description`: việc phải làm; `expected_output`: sản phẩm dự kiến; `state`: trạng thái GVHD duyệt; `reviewed_by`, `reviewed_at`, `review_comment`: ai duyệt, khi nào và nhận xét. Có `id`, `created_at`, `updated_at`, `row_version`. Đây là căn cứ giải thích vì sao các SV cùng khóa luận có thể được đánh giá khác nhau.

### `advisor_assignment` — phân công GVHD

`thesis_id`: khóa luận; `lecturer_id`: GVHD; `assignment_type`: chính/phụ; `assigned_by`: người chốt phân công; `effective_from`, `effective_to`: thời hạn; `state`: hiệu lực. Có `id`, `created_at`, `updated_at`, `row_version`. Partial unique chặn hai GVHD **chính đang active** cho cùng khóa luận; quyền TBM chốt được kiểm ở service.

### `reviewer_assignment` — phân công GVPB

`lecturer_id`: người phản biện; `proposal_id` hoặc `thesis_id`: đúng phạm vi đề cương hoặc khóa luận; `review_scope`: loại phản biện; `assigned_by`, `assigned_at`: nguồn phân công; `state`: hiệu lực. Có `id`, `created_at`, `updated_at`, `row_version`. Tách khỏi nhận xét để phân công tồn tại trước khi GVPB viết phiếu.

## 3. Đề cương, tiến độ, thay đổi, tệp và độ tương đồng

### `stored_file` — metadata tệp

`storage_key`: vị trí trong kho tệp; `original_name`: tên lúc tải lên; `media_type`: MIME; `byte_size`: kích thước; `sha256`: mã kiểm toàn vẹn; `scan_state`, `scanned_at`: kết quả/lúc quét an toàn. Có `id`, `created_at`, `updated_at`. CSDL không chứa bytes; backend phải chặn nộp file chưa `CLEAN`.

### `proposal` — hồ sơ đề cương của khóa luận

`thesis_id`: khóa luận, một hồ sơ đề cương; `current_version_no`: phiên bản hiện tại; `state`: trạng thái xét duyệt. Có `id`, `created_at`, `updated_at`, `row_version`. Bảng cha ổn định, các bản nộp nằm ở `proposal_version`.

### `proposal_version` — một bản đề cương đã nộp

`proposal_id`: hồ sơ cha; `version_no`: thứ tự; `stored_file_id`: tệp tương ứng; `submitted_by`, `submitted_at`: ai/lúc nộp; `content_sha256`: hash nội dung đúng bản. Có `id`, `created_at`, `updated_at`. Review và chữ ký phải biết bản nào được xét.

### `proposal_review` — góp ý hoặc quyết định trên một bản đề cương

`proposal_version_id`: bản được đọc; `reviewer_assignment_id`: phân công phản biện nếu có; `reviewer_user_id`: người nhận xét; `decision`: kết luận; `comment`: nội dung góp ý. Có `id`, `created_at`, `updated_at`. Giữ nhiều vòng SV sửa → GVHD/GVPB/Hội đồng góp ý → TBM chốt.

### `signature_confirmation` — xác nhận/ký đề cương

`proposal_id`: hồ sơ; `proposal_version_no`: **đúng số phiên bản đề cương được ký**, có FK ghép tới `proposal_version` của cùng hồ sơ; `signature_type`: loại chữ ký/xác nhận; `signer_user_id`: người ký; `confirmed_at`: thời điểm; `official_ref`: số hoặc tham chiếu văn bản. Có `id`, `created_at`, `updated_at`. TBM chốt nội dung và Trưởng khoa ký văn bản là hai hành động khác nhau. Migration mới không tự đoán phiên bản cho chữ ký cũ nếu đã có dữ liệu.

### `progress_milestone` — mốc tiến độ theo đợt

`round_id`: đợt; `code`, `title`: mã và tên mốc; `version_no`: phiên bản lịch; `due_at`: hạn; `expected_ratio`: mức hoàn thành dự kiến; `source_type`: căn cứ lập mốc; `state`: hiệu lực. Có `id`, `created_at`, `updated_at`, `row_version`. Không khóa cứng tất cả mốc khi GVHD mới nêu mốc đề cương và khoảng 70%.

### `progress_report` — SV báo cáo tiến độ khóa luận

`thesis_id`, `milestone_id`: khóa luận và mốc; `version_no`: lần nộp/sửa; `summary`: nội dung; `reported_ratio`: mức tự báo cáo; `evidence_file_id`: tệp minh chứng; `submitted_by`: người nộp; `state`: trạng thái. Có `id`, `created_at`, `updated_at`, `row_version`. GVHD xem và phản hồi ở bảng khác để không ghi đè bài nộp.

### `progress_review` — GVHD nhận xét tiến độ

`progress_report_id`: bản báo cáo; `reviewer_id`: người nhận xét; `decision`: đánh giá/xác nhận; `comment`: góp ý. Có `id`, `created_at`, `updated_at`. Phân quyền GVHD đúng khóa luận cần backend kiểm.

### `topic_change_request` — yêu cầu đổi đề tài trên hệ thống

`thesis_id`: khóa luận hiện tại; `requested_by`: người đề nghị; `reason`: lý do; `proposed_topic_id`, `proposed_title`: đề tài/tên muốn đổi; `advisor_reviewed_by`, `advisor_reviewed_at`: GVHD xác nhận; `department_decided_by`, `department_decided_at`: TBM chốt; `state`: trạng thái. Có `id`, `created_at`, `updated_at`, `row_version`. Tách đổi đề tài nội bộ khỏi thủ tục rút/gia hạn xử lý bên ngoài.

### `external_procedure_outcome` — kết quả thủ tục bên ngoài

`thesis_id`: khóa luận liên quan; `outcome_type`: rút hoặc gia hạn; `official_ref`: văn bản; `effective_at`: hiệu lực; `evidence_file_id`: tệp chứng cứ; `recorded_by`: người nhập kết quả. Có `id`, `created_at`, `updated_at`. Hệ thống ghi nhận kết quả, không tự tạo quy trình phê duyệt giả.

### `document` — loại hồ sơ/báo cáo của khóa luận

`thesis_id`: khóa luận; `document_type`: loại tài liệu; `title`: tên; `visibility`: phạm vi xem; `state`: trạng thái. Có `id`, `created_at`, `updated_at`, `row_version`. Bảng cha tách metadata tài liệu khỏi các file nộp lại.

### `document_version` — một bản tài liệu cụ thể

`document_id`: tài liệu cha; `version_no`: lần nộp; `stored_file_id`: file; `submitted_by`, `submitted_at`: người/lúc nộp; `content_sha256`: hash; `state`: trạng thái bản. Có `id`, `created_at`, `updated_at`, `row_version`. Kiểm tương đồng, nhận xét, công bố phải tham chiếu đúng version.

### `similarity_policy` — cấu hình kiểm tra độ tương đồng

`round_id`: đợt; `version_no`: phiên bản; `metric_code`: phép đo đã hiệu chỉnh, có thể trống; `threshold_value`: ngưỡng nếu có; `decision_mode`: tư vấn hay chặn; `config_json`: tham số; `state`: hiệu lực. Có `id`, `created_at`, `updated_at`. Không đồng nhất một điểm cosine kỹ thuật với “90% giống” khi chưa chốt metric/corpus.

### `similarity_check` — một lần kiểm tra một bản tài liệu

`document_version_id`: bản được kiểm; `policy_id`: policy áp dụng; `metric_code`: metric thực chạy; `lexical_coverage_pct`: độ phủ trùng chữ; `semantic_candidate_score`: điểm gợi ý ngữ nghĩa; `business_status`: kết luận nghiệp vụ nếu policy cho phép; `model_version`, `index_version`, `corpus_snapshot`: nguồn/phiên bản để tái kiểm; `state`: trạng thái tác vụ; `completed_at`: lúc xong. Có `id`, `created_at`, `updated_at`. Các chỉ số được tách để không coi semantic similarity là đạo văn.

### `similarity_match` — đoạn/nguồn khớp trong một lần kiểm

`check_id`: lần kiểm; `source_document_version_id` hoặc `source_ref`: nguồn trong hệ thống hoặc nguồn ngoài; `input_start`, `input_end`: vị trí đoạn trong bản nộp; `matched_text_hash`: hash đoạn, không lưu nguyên văn trong log; `lexical_score`, `semantic_score`: hai phép đo khác nhau. Có `id`, `created_at`, `updated_at`.

## 4. Hội đồng, bảo vệ, nhận xét và điểm

### `council` — Hội đồng theo quyết định

`round_id`, `department_id`: đợt và Bộ môn; `code`: mã Hội đồng; `decision_ref`, `decision_date`: quyết định thành lập; `state`: trạng thái. Có `id`, `created_at`, `updated_at`, `row_version`. Một Hội đồng có thể mở nhiều buổi bảo vệ.

### `council_member` — thành viên Hội đồng

`council_id`: Hội đồng; `lecturer_id`: GV được cử; `role_code`: Chủ tịch/Thư ký/Phản biện/Ủy viên; `role_slot`: vị trí khi có nhiều người cùng vai trò; `active`: còn trong quyết định hiệu lực. Có `id`, `created_at`, `updated_at`. DB chặn trùng người/vị trí; backend phải kiểm đủ năm người đúng cơ cấu.

### `defense_session` — buổi bảo vệ

`council_id`: Hội đồng tổ chức; `code`: mã buổi; `scheduled_at`: lịch; `location`: nơi họp; `state`: tiến trình buổi. Có `id`, `created_at`, `updated_at`, `row_version`. Một Hội đồng nhiều buổi; một buổi có thể có nhiều KLTN.

### `session_thesis` — khóa luận nằm trong buổi nào

`session_id`: buổi; `thesis_id`: khóa luận; `order_no`: thứ tự trình bày. Có `id`, `created_at`, `updated_at`. Bảng nối giải quyết quan hệ nhiều khóa luận trong một buổi và ngăn lặp.

### `council_attendance` — điểm danh theo buổi

`session_id`: buổi; `council_member_id`: thành viên; `present`: có mặt; `recorded_by`, `recorded_at`: ai/lúc ghi; `note`: lý do/ghi chú. Có `id`, `created_at`, `updated_at`, `row_version`. Quorum (vắng quá 2/5 hoặc vắng Chủ tịch/Thư ký) cần service đối chiếu đủ danh sách.

### `defense_eligibility_check` — điều kiện bảo vệ từng SV

`thesis_member_id`, `round_id`: SV trong KLTN và đợt; `advisor_review_id`: văn bản/phiếu GVHD; `discipline_result`, `completion_result`, `advisor_result`: ba điều kiện cấp Trường; `local_policy_result`: tiêu chí riêng Khoa nếu được ban hành; `similarity_result`: kết quả liên quan; `result`: quyết định tổng; `reason`: giải thích; `checked_by`: người kiểm. Có `id`, `created_at`, `updated_at`. Không tự bịa tiêu chí Khoa đang `OPEN`.

### `advisor_review` — phiếu nhận xét GVHD theo SV

`advisor_assignment_id`: phân công GVHD; `thesis_member_id`: SV được nhận xét; `document_version_id`: đúng bản báo cáo; `version_no`: lần nhận xét; `attitude`: thái độ; `content_response`: chất lượng nội dung; `presentation`: trình bày; `defense_recommendation`: ý kiến cho bảo vệ. Có `id`, `created_at`, `updated_at`, `row_version`.

### `reviewer_review` — phiếu nhận xét GVPB theo SV

`reviewer_assignment_id`: phân công GVPB; `thesis_member_id`: SV; `document_version_id`: đúng bản báo cáo; `version_no`: lần nhận xét; `presentation`: hình thức; `research_quality`: chất lượng nghiên cứu; `contribution`: đóng góp; `questions`: câu hỏi phản biện; `overall`: kết luận. Có `id`, `created_at`, `updated_at`, `row_version`.

### `rubric_template` — mẫu chấm theo phiên bản

`code`, `name`: mã/tên biểu mẫu; `version_no`: lần ban hành; `source_ref`: căn cứ, ví dụ Mẫu 6; `state`: có hiệu lực hay không. Có `id`, `created_at`, `updated_at`. Tách mẫu chấm khỏi điểm để không sửa lại phiếu lịch sử khi quy định đổi.

### `rubric_criterion` — nhóm và tiêu chí con của mẫu chấm

`rubric_template_id`: mẫu cha; `parent_id`: nhóm cha nếu là tiêu chí con; `code`, `label`: mã/nội dung; `max_points`: điểm tối đa; `criterion_type`: `GROUP`, `NORMAL` hoặc `BONUS`; `order_no`: thứ tự hiển thị. Có `id`, `created_at`, `updated_at`. Mẫu 6 baseline có ba nhóm 2/4/4, 12 tiêu chí con và thưởng tối đa 1; **điểm nhóm chỉ tổng hợp, không cộng thêm lần nữa**. Xung đột với cơ cấu QĐ2919 vẫn là `OPEN-12` trước khi chấm thật.

### `rubric_assignment` — chọn mẫu chấm cho đợt hoặc buổi

`rubric_template_id`: mẫu được chọn; `round_id` hoặc `session_id`: phạm vi áp dụng; `state`: hiệu lực. Có `id`, `created_at`, `updated_at`. Cho phép đổi mẫu theo đợt mà vẫn giữ mẫu đã dùng cho kết quả cũ.

### `bonus_evidence` — minh chứng điểm thưởng của một SV

`thesis_member_id`: SV; `evidence_type`: loại minh chứng; `reference`: mã/liên kết; `stored_file_id`: file chứng cứ nếu có. Có `id`, `created_at`, `updated_at`. Điểm thưởng phải có căn cứ và nằm **trong** tổng điểm phiếu.

### `evaluation` — phiếu chấm của một thành viên Hội đồng cho một SV

`session_id`: buổi; `evaluator_member_id`: thành viên chấm; `thesis_member_id`: SV được chấm; `rubric_assignment_id`: mẫu đang dùng; `total_points`: tổng phiếu tối đa 10; `bonus_points`: phần thưởng tối đa 1 đã nằm trong tổng; `status`: nháp/đã nộp; `submitted_at`: lúc nộp; `correction_reason`: lý do sửa trước khóa. Có `id`, `created_at`, `updated_at`, `row_version`. Unique ngăn cùng người chấm cùng SV hai lần trong buổi; backend phải kiểm người chấm có mặt và tự sở hữu phiếu.

### `evaluation_item` — điểm từng tiêu chí trên phiếu

`evaluation_id`: phiếu; `criterion_id`: tiêu chí; `points`: điểm chấm; `comment`: nhận xét; `bonus_evidence_id`: minh chứng nếu là bonus. Có `id`, `created_at`, `updated_at`. Backend phải kiểm tiêu chí thuộc đúng mẫu, điểm không quá `max_points`, không chấm trực tiếp cả group lẫn con, và tổng khớp `evaluation.total_points`.

### `final_result` — kết quả đã tổng hợp cho từng SV

`session_id`, `thesis_member_id`: buổi và SV; `scorer_count`: số phiếu hợp lệ; `average_score`: trung bình phiếu; `bonus_average`: phần thưởng trung bình để giải thích, **không cộng lại**; `final_score`: điểm cuối làm tròn một chữ số; `calculation_version`: phiên bản công thức; `calculated_at`: lúc tính. Có `id`, `created_at`, `updated_at`. Snapshot giúp tái kiểm trong khi phiếu gốc vẫn giữ.

## 5. Biên bản, kho công bố và nhật ký

### `council_minute` — biên bản của buổi bảo vệ

`session_id`: buổi; `minute_no`: số biên bản; `current_version_no`: bản hiện hành; `state`: nháp/in/ký; `printed_at`, `signed_at`: mốc khóa. Có `id`, `created_at`, `updated_at`, `row_version`. Thư ký lập biên bản, Chủ tịch ký; không cho Admin sửa điểm hoặc biên bản đã ký.

### `minute_version` — từng bản biên bản

`minute_id`: biên bản cha; `version_no`: thứ tự; `stored_file_id`: file xuất; `generated_by`: người tạo; `state`: nháp/void/ký; `replacement_for_id`: bản bị thay; `void_reason`: lý do hủy. Có `id`, `created_at`, `updated_at`. Không xóa bản sai; giữ đường thay thế để audit.

### `minute_signature` — chữ ký biên bản

`minute_version_id`: bản được ký; `signer_member_id`: thành viên Hội đồng ký; `signed_at`: lúc ký; `signature_ref`: tham chiếu bằng chứng chữ ký. Có `id`, `created_at`, `updated_at`. Backend phải xác nhận signer thật sự là Chủ tịch đúng Hội đồng; FK một mình không thể chứng minh vai trò đó.

### `repository_item` — bản KLTN được công bố trong kho

`thesis_id`: khóa luận nguồn; `published_document_version_id`: **đúng bản** được công bố; `title`, `abstract`, `keywords`: metadata tra cứu; `source_type`: nguồn; `visibility`: ai xem được; `published_at`, `revoked_at`: thời điểm công bố/thu hồi. Có `id`, `created_at`, `updated_at`, `row_version`. Bản nháp và dữ liệu cá nhân không tự biến thành tài liệu công khai; backend kiểm đăng nhập/quyền trước khi tải.

### `search_index_metadata` — liên kết tới chỉ mục tìm kiếm

`repository_item_id`, `document_version_id`: item và bản được lập chỉ mục; `index_name`, `index_version`: chỉ mục/phiên bản; `embedding_model`, `chunking_version`: cách xử lý; `external_point_namespace`: vùng định danh điểm ở Qdrant; `state`, `indexed_at`: tình trạng/lúc lập chỉ mục. Có `id`, `created_at`, `updated_at`. PostgreSQL là nguồn gốc; chỉ mục/vector ngoài có thể xây lại.

### `retrieval_audit` — dấu vết một lần tra cứu AI

`user_id`: người hỏi nếu đăng nhập; `question_hash`: hash câu hỏi, không phải câu gốc; `authorized_scope_hash`: hash phạm vi được phép; `retrieved_item_count`: số nguồn lấy được; `provider`, `model_version`: dịch vụ/model; `outcome`: kết quả; `correlation_id`: mã nối log. Có `id`, `created_at`, `updated_at`. Không lưu prompt thô, secret hay chunks nhạy cảm trong bảng audit.

### `audit_event` — dấu vết thay đổi nghiệp vụ

`actor_id`: người thao tác; `action`: hành động; `resource_type`, `resource_id`: loại và ID đối tượng; `before_hash`, `after_hash`: vết trạng thái trước/sau; `reason`: lý do ngắn, không chép PII thô; `occurred_at`: lúc xảy ra; `correlation_id`: nối các bước cùng yêu cầu; `id`: khóa chính. Bảng này dùng để giải trình quyết định và sửa sai, không thay thế bảng version/chứng từ gốc.

## 6. 18 câu GVHD được dữ liệu hỗ trợ ra sao

Đọc [mapping từng câu](../requirements/18-cau-hoi-gvhd-mapping.md) để xem **câu trả lời thật, nguồn, mức chắc chắn và chỗ còn mở**. Bảng dưới là đường nhanh từ câu hỏi đến cấu trúc CSDL:

| Câu | Dữ liệu chính | Cách sử dụng / giới hạn |
| --- | --- | --- |
| 1 | `stored_file`, `advisor_review`, `reviewer_review`, `council_minute`, `final_result` | Giữ các loại hồ sơ/phiếu đã có; bộ mẫu nội bộ bổ sung vẫn `OPEN`. |
| 2 | `position_assignment`, `resource_assignment`, `advisor_assignment`, `signature_confirmation`, `minute_signature` | Phân biệt TBM chốt, Trưởng khoa ký, Thư ký lập, Chủ tịch ký. |
| 3 | `academic_year`, `thesis_round` | Một năm có đợt chính và bổ sung. |
| 4 | `topic_registration`, `registration_member` | Một đăng ký hoạt động/SV/đợt; không có nhiều nguyện vọng. |
| 5 | `topic.max_students`, `registration_member`, `thesis_member` | 1–3 SV; ghép thêm sau đăng ký còn `OPEN`. |
| 6 | `member_work_assignment`, `evaluation`, `final_result` | Phân công việc và chấm riêng từng SV. |
| 7 | `position_assignment`, `advisor_assignment` | TBM chốt phân công GVHD theo quyền ngữ cảnh. |
| 8 | `lecturer_expertise`, `expertise_evidence` | GV tự khai; ai xác nhận còn `OPEN`. |
| 9 | `proposal_version`, `proposal_review`, `signature_confirmation` | Giữ từng vòng góp ý, chốt nội dung và ký văn bản. |
| 10 | `progress_milestone`, `progress_report`, `progress_review` | Mốc/lịch cấu hình; GVHD nhận xét. |
| 11 | `topic_change_request`, `external_procedure_outcome` | Đổi đề tài trong hệ thống; rút/gia hạn ghi kết quả thủ tục ngoài. |
| 12 | `repository_item`, `document_version` | Xem/tải bản đã công bố theo visibility; khách chưa đăng nhập còn `OPEN`. |
| 13 | `council`, `defense_session`, `session_thesis` | Một Hội đồng nhiều buổi, một buổi nhiều KLTN. |
| 14 | `defense_eligibility_check`, `advisor_review` | Điều kiện Trường có căn cứ; điều kiện riêng Khoa còn `OPEN`. |
| 15 | `evaluation`, `council_minute`, `minute_version`, `audit_event` | Người chấm sửa phiếu mình trước khóa; thủ tục hậu ký còn `OPEN`. |
| 16 | `rubric_template`, `rubric_criterion`, `evaluation_item`, `bonus_evidence` | Lưu đầy đủ Mẫu 6; hiệu lực so với QĐ2919 còn `OPEN-12`. |
| 17 | `repository_item`, `search_index_metadata` | Metadata và bản công bố phục vụ tra cứu; AI chỉ trỏ tới nguồn được phép. |
| 18 | `retrieval_audit`, `search_index_metadata` | Thiết kế giảm PII và kiểm quyền trước truy xuất; chính sách gửi chunks ra Gemini cấp Trường còn `OPEN`. |

## 7. Giới hạn thực thi cần hiểu rõ

PostgreSQL trực tiếp bảo đảm PK, FK, `UNIQUE`, `CHECK` và partial unique index. Các điều kiện cần **đếm nhiều dòng, kiểm chức vụ/quyền, đối chiếu trạng thái hoặc tính tổng** cần service FastAPI trong transaction: số SV 1–3, sức chứa đề tài, đủ năm thành viên Hội đồng và quorum, người chấm có mặt, tổng tiêu chí theo rubric, điểm trung bình, khóa sau in/ký, công bố và quyền tải. [Danh mục ràng buộc](database-rules.md) ghi rõ cái nào DB đã chặn và cái nào ứng dụng phải làm. 26 ca validation hiện có chủ yếu chứng minh schema/constraint, **không chứng minh API nghiệp vụ đã được xây dựng**.

Khi sửa thiết kế: bắt đầu từ câu hỏi GVHD/nguồn → requirement/rule → use case → bảng/cột và state → migration Alembic mới → cập nhật từ điển/ERD/trace → chạy PostgreSQL validation. Không sửa migration `20260920_0001` đã áp dụng, không dùng `Base.metadata.create_all()` thay Alembic, và không đưa dữ liệu thật/secret vào Git.


## 8. Xem và cập nhật CSDL về sau

- Trong pgAdmin, mở database cần xem → Schemas → public → Tables; mở Columns, Constraints và Indexes của từng bảng. Hai database trên máy chủ dự án hiện dùng PostgreSQL native; thông số kết nối và thao tác từng cú nhấp nằm trong tài liệu pgAdmin **chỉ lưu trên máy**, không đưa vào GitHub.
- Khi cần thêm/sửa/xóa cấu trúc, bắt đầu từ nguồn/câu trả lời GVHD → requirement/rule → use case → model SQLAlchemy → **migration Alembic mới** → từ điển/ERD/trace → validation PostgreSQL. Mỗi database đã có bảng chỉ cần áp dụng revision mới, không dựng lại từ file init.
- Khi chỉ xem dữ liệu, dùng SELECT hoặc View/Edit Data trong pgAdmin. SQL trong file chỉ là câu lệnh; lưu file không sửa database. Khi sửa dữ liệu thử, kiểm tra điều kiện WHERE và database đang kết nối; không đưa hồ sơ, điểm hoặc secret thật vào Git.
- Migration là lịch sử để các máy khác dựng cùng cấu trúc. Không sửa migration đã chạy, không dùng Base.metadata.create_all() thay Alembic, không xem file init như bản cập nhật cho database hiện có.