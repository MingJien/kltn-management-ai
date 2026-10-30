# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Ứng dụng React, FastAPI và PostgreSQL quản lý tài khoản, đề tài, đăng ký khóa luận, GVHD, tiến độ và tài liệu. Chatbot AI hiện ở mức prototype, dùng dữ liệu giả.

## CSDL hiện hành

PostgreSQL `kltn_management`, Alembic head `20261030_0017`: **41 bảng nghiệp vụ** và bảng kỹ thuật `alembic_version`. Cập nhật cấu trúc qua Alembic; [SQL schema-only](database/official/kltn-management-schema.sql) có mỗi bảng một lệnh tạo đầy đủ, không dùng thay migration trên database đang chạy.

Tiến độ có khung xem PDF và ghim nhận xét theo đúng lần nộp. Ghim nháp tự lưu riêng cho GV; khi gửi kết quả mới hiện cho SV. Trang, thu phóng, vị trí cuộn và nhận xét tổng quát đang viết được khôi phục trên cùng trình duyệt/tài khoản. DOCX/TXT nhận xét theo mục và đoạn trích.

Mục Tài liệu có lựa chọn sẵn, dẫn Mẫu 1a/1b về hồ sơ đăng ký và Mẫu 3 về Đề cương. Nộp bản sửa trong cùng hồ sơ giữ nguyên các phiên bản cũ. Tải bản gốc và xuất bản đã duyệt có footer để ký là hai thao tác riêng; lịch sử xuất hiển thị người xuất, mã và thời điểm theo từng phiên bản. Mẫu 1 có footer bản nộp, chưa xác nhận Khoa duyệt.

## Tình hình hiện tại

- **NV6 tuần 1** có UI/API phân công, thu hồi, gia hạn phản biện; nhận xét GVHD Mẫu 7/GVPB Mẫu 8 theo từng sinh viên và đúng bản báo cáo. Nháp riêng, xuất phiếu đã điền để ký, quét bản ký trước khi gửi; phiếu đã gửi giữ nguyên và bản sửa có lý do. TBM xét ba điều kiện cấp Trường theo căn cứ, lưu lịch sử và gửi thông báo đúng tài khoản. Nhóm chỉ sẵn sàng bảo vệ khi mọi thành viên đủ điều kiện. [Luồng bàn giao](docs/design/nv6-review-defense-workflow.md) · [Kiểm chứng và giới hạn](docs/evidence/nv6-week1-validation.md).

- Cuốn báo cáo KLTN trước bảo vệ có hạn REPORT riêng và phiên bản, tách khỏi báo cáo tiến độ theo mốc. Kiểm tra tương đồng chưa triển khai. Mẫu 1a/1b vẫn nộp tại Hồ sơ đăng ký.
- Chuông gửi thông báo theo đúng người liên quan, phản hồi cho cả nhóm; bấm thông báo nạp dữ liệu mới kể cả khi đang ở chính trang đó. Quyền được kiểm lại trước khi xem thông báo riêng. SV/GV/TBM/Admin đều tra cứu đề tài đã công bố, không được mở hồ sơ riêng chỉ nhờ biết liên kết.

- Kho “Biểu mẫu và tài liệu Khoa” quản lý theo đợt: người được giao quyền tải PDF/DOCX/XLSX (tối đa 25 MB), quét ClamAV, lưu nháp, xem trước rồi phát hành hoặc thu hồi. Từng phiên bản giữ nguyên tệp, nguồn và lý do cập nhật. SV chỉ thấy mẫu 1a/1b–5; GV thấy toàn bộ bộ mẫu. Danh sách đã điền (ví dụ Mẫu 4) là tài liệu công bố riêng, chỉ người thuộc đợt xem được; không tự nhập danh sách vào tài khoản. Admin cấp/thu hồi quyền `FORM_MANAGER`, không mặc nhiên duyệt nghiệp vụ.

