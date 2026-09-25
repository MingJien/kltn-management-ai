# Quyết định đã chốt và điều kiện trước khi vận hành thật

Phạm vi thiết kế hiện tại đã có quyết định xử lý cho các câu hỏi nghiệp vụ. “Đã chốt thiết kế” là lựa chọn của dự án, **không có nghĩa Khoa/Trường đã phê duyệt để áp dụng điểm hay từ chối bài thật**. Nguồn và lý do nằm ở [quyết định dự án](../decisions/quyet-dinh-du-an-2026-09-25.md).

| ID cũ | Kết luận cho sản phẩm hiện tại | Việc chỉ cần làm nếu triển khai thật hoặc đổi chính sách |
| --- | --- | --- |
| OPEN-01 | GV tự khai chuyên môn; TBM đúng bộ môn kiểm chứng bằng minh chứng. Khi TBM là người tự khai, Trưởng khoa/người được giao kiểm; không tự xác nhận. | Khoa phân công người giữ chức vụ/assignment thật trước khi bật nút VERIFIED. |
| OPEN-02 | SV tự lập nhóm 1–3 trước khi gửi; không thêm/đổi thành viên sau SUBMITTED; GV không ghép. | Nếu Khoa sau này cho đổi người, thiết kế một thủ tục có duyệt và audit riêng. |
| OPEN-03 | GVHD quản lý thường kỳ; góp ý đề cương lần 1; lần 2 dự kiến tháng 12 khoảng 70%, GVHD khác được giao góp ý chéo `COMMENT_ONLY`, không xác nhận thay GVHD chính. | Nhập ngày từng đợt từ kế hoạch đã duyệt. |
| OPEN-04 | Đợt hiện tại chỉ dùng Điều 7 QĐ2919 để xét bảo vệ, không tự thêm tiêu chí Khoa. | Nếu Khoa ban hành tiêu chí sau, thêm RoundPolicy có nguồn và version. |
| OPEN-05 | Similarity chỉ báo cáo tham khảo. Không diễn giải cosine 0,9 thành 90% giống và không tự chặn nộp/bảo vệ. | Gate tương lai chỉ bật sau khi Khoa duyệt metric, corpus, loại trừ, ngưỡng và bộ kiểm thử. |
| OPEN-06 | Lịch là dữ liệu theo đợt, không là hằng số trong CSDL. | Nhập ngày thật trước khi mở đợt. |
| OPEN-07 | Đã **in nhưng chưa ai ký**: sửa được với đối chiếu của Thư ký, lý do, audit, bản cũ VOID và in version mới. **Từ chữ ký đầu tiên**: khóa điểm/nội dung; bản sao chỉ lấy bản đã ký. | Cần runtime và mẫu trắng Mẫu 9 để phát hành đúng biểu mẫu. |
| OPEN-08 | Mẫu 9 do Chủ tịch và Thư ký ký; không gán TBM. | Văn bản khác nếu có phải phân tích riêng. |
| OPEN-09 | Thiết kế trích dẫn APA theo QĐ885 theo yêu cầu chủ dự án; Mẫu 5 vẫn là nguồn trình bày KLTN. | QĐ885 ghi phạm vi sau đại học; Khoa xác nhận văn bản áp dụng trước khi checker tự động từ chối KLTN đại học. |
| OPEN-10 | IN4299N là lựa chọn của SV đủ điều kiện, không bắt buộc toàn bộ SV năm cuối. | Không dùng nhãn học phần để tự đăng ký/thay lựa chọn của SV. |
| OPEN-11 | Người Khoa được giao `ELIGIBILITY_VERIFIER` theo đợt đối chiếu nguồn Phòng Đào tạo rồi xác nhận snapshot; SV chỉ tự khai, Admin/TBM không mặc nhiên có quyền. | Khoa chỉ định người thật theo từng đợt; QĐ2919 phân trách nhiệm cho đơn vị, không chỉ đích danh người bấm. |
| OPEN-12 | Baseline rubric sản phẩm theo Mẫu 6 Khoa: 2/4/4, 12 tiêu chí con, thưởng ≤1 trong tổng điểm ≤10. | QĐ2919 nêu cơ cấu khác 1/6/1/2; Khoa xác nhận mẫu có hiệu lực trước khi chấm thật. |

## Trạng thái thực hiện

- CSDL head `20260925_0005` đã bổ sung `COMMENT_ONLY` bằng Alembic migration; `kltn_dev` được nâng từ 0004, kiểm thử rollback dữ liệu giả. [Đối chiếu CSDL](../design/doi-chieu-quyet-dinh-csdl.md) nêu bảng/cột tương ứng.
- Prototype hiện chạy một lát cắt đăng ký nhóm và truy xuất AI trên dữ liệu giả. Xác nhận expertise/eligibility, chấm thật, xuất Mẫu 9 và kiểm tra tương đồng toàn văn **chưa phải runtime hoàn chỉnh**; xem [minh chứng](../evidence/prototype-validation.md).
- Hai việc có nguồn pháp lý mâu thuẫn (OPEN-09/12) được **chốt baseline thiết kế**, giữ điểm kiểm soát trước triển khai thật. Không tự gọi quyết định dự án là văn bản thay thế QĐ của Trường.
