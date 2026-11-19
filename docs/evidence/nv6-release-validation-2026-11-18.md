# Kiểm chứng bàn giao NV6 ngày 18/11/2026

Phạm vi từ phản biện đến bảng điểm, kho nội bộ, báo cáo và dữ liệu học vụ. Dùng hồ sơ giả trong schema kiểm thử riêng. Tạo/kích hoạt tài khoản qua giao diện và các chức năng AI không thuộc lượt nghiệm thu này.

- Backend đạt 266 ca nghiệp vụ, còn 6 cảnh báo deprecation. Kiểm cả trường hợp đổi lịch để lại sinh viên vẫn đủ điều kiện nhưng thiếu lịch: API chặn Mẫu 10/11. Khi dữ liệu học vụ dùng để điền mẫu cũ đổi mà phiên bảo vệ giữ nguyên, mã đối chiếu Mẫu 9 đổi và yêu cầu phát hành lại bản đã xem bị từ chối.
- 14 ca trình duyệt đạt cho thao tác kho, hội đồng, dashboard và thông báo. Kiểm giữ nội dung chưa lưu khi từ chối chuyển mục, bố cục đến 320 px và các màn đã khai báo kiểm tra accessibility.
- 12 ca trình duyệt bổ sung đạt trên API/PostgreSQL thật, gồm kho, bốn vai trò từ quản lý đợt đến hồ sơ nộp, thay đổi/gia hạn, phản biện và nộp/duyệt tài liệu. Ca phản biện đã kiểm xác nhận điện tử, tải Mẫu 7/8 sau gửi, báo cáo đổi phiên bản và bảo toàn nhận xét cũ. Ca tài liệu đã kiểm việc chặn phản hồi lên phiên bản vừa bị thay thế mà vẫn giữ bản nháp.
- Ca kho thật chạy bằng trình duyệt, cookie tài khoản, PostgreSQL và ClamAV. SV nộp → TBM xem PDF → trả → SV nộp v2 → TBM duyệt → tra không dấu và tải đúng byte → thu hồi có lý do. Tệp lịch sử và quyết định duyệt cũ còn trong chi tiết. Tài khoản ngoài phạm vi bị từ chối khi mở liên kết trực tiếp. Kiểm viewport 320, 390, 768 và 1440 px cùng accessibility tự động.
- Báo cáo đếm nộp lưu theo khóa luận, điểm và kết quả theo SV. Kiểm kết quả của phiên bổ sung không đếm thêm SV và trường hợp hết hạn gia hạn không rơi vào nhóm chưa xếp lịch. Khi còn đề nghị đính chính kết quả, kho chặn nộp/duyệt bản hoàn thiện.
- Build frontend đạt. Cảnh báo kích thước gói chính của Vite vẫn còn. Alembic local ở head `20261118_0033`, 55 bảng nghiệp vụ, `alembic check` không có thay đổi chưa được migration.
- Kiểm chỉ đọc trên demo đang dùng: TBM vào hàng hồ sơ nộp lưu và mở đúng đề tài mượn sách. Mở bản xem Mẫu 9 và xác nhận nút phát hành chỉ khả dụng sau khi Word hiển thị. Không nộp lưu, sửa điểm, gửi thông báo hay phát hành bản ký trên hồ sơ demo.

## Bổ sung kiểm chứng thống kê ngày 19/11/2026

- 17 ca pytest đạt trên schema PostgreSQL riêng, gồm tái sử dụng số liệu trước hạn 15 phút, tính lại khi hết hạn hoặc khi yêu cầu làm mới, từ chối tài khoản đã bị thu hồi quyền và lấy đúng trạng thái của bản nộp lưu mới nhất.
- 1 ca trình duyệt đạt trên API và PostgreSQL với tài khoản giả. Nút **Làm mới thống kê** gửi yêu cầu tính lại và trang hiển thị thời điểm cập nhật. Build frontend và kiểm tra đặc tả OpenAPI đạt.

## Kiểm tra quy trình từ đăng ký đến lưu kho ngày 19/11/2026

- Toàn bộ 280 ca pytest đạt. Ca tích hợp nhóm hai SV tạo đăng ký, GV nhận hướng dẫn, xử lý hồ sơ trước bảo vệ, lập hội đồng, ghi điểm và biên bản, xuất bảng điểm, rồi nộp và duyệt bản lưu trên cùng khóa luận. Có kiểm quyền nộp theo từng SV, liên kết trực tiếp, phiên bản gửi trùng, trạng thái **Hoàn thành** sau duyệt và **Đã bảo vệ** sau thu hồi. Chạy lại riêng 9 ca hội đồng và kho sau khi chỉnh liên kết phiên bảo vệ, cả 9 đạt.
- 63 ca Playwright trong 30 tệp kiểm thử đạt trên Chromium qua các lượt chạy và chạy lại sau sửa. Luồng nộp, trả, nộp lại, xem, duyệt và thu hồi chạy với cookie, API, PostgreSQL và ClamAV thật trong schema riêng. Các ca chuyên kiểm bố cục, bản nháp hoặc trạng thái khó tái hiện có dùng phản hồi API giả lập.
- Kiểm tra 8 màn hình từ danh sách đề tài tới kho ở chiều rộng 320, 390, 768 và 1440 px, gồm chiều rộng sử dụng được của vùng nội dung và đóng/mở menu bằng bàn phím. Kiểm tra axe trên danh sách và chi tiết kho đạt bộ tiêu chí tự động đã khai báo. Đường dẫn từ thống kê giữ đúng đợt kể cả khi chưa có hồ sơ sau bảo vệ.
- PostgreSQL trả trước mã đề tài và MSSV khớp chính xác, kể cả mã có số 0 ở đầu. Đã kiểm tra tiếng Việt có dấu và không dấu, Unicode dạng tổ hợp, ký tự tìm kiếm `%` và `_`, phân trang và dữ liệu phiên bản cũ. Chạy migration hai lần trên bộ dữ liệu kiểm thử giữ nguyên lịch sử và số phiên bản sau lần đầu.
- Đã áp dụng migration `20261119_0034` trên CSDL local. Kiểm tra sau nâng cấp có 55 bảng nghiệp vụ, không còn khóa luận có bản lưu mới nhất đã duyệt mà trạng thái vẫn là **Đã bảo vệ**. `alembic check` và đối chiếu OpenAPI đạt.
- Build TypeScript/Vite đạt. Tải trình xem theo loại tệp giúp gói JavaScript đầu vào giảm từ 397,90 KB xuống 198,07 KB sau gzip. Vite còn cảnh báo kích thước gói đầu vào trước nén. Bộ pytest ghi nhận 6 cảnh báo deprecation của các thư viện.
