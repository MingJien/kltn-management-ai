# Luồng đề tài và đăng ký đang triển khai

Quy tắc được xác nhận ngày 04/10/2026. Luồng hiện tại dùng đăng nhập email/mật khẩu và cookie phiên: **GV tạo → bộ môn duyệt → SV tự đăng ký → GV tiếp nhận chấp nhận/từ chối → TBM chốt**. Xem [đặc tả API](openapi.yaml); khi chạy backend, OpenAPI runtime ở `/openapi.json` và giao diện thử API ở `/docs`.

## Đề tài có sẵn

1. GV cùng bộ môn tạo bản nháp: năm học/đợt đang mở, tên, mô tả, tối đa 1–3 SV, yêu cầu bổ sung. Mã theo năm được cấp riêng và giữ nguyên khi đổi tên.
2. GV gửi; TBM có phân công còn hiệu lực đúng bộ môn duyệt, trả lại hoặc từ chối. Không được tự duyệt đề tài mình tạo. Sửa tên giữ phiên bản cũ; trả lại/từ chối phải có lý do.
3. SV xem đề tài đã duyệt và số chỗ còn lại. Mỗi SV tự đăng ký bằng tài khoản của mình; không chọn, mời hoặc xác nhận thay SV khác. Người đầu tiên là đại diện. Các bạn tiếp theo tham gia **cùng đăng ký** của đề tài.
4. Đại diện có thể gửi khi nhóm có một người; số SV tối đa không phải số tối thiểu bắt buộc. Từng người phải còn đủ điều kiện theo snapshot mới nhất, tài khoản hoạt động và cùng bộ môn. Một SV chỉ có một đăng ký hoạt động trong một đợt.
5. GV tiếp nhận xem hồ sơ/minh chứng rồi nhận hoặc từ chối có lý do. Từ chối kết thúc đăng ký, giải phóng thành viên; hồ sơ cũ vẫn được lưu.
6. Khi còn chỉ tiêu **và còn thời gian đăng ký**, SV khác vẫn được bổ sung, kể cả nhóm đã gửi hoặc được nhận. Nhóm có thành viên mới trở về `SUBMITTED`, tăng `row_version`, xóa quyết định hiện hành và chờ GV xét lại. Dấu vết quyết định trước nằm trong `audit_event`; không mặc nhiên nhận người mới theo quyết định cũ. `FINALIZED` không bổ sung tại đây.
7. Sau khi GV chấp nhận, TBM xác nhận chốt trên giao diện. GV đã tiếp nhận được ghi làm GVHD chính. Trước khi chốt, API kiểm lại tài khoản và kết quả đủ điều kiện hiện hành của từng SV; nếu thay đổi thì trả `409` để Khoa rà soát, không tạo khóa luận.

Đủ số SV thì đóng nhận thêm **ngay khi đăng ký**, không chờ GV chấp nhận. Quá hạn cũng đóng. Các yêu cầu GPA/kỹ năng riêng là thông tin để GV xét mức phù hợp, không tự thay điều kiện đăng ký chính thức của đợt.

## Đề tài SV đề xuất

SV lập đề xuất và đăng ký **cá nhân trước**, chọn GV mong muốn, rồi gửi để bộ môn xét nội dung. Trước khi duyệt, đề xuất không hiện trong danh sách đề tài có sẵn của SV khác. TBM sửa tên/xác nhận hoặc chọn GV phù hợp cùng bộ môn; sau khi duyệt, các SV khác tự tham gia khi còn chỗ và còn hạn. GV tiếp nhận được từ chối có lý do. Trả lại thì SV sửa nội dung rồi gửi lại.

## CSDL và xử lý đồng thời

