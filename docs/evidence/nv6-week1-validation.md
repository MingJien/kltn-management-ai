# Kiểm chứng NV6 tuần 1

Ngày chạy: **30/10/2026**, tại `D:\KLTN`. Phạm vi sản phẩm: phân công phản biện, Mẫu 7/8, điều kiện dự bảo vệ và thông báo tới tài khoản. Nhánh giao mã: `NV6`; nền NV5 được lưu ở commit riêng trước phần NV6. Tài khoản GitHub dùng Credential Manager của người dùng; tác giả và người commit là Phạm Minh Chiến, không có Codex co-author.

## Kết quả đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Backend `python -m pytest tests -q --tb=short` | **178 đạt**, có hai cảnh báo thư viện FastAPI/Starlette và Alembic; không có lỗi hoặc skip trong lượt kiểm này |
| Frontend `npm run build --prefix frontend` | **Đạt** kiểm tra TypeScript và production build; Vite còn cảnh báo bundle lớn ở phần xem tài liệu dùng chung |
| OpenAPI `python -m tools.export_runtime_openapi --check` | **Đạt**, đặc tả khớp route/schema FastAPI |
| PostgreSQL `python -m tools.validate_official_database` | **Đạt**, revision `20261030_0017`, 41 bảng nghiệp vụ, 106 FK, 90 CHECK, 34 UNIQUE và 26 index tường minh |
| NV6 UI `python -m tools.run_e2e nv6-evaluation.spec.ts` | **3 kịch bản đạt** với cookie đăng nhập, API, PostgreSQL và ClamAV thật; không mock route |
| Mobile và accessibility NV6 | **Đạt** viewport 390×844, không cuộn ngang; axe WCAG 2 A/AA và WCAG 2.1 AA không báo vi phạm trong vùng UI NV6 được kiểm |
| Xuất phiếu Mẫu 7/8 | **Đạt** nội dung, ACL, SHA-256 bản xuất, kiểm tra phần DOCX được giữ nguyên và nguồn gốc không bị sửa; API kiểm `If-Match` |
| Bố cục phiếu | Mẫu 7 và Mẫu 8 đã xuất, render qua Microsoft Word rồi xem PNG từng trang. Chỉnh phần điền về Times New Roman theo mẫu, tránh giãn chữ do xuống dòng thủ công, giữ khối ký và loại khoảng trống viết tay cuối mẫu đã được điền. Bản dài có thể nhiều trang, mỗi trang có footer. Mẫu nguồn chỉ được mở đọc |

`render_docx.py` đã được thử nhưng máy không có LibreOffice. Kiểm tra bố cục dùng Word chạy ẩn, mở chỉ đọc và xuất PDF; PDFium của runtime tài liệu tạo PNG để kiểm tra. Không coi việc trích xuất XML là thay cho kiểm tra bố cục.

## Nghiệp vụ và quyền được kiểm

- TBM có đúng thẩm quyền bộ môn mới phân công, thu hồi, gia hạn và xét điều kiện. Chặn GVHD đồng thời làm GVPB, GV khác bộ môn, tài khoản không hoạt động, phân công trùng và quá hai GVPB hiệu lực. Màn hình cũ bị từ chối bằng `409`.
- GVPB đọc được đúng cuốn báo cáo, không mở tiến độ/tài liệu riêng khác. Thu hồi phân công làm mất quyền API và tải tệp; thông báo cũ không trở thành quyền truy cập.
- Mỗi phiếu gắn sinh viên, phân công và phiên bản báo cáo. Nháp chỉ người viết xem; SV chỉ xem phiếu đã gửi của chính mình. Nội dung đã gửi không bị sửa đè. Bản sửa có lý do và số phiên bản riêng.
- Bản ký PDF/DOCX tối đa 10 MB, tệp chưa quét sạch bị chặn gửi/tải. Đổi nội dung nháp làm gỡ liên kết bản ký cũ. Người gửi phải xác nhận bản ký khớp nội dung; hệ thống không tuyên bố xác thực chữ ký số.
- Ba điều kiện cấp Trường được xét riêng từng SV, có căn cứ và lịch sử. Không thêm gate phản biện hoặc tương đồng. Chỉ khi mọi thành viên đủ điều kiện thì hồ sơ chung mới sẵn sàng bảo vệ. Báo cáo/Mẫu 7 đổi làm kết quả cũ cần xét lại; mở xét lại không xóa lịch sử.
- Không lộ kết quả kỷ luật/căn cứ xét cá nhân qua hồ sơ hay nhật ký của thành viên khác. Thông báo tới đúng tài khoản, bấm dẫn về đúng hồ sơ; người viết không nhận thông báo trùng cho chính thao tác của mình.

