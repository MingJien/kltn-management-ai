# Kiểm chứng xếp lịch, nhận xét và trình bày bản xuất ngày 17/11/2026

## Sản phẩm cập nhật

- Xếp một hoặc nhiều đề tài của một hội đồng trong một lần: chọn thứ tự, giờ bắt đầu, thời lượng, khoảng nghỉ, phòng. Mỗi đề tài có phiên và biên bản riêng. Lưu một giao dịch; một lịch xung đột thì không lưu lịch nào trong danh sách.
- Mẫu 7/8 xác nhận bằng tài khoản người được phân công. Bỏ API tải bản ký mới/quét bản ký/ghi biên nhận giấy, bỏ các bước ký bắt buộc trên UI. Các tệp và căn cứ lịch sử đã có giữ chế độ đọc. Tải phiếu nhận xét là tùy chọn.
- Trước khi xếp lịch, mọi phản biện đang được phân công phải gửi Mẫu 8 cho từng SV trên đúng báo cáo. Hai người thì thu đủ hai người; việc này tách với ba căn cứ xét điều kiện cấp Trường. UI hiện số phiếu đã gửi/cần có theo phân công.
- Thành viên hội đồng xem nhanh đúng báo cáo của phiên bằng vùng đọc PDF/Word. Thư ký tổng hợp Mẫu 9, nhìn được nhận xét đã lưu và nhập riêng ý kiến phát biểu bổ sung.
- Thư ký chỉnh phần diễn giải trực tiếp trên bản xem Mẫu 6/9. Chỉ gửi vị trí ngắt dòng/tab và thuộc tính chữ về máy chủ; không gửi nội dung thay thế. Nội dung và điểm từ hồ sơ, có kiểm phiên bản trước phát hành. Giữ rich text của các ô cố định Mẫu 6 từ tệp gốc, kể cả đoạn đậm/không đậm trong cùng ô.

## Kiểm chứng

- Toàn bộ backend: 278 ca đạt, 6 cảnh báo deprecation. Sau chỉnh chiều cao phần nhận xét và bản xem bảng, chạy lại nhóm nghiệp vụ/lịch/xuất/OpenAPI: 11 ca đạt.
- UI với API mô phỏng: 8 ca đạt, gồm xếp hai đề tài một lần, giờ nghỉ, đổi lịch, bảo vệ nội dung khi Enter/Tab/nhập ký tự và đổi định dạng trực tiếp, giữ nháp, Mẫu 11, đính chính, xử lý vắng.
- UI–API–PostgreSQL thật: 3 ca đạt qua `defense-workspace.spec.ts` và `workflow-notices.spec.ts`; dùng schema riêng, ClamAV thật, không dùng lại schema nghiệp vụ.
- Build frontend đạt; còn cảnh báo kích thước gói chính của Vite.
- Đọc bằng trình duyệt riêng trên CSDL demo hiện dùng: mở đủ 5 phiếu Mẫu 6, mở bản xem từ mẫu gốc và vùng định dạng, đối chiếu 4 nhận xét demo mới lưu và mở nhanh báo cáo chỉ đọc. Ảnh kiểm tra ở local, không đưa vào Git. Không chốt hoặc khóa phiên.
- Việc bổ sung bốn phiếu demo thực hiện qua dịch vụ `save_marks` bằng đúng tài khoản của từng người chấm, có kiểm quyền, phiên bản và audit; giữ nguyên phiếu đã có của người dùng. Đây không phải bốn lượt nhập tay trên UI.

Các ca mới xác nhận rollback cả danh sách khi lịch thứ hai xung đột, chấp nhận hai phiên liền kề, thu đủ cả hai phản biện và mọi SV, giữ font/rich runs của các ô nguồn sau lưu XLSX. Kiểm nguồn mới áp dụng Mẫu 6; các mẫu Word/Excel khác vẫn qua hồi quy bộ xuất hiện có. Bản xem trình duyệt không thay cho Print Preview của Word/Excel; lượt này không khẳng định đã in thử mọi biểu mẫu và mọi độ dài nội dung trên máy in thực tế.
