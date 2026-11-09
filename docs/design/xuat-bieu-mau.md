# Thiết kế nhập và xuất biểu mẫu

## Nguyên tắc

Người dùng **không sửa trực tiếp tệp Word hoặc Excel gốc trên web**. Hệ thống hiển thị biểu mẫu nghiệp vụ, tự điền dữ liệu đã có và chỉ mở các ô cần nhập thêm như nhận xét, đề xuất, điểm hoặc ghi chú. Khi hoàn tất, hệ thống tạo một bản xuất theo đúng mẫu đã được Khoa kiểm tra.

Mỗi bản xuất luôn có:

- mã biểu mẫu hoặc mã phiên bản;
- thời gian xuất;
- địa chỉ truy xuất của hệ thống;
- mã băm tệp, phiên bản mẫu và lịch sử thao tác.

Ba thông tin đầu in thành **một dòng ở chân trang bên trái** theo góp ý ngày 20/10/2026, đúng thứ tự: `<địa chỉ hệ thống>, mã số <mã>, <giờ> <ngày>`. Ví dụ: `https://kltn.dthu.edu.vn, mã số DC-2026-ABC123-V01-9F8E7D6C, 10:24 20/10/2026`. Dòng này giúp đối chiếu bản giấy đã ký với bản điện tử mà không sửa nội dung chính của mẫu. Với PDF, chữ được chuyển sang ASCII không dấu vì font in mặc định không có dấu tiếng Việt; DOCX giữ nguyên dấu.

Luồng kỹ thuật là:

`dữ liệu đã được phân quyền và chốt` → `DTO theo mẫu` → `template đã kiểm` → `DOCX/XLSX` → `PDF nếu cần` → `StoredFile + AuditEvent`.

Mẫu nguồn và bản xuất có dữ liệu thật đặt trong kho tệp được bảo vệ, ngoài Git. Repository chỉ giữ mã xuất và tài liệu thiết kế; không giữ mẫu có dữ liệu cá nhân.

## Các mẫu đã đối chiếu

| Mẫu | Vai trò trong hệ thống | Cách nhập | Trạng thái hiện tại |
| --- | --- | --- | --- |
| 1a, 1b — Đơn đăng ký cá nhân/nhóm | Tham khảo quy trình đăng ký | Đăng ký thực hiện trực tuyến | Không xuất lại. Mẫu giấy đòi GPA, tín chỉ, ngày sinh và nơi sinh; hệ thống không thu thập các dữ liệu này từ sinh viên. |
| 2 — Kế hoạch thực hiện | Kế hoạch theo khóa luận | SV tải khung trống, điền Word rồi nộp PDF/DOCX; GVHD tiếp nhận hoặc yêu cầu sửa | Runtime lưu phiên bản như tài liệu loại `PLAN`; chỉ bản mới nhất đã tiếp nhận mới xuất bản có URL, mã và giờ. Khung tải về được tạo bằng code theo đề mục Mẫu 2; cần Khoa đối chiếu bố cục trước khi dùng làm biểu mẫu chính thức. |
| 3 — Đề cương | Hồ sơ đề cương | SV tải khung trống, điền trên Word rồi nộp PDF/DOCX; GV nhập nhận xét qua luồng review | Runtime nhận và duyệt phiên bản, chỉ xuất bản in của phiên bản đã chốt có URL, mã và giờ xuất ở chân trang. Khung trống tạo bằng code theo đề mục Mẫu 3; Khoa cần đối chiếu bố cục trước khi phát hành chính thức. |
| 4 — Danh sách SV và GVHD | Báo cáo sau chốt đăng ký/phân công | Chỉ lấy dữ liệu đã chốt | Chưa xuất. Không phải biểu mẫu để sửa tay. |
| 5 — Quy định trình bày và bìa | Quy định soạn quyển báo cáo | SV tự soạn báo cáo theo quy định | Ngoài phạm vi hệ thống quản lý KLTN; không sinh bìa hay chỉnh nội dung báo cáo. |
| 6 — Phiếu đánh giá hội đồng | Chấm từng sinh viên | Thành viên hội đồng nhập điểm và nhận xét theo tiêu chí | Thiết kế rubric 2/4/4 đã có; chưa nằm trong schema 34 bảng và chưa có runtime chấm/xuất. |
| 7 — Nhận xét GVHD | Điều kiện/chất lượng trước bảo vệ | GVHD nhập ba phần nhận xét và đề nghị | Sẽ làm ở giai đoạn xét bảo vệ. |
| 8 — Nhận xét GVPB | Nhận xét phản biện | GVPB nhập nhận xét theo từng khung của mẫu | Sẽ làm cùng giai đoạn xét bảo vệ. |
| 9 — Biên bản họp hội đồng | Biên bản bảo vệ | Thư ký nhập phần diễn biến/ý kiến; dữ liệu hội đồng, điểm và kết quả tự điền | Chưa triển khai trong schema 34 bảng. Mẫu Drive hiện có dữ liệu đã điền, nên không dùng trực tiếp làm template. |
| 10 — Bảng điểm tổng hợp | Báo cáo điểm sau chấm | Chỉ tổng hợp kết quả đã khóa | Sẽ làm sau khi có chấm điểm và kết quả cuối. |
| 11 — Bảng điểm chính thức | Dữ liệu điểm học phần chính thức | Chỉ tổng hợp kết quả đã khóa theo thẩm quyền | Là biểu mẫu đào tạo có dữ liệu cá nhân; chỉ tích hợp/xuất khi có quy trình và quyền của Phòng Đào tạo. |

