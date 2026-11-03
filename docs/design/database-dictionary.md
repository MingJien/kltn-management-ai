# Từ điển dữ liệu CSDL chính thức `kltn_management`

Sinh từ metadata SQLAlchemy của revision Alembic `20261102_0019`; 43 bảng nghiệp vụ, không tính bảng quản lý revision `alembic_version`.

`NULL` ở đây là ràng buộc vật lý. Mọi hành động quan trọng còn chịu kiểm tra quyền/trạng thái trong service và audit. Ví dụ đều là dữ liệu giả.

## 01. `academic_year` — Năm học

**Mục đích và lý do tồn tại:** Đợt và lịch KLTN. Nếu bỏ, mất dữ liệu/quan hệ riêng của năm học hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đợt và lịch KLTN; `backend/api/account_admin.py`, `backend/services/proposal_export.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/topics.py`.
**Vai trò thao tác:** Admin kỹ thuật cấu hình năm học; người dùng được phân quyền xem đợt tương ứng.
**Tình huống giả:** Tạo năm học giả DEMO-2026-2027 để mở đợt KLTN chính.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Một năm học có nhiều đợt; không gộp lịch/loại đợt vào năm học.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `code` | Mã nghiệp vụ | `VARCHAR(20)` | Không | `—` | Mã nghiệp vụ; phục vụ đợt và lịch kltn. |
| `starts_on` | Ngày bắt đầu | `DATE` | Không | `—` | Ngày bắt đầu; phục vụ đợt và lịch kltn. |
| `ends_on` | Ngày kết thúc | `DATE` | Không | `—` | Ngày kết thúc; phục vụ đợt và lịch kltn. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** Không có FK.
**UNIQUE:** `code`.
**CHECK:** `ck_academic_year_date_window`: `ends_on > starts_on`; `ck_academic_year_state`: `state IN ('DRAFT','ACTIVE','CLOSED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 02. `advisor_assignment` — Phân công giảng viên hướng dẫn

**Mục đích và lý do tồn tại:** GVHD chính thức và lịch sử thay đổi. Nếu bỏ, mất dữ liệu/quan hệ riêng của phân công giảng viên hướng dẫn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** GVHD chính thức và lịch sử thay đổi; `backend/services/account_directory.py`, `backend/services/activity.py`, `backend/services/lecturer_profiles.py`, `backend/services/registration.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** Trưởng bộ môn chốt GVHD; GV được đề cử có quyền nhận/từ chối thay đổi; SV và GVHD xem trong phạm vi khóa luận.
**Tình huống giả:** Khi GV chấp nhận nhóm DEMO, một phân công GVHD chính được tạo trong cùng giao dịch với khóa luận và thành viên.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** GV chấp nhận đăng ký tạo ngay phân công GVHD chính thức cùng khóa luận trong một giao dịch; bảng giữ thời điểm và lịch sử phân công.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_id` | Mã khóa luận | `UUID` | Không | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `lecturer_id` | Mã giảng viên | `UUID` | Không | `—` | Mã giảng viên; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `assignment_type` | Loại phân công | `VARCHAR(20)` | Không | `PRIMARY` | Loại phân công; phục vụ gvhd chính thức và lịch sử thay đổi. |
| `assigned_by` | Mã người phân công | `UUID` | Không | `—` | Mã người phân công; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `effective_from` | Bắt đầu hiệu lực | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Bắt đầu hiệu lực; phục vụ gvhd chính thức và lịch sử thay đổi. |
| `effective_to` | Kết thúc hiệu lực | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Kết thúc hiệu lực; phục vụ gvhd chính thức và lịch sử thay đổi. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `ACTIVE` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `assigned_by` → `user_account.id`; `lecturer_id` → `lecturer_profile.id`; `thesis_id` → `thesis.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_advisor_assignment_assignment_type`: `assignment_type = 'PRIMARY'`; `ck_advisor_assignment_state`: `state IN ('ACTIVE','ENDED','REVOKED')`.
**Index:** `uq_advisor_assignment_active_primary` (advisor_assignment.thesis_id) UNIQUE.

## 03. `audit_event` — Nhật ký thao tác nghiệp vụ

**Mục đích và lý do tồn tại:** Dấu vết quyết định, phân quyền và tài liệu. Nếu bỏ, mất dữ liệu/quan hệ riêng của nhật ký thao tác nghiệp vụ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Dấu vết quyết định, phân quyền và tài liệu; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/auth.py`, `backend/api/core.py`, `backend/api/lecturer_import.py`, `backend/api/roster.py`, `backend/services/activity.py`, `backend/services/documents.py`, `backend/services/evaluation.py`, `backend/services/evidence.py`, `backend/services/lecturer_roster.py`, `backend/services/proposal_export.py`, `backend/services/registration.py`, `backend/services/roster.py`, `backend/services/theses.py`, `backend/services/topics.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** Service ghi khi có thao tác; Trưởng bộ môn đúng phạm vi xem lịch sử khóa luận.
**Tình huống giả:** Ghi actor, thời điểm và lý do khi GV chấp nhận đăng ký DEMO và tạo khóa luận.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Nhật ký nhiều sự kiện trên nhiều đối tượng; không thể thay bằng trạng thái cuối của từng bảng.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `actor_id` | Mã người thao tác | `UUID` | Cho phép | `—` | Mã người thao tác; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `action` | Hành động | `VARCHAR(100)` | Không | `—` | Hành động; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `resource_type` | Loại đối tượng nghiệp vụ | `VARCHAR(100)` | Không | `—` | Loại đối tượng nghiệp vụ; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `resource_id` | Mã đối tượng nghiệp vụ | `UUID` | Không | `—` | Mã đối tượng nghiệp vụ; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `before_hash` | Mã băm trước thay đổi | `VARCHAR(64)` | Cho phép | `—` | Mã băm trước thay đổi; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `after_hash` | Mã băm sau thay đổi | `VARCHAR(64)` | Cho phép | `—` | Mã băm sau thay đổi; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `reason` | Lý do hoặc căn cứ | `TEXT` | Cho phép | `—` | Lý do hoặc căn cứ; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `source_reference` | Căn cứ hoặc mã/số văn bản nguồn của thao tác | `VARCHAR(500)` | Cho phép | `—` | Căn cứ hoặc mã/số văn bản nguồn của thao tác; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `occurred_at` | Thời điểm sự kiện | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm sự kiện; dùng đối chiếu trình tự và audit. |
| `correlation_id` | Mã liên kết nhật ký | `UUID` | Không | `—` | Mã liên kết nhật ký; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |

**PK:** `id`.
**FK và quan hệ:** `actor_id` → `user_account.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** Không có CHECK riêng.
**Index:** `ix_audit_event_correlation_id` (audit_event.correlation_id); `ix_audit_event_occurred_id` (audit_event.occurred_at, audit_event.id); `ix_audit_event_resource_id` (audit_event.resource_id).

## 04. `defense_eligibility_check` — Lịch sử xét điều kiện dự bảo vệ

**Mục đích và lý do tồn tại:** Ba điều kiện cấp Trường theo từng sinh viên và phiên bản căn cứ. Nếu bỏ, mất dữ liệu/quan hệ riêng của lịch sử xét điều kiện dự bảo vệ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Ba điều kiện cấp Trường theo từng sinh viên và phiên bản căn cứ; `backend/services/activity.py`, `backend/services/evaluation.py`.
**Vai trò thao tác:** Chỉ actor được API/service cấp quyền theo vai trò, bộ môn/đợt/KLTN; Admin không mặc nhiên duyệt nghiệp vụ.
**Tình huống giả:** TBM đối chiếu nguồn kỷ luật và Mẫu 7 đã ký theo báo cáo hiện hành của SV DEMO; mỗi lần xét lưu căn cứ, người xét và kết quả riêng, không áp dụng cho thành viên khác.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_id` | Mã khóa luận | `UUID` | Không | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `thesis_member_id` | Mã thành viên khóa luận | `UUID` | Không | `—` | Mã thành viên khóa luận; liên kết tới `thesis_member.id`, giữ toàn vẹn tham chiếu. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `report_version_id` | Bản cuốn báo cáo được nhận xét | `UUID` | Cho phép | `—` | Bản cuốn báo cáo được nhận xét; liên kết tới `document_version.id`, giữ toàn vẹn tham chiếu. |
| `advisor_review_id` | Mẫu 7 được dùng để xét điều kiện | `UUID` | Cho phép | `—` | Mẫu 7 được dùng để xét điều kiện; liên kết tới `thesis_review.id`, giữ toàn vẹn tham chiếu. |
| `discipline_status` | Tình trạng kỷ luật đã đối chiếu | `VARCHAR(30)` | Không | `—` | Tình trạng kỷ luật đã đối chiếu; phục vụ ba điều kiện cấp trường theo từng sinh viên và phiên bản căn cứ. |
| `source_reference` | Căn cứ hoặc mã/số văn bản nguồn của thao tác | `VARCHAR(500)` | Không | `—` | Căn cứ hoặc mã/số văn bản nguồn của thao tác; phục vụ ba điều kiện cấp trường theo từng sinh viên và phiên bản căn cứ. |
| `reason` | Lý do hoặc căn cứ | `TEXT` | Không | `—` | Lý do hoặc căn cứ; phục vụ ba điều kiện cấp trường theo từng sinh viên và phiên bản căn cứ. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `—` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `checked_by` | Người xét điều kiện | `UUID` | Không | `—` | Người xét điều kiện; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `checked_at` | Thời điểm xét điều kiện | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm xét điều kiện; phục vụ ba điều kiện cấp trường theo từng sinh viên và phiên bản căn cứ. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |

**PK:** `id`.
**FK và quan hệ:** `advisor_review_id` → `thesis_review.id`; `checked_by` → `user_account.id`; `report_version_id` → `document_version.id`; `thesis_id` → `thesis.id`; `thesis_member_id` → `thesis_member.id`.
**UNIQUE:** `thesis_member_id, version_no`.
**CHECK:** `ck_defense_eligibility_check_discipline_status`: `discipline_status IN ('CLEAR','WARNING_OR_HIGHER','UNKNOWN')`; `ck_defense_eligibility_check_state`: `state IN ('ELIGIBLE','BLOCKED')`; `ck_defense_eligibility_check_version_positive`: `version_no > 0`.
**Index:** `ix_defense_eligibility_check_thesis_member` (defense_eligibility_check.thesis_id, defense_eligibility_check.thesis_member_id).

## 05. `department` — Bộ môn

**Mục đích và lý do tồn tại:** Phạm vi quyền và hồ sơ. Nếu bỏ, mất dữ liệu/quan hệ riêng của bộ môn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Phạm vi quyền và hồ sơ; `backend/api/account_admin.py`, `backend/api/lecturer_import.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/account_directory.py`, `backend/services/activity.py`, `backend/services/lecturer_profiles.py`, `backend/services/lecturer_roster.py`, `backend/services/review_form_export.py`, `backend/services/roster.py`, `backend/services/theses.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** Admin kỹ thuật quản lý dữ liệu tổ chức; quyền nghiệp vụ chỉ áp dụng cho bộ môn tương ứng.
**Tình huống giả:** Bộ môn CNTT-DEMO thuộc Khoa CNKT-DEMO.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `faculty_id` | Mã khoa | `UUID` | Không | `—` | Mã khoa; liên kết tới `faculty.id`, giữ toàn vẹn tham chiếu. |
| `code` | Mã nghiệp vụ | `VARCHAR(32)` | Không | `—` | Mã nghiệp vụ; phục vụ phạm vi quyền và hồ sơ. |
| `name` | Tên đầy đủ | `VARCHAR(255)` | Không | `—` | Tên đầy đủ; phục vụ phạm vi quyền và hồ sơ. |
| `major_code` | Mã ngành | `VARCHAR(32)` | Cho phép | `—` | Mã ngành; phục vụ phạm vi quyền và hồ sơ. |
| `active` | Còn hiệu lực | `BOOLEAN` | Không | `true` | Còn hiệu lực; phục vụ phạm vi quyền và hồ sơ. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `faculty_id` → `faculty.id`.
**UNIQUE:** `faculty_id, code`.
**CHECK:** Không có CHECK riêng.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 06. `department_major` — Ngành thuộc bộ môn

**Mục đích và lý do tồn tại:** Đối chiếu cặp mã bộ môn–ngành khi nhập sinh viên. Nếu bỏ, mất dữ liệu/quan hệ riêng của ngành thuộc bộ môn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đối chiếu cặp mã bộ môn–ngành khi nhập sinh viên; `backend/api/main.py`, `backend/api/roster.py`, `backend/services/roster.py`.
**Vai trò thao tác:** Admin kỹ thuật nạp danh mục đã đối chiếu; người nhập danh sách xem và chỉ dùng cặp mã đang hoạt động.
**Tình huống giả:** BM-KHMT chấp nhận ngành 7480101 và 7480208; mã ngành khác bị chặn khi nhập Excel.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Một bộ môn quản lý nhiều ngành; cặp mã cần quan hệ và ràng buộc riêng, không thể dùng một cột department.major_code.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `department_id` | Mã bộ môn | `UUID` | Không | `—` | Mã bộ môn; liên kết tới `department.id`, giữ toàn vẹn tham chiếu. |
| `code` | Mã ngành | `VARCHAR(32)` | Không | `—` | Mã ngành; phục vụ đối chiếu cặp mã bộ môn–ngành khi nhập sinh viên. |
| `name` | Tên ngành | `VARCHAR(255)` | Không | `—` | Tên ngành; phục vụ đối chiếu cặp mã bộ môn–ngành khi nhập sinh viên. |
| `active` | Còn hiệu lực | `BOOLEAN` | Không | `true` | Còn hiệu lực; phục vụ đối chiếu cặp mã bộ môn–ngành khi nhập sinh viên. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `department_id` → `department.id`.
**UNIQUE:** `department_id, code`.
**CHECK:** Không có CHECK riêng.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 07. `document` — Hồ sơ tài liệu KLTN

