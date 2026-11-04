# Xin thôi và cập nhật hồ sơ nhóm ngày 04/11/2026

## Thay đổi sản phẩm

- Thẻ đơn hiển thị bốn mốc và người cần thao tác tiếp; có nhãn đã tiếp nhận/chờ kết quả.
- Điều phối có thể đính kèm PDF/DOCX kết quả riêng với bản đơn đã ký. Phạm vi truy cập theo đúng đơn; tệp chưa sạch chặn ghi nhận kết quả nếu đã đính kèm. Lịch sử giữ tham chiếu các bản trước.
- Người dùng cho phép dùng tạm `Don_xin_thoi_thuc_hien_KLTN.docx` từ kho máy chủ. Có kiểm tra thông tin trước khi tải DOCX, tự điền thông tin và lý do, đánh dấu mẫu tạm và mã đơn. Mẫu gốc được đọc, không sửa, không đưa lên Git. Thay mẫu cần kiểm ánh xạ lại.
- Nhóm còn một SV tiếp tục đề tài, không mở thêm chỗ đăng ký vào khóa luận đã tiếp nhận. Mở nộp lại Mẫu 1a/1b trong cùng đăng ký; yêu cầu cập nhật kế hoạch Mẫu 2 và đề cương Mẫu 3. Phiên bản cũ được giữ. Nhận xét/xét bảo vệ chờ Mẫu 1 hiện hành sạch, Mẫu 2 mới được tiếp nhận, đề cương mới được duyệt lại và báo cáo mới.

## Kiểm chứng

- Backend: `tests/test_withdrawals.py tests/test_registration_forms.py tests/test_nv6_evaluation.py`: **37 đạt**, trên schema PostgreSQL riêng. Có kiểm chứng file kết quả cách ly, phạm vi người xem, xuất đúng thông tin và mẫu gốc không thay đổi.
- TypeScript: **đạt**.
- Source bàn giao được lấy riêng từ Git index, tách các sửa local ngoài tác vụ: TypeScript và kịch bản `withdrawals.spec.ts` **đạt**. Kịch bản chấp nhận cả câu xác nhận bản ký của phiên bản NV6 cũ và câu xác nhận nội dung của giao diện local mới.
- Playwright `withdrawals.spec.ts`: **1/1 đạt**, nhóm sau rút nộp Mẫu 1a, Mẫu 2 được GVHD tiếp nhận, đề cương v2 được chốt và xét lại bảo vệ. Cookie/API/PostgreSQL/ClamAV thật; một số chuẩn bị dữ liệu qua API, các bước chính qua trình duyệt.
- Playwright `student-withdrawal-demo.spec.ts`: **1/1 đạt**, bao gồm mở hộp kiểm tra, tải DOCX mẫu tạm và điều phối bổ sung/tải minh chứng kết quả riêng.
- DOCX dữ liệu giả đã xuất PDF bằng Microsoft Word và xem hai trang PNG. Thông tin và lý do hiển thị đúng trong mẫu tạm hai trang. Word phát cảnh báo RPC khi kết thúc ứng dụng, nhưng PDF/PNG đã được tạo và mở xem. Bản dài có thể tiếp trang; người dùng cần kiểm tra Word trước khi ký. Tệp QA chỉ giữ local.

Kết quả trên workspace hiện tại không thay cho kiểm thử toàn bộ các thay đổi local ngoài phạm vi. Chữ ký, căn cứ và quyết định trong kiểm thử là giả lập. Không xác thực chữ ký số hoặc quyết định ngoài đời thực.
