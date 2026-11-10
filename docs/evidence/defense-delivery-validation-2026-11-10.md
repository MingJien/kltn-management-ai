# Kiểm chứng hội đồng và bảo vệ — 10/11/2026

## Căn cứ làm tròn

Đã đọc trực tiếp hình trang scan của QĐ 2919/QĐ-ĐHĐT ngày 15/11/2022: **Khoản 2 Điều 11, trang in số 4, trang PDF thứ 5** trong bản tại `docs/QuyDinh/`. Quy định yêu cầu điểm từng thành viên theo thang 10, làm tròn một chữ số thập phân; điểm KLTN là trung bình cộng điểm các thành viên, tiếp tục làm tròn một chữ số thập phân. Vì vậy không lấy trung bình điểm chưa làm tròn của từng phiếu. Ví dụ 7,24 / 7,25 / 7,25 → 7,2 / 7,3 / 7,3 → trung bình 7,3.

Đã đọc QĐ 5964/QĐ-ĐHĐT ngày 16/08/2024 (một trang): văn bản sửa Điều 2 về điều kiện tham gia; không sửa Khoản 2 Điều 11. Đây là đối chiếu hai văn bản được cung cấp trong workspace, không phải xác nhận đã tra cứu mọi văn bản khác của Trường.

Phần mềm dùng cách làm tròn số học, phần bỏ đi từ 5 trở lên tăng một đơn vị. QĐ quy định số chữ số, không mô tả riêng thuật toán xử lý điểm giữa. Backend dùng Decimal; UI cộng bằng đơn vị 0,01 điểm rồi làm tròn, tránh sai số số thực. Bộ điểm kiểm thử có tổng 3,85 hiện đúng 3,9. Hồ sơ đã chốt từ trước giữ độ chính xác lịch sử.

## Thay đổi và kết quả

- Giữ định danh biểu mẫu khi tải workspace, giữ nháp qua các tab và khi lưu phần khác; thông báo ngay tại biểu mẫu. Cảnh báo khi đóng/tải lại trang hoặc bấm liên kết khi còn nội dung chưa lưu. Nháp hiện nằm trong bộ nhớ trang, không phải chức năng khôi phục sau đóng trình duyệt.
- Từng phiếu có revision riêng và mã ngữ cảnh điểm danh/thưởng/báo cáo. Các phiếu khác nhau được lưu từ cùng phiên bản phiên; ghi đè cùng phiếu hoặc ngữ cảnh cũ bị chặn và giữ nội dung để đối chiếu. Chốt vẫn khóa phiên chung.
- Sửa hội đồng trước khi có dữ liệu họp, kiểm lại GVHD/trùng lịch, kiểm chữ ký phiên bản của thành phần, lưu lịch sử. UI ngăn chọn trùng người.
- Hội đồng tải đúng phiên bản báo cáo gắn với lịch. Kiểm quyền tại server, kiểm quét và toàn vẹn tệp. Tên tệp giữ phần mở rộng gốc.
- In Mẫu 6 trống trước họp, có thông tin SV/đề tài/người chấm và nhãn chưa có kết quả; bản dùng ký kết quả vẫn cần chốt. Hủy phiếu nhập nhầm có lý do, giữ bản cũ trong audit; có thể sửa điểm danh sau khi hủy các phiếu liên quan.
- Chủ tịch chọn phiên bản tài liệu SUPPORTING làm minh chứng, xác nhận mức thưởng theo SV. Tệp phải thuộc cùng khóa luận và CLEAN; trước khi chốt kiểm lại minh chứng còn an toàn. SV nộp tại Hồ sơ nộp & xét duyệt, loại Tài liệu hỗ trợ. Phiếu cộng mức đã xác nhận, tối đa 10 và không cộng lại sau trung bình.
- Có bảng đối chiếu từng SV, tổng số phiên đã chốt và bảng điểm trước khóa; nút khóa bị vô hiệu khi còn phiên chưa chốt. Lịch sử phiên theo quyền và nhãn tiếng Việt. Mở sửa bản chưa ký thông báo lại người nhận; bản đã khóa không được sửa qua luồng này.
- Theo lựa chọn của người dùng, Khoa ghi quyết định từng SV vắng, có căn cứ/lý do/người/thời điểm: không đạt do vắng hoặc cho bảo vệ bổ sung. Quyết định học vụ lưu riêng với bản chấm đã ký, không tự biến điểm trống thành 0.
- Lịch bổ sung chọn đúng SV được phép, liên kết phiên gốc; chấm và biên bản riêng. Bạn đã bảo vệ không bị đưa vào chấm lại. Không sửa quyết định sau khi đã dùng xếp lịch; không mở lại phiên gốc khi đã được dùng làm căn cứ xử lý vắng. Bảng tổng hợp cùng hội đồng chỉ lấy lần cuối của mỗi SV, hồ sơ từng buổi vẫn giữ nguyên.

