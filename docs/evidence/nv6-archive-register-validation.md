# Kiểm chứng bảng điểm toàn đợt và kho nội bộ NV6

Đối chiếu ngày 15/11/2026 trên mã sản phẩm, biểu mẫu Khoa tại `docs/BieuMau` và dữ liệu kiểm thử giả lập. Không đọc thêm ChatGPT Project hoặc Google Drive trong lượt này.

| Kiểm tra | Kết quả |
| --- | --- |
| Backend `python -m pytest -q --tb=short` | 275 đạt, 6 cảnh báo deprecation thư viện/cấu hình, không lỗi hoặc skip. |
| Kiểm lại biểu mẫu sau chỉnh khoảng đệm Mẫu 10 | 7 đạt với `tests/test_defense_template_layout.py`. |
| UI qua `tools.run_ui_suite` | 55 ca trong 29 bộ đạt qua lượt tổng kiểm và chạy lại sau sửa. |
| `npm run build` trong frontend | Đạt, còn cảnh báo kích thước gói chính của Vite. |
| Alembic và CSDL local | Head `20261115_0030`; `alembic check` không có thao tác nâng cấp mới. 53 bảng nghiệp vụ, 155 FK, 126 CHECK, 39 UNIQUE, 39 index tường minh. |
| API và web local | `/health/ready` và trang web trả HTTP 200 sau khởi động lại mã mới. |

## Phạm vi đã kiểm

- Mẫu 10/11 lấy toàn bộ sinh viên đã xếp lịch trong đợt, mỗi SV một dòng; phiên bổ sung chỉ thay kết quả của đúng SV. Có kiểm trường hợp hai hội đồng và không đưa điểm giả cho SV vắng. Chưa khóa hội đồng hoặc còn chờ quyết định/kết quả thì chặn xuất bảng toàn đợt.
- Mẫu 11 yêu cầu mã học phần; kiểm mã gợi ý và mã khác ở cả bản xem trước, tệp lưu và ô B5 của XLSX. Giữ dấu nhận dạng nhập điểm từ tệp gốc.
- Biên bản mới cần mục tiêu, chức năng, kết quả, xếp loại từng SV có mặt và kiến nghị hoặc xác nhận không có kiến nghị. Ý kiến tại buổi họp được ghi theo SV và giảng viên hiện diện, bên cạnh nhận xét trên phiếu.
- Bản xuất để ký lưu nguyên byte và hash, người xuất, nguồn mẫu và bố trí. Tải lại khớp tệp đã lưu sau khi đính chính thông tin học vụ. Người ngoài phạm vi và SV không được truy cập lịch sử bản in hội đồng.
- Kho nội bộ: nộp, chống nộp trùng, TBM yêu cầu nộp lại, gửi phiên bản kế tiếp, duyệt lưu, tải theo quyền và thông báo. Kiểm thử tích hợp dùng PDF giả hợp lệ và mô phỏng kết quả quét an toàn; ca UI kho dùng API mô phỏng để kiểm thao tác, trạng thái, CSRF và phiên bản quyết định. Không xem các ca này là bằng chứng quét ClamAV thật cho riêng luồng kho.
- Các luồng UI nghiệp vụ khác dùng API/PostgreSQL và ClamAV thật trong schema riêng; ca hồi quy giao diện có mô phỏng API khi cần tái tạo tải chậm, lỗi hoặc dữ liệu đã chốt. Không gửi liên kết kích hoạt tới hộp thư thật.
- Báo cáo tổng hợp kiểm kết quả sau cùng của hai SV qua phiên chính/bổ sung; giới hạn quyền Admin ở số liệu tổng hợp. Bổ sung học vụ trước xếp lịch kiểm phạm vi, ngành trong danh mục, dữ liệu không hợp lệ và xung đột phiên bản. Dữ liệu đã xếp lịch dùng thao tác đính chính trên phiên bảo vệ.
- Tổng UI gồm tài khoản/phân quyền, danh sách giảng viên, đề tài, đăng ký, biểu mẫu, tài liệu/nhận xét theo vị trí, tiến độ, thông báo, đổi đề tài/gia hạn, xin thôi, xét bảo vệ, giao diện hội đồng, bảng điểm toàn đợt, kho và dashboard. Backend kiểm tiếp chấm, chốt, khóa và xuất mẫu.

Lượt tổng kiểm phát hiện lỗi khi tự lưu nhận xét trên bản đã được SV thay thế. Đã sửa để giữ nháp, chặn gửi lại bản cũ và hướng dẫn mở bản hiện hành; chạy lại luồng thực với API/PostgreSQL đạt. Ca thông báo được sửa để chờ xác nhận lưu thành công, tránh nhầm chữ còn trong ô nhập là báo cáo đã gửi. Các ca liên quan đều đã chạy lại.

