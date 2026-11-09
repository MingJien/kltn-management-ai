# NV6 tuần 2 — Hội đồng, bảo vệ và kết quả

## Thao tác theo vai trò

1. **TBM hoặc điều phối đợt** mở **Bảo vệ và đánh giá → Hội đồng và bảo vệ**. Lập hội đồng theo đợt, bộ môn và căn cứ phân công. Chọn đúng 5 người khác nhau gồm chủ tịch, thư ký, hai phản biện Hội đồng và một ủy viên. Phản biện Hội đồng là vai trò riêng với người viết Mẫu 8 trước bảo vệ.
2. **Người quản lý lịch** chọn đề tài đã chốt đủ điều kiện trên bản báo cáo hiện tại, nhập giờ bắt đầu, giờ kết thúc và phòng theo giờ Việt Nam. Hệ thống kiểm tra trùng phòng, trùng giảng viên và xung đột GVHD. SV và các thành viên hội đồng nhận thông báo trong tài khoản.
3. **Thư ký** ghi nhận thành phần hội đồng dự họp sau giờ bắt đầu. Cần ít nhất 3/5 người và có chủ tịch, thư ký. Chỉ người hiện diện được chấm. Sau đó ghi điểm danh từng SV. Có mặt thì mở phiếu chấm. Vắng thì ghi lý do và giữ ô điểm trống. **Chủ tịch** có thể xác nhận một mức thưởng chung cho SV (0–1), có căn cứ khi có thưởng. **Thành viên hội đồng** lưu đủ 12 tiêu chí Mẫu 6 cho từng SV. Nếu nhập hộ từ phiếu giấy, thư ký chọn đúng giảng viên và ghi căn cứ.
4. **Thư ký** nhập nội dung họp và kết luận. **Chủ tịch hoặc thư ký** chốt sau khi đủ biên bản, điểm của mọi thành viên cho từng SV có mặt và lý do của SV vắng. Điểm mỗi phiếu tối đa 10 sau khi tính thưởng. Điểm tổng hợp là trung bình các phiếu, làm tròn 1 chữ số thập phân, sau khi làm tròn mỗi phiếu 1 chữ số.
5. **Hội đồng** tải Mẫu 6 và Mẫu 9 từ bản đã chốt. **Người quản lý** khóa bảng điểm khi mọi lịch của hội đồng đã chốt, sau đó tải Mẫu 10 (Word) và Mẫu 11 (Excel). Bản in mang mã và phiên bản dữ liệu đã khóa. Việc ký diễn ra tại hội đồng. Mẫu 11 để trống ngày sinh vì hồ sơ SV hiện chưa có trường này. Bộ xuất dựng theo đề mục và cột đã đối chiếu; cần so bản in với mẫu Khoa trước khi dùng chính thức.

## Xin thôi KLTN trên hệ thống

SV gửi yêu cầu trong 14 ngày đầu kể từ mốc bắt đầu thực hiện do điều phối đợt ghi nhận, hoặc hủy yêu cầu của mình khi còn chờ. Điều phối đúng đợt chọn chấp thuận hoặc từ chối, nhập lý do và xác nhận. Hệ thống lưu mã, người xử lý, thời điểm và thông báo kết quả. Luồng này xử lý trực tiếp trong tài khoản.

Khi chấp thuận, chỉ SV đứng đơn rời nhóm. Nếu còn thành viên, nhóm giữ đề tài và cập nhật Mẫu 1–3, báo cáo và hồ sơ xét bảo vệ theo thành viên mới. Nếu là thành viên cuối, hệ thống kết thúc khóa luận và quyền tham gia. Người hướng dẫn nhận thông báo khi thành viên thay đổi.

## Đối chiếu báo cáo

Trong **Tra cứu AI → Đối chiếu báo cáo**, TBM hoặc điều phối chọn hai đề tài từ các báo cáo Word/PDF đã được quét an toàn trong phạm vi được giao. Hệ thống đối chiếu chữ có sẵn với chữ nhận dạng từ bản scan và ảnh chèn ở cả hai phía, chỉ vị trí và cụm trùng để đọc lại. Dấu hiệu ảnh trùng tệp hoặc gần giống được trình bày riêng. Kết quả chỉ hỗ trợ rà soát.

Máy chủ cần Tesseract và dữ liệu ngôn ngữ `vie+eng`. Trên Windows, ứng dụng tìm trong PATH hoặc thư mục cài Tesseract mặc định. Có thể cấu hình `KLTN_TESSERACT`, `KLTN_OCR_DATA_DIR` và `KLTN_OCR_LANG`. Mỗi báo cáo được xử lý tối đa 60 trang PDF, 24 ảnh và 24 giây OCR. Trang/ảnh không đọc đủ có cảnh báo phạm vi. Ảnh giống nhau là tín hiệu theo dấu vân tay ảnh, chưa có phân tích ngữ nghĩa hình ảnh. [Hướng dẫn cài Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html).

Cập nhật PostgreSQL qua Alembic đến revision `20261104_0021`.


Bổ sung rà soát ngày 09/11/2026. Trang bảo vệ có ô tìm theo đề tài/phòng/hội đồng, phần tạo hội đồng và xếp lịch thu gọn, tổng điểm dự kiến khi nhập Mẫu 6, danh sách phiếu/điểm danh/biên bản còn thiếu trước khi chốt. Chủ tịch hoặc thư ký có thể mở sửa bản chưa ký trước khi khóa bảng điểm hội đồng, bắt buộc lý do và xác nhận chưa ký. Dữ liệu cũ được lưu trong sự kiện lịch sử, bản in mới có phiên bản mới. Bảng điểm đã khóa được giữ nguyên.

Hệ thống lưu kết quả tổng hợp cùng bản chốt để tránh tính lại kết quả đã công bố khi quy tắc phần mềm thay đổi. Với bản cũ trước lần cập nhật này, bản tổng hợp vẫn giữ định dạng độ chính xác lịch sử.