## Các kiểm chứng đã chạy

- `python -m pytest tests/test_nv6_defense.py tests/test_nv6_evaluation.py tests/test_activity.py tests/test_official_schema.py -q --tb=short`: **35 passed**. Có cảnh báo deprecation thư viện/cấu hình.
- Ca tích hợp bảo vệ đi từ tạo/sửa hội đồng, xếp lịch, điểm danh, minh chứng thưởng, chấm từ cùng phiên bản, chặn phiếu cũ, hủy phiếu, chốt/mở/chốt lại, xuất 6/9/10/11; tiếp tục quyết định SV vắng, xếp bổ sung và chấm riêng. Kiểm tra điểm bạn đã bảo vệ vẫn 10,0, bản cũ của bạn vắng vẫn trống, bản bổ sung có kết quả riêng. Tất cả dùng dữ liệu giả trong schema PostgreSQL riêng.
- `python -m tools.run_e2e e2e/defense-drafts.spec.ts e2e/defense-workspace.spec.ts`: **3 passed**. Một ca đăng nhập/biểu mẫu hội đồng với API thật; hai ca có dữ liệu dùng API mô phỏng để tái hiện giữ nháp/làm tròn và quyết định vắng/xếp bổ sung. Không ghi nhận đây là toàn bộ buổi chấm qua trình duyệt/API thật.
- Kiểm tra không tràn ngang ở 320/390/768/1024/1440 px khi mở phiếu có dữ liệu. Axe WCAG 2A/2AA/2.1AA trong vùng bảo vệ của ca kiểm không có vi phạm; không thay thế mọi kiểm tra trình đọc màn hình.
- `npm run build --prefix frontend`: đạt; còn cảnh báo bundle lớn.
- Alembic `0023 → 0024` đã áp dụng lên CSDL local bằng migration; `alembic check`: không có chênh lệch metadata. `tools.validate_official_database`: PASS, head `20261110_0024`, 50 bảng nghiệp vụ.

## Phạm vi còn cần nghiệm thu

Chưa render/in thực tế Mẫu 6/9/10/11 bằng Word/Excel để đối chiếu từng trang với mẫu được Khoa chính thức chấp nhận. Mẫu 11 còn để trống ngày sinh vì hồ sơ hiện chưa có trường này; không tự tạo dữ liệu. Bản biểu mẫu đầu vào từng được xác định là bản tạm. Những điểm này cần được chốt trước khi gọi các bản xuất là biểu mẫu chính thức đã nghiệm thu.

Không có bằng chứng từ lượt này rằng mọi trang khác của hệ thống đều đã kiểm tra responsive. Các CSS mới được giới hạn trong trang bảo vệ. Không có thay đổi được tuyên bố là hoàn toàn không còn lỗi.

Dịch vụ local đã khởi chạy và xác nhận `/health/ready` HTTP 200, OpenAPI có route quyết định vắng mới; giao diện `http://127.0.0.1:1573/defense` HTTP 200. Đây là kiểm tra dịch vụ, không phải thao tác hồ sơ thật.