Responsive đã kiểm ở 320, 390, 768 và 1440 px cho dashboard/kho/bảng điểm; màn hội đồng còn kiểm ở 1024 px. Có kiểm accessibility tự động ở những màn đã khai báo trong bộ UI. Computer Use trực tiếp không hoàn tất trong lượt này vì cơ chế kiểm soát URL chưa hỗ trợ trình duyệt Windows đang dùng; không lấy việc mở cửa sổ làm bằng chứng đã thao tác đủ giao diện.

## Đối chiếu bản in

Dùng chính hàm xuất sản phẩm với tệp gốc của Khoa, dữ liệu giả hai SV và danh sách dài 36 SV. Mở bản xuất bằng Microsoft Word/Excel ở chế độ đọc, xuất PDF rồi kiểm từng trang. Nguồn mẫu, tệp giả và ảnh kiểm tra giữ ở thư mục local bị Git bỏ qua.

| Mẫu | Kết quả quan sát |
| --- | --- |
| 6 | Một trang với dữ liệu thường; có lớp, ngành, khóa học, điểm thưởng, tổng và chỗ ký. |
| 9 | Hai trang; đủ mục IV/V, nhận xét, số phiếu và kết quả theo SV. Chỗ ký cùng kết quả và kiến nghị. |
| 10 | Hai SV một trang; 36 SV ba trang. Lặp tiêu đề bảng; hai dòng kết quả cuối đi cùng phần ký. Tăng khoảng đệm ô để họ tên/MSSV không sát nhau. |
| 11 | Hai SV một trang; 36 SV có họ đệm dài bốn trang. Tính chiều cao theo cột để không cắt chữ; lặp tiêu đề, giữ ít nhất ba dòng dữ liệu trên trang ký. Chọn mã CT2026 kiểm thử hiển thị đúng. |

Kết quả trên xác nhận các dữ liệu và bố cục đã thử; không bảo đảm mọi độ dài nội dung hoặc máy in đều ngắt trang giống nhau. Người xuất có bước xem trước và các tùy chọn trình bày giới hạn, không sửa chữ/điểm trên bản xem trước. Mẫu Khoa đổi cấu trúc cần đối chiếu và kiểm lại ánh xạ. Không có yêu cầu tải bản ký giấy trở lại để hoàn tất luồng này.

## Rà soát thao tác và giao diện ngày 16/11/2026

Đã dùng Computer Use trong trình duyệt tích hợp, đăng nhập nhanh tài khoản TBM demo trên CSDL local đang dùng. Mở lập hội đồng và lựa chọn bộ môn, bảng điểm toàn đợt SYN-DEMO, chọn mã IN4299N và áp dụng bản xem trước Mẫu 11. Mở dashboard, bấm nhóm đã chốt điểm để lọc đúng hai SV; mở kho nội bộ, tìm không có kết quả rồi xóa từ khóa để khôi phục danh sách. Không lập thêm hội đồng hoặc thay đổi kết quả đã chốt trong lượt kiểm trực tiếp này.

Phát hiện bộ lọc kho lệch hàng vì nhãn tìm kiếm xuống dòng. Đã tách tìm kiếm ra một hàng đầy đủ, ba ô chọn căn cùng hàng và chuyển một cột trên màn hình nhỏ. Thêm hướng dẫn người làm tiếp khi hồ sơ chưa nộp. Các màn dùng bố cục NV6 được tăng cỡ chữ nội dung 15 px, ô nhập 16 px; nút/ô nhập tối thiểu cao 44 px, nút dài tự xuống dòng. Tăng tương phản chữ phụ, viền ô/nút và viền lấy nét bàn phím; lưới con trong biểu mẫu chiếm đủ chiều ngang.

Chạy lại 7 ca UI trong `defense-workspace.spec.ts`, `defense-drafts.spec.ts`, `archive-workspace.spec.ts`: đạt, gồm responsive và các kiểm tra accessibility đã khai báo. Đã quan sát trực tiếp bố cục kho ở chiều rộng 390 px. Đây là kiểm tra bổ sung cho các màn trên, không phải lượt click lại toàn bộ chức năng hoặc thao tác nộp/chốt mới qua Computer Use.

Build frontend cuối đạt; Vite vẫn có cảnh báo kích thước gói chính. Tính tương phản cho các cặp màu được chọn: viền `#64748b`/trắng 4,76:1; chữ phụ `#475569`/nền `#f8fafc` 7,24:1; chữ chính `#0f172a`/trắng 17,85:1. Các số này áp dụng cho những cặp màu nêu trên, không phải chứng nhận tương phản cho toàn hệ thống.
