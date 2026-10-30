# Luồng đề tài và đăng ký đang triển khai

Luồng NV5 hiện tại dùng đăng nhập email/mật khẩu và cookie phiên: **GV tạo → bộ môn duyệt → SV tự đăng ký → GV chấp nhận chính thức, tạo khóa luận và GVHD trong cùng transaction**. Không có bước TBM chốt đăng ký thêm sau khi GV đã nhận. Xem [đặc tả API](openapi.yaml); khi chạy backend, OpenAPI runtime ở `/openapi.json` và giao diện thử API ở `/docs`.

## Đề tài có sẵn

1. GV cùng bộ môn tạo bản nháp: năm học/đợt đang mở, tên, mô tả, tối đa 1–3 SV, yêu cầu bổ sung. Mã theo năm được cấp riêng và giữ nguyên khi đổi tên.
2. GV gửi; TBM có phân công còn hiệu lực đúng bộ môn duyệt, trả lại hoặc từ chối. Không được tự duyệt đề tài mình tạo. Sửa tên giữ phiên bản cũ; trả lại/từ chối phải có lý do.
3. SV xem đề tài đã duyệt và số chỗ còn lại. Mỗi SV tự đăng ký bằng tài khoản của mình; không chọn, mời hoặc xác nhận thay SV khác. Người đầu tiên là đại diện. Các bạn tiếp theo tham gia **cùng đăng ký** của đề tài.
4. Đại diện có thể gửi khi nhóm có một người; số SV tối đa không phải số tối thiểu bắt buộc. Từng người phải còn đủ điều kiện theo snapshot mới nhất, tài khoản hoạt động và cùng bộ môn. Một SV chỉ có một đăng ký hoạt động trong một đợt.
5. GV tiếp nhận xem hồ sơ/minh chứng rồi nhận hoặc từ chối có lý do. Từ chối kết thúc đăng ký, giải phóng thành viên; hồ sơ cũ vẫn được lưu.
6. Khi còn chỉ tiêu **và còn thời gian đăng ký**, SV khác được tự bổ sung trước khi GV chấp nhận chính thức. Nhóm đã chốt không nhận thêm thành viên hoặc tự rút qua màn hình đăng ký.
7. Khi GV chấp nhận, API kiểm lại tài khoản và điều kiện hiện hành của từng SV rồi tạo khóa luận, thành viên và phân công GVHD chính trong một transaction. Nếu điều kiện thay đổi thì trả `409`, không tạo hồ sơ dở dang. Các vai trò đúng phạm vi có thể mở hồ sơ khóa luận ngay từ đăng ký.

Đủ số SV thì đóng nhận thêm **ngay khi đăng ký**, không chờ GV chấp nhận. Quá hạn cũng đóng. Các yêu cầu GPA/kỹ năng riêng là thông tin để GV xét mức phù hợp, không tự thay điều kiện đăng ký chính thức của đợt.

## Đề tài SV đề xuất

SV lập đề xuất và đăng ký **cá nhân trước**, chọn GV mong muốn, rồi gửi để bộ môn xét nội dung. Trước khi duyệt, đề xuất không hiện trong danh sách đề tài có sẵn của SV khác. TBM sửa tên/xác nhận hoặc chọn GV phù hợp cùng bộ môn; sau khi duyệt, các SV khác tự tham gia khi còn chỗ và còn hạn. Khi GV từ chối, hồ sơ chờ TBM chọn GV khác hoặc trả lại cho SV sửa và gửi lại; thành viên vẫn được giữ để tránh đăng ký đồng thời nơi khác. Các quyết định giữ lịch sử.

## CSDL và xử lý đồng thời

