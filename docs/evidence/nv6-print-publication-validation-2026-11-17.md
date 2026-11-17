# Kiểm chứng bản in và lịch công bố NV6 ngày 17/11/2026

## Phạm vi sản phẩm

- Mẫu 6 giữ nguyên drawing/connector của tệp Excel nguồn, khôi phục hai đường kẻ dưới tên Khoa và tiêu ngữ; tăng khoảng ký trước họ tên. Giữ rich text và tiêu chí nguồn, kiểm vị trí 12 tiêu chí trước khi điền.
- Mẫu 9 đọc mẫu nội dung họp mới trong thư mục biểu mẫu nếu có; thay toàn bộ thông tin ví dụ bằng hồ sơ hiện tại, không lặp MSSV trong nội dung ý kiến/kết quả. Kết quả là tổng điểm các phiếu và trung bình, có số phiếu và xếp loại. Mẫu nguồn không nằm trong Git; thiếu nguồn tham chiếu mới thì dùng ánh xạ cũ đã hỗ trợ.
- Tên bản in gọn theo loại, đợt, mã đề tài/học phần, ngày, số lần phát hành. Footer chỉ giữ mã tra cứu 12 ký tự, bản và ngày; các hash nguồn/định dạng vẫn ở metadata.
- Lưu bản mới tự thay thế bản trước trong cùng phạm vi; tải lại bản lưu giữ nguyên byte. Tra mã và thu hồi có ACL/lý do/audit. Không hồi sinh bản cũ khi bản thay thế bị thu hồi. Luồng mở lại trước ký/chưa khóa giữ snapshot cũ; sau khóa vẫn dùng đính chính độc lập.
- Giờ tập trung tách với giờ dự kiến; chọn áp dụng chung khi tạo nhiều lịch hoặc chọn lịch chưa mở phiên để áp dụng giờ/phòng một lần. Kiểm cùng ngày, trước giờ bảo vệ, phiên bản, trùng phòng/GV; rollback cả lượt khi lỗi.
- Công bố danh sách toàn hội đồng có xem trước và kiểm fingerprint. SV được xác nhận trong cùng bộ môn/đợt xem cả các đề tài khác và tải Excel, chỉ có dữ liệu phục vụ lịch. Có phiên bản công bố, thông báo, cảnh báo khi lịch thay đổi; Excel cũ được ghi nhãn cũ/chờ cập nhật.

## Kiểm chứng đã chạy

- Toàn bộ backend: 278 ca đạt, 6 cảnh báo deprecation. Lượt đầu phát hiện dữ liệu test lấy giờ hiện tại làm lịch nên có thể đi qua nửa đêm; đã chuyển fixture sang 08:00 giờ Việt Nam và chạy tổng kiểm lại đạt.
- UI mô phỏng: 9 ca đạt; có nhập giờ tập trung chung, chọn áp dụng giờ/phòng cho lịch có sẵn, SV xem danh sách khác và tải Excel, responsive, giữ nháp, xuất/định dạng và các luồng trước đó.
- UI–API–PostgreSQL thật: 3 ca đạt trong schema test riêng, ClamAV thật. Lượt đầu bị chặn vì cơ sở nhận diện quá hạn; cập nhật bằng freshclam rồi chạy lại đạt, không bỏ kiểm quét.
- Build frontend đạt; cảnh báo kích thước bundle chính vẫn còn.
- Migration trên CSDL local: head `20261117_0032`, 55 bảng nghiệp vụ, 160 FK, 128 CHECK, 40 UNIQUE, 40 index tường minh. `alembic check` không có thay đổi chưa được migration.
- Trình duyệt riêng trên hồ sơ demo hiện dùng: mở được bản xem Word Mẫu 9 mới, mục mở lại, và xem trước danh sách công bố đúng SV/GVHD/thời gian. Chỉ đọc, không tự công bố, phát hành bản ký, mở lại hoặc sửa điểm của người dùng.

## Kiểm tra tệp xuất

Tạo bản kiểm tra local bằng bộ xuất hiện tại, không ghi bản ký vào hệ thống. Mẫu 9 dùng đúng **Mẫu nd họp của 9.Bien ban hop hoi dong cham KLTN.docx**. Kết xuất sang PDF bằng Microsoft Word chạy ẩn; xem ảnh cả hai trang sau căn gọn nhận xét: 2 trang, phần ký đi cùng kiến nghị, footer có trên từng trang. `render_docx.py` không chạy được vì thiếu LibreOffice, nên dùng Word và Poppler để kiểm thay thế. Mẫu 6 kết xuất bằng Excel chạy ẩn: 1 trang, thấy hai đường gạch chân, rich text, bảng tiêu chí và vùng ký đã tăng. Các bản PDF/PNG/DOCX/XLSX kiểm tra chỉ ở local, không commit.

Kiểm thử tích hợp xác nhận: lịch hai đề tài cùng hội đồng, chung giờ tập trung, xung đột rollback; danh sách công bố không có điểm/ngày sinh, SV ngoài phạm vi không tải được; nguồn đổi phải xem lại rồi công bố phiên bản mới. Bản in cũ tải lại đúng byte, tra mã nhận diện bản đã thay thế, quyền thu hồi và số lần phát hành đúng phạm vi. Các thử nghiệm này không khẳng định mọi độ dài nội dung và mọi máy in đã được kiểm.
