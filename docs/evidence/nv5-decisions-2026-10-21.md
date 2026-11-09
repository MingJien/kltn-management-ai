# NV5 theo quyết định nghiệp vụ — 21/10/2026

Ghi nhận việc sửa mã theo 7 quyết định đã chốt. Trạng thái kiểm chứng được ghi trung thực: **chưa chạy pytest/E2E** vì chưa có database kiểm thử riêng.

## Đã sửa

1. **GVHD**: luồng đề cử/đổi GVHD đã bị vô hiệu hóa ở API (route không còn) và UI; dữ liệu phân công cũ vẫn đọc được trong lịch sử. GV được ghi là GVHD chính ngay khi Trưởng bộ môn chốt.
2. **Mốc tiến độ**: ADMIN cấp/thu hồi `KLTN_COORDINATOR` theo đợt cho giảng viên đang hoạt động; người được giao mở/gia hạn/đóng mốc trong đợt, gia hạn bắt buộc có lý do và ghi audit. Quyền điều phối không kèm quyền duyệt học thuật. Lịch sử mốc cấp đợt hiển thị ở tab Tiến độ cho mọi thành viên đọc được hồ sơ, qua `/theses/{id}/milestone-history`.
3. **CSDL kiểm thử**: `tools/run_e2e.py` từ chối `kltn_management`; chỉ chạy khi `DATABASE_URL` trỏ database kiểm thử riêng. Không tạo schema, không ghi hay dọn dữ liệu trong `kltn_management`.
4. **Biểu mẫu**: bỏ sinh mẫu trắng bằng code. `form_templates` chỉ đọc nguyên bản `docs/BieuMau/mau 2...docx` và `mau 3...docx`; thiếu tệp thì trả 409 “chưa có mẫu chính thức”. `docs/BieuMau/` và `docs/QuyDinh/` được thêm vào `.gitignore`, không đưa bản sao lên Git.
5. **Tệp chưa quét**: tệp mới vẫn vào vùng cách ly (`QUARANTINED`). Tải xuống, duyệt tài liệu/đề cương và dùng làm minh chứng tiến độ đều trả 409 khi chưa `CLEAN`; UI ghi “Đang cách ly – chưa quét”. Không có mã nào tự gán `CLEAN`.
6. **Audit và toàn vẹn tệp**: audit mốc cấp đợt hiện trong tab Tiến độ; thêm `tools/check_file_integrity.py` (chỉ đọc) liệt kê metadata thiếu tệp, tệp thiếu metadata, sai kích thước/SHA-256, khóa lưu trữ lạ. Thay minh chứng giữ tệp cũ và ghi audit `REGISTRATION_EVIDENCE_REPLACED`; gỡ liên kết khi tham gia lại ghi `REGISTRATION_EVIDENCE_LINK_CLEARED`. Rollback khi lưu/xóa tệp lỗi không che lỗi gốc; tệp còn lại được công cụ đối soát báo là tệp thiếu metadata. Đã bổ sung kiểm thử cho các tình huống này (chưa chạy — xem BLOCKED).
7. **Bản in**: endpoint `print-copy` trả 409 và không tạo tệp, vì chưa có bộ sinh bản in từ mẫu chính thức. UI không còn nút xuất bản in; không giả lập “đã xuất”.

## Kiểm chứng đã chạy

- `python -m py_compile` các tệp backend/tools đã sửa: **PASS**.
- `npx tsc --noEmit -p tsconfig.json --incremental false`: **PASS**.
- `npm run build --prefix frontend`: **PASS**.
- `python -m tools.export_runtime_openapi --check`: **PASS** (OpenAPI đã cập nhật theo `ProposalVersionOut.scan_state`).
- Import smoke `backend.api.main` + các service đã sửa: **PASS**.
- `python -m tools.check_file_integrity --help`: **PASS** (chưa chạy đối soát thật vì cần database).

## BLOCKED

- `pytest tests -q`: **BLOCKED** — bộ test tích hợp dùng `DATABASE_URL` hiện hành; chưa có database kiểm thử riêng nên không chạy, không tạo schema và không dọn dữ liệu trong `kltn_management`.
- `python -m tools.run_e2e`: **BLOCKED** cùng lý do; script đã được sửa để từ chối `kltn_management`.
- Kiểm thử giao diện trên trình duyệt trong lượt này: **chưa chạy** vì thao tác sẽ dùng database nghiệp vụ. Cần khởi động lại API local để nạp mã mới khi có môi trường kiểm thử phù hợp.

Kết quả trong `docs/evidence/official-db-validation.md` là của lần chạy trước các thay đổi này; không dùng để khẳng định hành vi mới.

## Hạn chế đang được báo đúng

- Chưa có máy quét tệp thật nên mọi tệp mới ở trạng thái cách ly; luồng duyệt/tải tệp bị hạn chế cho đến khi có kết quả quét.
- Chưa có bộ sinh bản in từ mẫu chính thức nên chưa xuất được bản in.