- `topic.max_students` là chỉ tiêu tối đa; `topic_registration.expected_member_count` lưu quy mô dự kiến theo chỉ tiêu lúc lập đăng ký, trong khoảng 1–3. **Không dùng cột này bắt nhóm đủ người mới gửi.** Danh sách người thực tế nằm trong `registration_member`.
- Mỗi đăng ký mới chỉ thêm chính SV đang đăng nhập, ghi `ACCEPTED`, tài khoản và thời điểm. `PENDING/DECLINED` trong schema chỉ giữ dữ liệu/lịch sử cũ; API cũ chỉ còn hỗ trợ tự xác nhận bản nháp cũ. Không tạo lời mời mới.
- FK/CHECK/UNIQUE bảo vệ liên kết, tập giá trị và một đăng ký hoạt động/SV/đợt. Service khóa `topic → topic_registration → student_profile`, kiểm số chỗ trong transaction; hai yêu cầu tranh chỗ cuối chỉ một yêu cầu thành công. Quy tắc một nhóm hiện hành/đề tài được service kiểm, không được coi là FK/CHECK đã kiểm toàn bộ nghiệp vụ.
- Hồ sơ cạnh tranh theo cách cũ được báo rõ và giữ nguyên để đối chiếu; migration không tự hủy/đổi thành viên hoặc suy diễn đồng ý.
- Quyết định GV/TBM dùng `If-Match` và `row_version`; dữ liệu đã đổi thì trả 409 để người quyết định đọc lại. SV/GV ở ngoài phạm vi không được xem hoặc thao tác hồ sơ.
- API trả dữ liệu cá nhân với `Cache-Control: private, no-store`; tệp không có URL công khai. Mật khẩu chỉ giữ mã băm; bộ tài khoản demo chỉ nằm trong tệp local bị Git ignore.

## Minh chứng

Minh chứng đăng ký được giữ riêng, không nạp AI; từng SV chỉ thao tác minh chứng của mình. Minh chứng báo cáo tiến độ là tệp tùy chọn nộp trực tiếp trong mục Tiến độ, được gửi cùng báo cáo trong một transaction. Tài liệu/đề cương/minh chứng tiến độ dùng ClamAV thật; chỉ trạng thái `CLEAN` được tải và dùng để xác nhận. `QUARANTINED`, `FAILED` hoặc `INFECTED` không đồng nghĩa đã an toàn.

## Giao diện và kiểm chứng

Menu hiển thị chức năng theo vai trò: Tổng quan, Đề tài, Đăng ký, Tra cứu thử nghiệm, quản trị tài khoản, danh sách đủ điều kiện và quản lý đợt KLTN. ADMIN tạo đợt nháp rồi mở/đóng kèm căn cứ; quyền xác nhận đủ điều kiện vẫn phải được gán riêng theo đợt. Tổng quan đọc dữ liệu trong phạm vi tài khoản; đề tài có tìm kiếm/phân trang, chi tiết/duyệt trong hộp thoại, lỗi tiếng Việt và khóa nút khi đang xử lý. Có hỗ trợ bàn phím, màn hình nhỏ, tiêu đề trang, `lang=vi`; ứng dụng có đăng nhập đặt `noindex,nofollow`, không quảng bá hồ sơ SV lên công cụ tìm kiếm.

Chạy kiểm xuyên suốt: `python -m tools.run_e2e`. Script dựng schema tên ngẫu nhiên riêng trong `kltn_management`, tạo tài khoản/dữ liệu giả, chạy API ở 8001 và Vite ở 5174, rồi xóa đúng schema do lượt kiểm tạo. Không dùng dữ liệu demo `public` và không dừng server của người dùng. Mã kiểm: [Playwright](../../frontend/e2e/registration.spec.ts); kết quả hiện trực tiếp trong terminal.

Hồ sơ khóa luận đã có mốc theo đợt, báo cáo/nhận xét, đề cương, tài liệu có phiên bản và bản in có footer. Khoa gia hạn cả đợt có lý do/lịch sử; bản nộp cũ giữ hạn áp dụng và nhãn trễ. Trước hạn SV tự nộp bản sửa nếu chưa được phản hồi; sau hạn/đóng nhận cần GVHD yêu cầu sửa. Đổi GVHD sau tiếp nhận chính thức chưa thuộc luồng này. Gửi email thật khi vận hành cần SMTP và URL triển khai phù hợp.