- Quản trị nhập danh sách GV bằng Excel bốn cột (Mã GV, Họ tên, Email, Mã bộ môn), xem trước lỗi và xác nhận tạo tài khoản chờ kích hoạt. Có chọn từng người/chọn tất cả theo kết quả tìm kiếm để gửi link riêng, trạng thái và lịch sử gửi từng GV; tải tệp và tạo theo danh sách chưa tự gửi email.
- Nhật ký trên UI ghi nhận người thao tác, thời điểm, hồ sơ, lý do và căn cứ/số văn bản. Admin tra cứu toàn hệ thống hoặc mở lịch sử từng tài khoản; SV xem hồ sơ của mình; GV/TBM xem đúng phần được phân công và phạm vi bộ môn. Có tìm kiếm, lọc thao tác/ngày và phân trang; nhật ký cũ vẫn được giữ.
- UI/API có quản lý tài khoản và phân quyền, danh sách sinh viên đủ điều kiện; luồng tạo/duyệt đề tài, đăng ký cá nhân hoặc nhóm, xác nhận thành viên và giảng viên tiếp nhận/từ chối. Khi giảng viên chấp nhận, hệ thống tạo hồ sơ khóa luận, thành viên và GVHD chính trong cùng giao dịch.
- Mẫu 1a/1b được nộp theo phiên bản trong hồ sơ đăng ký trước tiếp nhận; bản xuất có footer ghi rõ bản nộp, chưa xác nhận Khoa duyệt. Khi nhóm, tên đề tài hoặc GV đề xuất đổi, phải nộp bản mới để xuất; bản cũ vẫn được giữ.
- Trong hồ sơ khóa luận có thông tin GVHD và lịch sử phân công; nộp đề cương theo phiên bản, nhận xét và chốt; tạo mốc tiến độ cho đợt, nộp báo cáo, GVHD xác nhận hoặc yêu cầu sửa. Nộp trễ vẫn được nhận khi mốc còn mở và được đánh dấu `!` màu đỏ; người điều phối có thể gia hạn cả đợt kèm lý do và lịch sử, kể cả mở nhận lại mốc đã đóng. Chỉ phiên bản mốc mới nhất được mở lại.
- Báo cáo có minh chứng được gửi cùng một giao dịch; không lưu báo cáo dở dang khi tải tệp thất bại. Trước hạn SV được tự nộp phiên bản sửa nếu GV chưa phản hồi; sau hạn/đóng nhận chỉ nộp lại khi GVHD yêu cầu sửa. Báo cáo tiến độ và minh chứng riêng chỉ nhóm SV/GVHD xem; TBM quản lý mốc chung, không đọc nội dung riêng.
- Mẫu 2 (kế hoạch), Mẫu 3 (đề cương) lấy từ `docs/BieuMau`. SV nộp các bản đã điền theo phiên bản; GVHD phản hồi/duyệt, TBM chốt đề cương. Bản đã duyệt xuất PDF/DOCX để ký ngoài có footer góc trái dưới: địa chỉ hệ thống, mã số, thời điểm xuất; tệp gốc giữ nguyên.
- Hạn theo từng loại tài liệu áp dụng cho toàn đợt, có lịch sử thiết lập/gia hạn/đóng/mở nhận lại trên UI. ClamAV quét tệp thật; tệp lỗi quét hoặc chưa quét sạch bị chặn tải/duyệt. Hồ sơ khóa luận có nút làm mới dữ liệu và giữ bản nháp chưa gửi.
- Cuốn báo cáo KLTN dùng loại tài liệu `REPORT`: Khoa đặt hạn riêng theo đợt như các loại khác, SV nộp PDF/DOCX và từng phiên bản được giữ nguyên để đối chiếu tương đồng về sau. Đối chiếu tương đồng chưa triển khai; khi có, kết quả chỉ để tham khảo, không tự chặn nộp hay bảo vệ. Báo cáo tiến độ hàng tuần vẫn nộp ở mốc Tiến độ, không dùng hồ sơ này.
- Chuông thông báo trong web gửi đúng người theo từng thao tác: SV nộp đề cương, báo cáo tiến độ, tài liệu hoặc Mẫu 1a/1b chỉ tới GVHD/GV tiếp nhận của đúng hồ sơ; GV phân công góp ý chéo tới đúng GV được phân công; GVHD/TBM/Trưởng khoa chốt đề cương tới SV, GVHD và TBM liên quan; thao tác tài khoản tới chính tài khoản đó. Thông báo chỉ hiện trong web cho người nhận, không gửi email và không lộ cho SV/GV/TBM khác.
- Minh chứng đăng ký cũng được quét ClamAV khi tải lên; UI hiển thị trạng thái, có quét lại nếu lỗi/chưa quét và chỉ cho tải tệp sạch. Bản in PDF dành vùng footer riêng để giữ nội dung gốc; hồ sơ GV hiển thị mã, bộ môn và Khoa theo đúng phạm vi.

Kiểm chứng NV6 ngày 30/10/2026 dùng dữ liệu giả trong schema riêng, không gửi SMTP thật: bộ backend, build frontend và kiểm tra schema drift; ba kịch bản NV6 tích hợp Chromium/API/PostgreSQL/ClamAV, mobile và accessibility. Phiếu Mẫu 7/8 được xuất và render bằng Word để kiểm tra bố cục. Bộ UI cũ chạy gộp chưa đạt toàn bộ; số liệu và ca lỗi được nêu rõ trong [minh chứng](docs/evidence/nv6-week1-validation.md), không dùng kết quả lịch sử thay kết quả hiện hành.