**Mục đích và lý do tồn tại:** Tài liệu và quyền truy cập. Nếu bỏ, mất dữ liệu/quan hệ riêng của hồ sơ tài liệu kltn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tài liệu và quyền truy cập; `backend/api/core.py`, `backend/services/activity.py`, `backend/services/documents.py`, `backend/services/evaluation.py`, `backend/services/progress.py`, `backend/services/proposal_export.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** SV thành viên nộp; GVHD xem/nhận xét; người ngoài phạm vi không xem.
**Tình huống giả:** Nhóm DEMO tạo hồ sơ báo cáo KLTN chỉ thành viên và GVHD được xem.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Một hồ sơ tài liệu có nhiều phiên bản; tách thông tin chung và bản nộp.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_id` | Mã khóa luận | `UUID` | Không | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `document_type` | Loại tài liệu | `VARCHAR(50)` | Không | `—` | Loại tài liệu; phục vụ tài liệu và quyền truy cập. |
| `title` | Tiêu đề | `VARCHAR(500)` | Không | `—` | Tiêu đề; phục vụ tài liệu và quyền truy cập. |
| `visibility` | Mức độ hiển thị | `VARCHAR(20)` | Không | `PRIVATE` | Mức độ hiển thị; phục vụ tài liệu và quyền truy cập. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `thesis_id` → `thesis.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_document_state`: `state IN ('DRAFT','ACTIVE','ARCHIVED','REVOKED')`; `ck_document_visibility`: `visibility IN ('PRIVATE','ASSIGNED','INTERNAL','PUBLISHED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 08. `document_deadline` — Hạn nộp tài liệu theo đợt và loại

**Mục đích và lý do tồn tại:** Khoa đặt hạn cho đề cương, kế hoạch và tài liệu hỗ trợ; giữ audit gia hạn/đóng. Nếu bỏ, mất dữ liệu/quan hệ riêng của hạn nộp tài liệu theo đợt và loại hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Khoa đặt hạn cho đề cương, kế hoạch và tài liệu hỗ trợ; giữ audit gia hạn/đóng; `backend/api/core.py`, `backend/services/activity.py`, `backend/services/deadlines.py`.
**Vai trò thao tác:** Chỉ actor được API/service cấp quyền theo vai trò, bộ môn/đợt/KLTN; Admin không mặc nhiên duyệt nghiệp vụ.
**Tình huống giả:** Khoa đặt hạn Mẫu 2 cho đợt DEMO; sau khi đóng có thể gia hạn và mở nhận lại, giữ nhãn trễ cũ.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `round_id` | Mã đợt KLTN | `UUID` | Không | `—` | Mã đợt KLTN; liên kết tới `thesis_round.id`, giữ toàn vẹn tham chiếu. |
| `document_type` | Loại tài liệu | `VARCHAR(30)` | Không | `—` | Loại tài liệu; phục vụ khoa đặt hạn cho đề cương, kế hoạch và tài liệu hỗ trợ; giữ audit gia hạn/đóng. |
| `due_at` | Hạn hoàn thành | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Hạn hoàn thành; phục vụ khoa đặt hạn cho đề cương, kế hoạch và tài liệu hỗ trợ; giữ audit gia hạn/đóng. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `OPEN` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `set_by` | Người ban hành hoặc cập nhật hạn nộp | `UUID` | Không | `—` | Người ban hành hoặc cập nhật hạn nộp; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `reason` | Lý do hoặc căn cứ | `TEXT` | Không | `—` | Lý do hoặc căn cứ; phục vụ khoa đặt hạn cho đề cương, kế hoạch và tài liệu hỗ trợ; giữ audit gia hạn/đóng. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `round_id` → `thesis_round.id`; `set_by` → `user_account.id`.
**UNIQUE:** `round_id, document_type`.
**CHECK:** `ck_document_deadline_document_type`: `document_type IN ('PROPOSAL','PLAN','REPORT','SUPPORTING')`; `ck_document_deadline_state`: `state IN ('OPEN','CLOSED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 09. `document_version` — Phiên bản tài liệu

**Mục đích và lý do tồn tại:** Nộp tài liệu bất biến. Nếu bỏ, mất dữ liệu/quan hệ riêng của phiên bản tài liệu hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Nộp tài liệu bất biến; `backend/api/account_admin.py`, `backend/services/activity.py`, `backend/services/documents.py`, `backend/services/evaluation.py`, `backend/services/progress.py`, `backend/services/progress_annotations.py`, `backend/services/proposal_export.py`, `backend/services/review_form_export.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** SV thành viên nộp bản mới; GVHD nhận xét; chỉ actor có quyền trên khóa luận được tải.
**Tình huống giả:** Lần nộp báo cáo thứ hai là v2, giữ nguyên v1 và SHA-256.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Tách khỏi document để không ghi đè bản đã nộp.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `document_id` | Mã tài liệu | `UUID` | Không | `—` | Mã tài liệu; liên kết tới `document.id`, giữ toàn vẹn tham chiếu. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `stored_file_id` | Mã tệp lưu trữ | `UUID` | Không | `—` | Mã tệp lưu trữ; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `submitted_by` | Mã người nộp | `UUID` | Không | `—` | Mã người nộp; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `submitted_at` | Thời điểm nộp | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm nộp; dùng đối chiếu trình tự và audit. |
| `due_at_at_submission` | Hạn áp dụng lúc nộp | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Hạn hiệu lực tại lúc gửi; giữ nguyên kết quả đúng hạn/trễ khi Khoa gia hạn mốc sau đó. Bản cũ trước migration chỉ được khôi phục theo hạn tại lúc chuyển đổi. |
| `content_sha256` | SHA-256 nội dung bản nộp | `VARCHAR(64)` | Không | `—` | SHA-256 nội dung bản nộp; phục vụ nộp tài liệu bất biến. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(30)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `document_id` → `document.id`; `stored_file_id` → `stored_file.id`; `submitted_by` → `student_profile.id`.
**UNIQUE:** `document_id, version_no`.
**CHECK:** `ck_document_version_state`: `state IN ('DRAFT','SUBMITTED','RESULT_AVAILABLE','REVISION_REQUESTED','ACCEPTED','FINAL','SUPERSEDED')`; `ck_document_version_version_positive`: `version_no > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 10. `eligibility_snapshot` — Kết quả điều kiện đăng ký

**Mục đích và lý do tồn tại:** Xác nhận đủ điều kiện theo đợt. Nếu bỏ, mất dữ liệu/quan hệ riêng của kết quả điều kiện đăng ký hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Xác nhận đủ điều kiện theo đợt; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/activity.py`, `backend/services/registration.py`, `backend/services/roster.py`, `backend/services/school_forms.py`.
**Vai trò thao tác:** Người Khoa được giao ELIGIBILITY_IMPORTER/VERIFIER theo đợt; SV chỉ xem kết quả của mình.
**Tình huống giả:** Khoa xác nhận SV-DEMO đủ điều kiện đợt chính theo danh sách nguồn; quyết định đặc biệt tạo snapshot v2 có số quyết định Hiệu trưởng.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Theo từng SV/đợt/phiên bản; không nhét điều kiện biến đổi vào hồ sơ SV cố định.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `student_id` | Mã sinh viên | `UUID` | Không | `—` | Mã sinh viên; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `round_id` | Mã đợt KLTN | `UUID` | Không | `—` | Mã đợt KLTN; liên kết tới `thesis_round.id`, giữ toàn vẹn tham chiếu. |
| `version` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `passed_credit_ratio` | Tỷ lệ tín chỉ đạt | `NUMERIC(5, 4)` | Cho phép | `—` | Tỷ lệ tín chỉ đạt; phục vụ xác nhận đủ điều kiện theo đợt. |
| `gpa_4` | Điểm trung bình hệ 4 | `NUMERIC(3, 2)` | Cho phép | `—` | Điểm trung bình hệ 4; phục vụ xác nhận đủ điều kiện theo đợt. |
| `evidence_ref` | Tham chiếu nguồn điều kiện | `VARCHAR(500)` | Không | `—` | Tham chiếu nguồn điều kiện; phục vụ xác nhận đủ điều kiện theo đợt. |
| `captured_at` | Thời điểm ghi nhận nguồn | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm ghi nhận nguồn; phục vụ xác nhận đủ điều kiện theo đợt. |
| `confirmed_by` | Mã người xác nhận | `UUID` | Cho phép | `—` | Mã người xác nhận; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `confirmed_at` | Thời điểm xác nhận | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm xác nhận; dùng đối chiếu trình tự và audit. |
| `decision_reason` | Lý do quyết định | `TEXT` | Cho phép | `—` | Lý do quyết định; phục vụ xác nhận đủ điều kiện theo đợt. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `confirmed_by` → `user_account.id`; `round_id` → `thesis_round.id`; `student_id` → `student_profile.id`.
**UNIQUE:** `student_id, round_id, version`.
**CHECK:** `ck_eligibility_snapshot_credit_ratio`: `passed_credit_ratio >= 0 AND passed_credit_ratio <= 1`; `ck_eligibility_snapshot_decision_metadata`: `state NOT IN ('CONFIRMED','REJECTED') OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)`; `ck_eligibility_snapshot_gpa`: `gpa_4 >= 0 AND gpa_4 <= 4`; `ck_eligibility_snapshot_state`: `state IN ('DRAFT','SUBMITTED','CONFIRMED','REJECTED')`; `ck_eligibility_snapshot_version_positive`: `version > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 11. `faculty` — Khoa

**Mục đích và lý do tồn tại:** Cấp trên của bộ môn và phạm vi Trưởng khoa. Nếu bỏ, mất dữ liệu/quan hệ riêng của khoa hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Cấp trên của bộ môn và phạm vi Trưởng khoa; `backend/api/main.py`, `backend/services/account_directory.py`, `backend/services/lecturer_profiles.py`, `backend/services/review_form_export.py`.
**Vai trò thao tác:** Admin kỹ thuật quản lý dữ liệu Khoa; Trưởng khoa chỉ có quyền theo phân công chức vụ còn hiệu lực.
**Tình huống giả:** Khoa CNKT-DEMO quản lý Bộ môn CNTT-DEMO.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `code` | Mã nghiệp vụ | `VARCHAR(32)` | Không | `—` | Mã nghiệp vụ; phục vụ cấp trên của bộ môn và phạm vi trưởng khoa. |
| `name` | Tên đầy đủ | `VARCHAR(255)` | Không | `—` | Tên đầy đủ; phục vụ cấp trên của bộ môn và phạm vi trưởng khoa. |
| `active` | Còn hiệu lực | `BOOLEAN` | Không | `true` | Còn hiệu lực; phục vụ cấp trên của bộ môn và phạm vi trưởng khoa. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** Không có FK.
**UNIQUE:** `code`.
**CHECK:** Không có CHECK riêng.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 12. `lecturer_profile` — Hồ sơ giảng viên

**Mục đích và lý do tồn tại:** Đề xuất, tiếp nhận, hướng dẫn và xét duyệt. Nếu bỏ, mất dữ liệu/quan hệ riêng của hồ sơ giảng viên hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đề xuất, tiếp nhận, hướng dẫn và xét duyệt; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/core.py`, `backend/api/lecturer_import.py`, `backend/api/main.py`, `backend/services/account_directory.py`, `backend/services/activity.py`, `backend/services/documents.py`, `backend/services/evaluation.py`, `backend/services/lecturer_profiles.py`, `backend/services/lecturer_roster.py`, `backend/services/notifications.py`, `backend/services/progress.py`, `backend/services/progress_annotations.py`, `backend/services/proposal_export.py`, `backend/services/proposals.py`, `backend/services/registration.py`, `backend/services/registration_forms.py`, `backend/services/review_form_export.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/topics.py`, `backend/services/withdrawals.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** GV xem/cập nhật hồ sơ của mình theo API; Admin quản lý tài khoản, không thay GV duyệt đề tài.
**Tình huống giả:** GV-DEMO có tài khoản riêng và thuộc Bộ môn CNTT-DEMO.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `user_id` | Mã tài khoản | `UUID` | Không | `—` | Mã tài khoản; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `lecturer_code` | Mã giảng viên | `VARCHAR(32)` | Không | `—` | Mã giảng viên; phục vụ đề xuất, tiếp nhận, hướng dẫn và xét duyệt. |
| `department_id` | Mã bộ môn | `UUID` | Không | `—` | Mã bộ môn; liên kết tới `department.id`, giữ toàn vẹn tham chiếu. |
| `display_name` | Họ tên hiển thị | `VARCHAR(255)` | Không | `—` | Họ tên hiển thị; phục vụ đề xuất, tiếp nhận, hướng dẫn và xét duyệt. |
| `profile_data` | Thông tin chuyên môn và liên hệ đã duyệt | `JSONB` | Không | `'{}'::jsonb` | Thông tin chuyên môn và liên hệ đã duyệt; phục vụ đề xuất, tiếp nhận, hướng dẫn và xét duyệt. |
| `avatar_file_id` | Ảnh đại diện đã chuẩn hóa và quét | `UUID` | Cho phép | `—` | Ảnh đại diện đã chuẩn hóa và quét; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `profile_verified_at` | Thời điểm duyệt hồ sơ | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm duyệt hồ sơ; phục vụ đề xuất, tiếp nhận, hướng dẫn và xét duyệt. |
| `profile_verified_by` | Người duyệt hồ sơ | `UUID` | Cho phép | `—` | Người duyệt hồ sơ; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `avatar_file_id` → `stored_file.id`; `department_id` → `department.id`; `profile_verified_by` → `user_account.id`; `user_id` → `user_account.id`.
**UNIQUE:** `lecturer_code`; `user_id`.
**CHECK:** `ck_lecturer_profile_profile_data_object`: `jsonb_typeof(profile_data) = 'object'`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 13. `lecturer_profile_change` — Yêu cầu cập nhật hồ sơ giảng viên

