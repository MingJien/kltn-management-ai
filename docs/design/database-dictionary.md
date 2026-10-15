# Từ điển dữ liệu CSDL chính thức `kltn_management`

Sinh tự động từ metadata SQLAlchemy của revision `20261015_0001_official`; 32 bảng nghiệp vụ, không tính `alembic_version`. Hai bản SQL 32/62 chỉ là nguồn đối chiếu.

`NULL` ở đây là ràng buộc vật lý. Mọi hành động quan trọng còn chịu kiểm tra quyền/trạng thái trong service và audit. Ví dụ đều là dữ liệu giả.

## 01. `academic_year` — Năm học

**Mục đích và lý do tồn tại:** Đợt và lịch KLTN. Nếu bỏ, mất dữ liệu/quan hệ riêng của năm học hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đợt và lịch KLTN; `backend/api/account_admin.py`, `backend/services/theses.py`, `backend/services/topics.py`.
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
**Use case/API/service:** GVHD chính thức và lịch sử thay đổi; `backend/services/registration.py`, `backend/services/theses.py`.
**Vai trò thao tác:** Trưởng bộ môn chốt GVHD; GV được đề cử có quyền nhận/từ chối thay đổi; SV và GVHD xem trong phạm vi khóa luận.
**Tình huống giả:** Sau khi Bộ môn chốt nhóm DEMO, một GV được ghi là GVHD chính từ ngày bắt đầu; khi thay GV lưu thêm bản phân công mới.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** GV tiếp nhận đăng ký chưa phải GVHD chính thức; bảng này chỉ phát sinh sau khi TBM chốt và giữ lịch sử thay GV.

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
**Use case/API/service:** Dấu vết quyết định, phân quyền và tài liệu; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/core.py`, `backend/api/roster.py`, `backend/services/documents.py`, `backend/services/evidence.py`, `backend/services/registration.py`, `backend/services/roster.py`, `backend/services/theses.py`, `backend/services/topics.py`.
**Vai trò thao tác:** Service ghi khi có thao tác; Trưởng bộ môn đúng phạm vi xem lịch sử khóa luận.
**Tình huống giả:** Ghi actor, thời điểm và lý do khi TBM chốt đăng ký DEMO.
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
| `occurred_at` | Thời điểm sự kiện | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm sự kiện; dùng đối chiếu trình tự và audit. |
| `correlation_id` | Mã liên kết nhật ký | `UUID` | Không | `—` | Mã liên kết nhật ký; phục vụ dấu vết quyết định, phân quyền và tài liệu. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |

**PK:** `id`.
**FK và quan hệ:** `actor_id` → `user_account.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** Không có CHECK riêng.
**Index:** `ix_audit_event_correlation_id` (audit_event.correlation_id); `ix_audit_event_resource_id` (audit_event.resource_id).

## 04. `department` — Bộ môn

**Mục đích và lý do tồn tại:** Phạm vi quyền và hồ sơ. Nếu bỏ, mất dữ liệu/quan hệ riêng của bộ môn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Phạm vi quyền và hồ sơ; `backend/api/account_admin.py`, `backend/api/roster.py`, `backend/services/roster.py`, `backend/services/theses.py`.
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

## 05. `document` — Hồ sơ tài liệu KLTN

**Mục đích và lý do tồn tại:** Tài liệu và quyền truy cập. Nếu bỏ, mất dữ liệu/quan hệ riêng của hồ sơ tài liệu kltn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tài liệu và quyền truy cập; `backend/api/core.py`, `backend/services/documents.py`, `backend/services/progress.py`.
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

## 06. `document_version` — Phiên bản tài liệu

**Mục đích và lý do tồn tại:** Nộp tài liệu bất biến. Nếu bỏ, mất dữ liệu/quan hệ riêng của phiên bản tài liệu hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Nộp tài liệu bất biến; `backend/services/documents.py`, `backend/services/progress.py`.
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

## 07. `eligibility_snapshot` — Kết quả điều kiện đăng ký

**Mục đích và lý do tồn tại:** Xác nhận đủ điều kiện theo đợt. Nếu bỏ, mất dữ liệu/quan hệ riêng của kết quả điều kiện đăng ký hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Xác nhận đủ điều kiện theo đợt; `backend/api/main.py`, `backend/api/roster.py`, `backend/services/registration.py`, `backend/services/roster.py`.
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

## 08. `faculty` — Khoa