## Khung nhập nhận xét

Những phần nhập tự do được tách rõ khỏi dữ liệu tự điền:

| Biểu mẫu | Nội dung người dùng nhập |
| --- | --- |
| Mẫu 3 | Tổng quan/vấn đề, mục tiêu, phạm vi, nhiệm vụ, phương pháp, bố cục chương, công cụ, kết quả dự kiến, kế hoạch và tài liệu tham khảo. |
| Mẫu 6 | Điểm từng tiêu chí, điểm thưởng, nhận xét/đề nghị của người chấm. Server kiểm nhóm 2/4/4, thưởng không quá 1 và tổng không quá 10. |
| Mẫu 7 | Tinh thần thái độ, mức đáp ứng nội dung, hình thức và đề nghị được/không được bảo vệ. |
| Mẫu 8 | Hình thức, ý nghĩa/mục tiêu/phương pháp, kết quả mới hoặc đóng góp, nội dung cần trao đổi và nhận xét chung. |
| Mẫu 9 | Ý kiến GVPB, ý kiến các thành viên, kết luận Chủ tịch, kiến nghị và ghi chú của Thư ký. Hệ thống không tự tạo các nhận xét này. |

Tên đề tài, thành viên, MSSV, lớp, GVHD, đợt, hội đồng, lịch, trạng thái, điểm đã khóa và chữ ký tham chiếu đến dữ liệu nghiệp vụ; người dùng không gõ lại các giá trị đó trong mỗi biểu mẫu.

## Phiên bản và bản giấy

1. Mỗi lần xuất nhận mã riêng, ví dụ `DC-2026-ABC123-V01-9F8E7D6C`, và footer một dòng gồm địa chỉ hệ thống, mã, thời gian xuất. Bản nộp gốc không bị ghi đè.
2. Trước chữ ký đầu tiên, Thư ký kiểm bản giấy. Nếu có lỗi, phiên bản cũ được đánh dấu hết hiệu lực và xuất phiên bản mới; không ghi đè tệp cũ.
3. Từ chữ ký đầu tiên, nội dung và điểm bị khóa. Chỉ được cấp bản sao của đúng phiên bản đã ký.
4. Khi nhận bản giấy, người đối chiếu tìm bằng mã trên footer và xác nhận mã, tệp băm, phiên bản và thời gian xuất trùng khớp.

## Điều kiện trước khi lập trình xuất đúng mẫu

- Có bản mẫu trắng hiện hành hoặc văn bản cho phép làm sạch mẫu nguồn.
- Xác định từng vùng điền, vùng lặp, chữ ký và quy tắc phân trang.
- Dùng dữ liệu giả để render DOCX/XLSX/PDF, đối chiếu bố cục, merged cells, công thức, vùng in và footer trước khi bật cho người dùng.
- Chỉ bổ sung bảng/migration cho giai đoạn hội đồng, chấm điểm và biên bản khi bắt đầu phần nghiệp vụ đó; không đưa các bảng này vào schema lõi 34 bảng chỉ để tạo biểu mẫu trước.

Mẫu 9 đang cần **bản trắng được Khoa xác nhận**. Bản xem được trên Drive là bản đã điền nên chỉ dùng để nhận diện cấu trúc, không tải vào repository, không làm mẫu phát hành và không coi là bằng chứng đã xuất đúng mẫu.
