# Rubric Mẫu 6 — baseline dữ liệu

Migration [`20260925_0006_mau6_baseline.py`](../../backend/migrations/versions/20260925_0006_mau6_baseline.py) nạp bản thiết kế từ `SRC-MAU-06` vào `rubric_template` và `rubric_criterion`. `code=MAU-06-HOIDONG`, `version_no=1`, `state=DRAFT`. DRAFT nghĩa là **chưa được gắn vào đợt hoặc phiên chấm thật**; Khoa phải xác nhận hiệu lực vì QĐ 2919 nêu cơ cấu khác.

| Mã | Nhóm cha | Nội dung tiêu chí | Điểm tối đa | Kiểu |
| --- | --- | --- | ---: | --- |
| 1 | — | Hình thức | 2.0 | GROUP |
| 1.1 | 1 | Chuyên cần | 1.0 | NORMAL |
| 1.2 | 1 | Cấu trúc khóa luận/đồ án hợp lý, bố cục chặt chẽ, rõ ràng, trình bày theo đúng quy định. Đúng kỹ thuật soạn thảo văn bản, không có dấu hiệu đạo văn. | 0.5 | NORMAL |
| 1.3 | 1 | Trích dẫn và trình bày tài liệu tham khảo, hình vẽ, bảng biểu rõ ràng, đúng quy định, không có lỗi chính tả, không lỗi in ấn. | 0.5 | NORMAL |
| 2 | — | Nội dung | 4.0 | GROUP |
| 2.1 | 2 | Nêu được tính cấp thiết của đề tài, làm rõ tổng quan các công trình nghiên cứu, xác định mục đích, nhiệm vụ, đối tượng, phạm vi, nghiên cứu rõ ràng, hợp lý. | 0.5 | NORMAL |
| 2.2 | 2 | Nội dung nghiên cứu: Khối lượng công việc hợp lí; tư liệu phong phú, chính xác, phù hợp mục đích nghiên cứu. | 0.5 | NORMAL |
| 2.3 | 2 | Phương pháp nghiên cứu: Biết vận dụng các phương pháp nghiên cứu phù hợp với nội dung nghiên cứu của đề tài; trình bày nội dung có hệ thống khoa học, logic. | 1.0 | NORMAL |
| 2.4 | 2 | Khả năng áp dụng các giải thuật hiệu quả, số liệu chính xác; Khả năng giải quyết vấn đề, đầy đủ minh chứng khoa học; Khả năng suy luận, phân tích, tổng hợp tốt; có khả năng sáng tạo. | 1.0 | NORMAL |
| 2.5 | 2 | Kết quả nghiên cứu: - Nêu được kết quả đạt được phù hợp với mục tiêu nghiên cứu của đề tài; - Kết quả có giá trị về mặt lý luận và thực tiễn khoa học; - Có đánh giá, nhận xét kết quả, dự đoán tương lai (nếu cần). | 0.5 | NORMAL |
| 2.6 | 2 | Kết luận, kiến nghị phù hợp với nội dung nghiên cứu. | 0.5 | NORMAL |
| 3 | — | Demo và trả lời câu hỏi | 4.0 | GROUP |
| 3.1 | 3 | Demo không có lỗi, không vi phạm luật an ninh mạng/luật sở hữu trí tuệ; Có quy trình sử dụng/hướng dẫn sử dụng rõ ràng; Có triển khai, có khả năng ứng dụng. | 1.0 | NORMAL |
| 3.2 | 3 | Giao diện thân thiện, hợp lý; Các chức năng đáp ứng được yêu cầu của đề tài; Độ tin cậy, độ tương thích; Tốc độ, bảo mật, chi phí hợp lý. | 2.0 | NORMAL |
| 3.3 | 3 | Thuyết trình lưu loát, slide trình chiếu rõ ràng, có sáng tạo; Trả lời đúng, đáp ứng được yêu cầu các câu hỏi đặt ra. | 1.0 | NORMAL |
| 4 | — | Điểm thưởng (nếu có công bố kết quả nghiên cứu trên tập chí khoa học hoặc hội thảo trong và ngoài nước). Tổng điểm là 10 (kể cả điểm thưởng) | 1.0 | BONUS |

Ba dòng `GROUP` có điểm tối đa 2 + 4 + 4, nhưng chỉ là tổng của 12 dòng `NORMAL`, **không cộng thêm lần nữa**. Dòng `BONUS` tối đa 1; `Evaluation.bonus_points` là phần thưởng đã nằm trong `Evaluation.total_points`, không được cộng lại. PostgreSQL CHECK chặn bonus >1 và tổng >10. Service chấm điểm tương lai phải đối chiếu từng `EvaluationItem` với max của đúng phiên bản rubric, tính đủ 12 tiêu chí, kiểm minh chứng thưởng, và khóa khi có chữ ký đầu tiên của Mẫu 9.

Phiên bản 1 này giữ nguyên để đối chiếu lịch sử. Nếu Khoa ban hành biểu mẫu khác, tạo `RubricTemplate` phiên bản mới và chỉ gắn cho đợt/phiên tương ứng; không sửa nội dung phiếu đã chấm.

Nguồn: [đăng ký nguồn](../references/source-register.md) `SRC-MAU-06`; [xung đột nguồn](../references/source-conflicts.md) `CONFLICT-011`; [quy tắc nghiệp vụ](../requirements/business-rules.md) `BR-EVAL-003`.