**Mục đích và lý do tồn tại:** Cấp trên của bộ môn và phạm vi Trưởng khoa. Nếu bỏ, mất dữ liệu/quan hệ riêng của khoa hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Cấp trên của bộ môn và phạm vi Trưởng khoa; bảng phụ trợ, chưa có truy cập trực tiếp.
**Vai trò thao tác:** Admin kỹ thuật quản lý dữ liệu Khoa; Trưởng khoa chỉ có quyền theo phân công chức vụ còn hiệu lực.
**Tình huống giả:** Khoa CNKT-DEMO quản lý Bộ môn CNTT-DEMO.
**Trạng thái sử dụng:** Phụ trợ cho FK/quyền/phiên bản.
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

## 09. `lecturer_profile` — Hồ sơ giảng viên

**Mục đích và lý do tồn tại:** Đề xuất, tiếp nhận, hướng dẫn và xét duyệt. Nếu bỏ, mất dữ liệu/quan hệ riêng của hồ sơ giảng viên hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đề xuất, tiếp nhận, hướng dẫn và xét duyệt; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/core.py`, `backend/api/main.py`, `backend/services/documents.py`, `backend/services/progress.py`, `backend/services/proposals.py`, `backend/services/registration.py`, `backend/services/theses.py`, `backend/services/topics.py`.
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
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `department_id` → `department.id`; `user_id` → `user_account.id`.
**UNIQUE:** `lecturer_code`; `user_id`.
**CHECK:** Không có CHECK riêng.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 10. `member_work_assignment` — Phân công việc thành viên

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

## 11. `organizational_position` — Chức vụ tổ chức

**Mục đích và lý do tồn tại:** Quyền Trưởng bộ môn/Trưởng khoa. Nếu bỏ, mất dữ liệu/quan hệ riêng của chức vụ tổ chức hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Quyền Trưởng bộ môn/Trưởng khoa; `backend/services/registration.py`, `backend/services/theses.py`.
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

## 12. `position_assignment` — Phân công chức vụ

**Mục đích và lý do tồn tại:** Quyền theo bộ môn/khoa và thời gian. Nếu bỏ, mất dữ liệu/quan hệ riêng của phân công chức vụ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Quyền theo bộ môn/khoa và thời gian; `backend/services/registration.py`, `backend/services/theses.py`.
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

## 13. `progress_milestone` — Mốc tiến độ

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

## 14. `progress_report` — Báo cáo tiến độ

**Mục đích và lý do tồn tại:** Bản nộp theo phiên bản. Nếu bỏ, mất dữ liệu/quan hệ riêng của báo cáo tiến độ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Bản nộp theo phiên bản; `backend/api/core.py`, `backend/services/progress.py`.
**Vai trò thao tác:** SV thành viên nộp; GVHD xác nhận; GV góp ý chéo chỉ COMMENT_ONLY.
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

## 15. `progress_review` — Nhận xét tiến độ

**Mục đích và lý do tồn tại:** GVHD xác nhận, GV khác chỉ góp ý. Nếu bỏ, mất dữ liệu/quan hệ riêng của nhận xét tiến độ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** GVHD xác nhận, GV khác chỉ góp ý; `backend/services/progress.py`.
**Vai trò thao tác:** GVHD xác nhận/yêu cầu sửa; GV được giao góp ý chéo chỉ COMMENT_ONLY.
**Tình huống giả:** GV góp ý chéo ghi COMMENT_ONLY; GVHD chính mới ghi CONFIRM.
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

## 16. `proposal` — Hồ sơ đề cương

**Mục đích và lý do tồn tại:** Trạng thái xét duyệt đề cương. Nếu bỏ, mất dữ liệu/quan hệ riêng của hồ sơ đề cương hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Trạng thái xét duyệt đề cương; `backend/services/proposals.py`, `backend/services/theses.py`.
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

## 17. `proposal_review` — Nhận xét đề cương

**Mục đích và lý do tồn tại:** Ý kiến GVHD và người được giao góp ý. Nếu bỏ, mất dữ liệu/quan hệ riêng của nhận xét đề cương hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Ý kiến GVHD và người được giao góp ý; `backend/services/proposals.py`.
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

## 18. `proposal_version` — Phiên bản đề cương

**Mục đích và lý do tồn tại:** Bản nộp đề cương bất biến. Nếu bỏ, mất dữ liệu/quan hệ riêng của phiên bản đề cương hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Bản nộp đề cương bất biến; `backend/services/proposals.py`.
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
| `content_sha256` | SHA-256 nội dung bản nộp | `VARCHAR(64)` | Không | `—` | SHA-256 nội dung bản nộp; phục vụ bản nộp đề cương bất biến. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `proposal_id` → `proposal.id`; `stored_file_id` → `stored_file.id`; `submitted_by` → `student_profile.id`.
**UNIQUE:** `proposal_id, version_no`.
**CHECK:** `ck_proposal_version_version_positive`: `version_no > 0`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 19. `registration_member` — Thành viên đăng ký

**Mục đích và lý do tồn tại:** Tự xác nhận nhóm và chống trùng đợt. Nếu bỏ, mất dữ liệu/quan hệ riêng của thành viên đăng ký hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tự xác nhận nhóm và chống trùng đợt; `backend/api/main.py`, `backend/services/evidence.py`, `backend/services/registration.py`, `backend/services/topics.py`.
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

## 20. `resource_assignment` — Phân công quyền theo tài nguyên

**Mục đích và lý do tồn tại:** Người xác nhận điều kiện/điều phối/góp ý theo đợt hoặc KLTN. Nếu bỏ, mất dữ liệu/quan hệ riêng của phân công quyền theo tài nguyên hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Người xác nhận điều kiện/điều phối/góp ý theo đợt hoặc KLTN; `backend/api/account_admin.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/progress.py`, `backend/services/roster.py`, `backend/services/theses.py`.
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

## 21. `reviewer_assignment` — Phân công góp ý đề cương

**Mục đích và lý do tồn tại:** Giới hạn người góp ý theo hồ sơ. Nếu bỏ, mất dữ liệu/quan hệ riêng của phân công góp ý đề cương hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Giới hạn người góp ý theo hồ sơ; `backend/services/proposals.py`, `backend/services/theses.py`.
**Vai trò thao tác:** Trưởng bộ môn phân công giảng viên góp ý; chỉ người được giao và người trong hồ sơ xem.
**Tình huống giả:** TBM giao GV khác GVHD góp ý đúng hồ sơ đề cương DEMO.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Giới hạn GV được góp ý theo từng đề cương; không mặc nhiên trao quyền bằng vai trò LECTURER.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `lecturer_id` | Mã giảng viên | `UUID` | Không | `—` | Mã giảng viên; liên kết tới `lecturer_profile.id`, giữ toàn vẹn tham chiếu. |
| `proposal_id` | Mã hồ sơ đề cương | `UUID` | Cho phép | `—` | Mã hồ sơ đề cương; liên kết tới `proposal.id`, giữ toàn vẹn tham chiếu. |
| `thesis_id` | Mã khóa luận | `UUID` | Cho phép | `—` | Mã khóa luận; liên kết tới `thesis.id`, giữ toàn vẹn tham chiếu. |
| `review_scope` | Phạm vi góp ý | `VARCHAR(20)` | Không | `—` | Phạm vi góp ý; phục vụ giới hạn người góp ý theo hồ sơ. |
| `assigned_by` | Mã người phân công | `UUID` | Không | `—` | Mã người phân công; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `assigned_at` | Thời điểm phân công | `TIMESTAMP WITH TIME ZONE` | Không | `—` | Thời điểm phân công; phục vụ giới hạn người góp ý theo hồ sơ. |
| `state` | Trạng thái nghiệp vụ | `VARCHAR(20)` | Không | `ACTIVE` | Trạng thái nghiệp vụ; điều khiển chuyển trạng thái và giới hạn thao tác theo quy trình. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `assigned_by` → `user_account.id`; `lecturer_id` → `lecturer_profile.id`; `proposal_id` → `proposal.id`; `thesis_id` → `thesis.id`.
**UNIQUE:** Không có ràng buộc UNIQUE riêng.
**CHECK:** `ck_reviewer_assignment_exactly_one_subject`: `(proposal_id IS NOT NULL AND thesis_id IS NULL) OR (proposal_id IS NULL AND thesis_id IS NOT NULL)`; `ck_reviewer_assignment_review_scope`: `review_scope IN ('PROPOSAL','THESIS')`; `ck_reviewer_assignment_scope_matches_subject`: `(review_scope = 'PROPOSAL' AND proposal_id IS NOT NULL) OR (review_scope = 'THESIS' AND thesis_id IS NOT NULL)`; `ck_reviewer_assignment_state`: `state IN ('ACTIVE','COMPLETED','REVOKED')`.
**Index:** `uq_reviewer_assignment_proposal` (reviewer_assignment.lecturer_id, reviewer_assignment.proposal_id) UNIQUE; `uq_reviewer_assignment_thesis` (reviewer_assignment.lecturer_id, reviewer_assignment.thesis_id) UNIQUE.

## 22. `signature_confirmation` — Xác nhận chữ ký đề cương

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
**UNIQUE:** `proposal_id, signature_type`.
**CHECK:** `ck_signature_confirmation_proposal_version_positive`: `proposal_version_no > 0`; `ck_signature_confirmation_signature_type`: `signature_type IN ('DEPARTMENT_FINALIZATION','DEAN_CONFIRMATION')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 23. `stored_file` — Tệp lưu trữ

