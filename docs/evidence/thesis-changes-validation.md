# Kiểm chứng đổi đề tài và hai loại gia hạn

Ngày kiểm chứng 04/11/2026. Dữ liệu kiểm thử là hồ sơ giả trong schema tạo riêng; công cụ dọn đúng schema do lần chạy tạo.

- `python -m pytest tests/test_thesis_changes.py tests/test_report_and_notification_routing.py tests/test_nv6_evaluation.py tests/test_withdrawals.py tests/test_round_reopening.py -q --tb=short` đạt **47 ca**. Có luồng điều chỉnh, chuyển đề tài/GVHD, đồng ý cá nhân, cửa sổ thời gian, dữ liệu đã đổi, quyền xử lý, yêu cầu trùng, từ chối/hủy và rollback nếu phê duyệt lỗi giữa chừng.
- Gia hạn riêng được kiểm tra giới hạn một lần, hạn mới, bằng chứng thuộc hồ sơ, quyền quyết định và hạn nộp báo cáo có hiệu lực thực tế. Hạn chung của đợt được đối chiếu sau khi ghi gia hạn riêng.
- `python -m tools.validate_official_database` đối chiếu PostgreSQL cục bộ tại revision `20261104_0022` và báo **47 bảng nghiệp vụ, 132 FK, 111 CHECK, 38 UNIQUE, 32 chỉ mục khai báo**.
- `npm run build --prefix frontend` hoàn tất. Bộ build còn cảnh báo kích thước một số bundle.
- `KLTN_E2E_ALLOW_ISOLATED_SCHEMA=true python -m tools.run_e2e e2e/thesis-changes.spec.ts` đạt **2 ca Playwright**. Ca thứ nhất đi qua SV gửi → thành viên đồng ý → GVHD đồng ý → TBM duyệt → ghi nhận gia hạn thực hiện. Ca thứ hai đi qua Admin gia hạn/mở lại đợt đã đóng với xác nhận và xem lịch sử.
- Trình duyệt xác minh không tràn ngang ở **320, 360, 390, 768, 1024, 1440 và 1920 px**. Axe kiểm trang thay đổi và hộp thoại theo WCAG 2A/2AA/2.1AA báo không có vi phạm trong phạm vi được chạy.
- ClamAV đã cập nhật chữ ký thật trước khi chạy Playwright. Không gán trạng thái tệp an toàn giả trong ca trình duyệt. Ảnh thao tác và thông tin đăng nhập thử nghiệm chỉ giữ trong `tmp/`, không thuộc commit.

Phạm vi kiểm chứng giới hạn ở Chromium và các ca nêu trên. Các quyết định gia hạn trong bài kiểm thử là dữ liệu giả, chưa phải hồ sơ hành chính được Khoa xác nhận.
