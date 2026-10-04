# ADR-004 — Ranh giới dữ liệu gửi Gemini

## Trạng thái

Quyết định thiết kế cập nhật theo phiếu góp ý GV ngày 03/10/2026. Runtime Gemini **chưa được bật**.

## Quyết định

Backend chỉ được cân nhắc gửi **câu hỏi đã lọc** và trích đoạn từ **quy định chính thức hoặc tài liệu đã công bố**. Không gửi tên, mã số sinh viên, điểm, tình trạng kỷ luật/án tích, hay báo cáo chưa công bố của người khác. Quyền xem tài liệu trong hệ thống không tự động đồng nghĩa được gửi tài liệu đó ra dịch vụ bên ngoài.

Trước lời gọi Gemini phải có bộ lọc nguồn theo trạng thái công bố, bộ lọc câu hỏi/dữ liệu cá nhân, phép kiểm quyền và log chỉ giữ metadata. Nếu chưa chứng minh được các kiểm soát này bằng thử nghiệm, hệ thống chỉ trả kết quả truy xuất kèm nguồn (`RETRIEVAL_ONLY`). Key chỉ ở backend, không vào frontend hoặc Git.

## Lý do và giới hạn

Bản prototype hiện truy xuất được dữ liệu giả trong Qdrant nhưng chưa kết nối Gemini. Hàm RAG chặn provider bên ngoài khi ranh giới dữ liệu chưa được triển khai, tránh vô ý chuyển đoạn nội bộ. Tài liệu lấy từ kho là dữ liệu không tin cậy, không được thay chỉ thị của ứng dụng. Gemini không có quyền duyệt đề tài, chấm điểm, ký hoặc sửa trạng thái.

## Điều kiện mở lại

Sau khi triển khai bộ lọc và kiểm thử cả trường hợp tài liệu nội bộ, tài liệu chưa công bố, câu hỏi chứa PII và prompt injection, mới xem xét bật provider theo chính sách được Khoa/Trường chấp thuận. Không suy diễn quyết định thiết kế này thành văn bản cho phép chuyển dữ liệu thật của Trường.

Nguồn: phiếu góp ý tiến độ 30/09–07/10/2026, lưu local; [yêu cầu AI](../requirements/business-requirements.md); [prototype](../ai/prototype.md).