Hội đồng/lịch bảo vệ, chấm điểm và biên bản chưa hoàn thiện. Chatbot chưa kết nối Gemini.

## Chạy local

Tạo `.env` từ `.env.example`, đặt `DATABASE_URL` trỏ đúng `kltn_management`, rồi cài dependencies. Ứng dụng và Alembic dùng cổng trong `DATABASE_URL`; `POSTGRES_PORT` chỉ là cổng xuất ra máy khi chạy PostgreSQL bằng Docker Compose. Nếu dùng PostgreSQL đã cài trên máy, không cần chạy container.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Chạy API và giao diện ở hai terminal:

```powershell
.\.venv\Scripts\python.exe -m tools.run_demo_api
```

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

Mở `http://127.0.0.1:1573` và dùng cùng hostname này cho liên kết trong email để giữ đúng phiên đăng nhập. Chọn **Bảo vệ và đánh giá → Phản biện & điều kiện bảo vệ** để vào NV6. Mật khẩu và cấu hình thư thật chỉ nằm trong máy local, không có trong repository.
Trên máy phát triển, `KLTN_DEMO_MODE=true` trong `.env` hiện lựa chọn SV/GV/TBM giả lập tại trang đăng nhập; tài khoản kích hoạt qua email vẫn đăng nhập bằng mật khẩu.

Windows đã cài ClamAV tại `C:\Program Files\ClamAV` và cấu hình `C:\ProgramData\ClamAV\clamd.conf` chỉ nghe `127.0.0.1:3310`: `run_demo_api` tự khởi động/reuse daemon. Cập nhật chữ ký bằng `freshclam.exe`; nếu bộ quét chưa sẵn sàng, hệ thống giữ tệp cách ly và báo trạng thái thật.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m tools.validate_official_database
.\.venv\Scripts\python.exe -m pytest tests/test_print_copy.py tests/test_proposal_export.py -q
npm run build --prefix frontend
$env:KLTN_E2E_ALLOW_ISOLATED_SCHEMA = 'true'
.\.venv\Scripts\python.exe -m tools.run_e2e
```

`run_e2e` yêu cầu ClamAV thật và tạo schema kiểm thử ngẫu nhiên riêng trong `kltn_management`; chỉ dọn schema do chính lượt kiểm tạo, không sửa dữ liệu `public`. Để kiểm bản in chính thức, máy chạy test cần các tệp Mẫu 2/Mẫu 3 trong `docs/BieuMau` (hoặc `KLTN_OFFICIAL_TEMPLATE_DIR`). Kiểm thử dùng tài khoản/tài liệu giả và không gửi SMTP thật.

## Tài liệu chính

- [API hiện hành](docs/design/api-design.md) · [OpenAPI sinh từ FastAPI](docs/design/openapi.yaml)
- [ERD hiện hành](docs/design/erd-kltn-management.md) · [ERD theo cụm](docs/design/erd-clusters/README.md)
- [Từ điển dữ liệu](docs/design/database-dictionary.md)
- [Quy trình đăng ký](docs/design/registration-workflow.md)
- [Luồng phản biện và xét điều kiện NV6](docs/design/nv6-review-defense-workflow.md)
- [Minh chứng NV6 và CSDL hiện hành](docs/evidence/nv6-week1-validation.md)

Repository không chứa dữ liệu thật hay cấu hình bí mật. Nội dung AI thử nghiệm dùng corpus giả cục bộ; việc gửi tài liệu cho dịch vụ AI cần theo chính sách của Khoa/Trường.

Khung xem và nhận xét trên tệp dùng chung cho tiến độ, tài liệu và đề cương: PDF ghim theo trang, DOCX/TXT theo đoạn/dòng; nháp tự lưu và góp ý gắn đúng phiên bản. Tài liệu/đề cương hiện bản mới nhất, các bản cũ nằm trong lịch sử thu gọn và vẫn xem/tải được theo quyền.

GV có thể đính kèm tối đa 5 bản PDF/DOCX phản hồi cho đúng phiên bản SV đã nộp (10 MB/tệp, quét ClamAV). Nhận xét chung và ghim tự lưu nháp trên máy chủ; chỉ công bố khi bấm “Hoàn thành và gửi góp ý”. SV xem tệp phản hồi ngay trên web, gồm nhận xét Word/Track Changes và nhận xét PDF phổ biến. Link trong góp ý bấm mở được; hình/bảng/biểu đồ phức tạp nên gửi trong PDF.
