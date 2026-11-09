# Rà soát phân hệ bảo vệ ngày 09/11/2026

Đã đối chiếu các mục nghiệp vụ đang lưu từ QĐ2919 với BR-COUNCIL-002, BR-EVAL-002 và BR-EVAL-003.

- Hội đồng mới cần đúng 5 tài khoản khác nhau gồm chủ tịch, thư ký, hai phản biện và một ủy viên.
- Thư ký ghi thành phần dự họp sau giờ bảo vệ. Phiên cần ít nhất 3/5 người và phải có chủ tịch, thư ký. Người vắng không được lập phiếu chấm. Biên bản ghi rõ người có mặt/vắng.
- Điểm mỗi phiếu sau thưởng được giới hạn 10 và làm tròn 1 chữ số, sau đó điểm trung bình các phiếu hiện diện được làm tròn 1 chữ số.
- Bản chốt mới lưu kết quả tổng hợp cùng dữ liệu chốt. Kết quả cũ dùng độ chính xác lịch sử, tránh áp dụng ngược cách tính mới.
- Chủ tịch/thư ký được mở sửa trước khi khóa bảng điểm, cần lý do và xác nhận hồ sơ chưa ký. Sự kiện lịch sử giữ bản dữ liệu cũ để đối chiếu. Sau sửa phải chốt lại, xuất theo mã phiên bản mới.
- UI bổ sung tổng điểm dự kiến, tìm lịch, thao tác thu gọn, danh sách việc/phiếu còn thiếu và điểm danh hội đồng.

Kiểm chứng đã chạy trên mã local:

- `python -m pytest tests/test_nv6_defense.py tests/test_nv6_evaluation.py -q --tb=short` đạt 23 ca.
- Sau bổ sung tương thích điểm cũ, `python -m pytest tests/test_nv6_defense.py -q --tb=short` đạt 2 ca, gồm xuất Mẫu 6/9/10/11 và chu trình chốt → mở sửa → chốt lại.
- `python -m tools.run_e2e e2e/defense-workspace.spec.ts` đạt 1 ca với tài khoản giả trong schema riêng. Kiểm tra biểu mẫu 5 người, không tràn ngang ở 320/390/768/1024/1440 px, Axe WCAG 2A/2AA/2.1AA trong trang bảo vệ không có vi phạm.
- `npm run build --prefix frontend` thành công. Có cảnh báo kích thước bundle.
- Chưa đối chiếu bản in thực tế từng trang với mẫu Khoa đã phát hành. Ca giao diện mới kiểm trang và biểu mẫu hội đồng; toàn bộ buổi chấm và xuất được kiểm ở API, chưa có ca trình duyệt đi hết chu trình.
