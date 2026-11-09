# Cuốn báo cáo KLTN, hạn nộp theo đợt và thông báo đúng người — 28/10/2026

Ghi nhận phần làm tiếp từ các câu hỏi về mốc tiến độ, hạn nộp tài liệu, Mẫu 1 và chuông thông báo. Trạng thái dưới đây chỉ ghi điều đã chạy và đã kiểm lại trên source tại `D:\KLTN`.

## Chốt cách hiểu nghiệp vụ

1. **“Mở mốc theo kế hoạch đợt” là tạo mốc tiến độ**, không phải tạo loại tài liệu. Mốc có mã, hạn nộp báo cáo tiến độ và tỉ lệ dự kiến; áp dụng cho mọi khóa luận trong đợt. Mốc đã mở giữ nguyên lịch sử; muốn đổi thì đóng mốc cũ rồi mở phiên bản mới cùng mã.
2. **“Hạn nộp tài liệu theo đợt” là thiết lập/gia hạn hạn cho từng loại tài liệu** (`Đề cương`, `Kế hoạch thực hiện`, `Cuốn báo cáo KLTN`, `Tài liệu hỗ trợ`). Chưa có hạn thì nút là thiết lập; đã có hạn thì thao tác là gia hạn hoặc mở nhận lại, bắt buộc lý do và ghi lịch sử.
3. **Không gộp loại tài liệu vào mốc tiến độ.** Báo cáo tiến độ hàng tuần và hồ sơ tài liệu là hai luồng khác nhau: mốc quyết định báo cáo tiến độ; hạn tài liệu quyết định nhận đề cương/kế hoạch/báo cáo/tài liệu hỗ trợ.
4. **Mẫu 1a/1b không nằm trong hạn tài liệu của khóa luận.** Mẫu 1 được nộp theo phiên bản ngay trong Hồ sơ đăng ký, trước khi có khóa luận và trước khi GV tiếp nhận. Vì vậy không thêm Mẫu 1 vào danh sách hạn nộp tài liệu; thay vào đó bổ sung thông báo cho GV tiếp nhận/TBM khi SV nộp lại Mẫu 1a/1b trong hồ sơ đăng ký đã gửi.
5. **Cuốn báo cáo KLTN dùng loại `REPORT` đã có.** Khoa đặt hạn theo đợt ở khu vực hạn nộp tài liệu; SV nộp tệp PDF/DOCX ở tab Tài liệu, mỗi phiên bản được giữ nguyên. Đây là bản lưu để đối chiếu tương đồng về sau, không phải báo cáo tiến độ. Chức năng đối chiếu tương đồng chưa triển khai; khi có, kết quả chỉ tham khảo và không tự chặn nộp/bảo vệ.

## Thay đổi đã làm

- Migration `20261028_0013_report_deadline_notifications` (đã có trong cây làm việc): thêm `REPORT` cho hạn tài liệu; mở rộng `user_notification` với `thesis_id`, `subject_type`, `subject_id`, `message`, `url`; cho phép `registration_id` rỗng. Không thêm bảng, vẫn **39 bảng nghiệp vụ**.
- Migration `20261028_0014_notification_coverage`: bổ sung bốn loại thông báo còn thiếu — `REGISTRATION_FORM_SUBMITTED`, `PROPOSAL_REVIEWER_ASSIGNED`, `PROGRESS_REVIEWER_ASSIGNED`, `PROPOSAL_DEAN_CONFIRMED`.
- Nộp đề cương trong hồ sơ khóa luận nay báo cho GVHD của đúng khóa luận; phân công góp ý đề cương/tiến độ báo cho đúng GV được phân công; Trưởng khoa ghi nhận bản ký báo cho SV, GVHD và TBM; nộp lại Mẫu 1a/1b báo cho GV tiếp nhận và TBM.
- Thông báo tiến độ/tài liệu/nhận xét vẫn chỉ tới đúng người: SV nộp báo cáo tiến độ → chỉ GVHD; SV nộp tài liệu → chỉ GVHD; GVHD nhận xét → SV của đúng khóa luận; GV góp ý chéo → SV và GVHD. SV/GV/TBM khác không nhận và không thấy thông báo của hồ sơ không liên quan.
- Khi bấm thông báo, trang hồ sơ khóa luận tải lại dữ liệu của đúng khóa luận/tab, nên tệp mới nộp hiện ngay thay vì giữ danh sách cũ.
- UI hạn nộp tài liệu và thẻ tài liệu đã có nhãn `Cuốn báo cáo KLTN`; thẻ này giải thích rõ đây là bản lưu để đối chiếu tương đồng, báo cáo tiến độ vẫn ở mục Tiến độ.

## Người nhận thông báo theo thao tác

| Thao tác | Người nhận |
|---|---|
| SV nộp đề cương | GVHD của khóa luận |
| GVHD/TBM chốt đề cương | SV trong khóa luận + GVHD; TBM nhận khi Trưởng khoa ghi nhận bản ký |
| Trưởng khoa ghi nhận bản ký | SV + GVHD + TBM của bộ môn |
| Phân công góp ý đề cương/tiến độ | GV được phân công |
| SV nộp báo cáo tiến độ | GVHD; GV góp ý chéo không nhận thay |
| GV nhận xét/yêu cầu sửa tiến độ | SV trong khóa luận; GVHD vẫn thấy trên hồ sơ |
| SV nộp tài liệu/cuốn báo cáo | GVHD |
| GVHD nhận/yêu cầu sửa tài liệu | SV trong khóa luận |
| SV nộp lại Mẫu 1a/1b | GV tiếp nhận (hoặc GV đề xuất) + TBM |
| Mở/gia hạn/đóng mốc hoặc hạn tài liệu | SV và GVHD thuộc đợt; không gửi ra ngoài đợt |
| Khóa/mở/khôi phục tài khoản, cấp lại link | Chính tài khoản đó |

## Kiểm chứng

Chạy trên PostgreSQL `kltn_management` và ClamAV thật; dữ liệu kiểm thử là dữ liệu giả trong schema riêng của lượt E2E.

- `python -m pytest tests -q`: **158 passed**, 1 cảnh báo deprecation của thư viện kiểm thử.
- Hai file kiểm thử trọng tâm: `tests/test_report_and_notification_routing.py` (hạn `REPORT`, nộp cuốn báo cáo, đề cương, phân công góp ý, Mẫu 1a/1b, Trưởng khoa) và `tests/test_core_workspace.py`.
- `python -m tools.export_official_schema_sql` + `python -m tools.validate_official_database`: PASS, head `20261028_0014`, **39 bảng**, 93 FK, 82 CHECK, 32 UNIQUE, 24 index tường minh.
- `npm run build --prefix frontend`: PASS; còn cảnh báo kích thước bundle >500 kB có từ trước.
- E2E `nv5-completion`: PASS sau khi thêm bước đặt hạn `REPORT`, nộp cuốn báo cáo, kiểm tra chuông của GVHD và kiểm tra GV ngoài khóa luận không thấy thông báo.

## Chưa làm

- Đối chiếu tương đồng (similarity) và hội đồng/chấm điểm/biên bản vẫn chưa triển khai; chưa có kết quả tương đồng để hiển thị.
- Không tự gửi email cho bất kỳ thông báo nào ở trên.
