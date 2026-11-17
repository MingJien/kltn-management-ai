# Hệ thống quản lý khóa luận tốt nghiệp

Ứng dụng React, FastAPI và PostgreSQL phục vụ quy trình KLTN của Khoa Công nghệ và Kỹ thuật, Trường Đại học Đồng Tháp.

## Hiện trạng

- Runtime dùng PostgreSQL `kltn_management` với 55 bảng nghiệp vụ và Alembic head `20261117_0032`. Bảng `defense_absence_decision` lưu quyết định xử lý SV vắng. Lịch bổ sung liên kết với phiên gốc. Cập nhật CSDL hiện có qua Alembic.
- NV5 có giao diện và API cho tài khoản/phân quyền, danh sách SV/GV, đề tài, xét duyệt, đăng ký cá nhân/nhóm, tiếp nhận và tạo hồ sơ khóa luận/GVHD.
- Hồ sơ khóa luận hỗ trợ đề cương, mốc và báo cáo tiến độ, hạn theo loại tài liệu, phiên bản, phản hồi đúng bản nộp, đánh dấu trễ, gia hạn theo đợt, thông báo và nhật ký.
- GVHD đặt, gia hạn và đóng mốc nội bộ từng khóa luận; SV nộp và GVHD phản hồi đúng hồ sơ. Mốc riêng tách quyền với lịch chung của đợt. Giới hạn 3 khóa luận đang hướng dẫn tính cả đề tài gia hạn từ đợt cũ.
- GVHD/phản biện được chọn trong cả Khoa; gợi ý phù hợp dựa trên chuyên môn đã xác nhận, TBM quyết định trong đúng phạm vi bộ môn.
- Tệp được quét qua ClamAV cục bộ; bản chưa xác nhận an toàn bị giới hạn tải/duyệt. Kho biểu mẫu Khoa quản lý phiên bản theo đợt.
- Đổi/tách đề tài có xác nhận của nhóm, GVHD liên quan và TBM. Khi tách cá nhân, nhóm cũ tiếp tục, SV được duyệt chuyển sang hồ sơ mới; hai bên cập nhật Mẫu 1–3. Xin gia hạn qua đồng thuận từng thành viên, ý kiến GVHD và TBM ghi nhận quyết định; hết hạn đồng thuận không hủy quyền tham gia. Gia hạn/mở lại đăng ký có lịch sử, thông báo. [Thao tác](docs/design/thesis-changes-workflow.md).
- Xin thôi KLTN trong 14 ngày đầu: sinh viên gửi yêu cầu, điều phối đợt quyết định trực tiếp và hệ thống giữ lịch sử riêng từng thành viên.
- Có giờ tập trung chung tách với giờ bảo vệ dự kiến; công bố danh sách toàn hội đồng cho SV cùng bộ môn/đợt xem và tải Excel, có phiên bản và cảnh báo lịch chờ cập nhật.
- Hội đồng xếp liên tiếp một hoặc nhiều đề tài trong một lần, có thứ tự và thời lượng; lưu toàn bộ hoặc không lưu khi một lịch bị xung đột.
- Trang bảo vệ giữ nháp khi đổi tab/lưu biểu mẫu khác, kiểm soát phiên bản từng phiếu, in phiếu trống trước họp, xem báo cáo đúng phiên bản và xử lý SV vắng theo quyết định Khoa. [Kiểm chứng ngày 10/11](docs/evidence/defense-delivery-validation-2026-11-10.md).
- NV6 tuần 2 có hội đồng, lịch bảo vệ, Mẫu 6, tổng hợp điểm, Mẫu 9–11 và đối chiếu báo cáo Word/PDF theo cặp, gồm OCR khi cấu hình Tesseract. [Hướng dẫn thao tác](docs/design/nv6-defense-operations.md).
- Mẫu 6, 9, 10 và 11 điền từ tệp gốc của Khoa. Mẫu 10/11 tổng hợp toàn đợt, kể cả bảo vệ bổ sung; Mẫu 11 chọn mã học phần trước khi xuất. TBM hoặc điều phối bổ sung thông tin học vụ có căn cứ. Bản xem trước chỉ cho chỉnh trình bày; bản dùng để ký được lưu nguyên tệp để tải lại. [Hướng dẫn biểu mẫu](docs/design/defense-forms.md).
- Kho nội bộ có SV nộp bản sau bảo vệ → TBM duyệt lưu hoặc yêu cầu nộp lại, lịch sử phiên bản và quyền tải theo hồ sơ. Báo cáo theo đợt/bộ môn tổng hợp điều kiện, kết quả, điểm, xếp loại, điểm danh, tiến độ nộp lưu và danh sách thiếu dữ liệu học vụ. [Hướng dẫn](docs/design/nv6-archive-reporting.md).
- Bản in mới tự thay thế bản cũ cùng loại; tra mã 12 ký tự trên footer để đối chiếu, có thu hồi và giữ nguyên tệp lịch sử.
- Hồ sơ đã khóa có đề nghị đính chính phiếu/biên bản và TBM khác người lập duyệt; giữ bản cũ, không mở khóa tùy ý. Bản xem trước gắn phiên bản nguồn và định dạng trước khi phát hành; lịch sử bản in cảnh báo khi hồ sơ đã đổi. [Luồng đính chính và phát hành](docs/design/defense-corrections.md).
- Mẫu nhận xét Mẫu 7/8 gắn với đúng sinh viên và bản báo cáo; GV gửi nhận xét trên hệ thống, tải phiếu theo mẫu khi cần. GV xác nhận nội dung bằng tài khoản của mình; thao tác gửi là căn cứ xác nhận trên hệ thống, không có bước tải bản ký hoặc tiếp nhận giấy.
- Điểm thưởng công bố khoa học có luồng SV nộp → GVHD xác nhận → TBM duyệt từng SV; tự đưa mức đã duyệt vào phiếu Mẫu 6 và khóa căn cứ khi đã chấm. [Kiểm chứng](docs/evidence/publication-bonus-approval.md).
- Có hồ sơ chuyên môn GV, phân công theo đợt và kiểm tra điều kiện bảo vệ ở mức hiện tại.

