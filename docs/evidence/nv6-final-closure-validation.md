# Kiểm chứng hoàn thiện luồng NV6 ngày 16/11/2026

Phạm vi: đính chính sau khóa, bổ sung biên bản lịch sử, phát hành bản in theo phiên bản, đối chiếu SV chưa xếp lịch và điều kiện nộp lưu. Không thay đổi AI, không sao chép dữ liệu thật hoặc biểu mẫu nguồn vào Git.

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend `python -m pytest -q --tb=short` | 276 đạt, 6 cảnh báo deprecation thư viện/cấu hình, không lỗi hoặc skip. |
| Hồi quy nghiệp vụ, xuất và OpenAPI | 15 đạt trước lượt tổng kiểm cuối. |
| UI liên quan | 8 ca đạt qua các bộ `defense-drafts`, `defense-workspace`, `archive-workspace` và lượt chạy lại sau sửa. |
| Build frontend | Đạt; vẫn có cảnh báo kích thước gói chính của Vite. |
| CSDL local | Alembic head `20261116_0031`, 54 bảng nghiệp vụ, 158 FK, 127 CHECK, 39 UNIQUE và 40 index tường minh. `alembic check` không có thay đổi mới. |

Kiểm thử tích hợp xác nhận:

- Thư ký lập đề nghị đính chính trên phiên đã khóa; người lập không tự duyệt, SV không được xử lý, TBM chỉ duyệt trong phạm vi bộ môn. Chặn đề nghị trùng, xử lý lại và duyệt khi nguồn đổi; đề nghị cũ có thể bị từ chối để lập lại.
- Duyệt phiếu tạo phiên bản mới, vẫn giữ hội đồng khóa và bản cũ. Chỉ tính lại SV cần đính chính, không làm tròn lại hoặc thay kết quả lịch sử của các SV khác; có ca riêng giữ điểm lịch sử 7,25 của người không bị đính chính.
- Biên bản cũ thiếu xếp loại được bổ sung qua đề nghị có căn cứ và duyệt độc lập, không đổi điểm. Bản Mẫu 9 mới dùng để ký bị chặn nếu còn thiếu nội dung bắt buộc.
- Bản xuất đã lưu tải lại đúng byte sau đính chính. Lịch sử nhận diện bản không còn khớp nguồn hiện tại và cảnh báo đề nghị đang chờ.
- Muốn lưu bản dùng để ký phải có dấu phiên bản từ bước xem trước. Đổi dữ liệu, nguồn mẫu hoặc định dạng sau bước xem trước bị từ chối; khi còn đề nghị chờ cũng chưa phát hành bản mới.
- Bảng toàn đợt hiện danh sách SV đủ điều kiện nhưng chưa xếp lịch, đồng thời giữ phạm vi bảng điểm là SV đã được xếp lịch; không tự cho 0 hoặc ghi không đạt cho SV chưa xếp lịch.
- Kho chưa đủ điều kiện vẫn có GVHD/SV để tìm kiếm, kèm điều kiện thiếu và liên kết tới hồ sơ đối chiếu. Quyền nộp lưu được giữ theo kết quả sau cùng và khóa hội đồng.

UI đã kiểm lựa chọn mã học phần, xem trước/lưu bản in, bảng đối chiếu trước–đề nghị, gửi/duyệt đính chính, giữ trạng thái khóa và responsive 320–1440 px trong các ca khai báo. Lượt đầu phát hiện tràn chiều ngang tại bảng đối chiếu lồng trong phiên bảo vệ; đã sửa co giãn vùng chứa rồi chạy lại đạt. Ca UI đính chính dùng API mô phỏng; quyền duyệt và tính toán điểm được kiểm trên PostgreSQL ở backend. Các bộ UI dùng schema và cổng riêng; không gửi email kích hoạt thật. Đây không phải lượt click thủ công toàn bộ hệ thống trên CSDL người dùng.

Áp dụng lên database đang dùng bằng Alembic, không chạy lại SQL khởi tạo. Hướng dẫn thao tác tại [Đính chính và phát hành hồ sơ](../design/defense-corrections.md).
