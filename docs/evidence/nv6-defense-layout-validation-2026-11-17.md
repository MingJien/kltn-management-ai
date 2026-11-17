# Kiểm chứng bố trí hội đồng và xếp lịch ngày 17/11/2026

Thay đổi giao diện: tách đợt/bộ môn, gợi ý tên hội đồng, ba mục danh sách riêng, hộp thoại tạo/xếp lịch, nhóm thành viên và căn chỉnh biểu mẫu đổi lịch. Giữ nguyên kiểm quyền và điều kiện nghiệp vụ phía máy chủ; không đổi dữ liệu hội đồng hiện có.

Kiểm chứng trên mã cập nhật:

- `npm --prefix frontend run build`: đạt. Vite còn cảnh báo kích thước gói chính.
- `defense-drafts.spec.ts`: 6 ca đạt với API mô phỏng. Kiểm tách đợt/bộ môn, phạm vi chưa được giao, tên gợi ý theo phạm vi, chặn trùng vai trò, đóng hộp thoại có nháp, chuyển danh sách, giải thích đề tài không có, đổi lịch và chặn giờ kết thúc sai; hồi quy giữ nháp/điểm, Mẫu 11, đính chính và bảo vệ bổ sung. Ca hội đồng kiểm viewport 320/390/768/1440 và axe; ca đổi lịch kiểm 320/768/1440.
- `python -m tools.run_e2e defense-workspace.spec.ts workflow-notices.spec.ts`, với `KLTN_E2E_ALLOW_ISOLATED_SCHEMA=true`: 3 ca đạt qua trình duyệt, API và PostgreSQL. Dùng schema mới và tài khoản giả, quét ClamAV thật; schema test được dọn riêng. Kiểm biểu mẫu 5 thành viên, responsive 320–1440, báo cáo/kho, thông báo theo phạm vi và chọn đề tài loại GVHD.

Lượt chạy ban đầu trong môi trường hạn chế chưa truy cập được dịch vụ cục bộ. Đã chạy lại với quyền localhost và schema test riêng, không bỏ kiểm quét tệp hoặc dùng dữ liệu nghiệp vụ của người dùng. Các ca mô phỏng không được coi là kiểm lại toàn bộ vòng đời thật; lượt này không thay đổi bộ xuất biểu mẫu và không kiểm in lại tất cả mẫu.