Các kiểm thử backend mô phỏng trạng thái quét ở nhánh kiểm thử dịch vụ để kiểm trường hợp cách ly và từ chối gửi; lượt UI riêng dùng **ClamAV thật** để xác minh nộp báo cáo và bản ký. Không gộp hai loại bằng chứng này thành tuyên bố mọi kiểm thử đều quét thật.

## Giới hạn của bộ UI cũ

Lượt chạy gộp toàn bộ `python -m tools.run_e2e` có **19 đạt, 15 lỗi, 2 không chạy**. Đây không phải một lượt release UI đạt toàn hệ thống. Có ca vẫn chọn tab/tên hoặc vị trí trước khi giao diện NV5 được tổ chức lại (ví dụ `Tiến độ`, form hạn tài liệu trên tab tiến độ, tên tài liệu tự nhập); có ca làm thay đổi dữ liệu seed dùng chung khiến ca sau nhận `409` hoặc có nhiều khóa luận thay vì một. NV6 chạy riêng trên schema mới đạt ba kịch bản; khi chạy trong lượt gộp này, setup NV6 gặp phân công điều phối đã có từ spec trước.

Đã đối chiếu thêm `workflow-notices.spec.ts` trên schema riêng: vẫn lỗi ở selector tìm form hạn tài liệu trên vị trí UI cũ. Bộ UI cũ cần được cập nhật selector và tách dữ liệu giữa các spec trước khi dùng làm điều kiện phát hành cho **toàn hệ thống**. Kết quả NV6 ở trên không thay thế công việc đó và không chứng nhận các giai đoạn hội đồng, chấm điểm, biên bản, lưu trữ hoặc AI chưa triển khai.

## Tái kiểm NV6

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m tools.validate_official_database
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short
npm run build --prefix frontend
.\.venv\Scripts\python.exe -m tools.export_runtime_openapi --check
$env:KLTN_E2E_ALLOW_ISOLATED_SCHEMA = 'true'
.\.venv\Scripts\python.exe -m tools.run_e2e nv6-evaluation.spec.ts
```

Backend tests và UI tests tạo schema PostgreSQL ngẫu nhiên riêng, migration từ đầu, dùng tài khoản/tệp giả, tắt gửi SMTP thật và chỉ dọn schema do lượt chạy tạo. Migration trên database local đang dùng chỉ là nâng cấu trúc qua Alembic, không chạy lại SQL init. Nguồn mẫu 7/8 phải được cấp trên máy chủ theo [hướng dẫn vận hành](../design/nv6-review-defense-workflow.md).

Các nguồn đã dùng: mã nguồn và yêu cầu trong repository, hai mẫu `mau 7.Ban nhan xet KLTN danh cho GVHD.docx`, `mau 8.Ban nhan xet KLTN danh cho GVPB.docx` trong kho nguồn local của Khoa. Không đọc lịch sử ChatGPT Project hoặc Google Drive cho tác vụ này. Bản mẫu, bản ký giả, PDF/PNG QA, log và dữ liệu kiểm thử được giữ local, không đưa vào GitHub.
