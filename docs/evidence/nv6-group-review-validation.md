# Kiểm chứng luồng phản biện, điều kiện bảo vệ và thay đổi thành viên nhóm

Ngày kiểm: **03/11/2026**. Phạm vi: NV6 tuần 1, nối luồng xin thôi cá nhân với đề cương, cuốn báo cáo, Mẫu 7/8, xét điều kiện và thông báo trong tài khoản. [Hướng dẫn UI theo vai trò](../design/nv6-review-defense-workflow.md).

## Kết quả trên bộ source giao NV6

Source được lấy từ Git index vào thư mục kiểm riêng, không lấy các sửa đổi local ngoài phạm vi. Các tài liệu schema/OpenAPI được sinh từ chính bộ source này; không đưa cấu hình, mẫu gốc, dữ liệu thật, tài khoản thử, ảnh hay log vào Git.

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend `python -m pytest tests -q --tb=short` | **205 đạt**, hai cảnh báo deprecation của thư viện, không lỗi/skip |
| Luồng rút nhóm và hồi quy NV6 `python -m tools.run_e2e nv6-evaluation.spec.ts withdrawals.spec.ts` | **4 kịch bản đạt** qua cookie đăng nhập, UI, API, PostgreSQL và ClamAV thật; không mock route |
| Frontend `npm run build` | **Đạt** TypeScript và Vite production build; còn cảnh báo chunk xem tài liệu lớn |
| `python -m tools.export_runtime_openapi --check` | **Đạt**, hợp đồng API khớp mã FastAPI |
| Database local `python -m tools.validate_official_database` | **Đạt**, head `20261102_0019`, **43 bảng nghiệp vụ, 117 FK, 102 CHECK, 35 UNIQUE, 30 index tường minh** |
| Mobile và accessibility | **Đạt** tại 390×844, không cuộn ngang; axe WCAG 2 A/AA và WCAG 2.1 AA không báo vi phạm trong vùng NV6 và Xin thôi được kiểm. Đã xem ảnh desktop/mobile để chỉnh phần căn cứ và các bước xử lý |

## Các nhánh nghiệp vụ đã kiểm

- TBM có đúng chức vụ/bộ môn mới phân công, thu hồi, gia hạn và xét điều kiện. Chặn GVHD phản biện chính đề tài mình, GV khác bộ môn, GV không hoạt động, trùng người, quá hai phân công và màn hình cũ. Thu hồi làm mất quyền đọc API/tệp và lọc lại liên kết thông báo.
- GVHD lập Mẫu 7, GVPB lập Mẫu 8, gắn đúng SV, phân công và phiên bản báo cáo. Nháp riêng; bản đã gửi bất biến; sửa nội dung nháp phải đính kèm lại bản ký. Tệp chưa sạch không được dùng, người gửi xác nhận bản ký khớp nội dung. Không tuyên bố xác thực chữ ký số.
- Xét riêng ba căn cứ cấp Trường theo từng SV; không tự thêm phản biện/tương đồng thành điều kiện chặn. Cả nhóm chỉ chuyển sẵn sàng khi tất cả thành viên đang thực hiện được xét đủ. Có lịch sử và mở xét lại, không sửa đè kết quả cũ.
- SV gửi đơn đúng cửa sổ 14 ngày theo giờ Việt Nam. Gửi đơn, GVHD xác nhận, trả lại hoặc SV hủy yêu cầu không tự rút thành viên. Đơn chỉ thay đổi quyền tham gia khi điều phối đúng đợt ghi nhận kết quả cho thôi, có minh chứng sạch, căn cứ, ngày hợp lệ và xác nhận đối chiếu ở cả UI/API. Ngoài hạn không tự hủy hay tự gán điểm.
- Sau khi đề cương đã chốt, một SV được ghi nhận cho thôi: thành viên còn lại giữ đề tài, mã khóa luận và GVHD; chuyển người đại diện nếu cần. Đề cương chuyển yêu cầu sửa; API từ chối xác nhận/chốt lại bản cũ. Phiên bản mới được GVHD xác nhận và TBM chốt riêng; xác nhận v1 vẫn còn trong CSDL, không áp dụng cho v2.
- Bản báo cáo cũ chuyển cần cập nhật, cho nộp một bản sửa trong cùng hồ sơ kể cả khi bản cũ đã tiếp nhận/hạn đóng. Trong lúc thiếu đề cương đã duyệt lại hoặc báo cáo cập nhật, API chặn tạo/sửa/gửi phiếu và lưu xét điều kiện; UI chỉ việc cần làm và dẫn đến đúng nơi cập nhật. Kết quả cũ cần xét lại; phiếu, tệp và lịch sử cũ được giữ.
- Hoàn tất đề cương mới và báo cáo mới chưa tự đủ điều kiện: GVHD lập/gửi Mẫu 7 mới, TBM đối chiếu và xét SV còn lại. Luồng trình duyệt đi đến `READY_FOR_DEFENSE` với một thành viên đang thực hiện; không phải chọn đề tài khác.
- Người đã rút mất quyền hồ sơ nhóm nhưng vẫn xem đơn của mình. Thành viên khác/GVPB không đọc lý do hoặc bản đơn riêng. Thông báo nhóm dùng nội dung chung; thông báo cá nhân dẫn đúng đơn. Không chấp thuận cho thôi thì SV giữ quyền; nếu không còn thành viên thì khóa luận kết thúc, phân công nhận xét bị thu hồi. Kiểm lỗi giữa giao dịch xác nhận rollback cả thành viên lẫn đơn.

Backend tests dùng schema mới được Alembic dựng, tắt SMTP và mô phỏng phán quyết quét ở một số nhánh để kiểm trạng thái cách ly/được phép. E2E dùng ClamAV thật với PDF và dữ liệu tổng hợp. Hai loại bằng chứng này được phân biệt; không dùng mô phỏng thay cho kết quả quét thật. Mỗi lượt chỉ xóa schema thử do chính nó tạo.

## Phạm vi chứng nhận và vận hành

Kết quả này chứng nhận các luồng nêu trên, không phải một lượt đạt toàn bộ bộ UI cũ. Giới hạn kiểm thử UI lịch sử vẫn được giữ ở [minh chứng NV6 tuần 1](nv6-week1-validation.md). Hội đồng, lịch bảo vệ, điểm, biên bản, lưu trữ và AI tiếp theo chưa được chứng nhận bởi lượt kiểm này.

Thông báo được gửi trong tài khoản, không phải email/lời nhắc hẹn giờ. Đơn xin thôi xuất DOCX hiện là phiếu đề nghị có mã do hệ thống tạo; bản mẫu hành chính chính thức cần Khoa cung cấp. Các bước xác nhận/ký và xử lý hành chính ngoài hệ thống vẫn cần thực hiện thật. Luồng tự gửi đơn áp dụng trong 02 tuần đầu theo quy tắc đang cấu hình của dự án; hồ sơ quá hạn được hướng dẫn liên hệ đơn vị phụ trách, không tự tạo ngoại lệ.

Database hiện có nâng bằng `alembic upgrade head`; không chạy SQL init. Máy chủ cần PostgreSQL, ClamAV và mẫu 7/8 chính thức qua kho theo đợt hoặc `KLTN_OFFICIAL_TEMPLATE_DIR`. Nguồn đối chiếu là mã dự án, yêu cầu trực tiếp của người dùng và mẫu local đã có; lượt này không đọc lịch sử ChatGPT Project hay Google Drive.