Gia hạn KLTN theo quyết định của Khoa, tối đa 5 tháng. Kỳ bảo vệ tiếp theo theo lịch thực tế của Khoa, nằm trọn trong thời hạn được duyệt. Hết hạn không có lịch hợp lệ thì ghi nhận không đạt, giữ quyết định và lịch sử; có lịch hợp lệ chưa chốt thì hiển thị chờ đối chiếu kết quả.

Chất lượng OCR trên tập báo cáo thực tế và chatbot AI hoàn chỉnh vẫn cần được kiểm chứng tiếp.

## Chạy local

Mở hai cửa sổ PowerShell:

    Set-Location 'D:\KLTN'; .\.venv\Scripts\python.exe -m tools.run_demo_api

    npm --prefix 'D:\KLTN\frontend' run dev -- --host 127.0.0.1 --port 1573 --strictPort

Mở http://127.0.0.1:1573. Cấu hình máy và mật khẩu nằm trong .env cục bộ; không đưa lên Git.

## Kiểm tra

    .\.venv\Scripts\python.exe -m tools.validate_official_database
    npm run build --prefix 'D:\KLTN\frontend'

Các kiểm thử tích hợp dùng dữ liệu giả trong schema riêng. [Kiểm chứng mới nhất: bản in và công bố lịch hội đồng](docs/evidence/nv6-print-publication-validation-2026-11-17.md). [Đính chính và phát hành hồ sơ NV6](docs/evidence/nv6-final-closure-validation.md). [Bảng điểm toàn đợt, kho nội bộ, dashboard và bản in](docs/evidence/nv6-archive-register-validation.md). [Kết quả đối chiếu biểu mẫu trước đó](docs/evidence/nv6-export-workflow-validation.md).
