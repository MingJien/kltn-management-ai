# Kiểm chứng bàn giao NV6 ngày 18/11/2026

Phạm vi từ phản biện đến bảng điểm, kho nội bộ, báo cáo và dữ liệu học vụ. Dùng hồ sơ giả trong schema kiểm thử riêng. Tạo/kích hoạt tài khoản qua giao diện và các chức năng AI không thuộc lượt nghiệm thu này.

- Backend đạt 266 ca nghiệp vụ, còn 6 cảnh báo deprecation. Kiểm cả trường hợp đổi lịch để lại sinh viên vẫn đủ điều kiện nhưng thiếu lịch: API chặn Mẫu 10/11. Khi dữ liệu học vụ dùng để điền mẫu cũ đổi mà phiên bảo vệ giữ nguyên, mã đối chiếu Mẫu 9 đổi và yêu cầu phát hành lại bản đã xem bị từ chối.
- 14 ca trình duyệt đạt cho thao tác kho, hội đồng, dashboard và thông báo. Kiểm giữ nội dung chưa lưu khi từ chối chuyển mục, bố cục đến 320 px và các màn đã khai báo kiểm tra accessibility.
- 12 ca trình duyệt bổ sung đạt trên API/PostgreSQL thật, gồm kho, bốn vai trò từ quản lý đợt đến hồ sơ nộp, thay đổi/gia hạn, phản biện và nộp/duyệt tài liệu. Ca phản biện đã kiểm xác nhận điện tử, tải Mẫu 7/8 sau gửi, báo cáo đổi phiên bản và bảo toàn nhận xét cũ. Ca tài liệu đã kiểm việc chặn phản hồi lên phiên bản vừa bị thay thế mà vẫn giữ bản nháp.
- Ca kho thật chạy bằng trình duyệt, cookie tài khoản, PostgreSQL và ClamAV. SV nộp → TBM xem PDF → trả → SV nộp v2 → TBM duyệt → tra không dấu và tải đúng byte → thu hồi có lý do. Tệp lịch sử và quyết định duyệt cũ còn trong chi tiết. Tài khoản ngoài phạm vi bị từ chối khi mở liên kết trực tiếp. Kiểm viewport 320, 390, 768 và 1440 px cùng accessibility tự động.
- Báo cáo đếm nộp lưu theo khóa luận, điểm và kết quả theo SV. Kiểm kết quả của phiên bổ sung không đếm thêm SV và trường hợp hết hạn gia hạn không rơi vào nhóm chưa xếp lịch. Khi còn đề nghị đính chính kết quả, kho chặn nộp/duyệt bản hoàn thiện.
- Build frontend đạt. Cảnh báo kích thước gói chính của Vite vẫn còn. Alembic local ở head `20261118_0033`, 55 bảng nghiệp vụ, `alembic check` không có thay đổi chưa được migration.
- Kiểm chỉ đọc trên demo đang dùng: TBM vào hàng hồ sơ nộp lưu và mở đúng đề tài mượn sách. Mở bản xem Mẫu 9 và xác nhận nút phát hành chỉ khả dụng sau khi Word hiển thị. Không nộp lưu, sửa điểm, gửi thông báo hay phát hành bản ký trên hồ sơ demo.