**Mục đích và lý do tồn tại:** Nháp riêng, gửi TBM duyệt, công bố và lịch sử xử lý theo phiên bản. Nếu bỏ, mất dữ liệu/quan hệ riêng của yêu cầu cập nhật hồ sơ giảng viên hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Nháp riêng, gửi TBM duyệt, công bố và lịch sử xử lý theo phiên bản; `backend/services/activity.py`, `backend/services/lecturer_profiles.py`.
**Vai trò thao tác:** Chỉ actor được API/service cấp quyền theo vai trò, bộ môn/đợt/KLTN; Admin không mặc nhiên duyệt nghiệp vụ.
**Tình huống giả:** GV DEMO gửi cập nhật học vị, chuyên môn và ảnh; TBM đối chiếu trước–sau, duyệt rồi mới công bố. Phiếu trả lại được lập bản mới để sửa, không xóa lịch sử.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `lecturer_id` | Mã giảng viên | `UUID` | Không | `—` | Mã giảng viên; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `base_profile_version` | Phiên bản hồ sơ gốc khi lập yêu cầu | `INTEGER` | Không | `—` | Phiên bản hồ sơ gốc khi lập yêu cầu; phục vụ nháp riêng, gửi tbm duyệt, công bố và lịch sử xử lý theo phiên bản. |
| `proposed_data` | Thông tin đề nghị cập nhật | `JSONB` | Không | `—` | Thông tin đề nghị cập nhật; phục vụ nháp riêng, gửi tbm duyệt, công bố và lịch sử xử lý theo phiên bản. |
| `original_data` | Thông tin trước cập nhật | `JSONB` | Không | `—` | Thông tin trước cập nhật; phục vụ nháp riêng, gửi tbm duyệt, công bố và lịch sử xử lý theo phiên bản. |
| `avatar_file_id` | Ảnh đại diện đã chuẩn hóa và quét | `UUID` | Cho phép | `—` | Ảnh đại diện đã chuẩn hóa và quét; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `original_avatar_file_id` | Ảnh trước cập nhật | `UUID` | Cho phép | `—` | Ảnh trước cập nhật; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `submission_note` | Nội dung đề nghị và căn cứ | `TEXT` | Cho phép | `—` | Nội dung đề nghị và căn cứ; phục vụ nháp riêng, gửi tbm duyệt, công bố và lịch sử xử lý theo phiên bản. |
| `submitted_at` | Thời điểm nộp | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm nộp; dùng đối chiếu trình tự và audit. |
| `reviewed_by` | Mã người nhận xét | `UUID` | Cho phép | `—` | Mã người nhận xét; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `reviewed_at` | Thời điểm nhận xét | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm nhận xét; phục vụ nháp riêng, gửi tbm duyệt, công bố và lịch sử xử lý theo phiên bản. |
| `decision_reason` | Lý do quyết định | `TEXT` | Cho phép | `—` | Lý do quyết định; phục vụ nháp riêng, gửi tbm duyệt, công bố và lịch sử xử lý theo phiên bản. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `avatar_file_id` → `stored_file.id`; `lecturer_id` → `lecturer_profile.id`; `original_avatar_file_id` → `stored_file.id`; `reviewed_by` → `user_account.id`.
**UNIQUE:** `lecturer_id, version_no`.
**CHECK:** `ck_lecturer_profile_change_data_objects`: `jsonb_typeof(proposed_data) = 'object' AND jsonb_typeof(original_data) = 'object'`; `ck_lecturer_profile_change_decision_recorded`: `state NOT IN ('APPROVED','RETURNED') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND decision_reason IS NOT NULL)`; `ck_lecturer_profile_change_state`: `state IN ('DRAFT','SUBMITTED','APPROVED','RETURNED','WITHDRAWN')`; `ck_lecturer_profile_change_submitted_timestamp`: `state NOT IN ('SUBMITTED','APPROVED','RETURNED') OR submitted_at IS NOT NULL`; `ck_lecturer_profile_change_version_positive`: `version_no > 0 AND base_profile_version > 0`.
**Index:** `ix_lecturer_profile_change_state_created` (lecturer_profile_change.state, lecturer_profile_change.created_at); `uq_lecturer_profile_change_open` (lecturer_profile_change.lecturer_id) UNIQUE.

## 14. `member_work_assignment` — Phân công việc thành viên

**Mục đích và lý do tồn tại:** Tiến độ cá nhân và nhận xét GVHD. Nếu bỏ, mất dữ liệu/quan hệ riêng của phân công việc thành viên hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tiến độ cá nhân và nhận xét GVHD; `backend/api/core.py`, `backend/services/progress.py`.
**Vai trò thao tác:** SV/nhóm ghi phần việc theo khóa luận; GVHD nhận xét đúng phạm vi.
**Tình huống giả:** SV-DEMO nộp phần việc làm API v1, GVHD yêu cầu sửa và SV nộp v2.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Phần việc riêng từng SV có phiên bản/nhận xét, không phải nội dung chung của KLTN.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_member_id` | Mã thành viên khóa luận | `UUID` | Không | `—` | Mã thành viên khóa luận; liên kết tới `thesis_member.id`, giữ toàn vẹn tham chiếu. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `work_description` | Công việc được giao | `TEXT` | Không | `—` | Công việc được giao; phục vụ tiến độ cá nhân và nhận xét gvhd. |
| `expected_output` | Sản phẩm dự kiến | `TEXT` | Không | `—` | Sản phẩm dự kiến; phục vụ tiến độ cá nhân và nhận xét gvhd. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(30)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `reviewed_by` | Mã người nhận xét | `UUID` | Cho phép | `—` | Mã người nhận xét; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `reviewed_at` | Thời điểm nhận xét | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm nhận xét; phục vụ tiến độ cá nhân và nhận xét gvhd. |
| `review_comment` | Nhận xét xét duyệt | `TEXT` | Cho phép | `—` | Nhận xét xét duyệt; phục vụ tiến độ cá nhân và nhận xét gvhd. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `reviewed_by` → `lecturer_profile.id`; `thesis_member_id` → `thesis_member.id`.
**UNIQUE:** `thesis_member_id, version_no`.
**CHECK:** `ck_member_work_assignment_state`: `state IN ('DRAFT','SUBMITTED','APPROVED','REVISION_REQUIRED')`; `ck_member_work_assignment_version_positive`: `version_no > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 15. `official_form` — Danh mục biểu mẫu và tài liệu Khoa theo đợt