- `topic.max_students` là chỉ tiêu tối đa; `topic_registration.expected_member_count` lưu quy mô dự kiến theo chỉ tiêu lúc lập đăng ký, trong khoảng 1–3. **Không dùng cột này bắt nhóm đủ người mới gửi.** Danh sách người thực tế nằm trong `registration_member`.
- Mỗi đăng ký mới chỉ thêm chính SV đang đăng nhập, ghi `ACCEPTED`, tài khoản và thời điểm. `PENDING/DECLINED` trong schema chỉ giữ dữ liệu/lịch sử cũ; API cũ chỉ còn hỗ trợ tự xác nhận bản nháp cũ. Không tạo lời mời mới.
- FK/CHECK/UNIQUE bảo vệ liên kết, tập giá trị và một đăng ký hoạt động/SV/đợt. Service khóa `topic → topic_registration → student_profile`, kiểm số chỗ trong transaction; hai yêu cầu tranh chỗ cuối chỉ một yêu cầu thành công. Quy tắc một nhóm hiện hành/đề tài được service kiểm, không được coi là FK/CHECK đã kiểm toàn bộ nghiệp vụ.
- Hồ sơ cạnh tranh theo cách cũ được báo rõ và giữ nguyên để đối chiếu; migration không tự hủy/đổi thành viên hoặc suy diễn đồng ý.
- Quyết định GV/TBM dùng `If-Match` và `row_version`; dữ liệu đã đổi thì trả 409 để người quyết định đọc lại. SV/GV ở ngoài phạm vi không được xem hoặc thao tác hồ sơ.
- API trả dữ liệu cá nhân với `Cache-Control: private, no-store`; tệp không có URL công khai. Mật khẩu chỉ giữ mã băm; bộ tài khoản demo chỉ nằm trong tệp local bị Git ignore.

## Minh chứng

Mỗi SV tự tải PDF/PNG/JPEG tối đa 5 MB, kiểm đuôi và chữ ký định dạng. Trong bản nháp/trả lại được thay tệp; sau gửi, tệp cũ khóa. SV vừa bổ sung vào nhóm đã gửi có thể tải **minh chứng lần đầu** trước khi GV xét lại; tải sẽ tăng phiên bản để quyết định cũ không dùng dữ liệu trước thay đổi. Tệp giữ riêng, không nạp AI. Chưa có antivirus; trạng thái `QUARANTINED` và tải bắt buộc dạng attachment không đồng nghĩa đã quét sạch.

## Giao diện và kiểm chứng

Menu hiển thị chức năng theo vai trò: Tổng quan, Đề tài, Đăng ký, Tra cứu thử nghiệm, quản trị tài khoản, danh sách đủ điều kiện và quản lý đợt KLTN. ADMIN tạo đợt nháp rồi mở/đóng kèm căn cứ; quyền xác nhận đủ điều kiện vẫn phải được gán riêng theo đợt. Tổng quan đọc dữ liệu trong phạm vi tài khoản; đề tài có tìm kiếm/phân trang, chi tiết/duyệt trong hộp thoại, lỗi tiếng Việt và khóa nút khi đang xử lý. Có hỗ trợ bàn phím, màn hình nhỏ, tiêu đề trang, `lang=vi`; ứng dụng có đăng nhập đặt `noindex,nofollow`, không quảng bá hồ sơ SV lên công cụ tìm kiếm.

Chạy kiểm xuyên suốt: `python -m tools.run_e2e`. Script dựng schema tên ngẫu nhiên riêng trong `kltn_management`, tạo tài khoản/dữ liệu giả, chạy API ở 8001 và Vite ở 5174, rồi xóa đúng schema do lượt kiểm tạo. Không dùng dữ liệu demo `public` và không dừng server của người dùng. Mã kiểm: [Playwright](../../frontend/e2e/registration.spec.ts); kết quả hiện trực tiếp trong terminal.

Quản lý thay đổi GVHD sau khi chốt, tiến độ và tài liệu thuộc các giai đoạn tiếp theo. Gửi email thật vẫn cần SMTP/HTTPS và danh sách thật do Khoa cấp khi vận hành.