**Mục đích và lý do tồn tại:** Checksum và metadata tệp đề cương, tiến độ, tài liệu. Nếu bỏ, mất dữ liệu/quan hệ riêng của tệp lưu trữ hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Checksum và metadata tệp đề cương, tiến độ, tài liệu; `backend/services/documents.py`, `backend/services/evidence.py`, `backend/services/progress.py`, `backend/services/proposals.py`, `backend/services/registration.py`.
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

## 24. `student_profile` — Hồ sơ sinh viên

**Mục đích và lý do tồn tại:** Điều kiện, đề xuất và đăng ký. Nếu bỏ, mất dữ liệu/quan hệ riêng của hồ sơ sinh viên hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Điều kiện, đề xuất và đăng ký; `backend/api/account.py`, `backend/api/core.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/documents.py`, `backend/services/progress.py`, `backend/services/proposals.py`, `backend/services/registration.py`, `backend/services/roster.py`, `backend/services/theses.py`.
**Vai trò thao tác:** SV xem hồ sơ của mình; Khoa nhập và xác nhận nguồn danh sách theo phân công đợt.
**Tình huống giả:** SV-DEMO-01 có MSSV giả và tài khoản thuộc Bộ môn CNTT-DEMO.
**Trạng thái sử dụng:** Đọc/ghi trực tiếp trong API/service.
**Vì sao không gộp/xóa:** Bản ghi có định danh, ràng buộc và vòng đời riêng; gộp vào bảng liên quan sẽ mất quan hệ một-nhiều hoặc quyền kiểm soát.