**Mục đích và lý do tồn tại:** Phân loại, phạm vi và đối tượng xem tài liệu Khoa. Nếu bỏ, mất dữ liệu/quan hệ riêng của danh mục biểu mẫu và tài liệu khoa theo đợt hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Phân loại, phạm vi và đối tượng xem tài liệu Khoa; `backend/services/activity.py`, `backend/services/school_forms.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** FORM_MANAGER được cấp rõ theo đợt mới quản lý. Admin không tự có quyền phát hành; SV/GV xem theo đối tượng và phạm vi đợt.
**Tình huống giả:** Khoa tạo danh mục Mẫu 2 của đợt DEMO; Mẫu 4 trắng và danh sách SV đã chốt nằm ở hai danh mục khác nhau.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Danh mục có mã, đợt, loại tài liệu và đối tượng xem ổn định; không lặp danh mục trong từng tệp hay nhầm tài liệu Khoa với bài SV nộp.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `round_id` | Mã đợt KLTN | `UUID` | Không | `—` | Mã đợt KLTN; liên kết tới `thesis_round.id`, giữ toàn vẹn tham chiếu. |
| `code` | Mã nghiệp vụ | `VARCHAR(50)` | Không | `—` | Mã nghiệp vụ; phục vụ phân loại, phạm vi và đối tượng xem tài liệu khoa. |
| `title` | Tiêu đề | `VARCHAR(255)` | Không | `—` | Tiêu đề; phục vụ phân loại, phạm vi và đối tượng xem tài liệu khoa. |
| `document_kind` | Phân loại biểu mẫu trắng hoặc tài liệu công bố | `VARCHAR(20)` | Không | `—` | Phân loại biểu mẫu trắng hoặc tài liệu công bố; phục vụ phân loại, phạm vi và đối tượng xem tài liệu khoa. |
| `audience` | Đối tượng được xem | `VARCHAR(30)` | Không | `—` | Đối tượng được xem; phục vụ phân loại, phạm vi và đối tượng xem tài liệu khoa. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `ACTIVE` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `created_by` | Mã người tạo | `UUID` | Không | `—` | Mã người tạo; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `created_by` → `user_account.id`; `round_id` → `thesis_round.id`.
**UNIQUE:** `round_id, code`.
**CHECK:** `ck_official_form_audience`: `audience IN ('STUDENT_AND_LECTURER','LECTURER')`; `ck_official_form_document_kind`: `document_kind IN ('FORM','PUBLICATION')`; `ck_official_form_state`: `state IN ('ACTIVE','ARCHIVED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 16. `official_form_version` — Phiên bản tệp biểu mẫu và tài liệu Khoa

**Mục đích và lý do tồn tại:** Bản nháp, phát hành, thu hồi và lịch sử tệp đã quét. Nếu bỏ, mất dữ liệu/quan hệ riêng của phiên bản tệp biểu mẫu và tài liệu khoa hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Bản nháp, phát hành, thu hồi và lịch sử tệp đã quét; `backend/services/school_forms.py`.
**Vai trò thao tác:** FORM_MANAGER theo đợt tải/kiểm/phát hành/thu hồi. SV/GV chỉ xem bản đã phát hành và lịch sử hợp lệ, không xem nháp hoặc danh sách ngoài đợt.
**Tình huống giả:** Cán bộ được giao FORM_MANAGER nộp bản Mẫu 2 v2, quét sạch rồi phát hành; v1 giữ trong lịch sử. Danh sách XLSX đã chốt chỉ SV/GV của đúng đợt đọc được.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Một danh mục có nhiều tệp bất biến và vòng đời nháp/phát hành/thu hồi riêng. stored_file chỉ lưu bytes/checksum/scan; không thay thế lịch sử phát hành nghiệp vụ.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `official_form_id` | Mã danh mục biểu mẫu/tài liệu Khoa | `UUID` | Không | `—` | Mã danh mục biểu mẫu/tài liệu Khoa; liên kết tới `official_form.id`, giữ toàn vẹn tham chiếu. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `stored_file_id` | Mã tệp lưu trữ | `UUID` | Không | `—` | Mã tệp lưu trữ; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `uploaded_by` | Tài khoản tải tệp lên | `UUID` | Không | `—` | Tài khoản tải tệp lên; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `source_reference` | Căn cứ hoặc mã/số văn bản nguồn của thao tác | `VARCHAR(500)` | Không | `—` | Căn cứ hoặc mã/số văn bản nguồn của thao tác; phục vụ bản nháp, phát hành, thu hồi và lịch sử tệp đã quét. |
| `change_reason` | Lý do đổi tên | `TEXT` | Không | `—` | Lý do đổi tên; phục vụ bản nháp, phát hành, thu hồi và lịch sử tệp đã quét. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `published_by` | Tài khoản phát hành | `UUID` | Cho phép | `—` | Tài khoản phát hành; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `published_at` | Thời điểm gửi ghim cho nhóm sinh viên | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm gửi ghim cho nhóm sinh viên; phục vụ bản nháp, phát hành, thu hồi và lịch sử tệp đã quét. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `official_form_id` → `official_form.id`; `published_by` → `user_account.id`; `stored_file_id` → `stored_file.id`; `uploaded_by` → `user_account.id`.
**UNIQUE:** `official_form_id, version_no`.
**CHECK:** `ck_official_form_version_draft_stamp`: `state != 'DRAFT' OR published_at IS NULL`; `ck_official_form_version_published_stamp`: `state NOT IN ('PUBLISHED','SUPERSEDED') OR published_at IS NOT NULL`; `ck_official_form_version_publisher_pair`: `(published_at IS NULL) = (published_by IS NULL)`; `ck_official_form_version_state`: `state IN ('DRAFT','PUBLISHED','SUPERSEDED','WITHDRAWN')`; `ck_official_form_version_version_positive`: `version_no > 0`.
**Index:** `uq_official_form_current` (official_form_version.official_form_id) UNIQUE.

## 17. `organizational_position` — Chức vụ tổ chức

**Mục đích và lý do tồn tại:** Quyền Trưởng bộ môn/Trưởng khoa. Nếu bỏ, mất dữ liệu/quan hệ riêng của chức vụ tổ chức hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Quyền Trưởng bộ môn/Trưởng khoa; `backend/services/account_directory.py`, `backend/services/lecturer_profiles.py`, `backend/services/notifications.py`, `backend/services/registration.py`, `backend/services/theses.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** Admin kỹ thuật quản lý mã chức vụ; chỉ phân công position_assignment có hiệu lực mới cấp quyền nghiệp vụ.
**Tình huống giả:** Mã DEPARTMENT_HEAD đại diện chức vụ Trưởng bộ môn.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `code` | Mã nghiệp vụ | `VARCHAR(40)` | Không | `—` | Mã nghiệp vụ; phục vụ quyền trưởng bộ môn/trưởng khoa. |
| `name` | Tên đầy đủ | `VARCHAR(255)` | Không | `—` | Tên đầy đủ; phục vụ quyền trưởng bộ môn/trưởng khoa. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** Không có FK.
**UNIQUE:** `code`.
**CHECK:** `ck_organizational_position_code`: `code IN ('DEPARTMENT_HEAD','FACULTY_DEAN')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 18. `position_assignment` — Phân công chức vụ

**Mục đích và lý do tồn tại:** Quyền theo bộ môn/khoa và thời gian. Nếu bỏ, mất dữ liệu/quan hệ riêng của phân công chức vụ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Quyền theo bộ môn/khoa và thời gian; `backend/services/account_directory.py`, `backend/services/lecturer_profiles.py`, `backend/services/notifications.py`, `backend/services/registration.py`, `backend/services/theses.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** Admin quản trị phân công có căn cứ; Trưởng bộ môn/Trưởng khoa thực thi quyền trong phạm vi hiệu lực.
**Tình huống giả:** GV-DEMO được phân công Trưởng bộ môn CNTT-DEMO trong một khoảng hiệu lực.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Chức vụ tổ chức theo khoa/bộ môn khác quyền nghiệp vụ theo đợt/KLTN của resource_assignment.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `lecturer_id` | Mã giảng viên | `UUID` | Không | `—` | Mã giảng viên; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `position_id` | Mã chức vụ | `UUID` | Không | `—` | Mã chức vụ; liên kết tới `organizational_position.id`, giữ toàn vẹn tham chiếu. |
| `faculty_id` | Mã khoa | `UUID` | Cho phép | `—` | Mã khoa; liên kết tới `faculty.id`, giữ toàn vẹn tham chiếu. |
| `department_id` | Mã bộ môn | `UUID` | Cho phép | `—` | Mã bộ môn; liên kết tới `department.id`, giữ toàn vẹn tham chiếu. |
| `effective_from` | Bắt đầu hiệu lực | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Bắt đầu hiệu lực; phục vụ quyền theo bộ môn/khoa và thời gian. |
| `effective_to` | Kết thúc hiệu lực | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Kết thúc hiệu lực; phục vụ quyền theo bộ môn/khoa và thời gian. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `ACTIVE` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `department_id` → `department.id`; `faculty_id` → `faculty.id`; `lecturer_id` → `lecturer_profile.id`; `position_id` → `organizational_position.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_position_assignment_effective_window`: `effective_to IS NULL OR effective_to > effective_from`; `ck_position_assignment_exactly_one_scope`: `(faculty_id IS NOT NULL AND department_id IS NULL) OR (faculty_id IS NULL AND department_id IS NOT NULL)`; `ck_position_assignment_state`: `state IN ('ACTIVE','REVOKED','EXPIRED')`.
**Index:** `uq_position_assignment_department_scope` (position_assignment.lecturer_id, position_assignment.position_id, position_assignment.department_id) UNIQUE; `uq_position_assignment_faculty_scope` (position_assignment.lecturer_id, position_assignment.position_id, position_assignment.faculty_id) UNIQUE.

## 19. `progress_milestone` — Mốc tiến độ

**Mục đích và lý do tồn tại:** Lịch theo đợt KLTN. Nếu bỏ, mất dữ liệu/quan hệ riêng của mốc tiến độ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Lịch theo đợt KLTN; `backend/services/progress.py`.
**Vai trò thao tác:** Người điều phối KLTN được giao theo đợt quản lý mốc; SV/GV xem mốc khóa luận liên quan.
**Tình huống giả:** Đợt DEMO mở mốc báo cáo lần 2 với hạn theo kế hoạch Khoa đã duyệt.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `round_id` | Mã đợt KLTN | `UUID` | Không | `—` | Mã đợt KLTN; liên kết tới `thesis_round.id`, giữ toàn vẹn tham chiếu. |
| `code` | Mã nghiệp vụ | `VARCHAR(50)` | Không | `—` | Mã nghiệp vụ; phục vụ lịch theo đợt kltn. |
| `title` | Tiêu đề | `VARCHAR(255)` | Không | `—` | Tiêu đề; phục vụ lịch theo đợt kltn. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `due_at` | Hạn hoàn thành | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Hạn hoàn thành; phục vụ lịch theo đợt kltn. |
| `expected_ratio` | Tỷ lệ tiến độ dự kiến | `NUMERIC(5, 2)` | Cho phép | `—` | Tỷ lệ tiến độ dự kiến; phục vụ lịch theo đợt kltn. |
| `source_type` | Loại nguồn mốc | `VARCHAR(20)` | Không | `—` | Loại nguồn mốc; phục vụ lịch theo đợt kltn. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `round_id` → `thesis_round.id`.
**UNIQUE:** `round_id, code, version_no`.
**CHECK:** `ck_progress_milestone_expected_ratio`: `expected_ratio IS NULL OR (expected_ratio >= 0 AND expected_ratio <= 100)`; `ck_progress_milestone_source_type`: `source_type IN ('ROUND_POLICY','STUDENT_PLAN')`; `ck_progress_milestone_state`: `state IN ('DRAFT','OPEN','CLOSED','CANCELLED')`; `ck_progress_milestone_version_positive`: `version_no > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 20. `progress_report` — Báo cáo tiến độ

**Mục đích và lý do tồn tại:** Bản nộp theo phiên bản. Nếu bỏ, mất dữ liệu/quan hệ riêng của báo cáo tiến độ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Bản nộp theo phiên bản; `backend/api/account_admin.py`, `backend/api/core.py`, `backend/services/activity.py`, `backend/services/documents.py`, `backend/services/progress.py`, `backend/services/progress_annotations.py`.
**Vai trò thao tác:** SV trong nhóm nộp và xem; chỉ GVHD đúng đề tài nhận xét/xác nhận. TBM quản lý mốc chung không đọc nội dung tiến độ.
**Tình huống giả:** Nhóm DEMO nộp báo cáo mốc lần 2 v1; sửa thành v2 sau góp ý.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Mỗi mốc có nhiều bản nộp; cần lịch sử và trạng thái riêng.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_id` | Mã khóa luận | `UUID` | Không | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `milestone_id` | Mã mốc tiến độ | `UUID` | Không | `—` | Mã mốc tiến độ; liên kết tới `progress_milestone.id`, giữ toàn vẹn tham chiếu. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `summary` | Tóm tắt tiến độ | `TEXT` | Không | `—` | Tóm tắt tiến độ; phục vụ bản nộp theo phiên bản. |
| `reported_ratio` | Tỷ lệ tiến độ báo cáo | `NUMERIC(5, 2)` | Cho phép | `—` | Tỷ lệ tiến độ báo cáo; phục vụ bản nộp theo phiên bản. |
| `evidence_file_id` | Mã tệp minh chứng | `UUID` | Cho phép | `—` | Mã tệp minh chứng; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `due_at_at_submission` | Hạn áp dụng lúc nộp | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Hạn hiệu lực tại lúc gửi; giữ nguyên kết quả đúng hạn/trễ khi Khoa gia hạn mốc sau đó. Bản cũ trước migration chỉ được khôi phục theo hạn tại lúc chuyển đổi. |
| `submitted_by` | Mã người nộp | `UUID` | Không | `—` | Mã người nộp; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(30)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `evidence_file_id` → `stored_file.id`; `milestone_id` → `progress_milestone.id`; `submitted_by` → `student_profile.id`; `thesis_id` → `thesis.id`.
**UNIQUE:** `thesis_id, milestone_id, version_no`.
**CHECK:** `ck_progress_report_reported_ratio`: `reported_ratio IS NULL OR (reported_ratio >= 0 AND reported_ratio <= 100)`; `ck_progress_report_state`: `state IN ('DRAFT','SUBMITTED','CONFIRMED','REVISION_REQUIRED')`; `ck_progress_report_version_positive`: `version_no > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 21. `progress_review` — Nhận xét tiến độ

**Mục đích và lý do tồn tại:** GVHD xác nhận, GV khác chỉ góp ý. Nếu bỏ, mất dữ liệu/quan hệ riêng của nhận xét tiến độ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** GVHD xác nhận, GV khác chỉ góp ý; `backend/services/progress.py`, `backend/services/progress_annotations.py`.
**Vai trò thao tác:** Chỉ GVHD chính nhận xét và xác nhận/yêu cầu sửa báo cáo tiến độ của nhóm mình.
**Tình huống giả:** GVHD ghi nhận xét và CONFIRM hoặc yêu cầu sửa đúng lần nộp; COMMENT_ONLY còn trong ràng buộc để bảo toàn lịch sử cũ, không cấp quyền góp ý chéo tiến độ mới.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Có thể có nhiều người nhận xét cùng báo cáo; COMMENT_ONLY khác quyền GVHD xác nhận.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `progress_report_id` | Mã báo cáo tiến độ | `UUID` | Không | `—` | Mã báo cáo tiến độ; liên kết tới `progress_report.id`, giữ toàn vẹn tham chiếu. |
| `reviewer_id` | Mã GV nhận xét | `UUID` | Không | `—` | Mã GV nhận xét; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `decision` | Quyết định | `VARCHAR(30)` | Không | `—` | Quyết định; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `comment` | Nội dung nhận xét | `TEXT` | Không | `—` | Nội dung nhận xét; phục vụ gvhd xác nhận, gv khác chỉ góp ý. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `progress_report_id` → `progress_report.id`; `reviewer_id` → `lecturer_profile.id`.
**UNIQUE:** `progress_report_id, reviewer_id`.
**CHECK:** `ck_progress_review_decision`: `decision IN ('COMMENT_ONLY','CONFIRM','REVISION_REQUIRED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 22. `progress_review_annotation` — Ghim nhận xét theo phiên bản tệp

**Mục đích và lý do tồn tại:** Ghim, nhận xét chung và tệp GV phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. Nếu bỏ, mất dữ liệu/quan hệ riêng của ghim nhận xét theo phiên bản tệp hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Ghim, nhận xét chung và tệp GV phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi; `backend/services/progress_annotations.py`.
**Vai trò thao tác:** GVHD/người góp ý được phân công tự lưu và sửa ghim nháp riêng trên bản hiện hành. Chỉ sau khi gửi kết quả, SV thành viên và người có quyền xem tài nguyên tương ứng mới thấy ghim. Không mở rộng quyền xác nhận cho người góp ý chéo.
**Tình huống giả:** GVHD ghim góp ý ở trang 2 của minh chứng lần nộp 1, tự lưu nháp riêng; khi yêu cầu sửa, SV xem đúng ghim của v1 rồi nộp v2 mà ghim không bị dịch sang tệp mới.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Một kết quả phản hồi có nhiều vị trí cần sửa. Mỗi ghim liên kết đúng một bản tiến độ, tài liệu hoặc đề cương (CHECK one_target), cùng tệp bất biến. Loại PIN lưu vị trí, SUMMARY lưu nhận xét chung riêng của từng GV, ATTACHMENT liên kết một tệp phản hồi riêng đã quét trong stored_file. CHECK ràng buộc đúng loại; partial UNIQUE giới hạn một SUMMARY cho mỗi GV/phiên bản. Nháp riêng và góp ý đã gửi có vòng đời khác quyết định duyệt; không gộp danh sách một-nhiều vào JSON/text.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `progress_report_id` | Mã báo cáo tiến độ | `UUID` | Cho phép | `—` | Mã báo cáo tiến độ; liên kết tới `progress_report.id`, giữ toàn vẹn tham chiếu. |
| `document_version_id` | Mã phiên bản tài liệu | `UUID` | Cho phép | `—` | Mã phiên bản tài liệu; liên kết tới `document_version.id`, giữ toàn vẹn tham chiếu. |
| `proposal_version_id` | Mã phiên bản đề cương | `UUID` | Cho phép | `—` | Mã phiên bản đề cương; liên kết tới `proposal_version.id`, giữ toàn vẹn tham chiếu. |
| `reviewer_id` | Mã GV nhận xét | `UUID` | Không | `—` | Mã GV nhận xét; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `stored_file_id` | Mã tệp lưu trữ | `UUID` | Không | `—` | Mã tệp lưu trữ; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `annotation_kind` | Loại nội dung phản hồi | `VARCHAR(20)` | Không | `PIN` | Loại nội dung phản hồi; phục vụ ghim, nhận xét chung và tệp gv phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. |
| `attachment_file_id` | Mã tệp giảng viên đính kèm | `UUID` | Cho phép | `—` | Mã tệp giảng viên đính kèm; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `page_number` | Số trang của tệp PDF | `INTEGER` | Cho phép | `—` | Số trang của tệp PDF; phục vụ ghim, nhận xét chung và tệp gv phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. |
| `x` | Tọa độ ngang chuẩn hóa từ 0 đến 1 | `NUMERIC(8, 7)` | Cho phép | `—` | Tọa độ ngang chuẩn hóa từ 0 đến 1; phục vụ ghim, nhận xét chung và tệp gv phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. |
| `y` | Tọa độ dọc chuẩn hóa từ 0 đến 1 | `NUMERIC(8, 7)` | Cho phép | `—` | Tọa độ dọc chuẩn hóa từ 0 đến 1; phục vụ ghim, nhận xét chung và tệp gv phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. |
| `location_label` | Tiêu đề mục hoặc mô tả vị trí cần sửa | `VARCHAR(255)` | Không | `` | Tiêu đề mục hoặc mô tả vị trí cần sửa; phục vụ ghim, nhận xét chung và tệp gv phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. |
| `quoted_text` | Đoạn trích được nhận xét | `VARCHAR(1000)` | Không | `` | Đoạn trích được nhận xét; phục vụ ghim, nhận xét chung và tệp gv phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. |
| `comment` | Nội dung nhận xét | `TEXT` | Không | `` | Nội dung nhận xét; phục vụ ghim, nhận xét chung và tệp gv phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `published_at` | Thời điểm gửi ghim cho nhóm sinh viên | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm gửi ghim cho nhóm sinh viên; phục vụ ghim, nhận xét chung và tệp gv phản hồi; nháp riêng theo đúng phiên bản, chỉ công bố cùng quyết định phản hồi. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `attachment_file_id` → `stored_file.id`; `document_version_id` → `document_version.id`; `progress_report_id` → `progress_report.id`; `proposal_version_id` → `proposal_version.id`; `reviewer_id` → `lecturer_profile.id`; `stored_file_id` → `stored_file.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_progress_review_annotation_annotation_kind`: `annotation_kind IN ('PIN','SUMMARY','ATTACHMENT')`; `ck_progress_review_annotation_attachment_kind`: `(annotation_kind = 'ATTACHMENT' AND attachment_file_id IS NOT NULL) OR (annotation_kind IN ('PIN','SUMMARY') AND attachment_file_id IS NULL)`; `ck_progress_review_annotation_coordinates`: `(x IS NULL AND y IS NULL) OR (page_number IS NOT NULL AND x IS NOT NULL AND y IS NOT NULL AND x BETWEEN 0 AND 1 AND y BETWEEN 0 AND 1)`; `ck_progress_review_annotation_kind_coordinates`: `annotation_kind = 'PIN' OR (page_number IS NULL AND x IS NULL AND y IS NULL)`; `ck_progress_review_annotation_one_target`: `num_nonnulls(progress_report_id, document_version_id, proposal_version_id) = 1`; `ck_progress_review_annotation_page_number`: `page_number IS NULL OR page_number BETWEEN 1 AND 10000`; `ck_progress_review_annotation_publication`: `(state = 'DRAFT' AND published_at IS NULL) OR (state = 'PUBLISHED' AND published_at IS NOT NULL AND length(trim(comment)) > 0)`; `ck_progress_review_annotation_state`: `state IN ('DRAFT','PUBLISHED')`.
**Index:** `ix_progress_review_annotation_document_reviewer` (progress_review_annotation.document_version_id, progress_review_annotation.reviewer_id, progress_review_annotation.state); `ix_progress_review_annotation_proposal_reviewer` (progress_review_annotation.proposal_version_id, progress_review_annotation.reviewer_id, progress_review_annotation.state); `ix_progress_review_annotation_report_reviewer` (progress_review_annotation.progress_report_id, progress_review_annotation.reviewer_id, progress_review_annotation.state); `uq_review_summary_document` (progress_review_annotation.document_version_id, progress_review_annotation.reviewer_id) UNIQUE; `uq_review_summary_progress` (progress_review_annotation.progress_report_id, progress_review_annotation.reviewer_id) UNIQUE; `uq_review_summary_proposal` (progress_review_annotation.proposal_version_id, progress_review_annotation.reviewer_id) UNIQUE.

## 23. `proposal` — Hồ sơ đề cương

**Mục đích và lý do tồn tại:** Trạng thái xét duyệt đề cương. Nếu bỏ, mất dữ liệu/quan hệ riêng của hồ sơ đề cương hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Trạng thái xét duyệt đề cương; `backend/services/activity.py`, `backend/services/membership_revision.py`, `backend/services/progress_annotations.py`, `backend/services/proposal_export.py`, `backend/services/proposals.py`, `backend/services/theses.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** SV thành viên nộp; GVHD xác nhận; GV được giao góp ý; TBM chốt; Trưởng khoa ghi bản ký.
**Tình huống giả:** Khóa luận DEMO có một hồ sơ đề cương đang chờ GVHD xác nhận.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Đề cương có chu trình xét duyệt riêng; không dùng document chung để giả xác nhận học thuật.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_id` | Mã khóa luận | `UUID` | Không | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `current_version_no` | Số phiên bản hiện hành | `INTEGER` | Cho phép | `—` | Số phiên bản hiện hành; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(40)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `thesis_id` → `thesis.id`.
**UNIQUE:** `thesis_id`.
**CHECK:** `ck_proposal_state`: `state IN ('DRAFT','SUBMITTED','UNDER_REVIEW','REVISION_REQUIRED','ADVISOR_CONFIRMED','DEPARTMENT_FINALIZED','DEAN_CONFIRMED','PRINT_READY')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 24. `proposal_review` — Nhận xét đề cương

**Mục đích và lý do tồn tại:** Ý kiến GVHD và người được giao góp ý. Nếu bỏ, mất dữ liệu/quan hệ riêng của nhận xét đề cương hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Ý kiến GVHD và người được giao góp ý; `backend/services/progress_annotations.py`, `backend/services/proposals.py`.
**Vai trò thao tác:** GVHD chính xác nhận hoặc yêu cầu sửa; GV được TBM giao chỉ COMMENT; SV thành viên xem.
**Tình huống giả:** GVHD nhận xét đề cương v1 cần sửa; GV khác chỉ góp ý.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Nhận xét theo đúng phiên bản đề cương và phân công; khác nhận xét tiến độ.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `proposal_version_id` | Mã phiên bản đề cương | `UUID` | Không | `—` | Mã phiên bản đề cương; liên kết tới `proposal_version.id`, giữ toàn vẹn tham chiếu. |
| `reviewer_assignment_id` | Mã phân công người góp ý | `UUID` | Không | `—` | Mã phân công người góp ý; liên kết tới `reviewer_assignment.id`, giữ toàn vẹn tham chiếu. |
| `reviewer_user_id` | Mã tài khoản người góp ý | `UUID` | Không | `—` | Mã tài khoản người góp ý; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `decision` | Quyết định | `VARCHAR(30)` | Không | `—` | Quyết định; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `comment` | Nội dung nhận xét | `TEXT` | Không | `—` | Nội dung nhận xét; phục vụ ý kiến gvhd và người được giao góp ý. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `proposal_version_id` → `proposal_version.id`; `reviewer_assignment_id` → `reviewer_assignment.id`; `reviewer_user_id` → `user_account.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_proposal_review_decision`: `decision IN ('COMMENT','REVISION_REQUIRED','CONFIRM')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 25. `proposal_version` — Phiên bản đề cương

**Mục đích và lý do tồn tại:** Bản nộp đề cương bất biến. Nếu bỏ, mất dữ liệu/quan hệ riêng của phiên bản đề cương hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Bản nộp đề cương bất biến; `backend/services/activity.py`, `backend/services/membership_revision.py`, `backend/services/progress_annotations.py`, `backend/services/proposal_export.py`, `backend/services/proposals.py`.
**Vai trò thao tác:** SV thành viên nộp bản mới sau yêu cầu sửa; GVHD/GV góp ý và người chốt xem đúng phạm vi.
**Tình huống giả:** SV-DEMO nộp đề cương v2 PDF; v1 vẫn tải được và có mã băm riêng.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Giữ file và SHA-256 của từng lần nộp, không ghi đè proposal hay document_version.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `proposal_id` | Mã hồ sơ đề cương | `UUID` | Không | `—` | Mã hồ sơ đề cương; liên kết tới `proposal.id`, giữ toàn vẹn tham chiếu. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `stored_file_id` | Mã tệp lưu trữ | `UUID` | Không | `—` | Mã tệp lưu trữ; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `submitted_by` | Mã người nộp | `UUID` | Không | `—` | Mã người nộp; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `submitted_at` | Thời điểm nộp | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm nộp; dùng đối chiếu trình tự và audit. |
| `due_at_at_submission` | Hạn áp dụng lúc nộp | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Hạn hiệu lực tại lúc gửi; giữ nguyên kết quả đúng hạn/trễ khi Khoa gia hạn mốc sau đó. Bản cũ trước migration chỉ được khôi phục theo hạn tại lúc chuyển đổi. |
| `content_sha256` | SHA-256 nội dung bản nộp | `VARCHAR(64)` | Không | `—` | SHA-256 nội dung bản nộp; phục vụ bản nộp đề cương bất biến. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `proposal_id` → `proposal.id`; `stored_file_id` → `stored_file.id`; `submitted_by` → `student_profile.id`.
**UNIQUE:** `proposal_id, version_no`.
**CHECK:** `ck_proposal_version_version_positive`: `version_no > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 26. `registration_form_version` — Phiên bản đơn đăng ký Mẫu 1a/1b

**Mục đích và lý do tồn tại:** Tệp nộp bất biến trước tiếp nhận; đối chiếu thành viên và xuất bản nộp có footer, không tự xác nhận Khoa duyệt. Nếu bỏ, mất dữ liệu/quan hệ riêng của phiên bản đơn đăng ký mẫu 1a/1b hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tệp nộp bất biến trước tiếp nhận; đối chiếu thành viên và xuất bản nộp có footer, không tự xác nhận Khoa duyệt; `backend/services/registration_forms.py`.
**Vai trò thao tác:** SV đang trong nhóm nộp trước hạn tiếp nhận; nhóm, GV tiếp nhận và TBM đúng phạm vi được xem/tải/xuất bản nộp. Admin kỹ thuật không có quyền đọc mặc định.
**Tình huống giả:** Nhóm DEMO nộp Mẫu 1b v1 rồi sửa thành v2 trước tiếp nhận; bản in v2 ghi rõ bản nộp chưa xác nhận Khoa duyệt.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Đơn thuộc hồ sơ đăng ký trước khi có khóa luận. document_version thuộc khóa luận nên không thay thế được quan hệ này; mỗi bản tệp và dấu đối chiếu được giữ nguyên.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `registration_id` | Mã đăng ký | `UUID` | Không | `—` | Mã đăng ký; liên kết tới `topic_registration.id`, giữ toàn vẹn tham chiếu. |
| `stored_file_id` | Mã tệp lưu trữ | `UUID` | Không | `—` | Mã tệp lưu trữ; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `submitted_by` | Mã người nộp | `UUID` | Không | `—` | Mã người nộp; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `form_code` | Loại đơn Mẫu 1a/1b | `VARCHAR(2)` | Không | `—` | Loại đơn Mẫu 1a/1b; phục vụ tệp nộp bất biến trước tiếp nhận; đối chiếu thành viên và xuất bản nộp có footer, không tự xác nhận khoa duyệt. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `content_sha256` | SHA-256 nội dung bản nộp | `VARCHAR(64)` | Không | `—` | SHA-256 nội dung bản nộp; phục vụ tệp nộp bất biến trước tiếp nhận; đối chiếu thành viên và xuất bản nộp có footer, không tự xác nhận khoa duyệt. |
| `registration_fingerprint` | Mã đối chiếu thành viên, tên đề tài và GV đề xuất khi nộp | `VARCHAR(64)` | Không | `—` | Mã đối chiếu thành viên, tên đề tài và GV đề xuất khi nộp; phục vụ tệp nộp bất biến trước tiếp nhận; đối chiếu thành viên và xuất bản nộp có footer, không tự xác nhận khoa duyệt. |
| `submitted_at` | Thời điểm nộp | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm nộp; dùng đối chiếu trình tự và audit. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |

**PK:** `id`.
**FK và quan hệ:** `registration_id` → `topic_registration.id`; `stored_file_id` → `stored_file.id`; `submitted_by` → `student_profile.id`.
**UNIQUE:** `registration_id, version_no`.
**CHECK:** `ck_registration_form_version_form_code`: `form_code IN ('1A','1B')`; `ck_registration_form_version_hash_length`: `length(content_sha256) = 64 AND length(registration_fingerprint) = 64`; `ck_registration_form_version_version_positive`: `version_no > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 27. `registration_member` — Thành viên đăng ký

**Mục đích và lý do tồn tại:** Tự xác nhận nhóm và chống trùng đợt. Nếu bỏ, mất dữ liệu/quan hệ riêng của thành viên đăng ký hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tự xác nhận nhóm và chống trùng đợt; `backend/api/main.py`, `backend/api/roster.py`, `backend/services/activity.py`, `backend/services/evidence.py`, `backend/services/registration.py`, `backend/services/registration_forms.py`, `backend/services/topics.py`, `backend/services/withdrawals.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** Từng sinh viên tự xác nhận tham gia; GV tiếp nhận và Trưởng bộ môn xem nhóm đúng phạm vi.
**Tình huống giả:** Hai SV-DEMO tự xác nhận vào cùng một đăng ký trước khi gửi.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Đồng thuận trước khi chốt khác tư cách thành viên chính thức trong thesis_member.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `registration_id` | Mã đăng ký | `UUID` | Không | `—` | Mã đăng ký; liên kết tới `topic_registration.id`, giữ toàn vẹn tham chiếu. |
| `round_id` | Mã đợt KLTN | `UUID` | Không | `—` | Mã đợt KLTN; liên kết tới `topic_registration.round_id`, giữ toàn vẹn tham chiếu. |
| `student_id` | Mã sinh viên | `UUID` | Không | `—` | Mã sinh viên; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `evidence_file_id` | Mã tệp minh chứng | `UUID` | Cho phép | `—` | Mã tệp minh chứng; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `is_coordinator` | Là nhóm trưởng điều phối | `BOOLEAN` | Không | `false` | Là nhóm trưởng điều phối; phục vụ tự xác nhận nhóm và chống trùng đợt. |
| `active` | Còn hiệu lực | `BOOLEAN` | Không | `true` | Còn hiệu lực; phục vụ tự xác nhận nhóm và chống trùng đợt. |
| `consent_status` | Trạng thái đồng thuận | `VARCHAR(20)` | Không | `PENDING` | Trạng thái đồng thuận; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `responded_by_user_id` | Mã tài khoản tự phản hồi | `UUID` | Cho phép | `—` | Mã tài khoản tự phản hồi; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `responded_at` | Thời điểm phản hồi | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm phản hồi; phục vụ tự xác nhận nhóm và chống trùng đợt. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `evidence_file_id` → `stored_file.id`; `registration_id, round_id` → `topic_registration.id, topic_registration.round_id`; `responded_by_user_id` → `user_account.id`; `student_id` → `student_profile.id`.
**UNIQUE:** `registration_id, student_id`.
**CHECK:** `ck_registration_member_consent_consistency`: `(consent_status = 'PENDING' AND responded_by_user_id IS NULL AND responded_at IS NULL) OR (consent_status IN ('ACCEPTED','DECLINED') AND responded_by_user_id IS NOT NULL AND responded_at IS NOT NULL)`.
**Index:** `uq_registration_member_one_coordinator` (registration_member.registration_id) UNIQUE; `uq_registration_member_student_round_active` (registration_member.student_id, registration_member.round_id) UNIQUE.

## 28. `resource_assignment` — Phân công quyền theo tài nguyên

**Mục đích và lý do tồn tại:** Người xác nhận điều kiện/điều phối/góp ý theo đợt hoặc KLTN. Nếu bỏ, mất dữ liệu/quan hệ riêng của phân công quyền theo tài nguyên hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Người xác nhận điều kiện/điều phối/góp ý theo đợt hoặc KLTN; `backend/api/account_admin.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/account_directory.py`, `backend/services/activity.py`, `backend/services/lecturer_profiles.py`, `backend/services/progress.py`, `backend/services/roster.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** Admin quản trị phân công có căn cứ; người được giao chỉ thao tác đúng tài nguyên.
**Tình huống giả:** Khoa giao ELIGIBILITY_VERIFIER cho GV-DEMO đúng đợt; quyền tự hết khi thu hồi.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Quyền theo tài nguyên và thời hạn không suy ra từ base_role hoặc chức vụ chung.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `assignment_type` | Loại phân công | `VARCHAR(50)` | Không | `—` | Loại phân công; phục vụ người xác nhận điều kiện/điều phối/góp ý theo đợt hoặc kltn. |
| `user_id` | Mã tài khoản | `UUID` | Không | `—` | Mã tài khoản; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `round_id` | Mã đợt KLTN | `UUID` | Cho phép | `—` | Mã đợt KLTN; liên kết tới `thesis_round.id`, giữ toàn vẹn tham chiếu. |
| `thesis_id` | Mã khóa luận | `UUID` | Cho phép | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `effective_from` | Bắt đầu hiệu lực | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Bắt đầu hiệu lực; phục vụ người xác nhận điều kiện/điều phối/góp ý theo đợt hoặc kltn. |
| `effective_to` | Kết thúc hiệu lực | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Kết thúc hiệu lực; phục vụ người xác nhận điều kiện/điều phối/góp ý theo đợt hoặc kltn. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `ACTIVE` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `round_id` → `thesis_round.id`; `thesis_id` → `thesis.id`; `user_id` → `user_account.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_resource_assignment_effective_window`: `effective_to IS NULL OR effective_to > effective_from`; `ck_resource_assignment_exactly_one_resource`: `(CASE WHEN round_id IS NULL THEN 0 ELSE 1 END + CASE WHEN thesis_id IS NULL THEN 0 ELSE 1 END) = 1`; `ck_resource_assignment_state`: `state IN ('ACTIVE','REVOKED','EXPIRED')`.
**Index:** `uq_resource_assignment_round_scope` (resource_assignment.assignment_type, resource_assignment.user_id, resource_assignment.round_id) UNIQUE; `uq_resource_assignment_thesis_scope` (resource_assignment.assignment_type, resource_assignment.user_id, resource_assignment.thesis_id) UNIQUE.

## 29. `reviewer_assignment` — Phân công góp ý đề cương và phản biện KLTN

**Mục đích và lý do tồn tại:** Người phản biện, căn cứ phân công và hạn gửi nhận xét. Nếu bỏ, mất dữ liệu/quan hệ riêng của phân công góp ý đề cương và phản biện kltn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Người phản biện, căn cứ phân công và hạn gửi nhận xét; `backend/services/account_directory.py`, `backend/services/activity.py`, `backend/services/evaluation.py`, `backend/services/lecturer_profiles.py`, `backend/services/proposals.py`, `backend/services/theses.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** Trưởng bộ môn phân công giảng viên góp ý; chỉ người được giao và người trong hồ sơ xem.
**Tình huống giả:** TBM giao GV khác GVHD góp ý đúng hồ sơ đề cương DEMO.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Giới hạn GV được góp ý theo từng đề cương; không mặc nhiên trao quyền bằng vai trò LECTURER.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `lecturer_id` | Mã giảng viên | `UUID` | Không | `—` | Mã giảng viên; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `proposal_id` | Mã hồ sơ đề cương | `UUID` | Cho phép | `—` | Mã hồ sơ đề cương; liên kết tới `proposal.id`, giữ toàn vẹn tham chiếu. |
| `thesis_id` | Mã khóa luận | `UUID` | Cho phép | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `review_scope` | Phạm vi góp ý | `VARCHAR(20)` | Không | `—` | Phạm vi góp ý; phục vụ người phản biện, căn cứ phân công và hạn gửi nhận xét. |
| `assigned_by` | Mã người phân công | `UUID` | Không | `—` | Mã người phân công; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `assigned_at` | Thời điểm phân công | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm phân công; phục vụ người phản biện, căn cứ phân công và hạn gửi nhận xét. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `ACTIVE` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `due_at` | Hạn hoàn thành | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Hạn hoàn thành; phục vụ người phản biện, căn cứ phân công và hạn gửi nhận xét. |
| `assignment_reason` | Lý do phân công phản biện | `TEXT` | Cho phép | `—` | Lý do phân công phản biện; phục vụ người phản biện, căn cứ phân công và hạn gửi nhận xét. |
| `source_reference` | Căn cứ hoặc mã/số văn bản nguồn của thao tác | `VARCHAR(500)` | Cho phép | `—` | Căn cứ hoặc mã/số văn bản nguồn của thao tác; phục vụ người phản biện, căn cứ phân công và hạn gửi nhận xét. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `assigned_by` → `user_account.id`; `lecturer_id` → `lecturer_profile.id`; `proposal_id` → `proposal.id`; `thesis_id` → `thesis.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_reviewer_assignment_exactly_one_subject`: `(proposal_id IS NOT NULL AND thesis_id IS NULL) OR (proposal_id IS NULL AND thesis_id IS NOT NULL)`; `ck_reviewer_assignment_review_scope`: `review_scope IN ('PROPOSAL','THESIS')`; `ck_reviewer_assignment_scope_matches_subject`: `(review_scope = 'PROPOSAL' AND proposal_id IS NOT NULL) OR (review_scope = 'THESIS' AND thesis_id IS NOT NULL)`; `ck_reviewer_assignment_state`: `state IN ('ACTIVE','COMPLETED','REVOKED')`.
**Index:** `uq_reviewer_assignment_proposal` (reviewer_assignment.lecturer_id, reviewer_assignment.proposal_id) UNIQUE; `uq_reviewer_assignment_thesis` (reviewer_assignment.lecturer_id, reviewer_assignment.thesis_id) UNIQUE.

## 30. `signature_confirmation` — Xác nhận chữ ký đề cương

**Mục đích và lý do tồn tại:** Ghi phiên bản và căn cứ chốt đề cương. Nếu bỏ, mất dữ liệu/quan hệ riêng của xác nhận chữ ký đề cương hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Ghi phiên bản và căn cứ chốt đề cương; `backend/services/proposals.py`.
**Vai trò thao tác:** Trưởng bộ môn chốt phiên bản; Trưởng khoa ghi tham chiếu bản giấy đã ký đúng phạm vi Khoa.
**Tình huống giả:** TBM ghi bản đề cương v2 đã chốt; Trưởng khoa ghi tham chiếu bản giấy đã ký.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Một quyết định xác nhận trỏ đúng phiên bản đã chốt; không gộp thành cờ trên proposal.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `proposal_id` | Mã hồ sơ đề cương | `UUID` | Không | `—` | Mã hồ sơ đề cương; liên kết tới `proposal.id`, `proposal_version.proposal_id`, giữ toàn vẹn tham chiếu. |
| `proposal_version_no` | Số phiên bản đề cương | `INTEGER` | Không | `—` | Số phiên bản đề cương; liên kết tới `proposal_version.version_no`, giữ toàn vẹn tham chiếu. |
| `signature_type` | Loại xác nhận chữ ký | `VARCHAR(40)` | Không | `—` | Loại xác nhận chữ ký; phục vụ ghi phiên bản và căn cứ chốt đề cương. |
| `signer_user_id` | Mã người ghi xác nhận | `UUID` | Không | `—` | Mã người ghi xác nhận; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `confirmed_at` | Thời điểm xác nhận | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm xác nhận; dùng đối chiếu trình tự và audit. |
| `official_ref` | Tham chiếu văn bản chính thức | `VARCHAR(500)` | Cho phép | `—` | Tham chiếu văn bản chính thức; phục vụ ghi phiên bản và căn cứ chốt đề cương. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `proposal_id, proposal_version_no` → `proposal_version.proposal_id, proposal_version.version_no`; `proposal_id` → `proposal.id`; `signer_user_id` → `user_account.id`.
**UNIQUE:** `proposal_id, proposal_version_no, signature_type`.
**CHECK:** `ck_signature_confirmation_proposal_version_positive`: `proposal_version_no > 0`; `ck_signature_confirmation_signature_type`: `signature_type IN ('DEPARTMENT_FINALIZATION','DEAN_CONFIRMATION')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 31. `stored_file` — Tệp lưu trữ

**Mục đích và lý do tồn tại:** Checksum và metadata tệp đề cương, tiến độ, tài liệu. Nếu bỏ, mất dữ liệu/quan hệ riêng của tệp lưu trữ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Checksum và metadata tệp đề cương, tiến độ, tài liệu; `backend/services/documents.py`, `backend/services/evaluation.py`, `backend/services/evidence.py`, `backend/services/lecturer_profiles.py`, `backend/services/progress.py`, `backend/services/progress_annotations.py`, `backend/services/proposal_export.py`, `backend/services/proposals.py`, `backend/services/registration.py`, `backend/services/registration_forms.py`, `backend/services/school_forms.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** Chỉ service tài liệu/đề cương/minh chứng ghi metadata; tải file qua API kiểm quyền, không truy cập storage trực tiếp.
**Tình huống giả:** Tệp đề cương DEMO lưu khóa nội bộ và SHA-256, không tạo URL công khai.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Tách metadata tệp vật lý khỏi hồ sơ nghiệp vụ và phiên bản để kiểm checksum/đường dẫn riêng.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `storage_key` | Khóa lưu trữ nội bộ | `VARCHAR(500)` | Không | `—` | Khóa lưu trữ nội bộ; phục vụ checksum và metadata tệp đề cương, tiến độ, tài liệu. |
| `original_name` | Tên tệp gốc | `VARCHAR(500)` | Không | `—` | Tên tệp gốc; phục vụ checksum và metadata tệp đề cương, tiến độ, tài liệu. |
| `media_type` | Kiểu nội dung tệp | `VARCHAR(150)` | Không | `—` | Kiểu nội dung tệp; phục vụ checksum và metadata tệp đề cương, tiến độ, tài liệu. |
| `byte_size` | Kích thước tệp (byte) | `INTEGER` | Không | `—` | Kích thước tệp (byte); phục vụ checksum và metadata tệp đề cương, tiến độ, tài liệu. |
| `sha256` | SHA-256 của tệp | `VARCHAR(64)` | Không | `—` | SHA-256 của tệp; phục vụ checksum và metadata tệp đề cương, tiến độ, tài liệu. |
| `scan_state` | Trạng thái quét an toàn | `VARCHAR(20)` | Không | `QUARANTINED` | Trạng thái quét an toàn; phục vụ checksum và metadata tệp đề cương, tiến độ, tài liệu. |
| `scanned_at` | Thời điểm quét | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm quét; phục vụ checksum và metadata tệp đề cương, tiến độ, tài liệu. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** Không có FK.
**UNIQUE:** `storage_key`.
**CHECK:** `ck_stored_file_byte_size_positive`: `byte_size > 0`; `ck_stored_file_scan_state`: `scan_state IN ('QUARANTINED','CLEAN','INFECTED','FAILED')`.
**Index:** `ix_stored_file_sha256` (stored_file.sha256).

## 32. `student_profile` — Hồ sơ sinh viên

**Mục đích và lý do tồn tại:** Điều kiện, đề xuất và đăng ký. Nếu bỏ, mất dữ liệu/quan hệ riêng của hồ sơ sinh viên hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Điều kiện, đề xuất và đăng ký; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/core.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/account_directory.py`, `backend/services/activity.py`, `backend/services/documents.py`, `backend/services/evaluation.py`, `backend/services/notifications.py`, `backend/services/progress.py`, `backend/services/proposal_export.py`, `backend/services/proposals.py`, `backend/services/registration.py`, `backend/services/registration_forms.py`, `backend/services/review_form_export.py`, `backend/services/roster.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/topics.py`, `backend/services/withdrawals.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** SV xem hồ sơ của mình; Khoa nhập và xác nhận nguồn danh sách theo phân công đợt.
**Tình huống giả:** SV-DEMO-01 có MSSV giả và tài khoản thuộc Bộ môn CNTT-DEMO.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `user_id` | Mã tài khoản | `UUID` | Không | `—` | Mã tài khoản; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `student_code` | Mã số sinh viên | `VARCHAR(32)` | Không | `—` | Mã số sinh viên; phục vụ điều kiện, đề xuất và đăng ký. |
| `department_id` | Mã bộ môn | `UUID` | Không | `—` | Mã bộ môn; liên kết tới `department.id`, `department_major.department_id`, giữ toàn vẹn tham chiếu. |
| `display_name` | Họ tên hiển thị | `VARCHAR(255)` | Không | `—` | Họ tên hiển thị; phục vụ điều kiện, đề xuất và đăng ký. |
| `class_name` | Tên lớp | `VARCHAR(100)` | Cho phép | `—` | Tên lớp; phục vụ điều kiện, đề xuất và đăng ký. |
| `major_code` | Mã ngành | `VARCHAR(32)` | Cho phép | `—` | Mã ngành; liên kết tới `department_major.code`, giữ toàn vẹn tham chiếu. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `department_id, major_code` → `department_major.department_id, department_major.code`; `department_id` → `department.id`; `user_id` → `user_account.id`.
**UNIQUE:** `student_code`; `user_id`.
**CHECK:** Không có CHECK riêng.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 33. `thesis` — Khóa luận

**Mục đích và lý do tồn tại:** Hồ sơ sau khi chốt đăng ký. Nếu bỏ, mất dữ liệu/quan hệ riêng của khóa luận hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Hồ sơ sau khi chốt đăng ký; `backend/api/account_admin.py`, `backend/api/core.py`, `backend/services/account_directory.py`, `backend/services/activity.py`, `backend/services/evaluation.py`, `backend/services/notifications.py`, `backend/services/progress_annotations.py`, `backend/services/registration.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/topics.py`, `backend/services/withdrawals.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** SV thành viên, GVHD, Trưởng bộ môn và người được giao xem đúng phạm vi; GV tiếp nhận tạo khóa luận trong giao dịch; TBM có quyền theo dõi đúng bộ môn.
**Tình huống giả:** Sau khi chốt đăng ký DEMO, một khóa luận được tạo trong cùng transaction.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** KLTN chỉ hình thành sau khi đăng ký chốt; không dùng topic_registration như hồ sơ thực hiện.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `round_id` | Mã đợt KLTN | `UUID` | Không | `—` | Mã đợt KLTN; liên kết tới `thesis_round.id`, giữ toàn vẹn tham chiếu. |
| `topic_id` | Mã đề tài | `UUID` | Không | `—` | Mã đề tài; liên kết tới `topic.id`, giữ toàn vẹn tham chiếu. |
| `registration_id` | Mã đăng ký | `UUID` | Không | `—` | Mã đăng ký; liên kết tới `topic_registration.id`, giữ toàn vẹn tham chiếu. |
| `department_id` | Mã bộ môn | `UUID` | Không | `—` | Mã bộ môn; liên kết tới `department.id`, giữ toàn vẹn tham chiếu. |
| `current_title` | Tên đề tài hiện hành | `VARCHAR(500)` | Không | `—` | Tên đề tài hiện hành; phục vụ hồ sơ sau khi chốt đăng ký. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(30)` | Không | `ACTIVE` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `department_id` → `department.id`; `registration_id` → `topic_registration.id`; `round_id` → `thesis_round.id`; `topic_id` → `topic.id`.
**UNIQUE:** `registration_id`; `round_id, topic_id`.
**CHECK:** `ck_thesis_state`: `state IN ('ACTIVE','PROPOSAL_APPROVED','IN_PROGRESS','EXTENDED','WITHDRAWN','READY_FOR_DEFENSE','DEFENDED','COMPLETED','ARCHIVED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 34. `thesis_member` — Thành viên khóa luận

**Mục đích và lý do tồn tại:** Tư cách thành viên chính thức. Nếu bỏ, mất dữ liệu/quan hệ riêng của thành viên khóa luận hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tư cách thành viên chính thức; `backend/api/core.py`, `backend/services/activity.py`, `backend/services/evaluation.py`, `backend/services/notifications.py`, `backend/services/progress.py`, `backend/services/registration.py`, `backend/services/review_form_export.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/withdrawals.py`.
**Vai trò thao tác:** Phát sinh khi GV chấp nhận đăng ký; SV/GV liên quan xem danh sách thành viên.
**Tình huống giả:** SV-DEMO-01 và SV-DEMO-02 thành thành viên chính thức sau chốt.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Thành viên chính thức có lịch sử riêng, không đồng nhất với registration_member trước chốt.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_id` | Mã khóa luận | `UUID` | Không | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `student_id` | Mã sinh viên | `UUID` | Không | `—` | Mã sinh viên; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `is_coordinator` | Là nhóm trưởng điều phối | `BOOLEAN` | Không | `false` | Là nhóm trưởng điều phối; phục vụ tư cách thành viên chính thức. |
| `active` | Còn hiệu lực | `BOOLEAN` | Không | `true` | Còn hiệu lực; phục vụ tư cách thành viên chính thức. |
| `joined_at` | Thời điểm tham gia | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm tham gia; phục vụ tư cách thành viên chính thức. |
| `left_at` | Thời điểm rời nhóm | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm rời nhóm; phục vụ tư cách thành viên chính thức. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `student_id` → `student_profile.id`; `thesis_id` → `thesis.id`.
**UNIQUE:** `thesis_id, student_id`.
**CHECK:** Không có CHECK riêng.
**Index:** `uq_thesis_member_one_coordinator` (thesis_member.thesis_id) UNIQUE.

## 35. `thesis_review` — Phiếu nhận xét KLTN Mẫu 7 và Mẫu 8

**Mục đích và lý do tồn tại:** Nháp riêng và phiếu đã ký theo sinh viên, phân công và bản báo cáo. Nếu bỏ, mất dữ liệu/quan hệ riêng của phiếu nhận xét kltn mẫu 7 và mẫu 8 hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Nháp riêng và phiếu đã ký theo sinh viên, phân công và bản báo cáo; `backend/services/evaluation.py`.
**Vai trò thao tác:** Chỉ actor được API/service cấp quyền theo vai trò, bộ môn/đợt/KLTN; Admin không mặc nhiên duyệt nghiệp vụ.
**Tình huống giả:** GVHD lưu nháp Mẫu 7 riêng cho SV DEMO theo báo cáo v2; xuất phiếu để ký, tải bản ký đã quét sạch rồi gửi. Bản sửa lập phiếu phiên bản mới.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_id` | Mã khóa luận | `UUID` | Không | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `thesis_member_id` | Mã thành viên khóa luận | `UUID` | Không | `—` | Mã thành viên khóa luận; liên kết tới `thesis_member.id`, giữ toàn vẹn tham chiếu. |
| `lecturer_id` | Mã giảng viên | `UUID` | Không | `—` | Mã giảng viên; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `advisor_assignment_id` | Phân công GVHD gắn với phiếu | `UUID` | Cho phép | `—` | Phân công GVHD gắn với phiếu; liên kết tới `advisor_assignment.id`, giữ toàn vẹn tham chiếu. |
| `reviewer_assignment_id` | Mã phân công người góp ý | `UUID` | Cho phép | `—` | Mã phân công người góp ý; liên kết tới `reviewer_assignment.id`, giữ toàn vẹn tham chiếu. |
| `report_version_id` | Bản cuốn báo cáo được nhận xét | `UUID` | Không | `—` | Bản cuốn báo cáo được nhận xét; liên kết tới `document_version.id`, giữ toàn vẹn tham chiếu. |
| `kind` | Loại thông báo | `VARCHAR(20)` | Không | `—` | Loại thông báo; phục vụ nháp riêng và phiếu đã ký theo sinh viên, phân công và bản báo cáo. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `sections` | Các mục nhận xét theo Mẫu 7 hoặc Mẫu 8 | `JSONB` | Không | `—` | Các mục nhận xét theo Mẫu 7 hoặc Mẫu 8; phục vụ nháp riêng và phiếu đã ký theo sinh viên, phân công và bản báo cáo. |
| `thesis_completed` | GVHD xác nhận hoàn thành KLTN | `BOOLEAN` | Cho phép | `—` | GVHD xác nhận hoàn thành KLTN; phục vụ nháp riêng và phiếu đã ký theo sinh viên, phân công và bản báo cáo. |
| `allow_defense` | GVHD đồng ý cho bảo vệ | `BOOLEAN` | Cho phép | `—` | GVHD đồng ý cho bảo vệ; phục vụ nháp riêng và phiếu đã ký theo sinh viên, phân công và bản báo cáo. |
| `signed_file_id` | Tệp bản nhận xét đã ký | `UUID` | Cho phép | `—` | Tệp bản nhận xét đã ký; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `source_reference` | Căn cứ hoặc mã/số văn bản nguồn của thao tác | `VARCHAR(500)` | Cho phép | `—` | Căn cứ hoặc mã/số văn bản nguồn của thao tác; phục vụ nháp riêng và phiếu đã ký theo sinh viên, phân công và bản báo cáo. |
| `revision_reason` | Lý do lập phiếu hoặc bản sửa | `TEXT` | Không | `—` | Lý do lập phiếu hoặc bản sửa; phục vụ nháp riêng và phiếu đã ký theo sinh viên, phân công và bản báo cáo. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `submitted_at` | Thời điểm nộp | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm nộp; dùng đối chiếu trình tự và audit. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `advisor_assignment_id` → `advisor_assignment.id`; `lecturer_id` → `lecturer_profile.id`; `report_version_id` → `document_version.id`; `reviewer_assignment_id` → `reviewer_assignment.id`; `signed_file_id` → `stored_file.id`; `thesis_id` → `thesis.id`; `thesis_member_id` → `thesis_member.id`.
**UNIQUE:** `thesis_member_id, lecturer_id, kind, version_no`.
**CHECK:** `ck_thesis_review_assignment_matches_kind`: `(kind = 'ADVISOR' AND advisor_assignment_id IS NOT NULL AND reviewer_assignment_id IS NULL) OR (kind = 'REVIEWER' AND reviewer_assignment_id IS NOT NULL AND advisor_assignment_id IS NULL)`; `ck_thesis_review_kind`: `kind IN ('ADVISOR','REVIEWER')`; `ck_thesis_review_state`: `state IN ('DRAFT','SUBMITTED')`; `ck_thesis_review_submitted_has_signed_copy`: `state = 'DRAFT' OR (signed_file_id IS NOT NULL AND submitted_at IS NOT NULL)`; `ck_thesis_review_version_positive`: `version_no > 0`.
**Index:** `ix_thesis_review_thesis_member` (thesis_review.thesis_id, thesis_review.thesis_member_id).

## 36. `thesis_round` — Đợt KLTN

**Mục đích và lý do tồn tại:** Đợt chính/bổ sung và thời hạn. Nếu bỏ, mất dữ liệu/quan hệ riêng của đợt kltn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đợt chính/bổ sung và thời hạn; `backend/api/account_admin.py`, `backend/api/roster.py`, `backend/services/account_directory.py`, `backend/services/activity.py`, `backend/services/deadlines.py`, `backend/services/evaluation.py`, `backend/services/progress.py`, `backend/services/proposal_export.py`, `backend/services/registration.py`, `backend/services/registration_forms.py`, `backend/services/roster.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/topics.py`, `backend/services/withdrawals.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** Admin kỹ thuật cấu hình đợt; Khoa xác nhận danh sách theo phân công; SV/GV xem đợt mở.
**Tình huống giả:** Năm học DEMO có đợt MAIN; SUPPLEMENTARY thêm khi Khoa mở.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Đợt chính/bổ sung có cửa sổ và trạng thái độc lập trong cùng năm học.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `academic_year_id` | Mã năm học | `UUID` | Không | `—` | Mã năm học; liên kết tới `academic_year.id`, giữ toàn vẹn tham chiếu. |
| `code` | Mã nghiệp vụ | `VARCHAR(32)` | Không | `—` | Mã nghiệp vụ; phục vụ đợt chính/bổ sung và thời hạn. |
| `round_type` | Loại đợt | `VARCHAR(20)` | Không | `—` | Loại đợt; phục vụ đợt chính/bổ sung và thời hạn. |
| `opens_at` | Thời điểm mở | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm mở; phục vụ đợt chính/bổ sung và thời hạn. |
| `closes_at` | Thời điểm đóng | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm đóng; phục vụ đợt chính/bổ sung và thời hạn. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `execution_starts_on` | Ngày bắt đầu thực hiện theo kế hoạch Khoa | `DATE` | Cho phép | `—` | Ngày bắt đầu thực hiện theo kế hoạch Khoa; phục vụ đợt chính/bổ sung và thời hạn. |
| `execution_start_reference` | Căn cứ xác định ngày bắt đầu | `VARCHAR(500)` | Cho phép | `—` | Căn cứ xác định ngày bắt đầu; phục vụ đợt chính/bổ sung và thời hạn. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `academic_year_id` → `academic_year.id`.
**UNIQUE:** `academic_year_id, code`.
**CHECK:** `ck_thesis_round_execution_start_pair`: `(execution_starts_on IS NULL AND execution_start_reference IS NULL) OR (execution_starts_on IS NOT NULL AND execution_start_reference IS NOT NULL AND length(trim(execution_start_reference)) >= 5)`; `ck_thesis_round_round_type`: `round_type IN ('MAIN','SUPPLEMENTARY')`; `ck_thesis_round_state`: `state IN ('DRAFT','OPEN','CLOSED','ARCHIVED')`; `ck_thesis_round_time_window`: `closes_at > opens_at`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 37. `thesis_withdrawal_request` — Yêu cầu xin thôi thực hiện KLTN

**Mục đích và lý do tồn tại:** Đơn theo từng SV, xác nhận GVHD và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. Nếu bỏ, mất dữ liệu/quan hệ riêng của yêu cầu xin thôi thực hiện kltn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đơn theo từng SV, xác nhận GVHD và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ; `backend/services/activity.py`, `backend/services/membership_revision.py`, `backend/services/registration.py`, `backend/services/withdrawals.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** SV gửi / hủy đơn của mình trước xác nhận; GVHD chính xác nhận / trả lại. KLTN_COORDINATOR đúng đợt ghi nhận kết quả ngoài hệ thống kèm bản đơn sạch và căn cứ. Admin không tự có quyền nghiệp vụ; thành viên khác không đọc đơn riêng của người xin thôi.
**Tình huống giả:** SV-DEMO-01 xin thôi trong 02 tuần; GVHD xác nhận; điều phối đối chiếu bản ký và căn cứ bên ngoài để ghi nhận. SV-DEMO-02 tiếp tục cùng đề tài, nộp đề cương v2 để duyệt lại.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Một sinh viên có thể gửi nhiều đơn bị trả lại/hủy trước khi có kết quả. Cần đối tượng và trạng thái để xử lý, không dùng audit_event thay hồ sơ. Đơn theo SV không đồng nghĩa xóa đề tài nhóm; application_data chỉ là snapshot nội dung đơn bất biến, các quan hệ nghiệp vụ vẫn dùng FK.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `thesis_id` | Mã khóa luận | `UUID` | Không | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `student_id` | Mã sinh viên | `UUID` | Không | `—` | Mã sinh viên; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `reason` | Lý do hoặc căn cứ | `TEXT` | Không | `—` | Lý do hoặc căn cứ; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `application_data` | Bản chụp thông tin đơn tại thời điểm gửi | `JSONB` | Không | `—` | Bản chụp thông tin đơn tại thời điểm gửi; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `execution_starts_on` | Ngày bắt đầu thực hiện theo kế hoạch Khoa | `DATE` | Không | `—` | Ngày bắt đầu thực hiện theo kế hoạch Khoa; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `submitted_at` | Thời điểm nộp | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm nộp; dùng đối chiếu trình tự và audit. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(25)` | Không | `SUBMITTED` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `advisor_reviewed_by` | Người xác nhận của GVHD | `UUID` | Cho phép | `—` | Người xác nhận của GVHD; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `advisor_reviewed_at` | Thời điểm GVHD xác nhận / trả lại | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm GVHD xác nhận / trả lại; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `advisor_comment` | Ý kiến xác nhận hoặc trả lại của GVHD | `TEXT` | Cho phép | `—` | Ý kiến xác nhận hoặc trả lại của GVHD; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `evidence_file_id` | Mã tệp minh chứng | `UUID` | Cho phép | `—` | Mã tệp minh chứng; liên kết tới `stored_file.id`, giữ toàn vẹn tham chiếu. |
| `official_reference` | Số / căn cứ kết quả xử lý ngoài hệ thống | `VARCHAR(500)` | Cho phép | `—` | Số / căn cứ kết quả xử lý ngoài hệ thống; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `outcome_note` | Nội dung kết quả bên ngoài | `TEXT` | Cho phép | `—` | Nội dung kết quả bên ngoài; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `effective_on` | Ngày kết quả có hiệu lực | `DATE` | Cho phép | `—` | Ngày kết quả có hiệu lực; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `recorded_by` | Người ghi nhận kết quả bên ngoài | `UUID` | Cho phép | `—` | Người ghi nhận kết quả bên ngoài; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `recorded_at` | Thời điểm ghi nhận kết quả bên ngoài | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm ghi nhận kết quả bên ngoài; phục vụ đơn theo từng sv, xác nhận gvhd và kết quả xử lý ngoài hệ thống; không xóa hồ sơ cũ. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `advisor_reviewed_by` → `user_account.id`; `evidence_file_id` → `stored_file.id`; `recorded_by` → `user_account.id`; `student_id` → `student_profile.id`; `thesis_id` → `thesis.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_thesis_withdrawal_request_advisor_stamp`: `state NOT IN ('ADVISOR_CONFIRMED','RETURNED','RECORDED','NOT_GRANTED') OR (advisor_reviewed_by IS NOT NULL AND advisor_reviewed_at IS NOT NULL AND advisor_comment IS NOT NULL)`; `ck_thesis_withdrawal_request_application_data`: `jsonb_typeof(application_data) = 'object'`; `ck_thesis_withdrawal_request_outcome_stamp`: `state NOT IN ('RECORDED','NOT_GRANTED') OR (recorded_by IS NOT NULL AND recorded_at IS NOT NULL AND official_reference IS NOT NULL AND evidence_file_id IS NOT NULL AND effective_on IS NOT NULL)`; `ck_thesis_withdrawal_request_reason`: `length(trim(reason)) >= 10`; `ck_thesis_withdrawal_request_state`: `state IN ('SUBMITTED','ADVISOR_CONFIRMED','RETURNED','CANCELLED','RECORDED','NOT_GRANTED')`.
**Index:** `ix_withdrawal_student_state` (thesis_withdrawal_request.student_id, thesis_withdrawal_request.state); `uq_withdrawal_member_open` (thesis_withdrawal_request.thesis_id, thesis_withdrawal_request.student_id) UNIQUE.

## 38. `topic` — Đề tài

**Mục đích và lý do tồn tại:** Đề xuất và xét duyệt. Nếu bỏ, mất dữ liệu/quan hệ riêng của đề tài hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đề xuất và xét duyệt; `backend/api/account_admin.py`, `backend/api/main.py`, `backend/services/activity.py`, `backend/services/lecturer_profiles.py`, `backend/services/notifications.py`, `backend/services/proposal_export.py`, `backend/services/registration.py`, `backend/services/registration_forms.py`, `backend/services/school_forms.py`, `backend/services/topics.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** GV hoặc SV đề xuất; Trưởng bộ môn đúng phạm vi xét duyệt.
**Tình huống giả:** GV-DEMO đề xuất đề tài TOP-DEMO, TBM duyệt rồi SV đăng ký.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `round_id` | Mã đợt KLTN | `UUID` | Không | `—` | Mã đợt KLTN; liên kết tới `thesis_round.id`, giữ toàn vẹn tham chiếu. |
| `code` | Mã nghiệp vụ | `VARCHAR(40)` | Không | `—` | Mã nghiệp vụ; phục vụ đề xuất và xét duyệt. |
| `receiving_lecturer_id` | Mã GV tiếp nhận | `UUID` | Cho phép | `—` | Mã GV tiếp nhận; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `department_id` | Mã bộ môn | `UUID` | Không | `—` | Mã bộ môn; liên kết tới `department.id`, giữ toàn vẹn tham chiếu. |
| `proposer_user_id` | Mã tài khoản đề xuất | `UUID` | Không | `—` | Mã tài khoản đề xuất; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `proposer_type` | Loại người đề xuất | `VARCHAR(20)` | Không | `—` | Loại người đề xuất; phục vụ đề xuất và xét duyệt. |
| `current_title` | Tên đề tài hiện hành | `VARCHAR(500)` | Không | `—` | Tên đề tài hiện hành; phục vụ đề xuất và xét duyệt. |
| `description` | Mô tả | `TEXT` | Cho phép | `—` | Mô tả; phục vụ đề xuất và xét duyệt. |
| `max_students` | Sức chứa tối đa | `INTEGER` | Không | `3` | Sức chứa tối đa; phục vụ đề xuất và xét duyệt. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `decided_by` | Mã người quyết định | `UUID` | Cho phép | `—` | Mã người quyết định; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `decided_at` | Thời điểm quyết định | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm quyết định; dùng đối chiếu trình tự và audit. |
| `archived_at` | Thời điểm ngừng dùng đề tài cho đăng ký mới | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm ngừng dùng đề tài cho đăng ký mới; phục vụ đề xuất và xét duyệt. |
| `archived_by` | Người ngừng dùng đề tài | `UUID` | Cho phép | `—` | Người ngừng dùng đề tài; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `archive_reason` | Lý do ngừng dùng đề tài | `TEXT` | Cho phép | `—` | Lý do ngừng dùng đề tài; phục vụ đề xuất và xét duyệt. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `archived_by` → `user_account.id`; `decided_by` → `user_account.id`; `department_id` → `department.id`; `proposer_user_id` → `user_account.id`; `receiving_lecturer_id` → `lecturer_profile.id`; `round_id` → `thesis_round.id`.
**UNIQUE:** `code`.
**CHECK:** `ck_topic_max_students`: `max_students BETWEEN 1 AND 3`; `ck_topic_proposer_type`: `proposer_type IN ('LECTURER','STUDENT')`; `ck_topic_state`: `state IN ('DRAFT','SUBMITTED','APPROVED','RETURNED','REJECTED','LOCKED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 39. `topic_registration` — Đăng ký đề tài

**Mục đích và lý do tồn tại:** Tiếp nhận và chốt nhóm. Nếu bỏ, mất dữ liệu/quan hệ riêng của đăng ký đề tài hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tiếp nhận và chốt nhóm; `backend/api/account_admin.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/activity.py`, `backend/services/evidence.py`, `backend/services/notifications.py`, `backend/services/registration.py`, `backend/services/topics.py`, `backend/services/withdrawals.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** Từng SV tự tham gia; GV tiếp nhận quyết định; Trưởng bộ môn chốt.
**Tình huống giả:** Nhóm DEMO gửi đăng ký; GV chấp nhận tạo khóa luận và GVHD chính thức; trạng thái và lịch sử được giữ.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `round_id` | Mã đợt KLTN | `UUID` | Không | `—` | Mã đợt KLTN; liên kết tới `thesis_round.id`, giữ toàn vẹn tham chiếu. |
| `topic_id` | Mã đề tài | `UUID` | Không | `—` | Mã đề tài; liên kết tới `topic.id`, giữ toàn vẹn tham chiếu. |
| `created_by` | Mã người tạo | `UUID` | Không | `—` | Mã người tạo; liên kết tới `student_profile.id`, giữ toàn vẹn tham chiếu. |
| `expected_member_count` | Quy mô nhóm dự kiến | `INTEGER` | Không | `1` | Quy mô nhóm dự kiến; phục vụ tiếp nhận và chốt nhóm. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(30)` | Không | `DRAFT` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `submitted_at` | Thời điểm nộp | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm nộp; dùng đối chiếu trình tự và audit. |
| `lecturer_decided_by` | Mã GV tiếp nhận quyết định | `UUID` | Cho phép | `—` | Mã GV tiếp nhận quyết định; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `lecturer_decided_at` | Thời điểm GV tiếp nhận quyết định | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm GV tiếp nhận quyết định; phục vụ tiếp nhận và chốt nhóm. |
| `lecturer_reason` | Lý do quyết định của GV | `TEXT` | Cho phép | `—` | Lý do quyết định của GV; phục vụ tiếp nhận và chốt nhóm. |
| `department_finalized_by` | Mã người chốt tại Bộ môn | `UUID` | Cho phép | `—` | Mã người chốt tại Bộ môn; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `department_finalized_at` | Thời điểm Bộ môn chốt | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm Bộ môn chốt; phục vụ tiếp nhận và chốt nhóm. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `created_by` → `student_profile.id`; `department_finalized_by` → `user_account.id`; `lecturer_decided_by` → `lecturer_profile.id`; `round_id` → `thesis_round.id`; `topic_id` → `topic.id`.
**UNIQUE:** `id, round_id`.
**CHECK:** `ck_topic_registration_expected_member_count`: `expected_member_count BETWEEN 1 AND 3`; `ck_topic_registration_state`: `state IN ('DRAFT','SUBMITTED','LECTURER_ACCEPTED','LECTURER_REJECTED','RETURNED','FINALIZED','CANCELLED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 40. `topic_requirement` — Yêu cầu mong muốn của đề tài

**Mục đích và lý do tồn tại:** Thông tin để GV xét phù hợp, không thay điều kiện chính thức. Nếu bỏ, mất dữ liệu/quan hệ riêng của yêu cầu mong muốn của đề tài hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Thông tin để GV xét phù hợp, không thay điều kiện chính thức; `backend/services/topics.py`.
**Vai trò thao tác:** GV đề xuất yêu cầu mong muốn; Trưởng bộ môn xét đề tài; SV xem trước khi đăng ký.
**Tình huống giả:** GV nêu kỹ năng Python là mong muốn; không tự chặn SV đủ điều kiện.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `topic_id` | Mã đề tài | `UUID` | Không | `—` | Mã đề tài; liên kết tới `topic.id`, giữ toàn vẹn tham chiếu. |
| `requirement_type` | Loại yêu cầu | `VARCHAR(30)` | Không | `—` | Loại yêu cầu; phục vụ thông tin để gv xét phù hợp, không thay điều kiện chính thức. |
| `value_text` | Nội dung yêu cầu | `TEXT` | Cho phép | `—` | Nội dung yêu cầu; phục vụ thông tin để gv xét phù hợp, không thay điều kiện chính thức. |
| `preferred_gpa` | GPA mong muốn | `NUMERIC(3, 2)` | Cho phép | `—` | GPA mong muốn; phục vụ thông tin để gv xét phù hợp, không thay điều kiện chính thức. |
| `enforcement` | Tính chất yêu cầu | `VARCHAR(20)` | Không | `DESIRED` | Tính chất yêu cầu; phục vụ thông tin để gv xét phù hợp, không thay điều kiện chính thức. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `topic_id` → `topic.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_topic_requirement_enforcement_desired`: `enforcement = 'DESIRED'`; `ck_topic_requirement_preferred_gpa`: `preferred_gpa IS NULL OR (preferred_gpa >= 0 AND preferred_gpa <= 4)`; `ck_topic_requirement_requirement_type`: `requirement_type IN ('PREFERRED_GPA','SKILL','TECHNOLOGY','KNOWLEDGE','OTHER')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 41. `topic_title_version` — Lịch sử tên đề tài

**Mục đích và lý do tồn tại:** Tên ổn định theo phiên bản và audit. Nếu bỏ, mất dữ liệu/quan hệ riêng của lịch sử tên đề tài hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tên ổn định theo phiên bản và audit; `backend/services/topics.py`.
**Vai trò thao tác:** GV/SV đề xuất thay tên theo quy trình; Trưởng bộ môn quyết định; mọi bên liên quan xem lịch sử.
**Tình huống giả:** TBM đổi tên TOP-DEMO ở v2, mã đề tài giữ nguyên.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Tên đổi theo lịch sử; topic giữ mã và tên hiện hành để truy vấn nhanh.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `topic_id` | Mã đề tài | `UUID` | Không | `—` | Mã đề tài; liên kết tới `topic.id`, giữ toàn vẹn tham chiếu. |
| `version_no` | Số phiên bản | `INTEGER` | Không | `—` | Số phiên bản; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |
| `title` | Tiêu đề | `VARCHAR(500)` | Không | `—` | Tiêu đề; phục vụ tên ổn định theo phiên bản và audit. |
| `changed_by` | Mã người đổi tên | `UUID` | Không | `—` | Mã người đổi tên; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `change_reason` | Lý do đổi tên | `TEXT` | Cho phép | `—` | Lý do đổi tên; phục vụ tên ổn định theo phiên bản và audit. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `changed_by` → `user_account.id`; `topic_id` → `topic.id`.
**UNIQUE:** `topic_id, version_no`.
**CHECK:** `ck_topic_title_version_version_positive`: `version_no > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 42. `user_account` — Tài khoản người dùng

**Mục đích và lý do tồn tại:** Đăng nhập, khóa tài khoản và vai trò nền. Nếu bỏ, mất dữ liệu/quan hệ riêng của tài khoản người dùng hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đăng nhập, khóa tài khoản và vai trò nền; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/dependencies.py`, `backend/api/lecturer_import.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/account_directory.py`, `backend/services/account_tokens.py`, `backend/services/activity.py`, `backend/services/evaluation.py`, `backend/services/evidence.py`, `backend/services/lecturer_profiles.py`, `backend/services/lecturer_roster.py`, `backend/services/notifications.py`, `backend/services/registration.py`, `backend/services/roster.py`, `backend/services/school_forms.py`, `backend/services/theses.py`, `backend/services/topics.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** Admin kỹ thuật quản lý trạng thái; chính chủ đăng nhập; không cấp quyền duyệt nghiệp vụ cho Admin.
**Tình huống giả:** Tài khoản demo SV-DEMO đăng nhập bằng email đã xác minh và bị chặn khi LOCKED.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `external_subject` | Định danh ngoài hệ thống | `VARCHAR(255)` | Cho phép | `—` | Định danh ngoài hệ thống; phục vụ đăng nhập, khóa tài khoản và vai trò nền. |
| `email` | Địa chỉ email | `VARCHAR(255)` | Cho phép | `—` | Địa chỉ email; phục vụ đăng nhập, khóa tài khoản và vai trò nền. |
| `password_hash` | Mã băm mật khẩu | `VARCHAR(255)` | Cho phép | `—` | Mã băm mật khẩu; phục vụ đăng nhập, khóa tài khoản và vai trò nền. |
| `email_verified_at` | Thời điểm xác minh email | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm xác minh email; phục vụ đăng nhập, khóa tài khoản và vai trò nền. |
| `base_role` | Vai trò nền | `VARCHAR(20)` | Không | `—` | Vai trò nền; phục vụ đăng nhập, khóa tài khoản và vai trò nền. |
| `status` | Trạng thái tài khoản | `VARCHAR(20)` | Không | `ACTIVE` | Trạng thái tài khoản; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** Không có FK.
**UNIQUE:** `external_subject`.
**CHECK:** `ck_user_account_base_role`: `base_role IN ('ADMIN','LECTURER','STUDENT')`; `ck_user_account_email_normalized`: `email IS NULL OR email = lower(email)`; `ck_user_account_identity_present`: `external_subject IS NOT NULL OR email IS NOT NULL`; `ck_user_account_local_credentials_pair`: `(email IS NULL AND password_hash IS NULL) OR (email IS NOT NULL AND password_hash IS NOT NULL)`; `ck_user_account_status`: `status IN ('ACTIVE','LOCKED','DISABLED')`.
**Index:** `uq_user_account_email_lower` (lower(email)) UNIQUE.

## 43. `user_notification` — Thông báo người dùng

**Mục đích và lý do tồn tại:** Thông báo đề xuất và đăng ký theo người nhận. Nếu bỏ, mất dữ liệu/quan hệ riêng của thông báo người dùng hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Thông báo đề xuất và đăng ký theo người nhận; `backend/services/notifications.py`, `backend/services/workflow_notices.py`.
**Vai trò thao tác:** Chỉ actor được API/service cấp quyền theo vai trò, bộ môn/đợt/KLTN; Admin không mặc nhiên duyệt nghiệp vụ.
**Tình huống giả:** SV nhóm DEMO nộp báo cáo tiến độ; chỉ GVHD đúng đề tài và thành viên nhóm nhận thông báo. GVHD phản hồi thì cả nhóm nhận. TBM nhận đề tài chờ duyệt, không nhận tiến độ riêng.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `recipient_user_id` | Mã tài khoản nhận thông báo | `UUID` | Không | `—` | Mã tài khoản nhận thông báo; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `actor_user_id` | Mã tài khoản sinh viên thực hiện | `UUID` | Không | `—` | Mã tài khoản sinh viên thực hiện; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `registration_id` | Mã đăng ký | `UUID` | Cho phép | `—` | Mã đăng ký; liên kết tới `topic_registration.id`, giữ toàn vẹn tham chiếu. |
| `thesis_id` | Mã khóa luận | `UUID` | Cho phép | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `subject_type` | Loại đối tượng của thông báo | `VARCHAR(40)` | Cho phép | `—` | Loại đối tượng của thông báo; phục vụ thông báo đề xuất và đăng ký theo người nhận. |
| `subject_id` | Mã đối tượng của thông báo | `UUID` | Cho phép | `—` | Mã đối tượng của thông báo; phục vụ thông báo đề xuất và đăng ký theo người nhận. |
| `message` | Nội dung thông báo theo đối tượng | `TEXT` | Cho phép | `—` | Nội dung thông báo theo đối tượng; phục vụ thông báo đề xuất và đăng ký theo người nhận. |
| `url` | Đường dẫn nội bộ tới đúng hồ sơ | `VARCHAR(300)` | Cho phép | `—` | Đường dẫn nội bộ tới đúng hồ sơ; phục vụ thông báo đề xuất và đăng ký theo người nhận. |
| `kind` | Loại thông báo | `VARCHAR(32)` | Không | `—` | Loại thông báo; phục vụ thông báo đề xuất và đăng ký theo người nhận. |
| `read_at` | Thời điểm đã xem | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm đã xem; phục vụ thông báo đề xuất và đăng ký theo người nhận. |
| `revoked_at` | Thời điểm thu hồi | `TIMESTAMP WITH TIME ZONE` | Cho phép | `—` | Thời điểm thu hồi; phục vụ thông báo đề xuất và đăng ký theo người nhận. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `actor_user_id` → `user_account.id`; `recipient_user_id` → `user_account.id`; `registration_id` → `topic_registration.id`; `thesis_id` → `thesis.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_user_notification_kind`: `kind IN ('PROPOSAL_SUBMITTED','PROPOSAL_APPROVED','PROPOSAL_REVIEWED','PROPOSAL_FINALIZED','REGISTRATION_SUBMITTED','REGISTRATION_JOINED','REGISTRATION_ACCEPTED','REGISTRATION_REJECTED','MILESTONE_OPENED','MILESTONE_EXTENDED','MILESTONE_REOPENED','MILESTONE_CLOSED','DOCUMENT_DEADLINE_SET','DOCUMENT_DEADLINE_EXTENDED','DOCUMENT_DEADLINE_REOPENED','DOCUMENT_DEADLINE_CLOSED','PROGRESS_SUBMITTED','PROGRESS_CONFIRMED','PROGRESS_REVISION_REQUIRED','PROGRESS_COMMENT','DOCUMENT_SUBMITTED','DOCUMENT_ACCEPTED','DOCUMENT_REVISION_REQUESTED','WORK_SUBMITTED','WORK_APPROVED','WORK_REVISION_REQUIRED','ACCOUNT_LOCKED','ACCOUNT_UNLOCKED','ACCOUNT_DISABLED','ACCOUNT_RESTORED','ACCOUNT_LINK_REISSUED','ACCOUNT_EMAIL_CORRECTED','REGISTRATION_FORM_SUBMITTED','PROPOSAL_REVIEWER_ASSIGNED','PROGRESS_REVIEWER_ASSIGNED','PROPOSAL_DEAN_CONFIRMED','WORKFLOW_NOTICE')`.
**Index:** `ix_user_notification_recipient_created` (user_notification.recipient_user_id, user_notification.created_at); `ix_user_notification_thesis_created` (user_notification.thesis_id, user_notification.created_at).