| Cột SQL | Tên tiếng Việt | Kiểu PostgreSQL | NULL | Default | Công dụng/ý nghĩa |
|---|---|---|---|---|---|
| `user_id` | Mã tài khoản | `UUID` | Không | `—` | Mã tài khoản; liên kết tới `user_account.id`, giữ toàn vẹn tham chiếu. |
| `student_code` | Mã số sinh viên | `VARCHAR(32)` | Không | `—` | Mã số sinh viên; phục vụ điều kiện, đề xuất và đăng ký. |
| `department_id` | Mã bộ môn | `UUID` | Không | `—` | Mã bộ môn; liên kết tới `department.id`, giữ toàn vẹn tham chiếu. |
| `display_name` | Họ tên hiển thị | `VARCHAR(255)` | Không | `—` | Họ tên hiển thị; phục vụ điều kiện, đề xuất và đăng ký. |
| `class_name` | Tên lớp | `VARCHAR(100)` | Cho phép | `—` | Tên lớp; phục vụ điều kiện, đề xuất và đăng ký. |
| `major_code` | Mã ngành | `VARCHAR(32)` | Cho phép | `—` | Mã ngành; phục vụ điều kiện, đề xuất và đăng ký. |
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |

**PK:** `id`.
**FK và quan hệ:** `department_id` → `department.id`; `user_id` → `user_account.id`.
**UNIQUE:** `student_code`; `user_id`.
**CHECK:** Không có CHECK riêng.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 25. `thesis` — Khóa luận

**Mục đích và lý do tồn tại:** Hồ sơ sau khi chốt đăng ký. Nếu bỏ, mất dữ liệu/quan hệ riêng của khóa luận hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Hồ sơ sau khi chốt đăng ký; `backend/services/registration.py`, `backend/services/theses.py`.
**Vai trò thao tác:** SV thành viên, GVHD, Trưởng bộ môn và người được giao xem đúng phạm vi; Trưởng bộ môn chốt tạo khóa luận.
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

## 26. `thesis_member` — Thành viên khóa luận

**Mục đích và lý do tồn tại:** Tư cách thành viên chính thức. Nếu bỏ, mất dữ liệu/quan hệ riêng của thành viên khóa luận hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tư cách thành viên chính thức; `backend/api/core.py`, `backend/services/progress.py`, `backend/services/registration.py`, `backend/services/theses.py`.
**Vai trò thao tác:** Chỉ phát sinh khi Trưởng bộ môn chốt đăng ký; SV/GV liên quan xem danh sách thành viên.
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

## 27. `thesis_round` — Đợt KLTN

**Mục đích và lý do tồn tại:** Đợt chính/bổ sung và thời hạn. Nếu bỏ, mất dữ liệu/quan hệ riêng của đợt kltn hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đợt chính/bổ sung và thời hạn; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/roster.py`, `backend/services/progress.py`, `backend/services/registration.py`, `backend/services/roster.py`, `backend/services/theses.py`, `backend/services/topics.py`.
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
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `academic_year_id` → `academic_year.id`.
**UNIQUE:** `academic_year_id, code`.
**CHECK:** `ck_thesis_round_round_type`: `round_type IN ('MAIN','SUPPLEMENTARY')`; `ck_thesis_round_state`: `state IN ('DRAFT','OPEN','CLOSED','ARCHIVED')`; `ck_thesis_round_time_window`: `closes_at > opens_at`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 28. `topic` — Đề tài

**Mục đích và lý do tồn tại:** Đề xuất và xét duyệt. Nếu bỏ, mất dữ liệu/quan hệ riêng của đề tài hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đề xuất và xét duyệt; `backend/api/main.py`, `backend/services/registration.py`, `backend/services/topics.py`.
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
| `id` | Khóa chính UUID | `UUID` | Không | `Ứng dụng sinh UUID` | Định danh ổn định của bản ghi; các bảng khác có thể tham chiếu bằng FK. |
| `created_at` | Thời điểm tạo | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm tạo; dùng đối chiếu trình tự và audit. |
| `updated_at` | Thời điểm cập nhật | `TIMESTAMP WITH TIME ZONE` | Không | `now()` | Thời điểm cập nhật; dùng đối chiếu trình tự và audit. |
| `row_version` | Số phiên bản bản ghi | `INTEGER` | Không | `1` | Số phiên bản bản ghi; giữ lịch sử hoặc chống ghi đè khi xử lý đồng thời. |

**PK:** `id`.
**FK và quan hệ:** `decided_by` → `user_account.id`; `department_id` → `department.id`; `proposer_user_id` → `user_account.id`; `receiving_lecturer_id` → `lecturer_profile.id`; `round_id` → `thesis_round.id`.
**UNIQUE:** `code`.
**CHECK:** `ck_topic_max_students`: `max_students BETWEEN 1 AND 3`; `ck_topic_proposer_type`: `proposer_type IN ('LECTURER','STUDENT')`; `ck_topic_state`: `state IN ('DRAFT','SUBMITTED','APPROVED','RETURNED','REJECTED','LOCKED')`.
**Index:** Chỉ index PK/UNIQUE do PostgreSQL tạo.

## 29. `topic_registration` — Đăng ký đề tài

**Mục đích và lý do tồn tại:** Tiếp nhận và chốt nhóm. Nếu bỏ, mất dữ liệu/quan hệ riêng của đăng ký đề tài hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Tiếp nhận và chốt nhóm; `backend/api/main.py`, `backend/services/evidence.py`, `backend/services/registration.py`, `backend/services/topics.py`.
**Vai trò thao tác:** Từng SV tự tham gia; GV tiếp nhận quyết định; Trưởng bộ môn chốt.
**Tình huống giả:** Nhóm DEMO gửi đăng ký, GV tiếp nhận, TBM chốt; trạng thái cũ vẫn lưu.
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

## 30. `topic_requirement` — Yêu cầu mong muốn của đề tài

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

## 31. `topic_title_version` — Lịch sử tên đề tài

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

## 32. `user_account` — Tài khoản người dùng

**Mục đích và lý do tồn tại:** Đăng nhập, khóa tài khoản và vai trò nền. Nếu bỏ, mất dữ liệu/quan hệ riêng của tài khoản người dùng hoặc không còn kiểm được lịch sử và quyền liên quan.
**Use case/API/service:** Đăng nhập, khóa tài khoản và vai trò nền; `backend/api/account.py`, `backend/api/account_admin.py`, `backend/api/auth.py`, `backend/api/dependencies.py`, `backend/api/main.py`, `backend/api/roster.py`, `backend/services/account_tokens.py`, `backend/services/evidence.py`, `backend/services/registration.py`, `backend/services/roster.py`, `backend/services/theses.py`, `backend/services/topics.py`.
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
