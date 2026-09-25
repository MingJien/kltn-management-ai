# Vấn đề còn mở

## Quy ước

- `Blocking toàn Week 3`: cản mọi triển khai. Hiện không có mục nào ở mức này.
- `Blocking feature`: chỉ cản việc kích hoạt chức năng/quyết định tương ứng; vẫn có thể dựng schema, API và UI ở chế độ an toàn.
- `NO`: không cản logical design vì có safe default hoặc configuration point.
- Không OPEN nào được coi là đã chốt nếu chưa có nguồn/quyết định mới.

| ID | Vấn đề | Source/gap | Tác động | Blocking? | Workaround thiết kế hiện tại | Ai cần xác nhận | Thời điểm phải chốt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OPEN-01 | Ai xác nhận expertise do giảng viên tự khai? | SRC-GVHD-NV4-001 chỉ chắc phần GV tự khai; dòng “Trưởng bộ môn” không đủ ngữ pháp để gán quyền. | Publish hồ sơ chuyên môn/gợi ý GVHD. | NO; blocking feature verify | Giữ `SELF_DECLARED`; endpoint verify bị feature-flag; `PROPOSED` TBM. | GVHD/TBM/Khoa | Trước khi bật nhãn `VERIFIED` hoặc auto-suggestion dựa trên verified data. |
| OPEN-02 | Có cho ghép thêm SV sau đăng ký không? | Câu 5 chưa được trả lời trực tiếp. | Thành viên nhóm và invariant một SV/một đợt. | NO; blocking feature add-member | Không có lệnh ghép hậu đăng ký; thay đổi chỉ qua policy/quy trình mới. | GVHD/TBM | Trước khi triển khai chức năng thay đổi thành viên. |
| OPEN-03 | Milestone chi tiết ngoài kế hoạch SV/GVHD và mốc khoảng 70% là gì? | GVHD/Kế hoạch chỉ nêu checkpoint, lịch mẫu mâu thuẫn. | Lịch/nhắc việc và completeness. | NO | `ProgressMilestone` cấu hình/version theo round; không hard-code ngày. | GVHD/TBM | Trước khi mở từng ThesisRound. |
| OPEN-04 | Khoa có điều kiện riêng nào ngoài QĐ 2919 để đủ điều kiện bảo vệ? | Câu 14 không có câu trả lời trực tiếp; QĐ 5964 cho phép Khoa bổ sung tiêu chí. | Defense eligibility gate. | NO; blocking feature local-policy | Chỉ enforce điều kiện Trường; policy Khoa chưa có thì trả `NOT_CONFIGURED`, không tự loại. | Trưởng khoa/TBM | Trước khi Khoa muốn áp dụng tiêu chí riêng. |
| OPEN-05 | Exact metric, corpus, exclusion và hiệu chỉnh ngưỡng “90%”? | GVHD có mốc nghiệp vụ; project decision cấm map cosine; chưa có thực nghiệm. | Similarity decision gate. | NO cho Week 3; YES trước khi bật auto-block | Chạy advisory/evidence; `SimilarityPolicy` chưa ACTIVE thì không pass/fail/chặn. | Chủ dự án + GVHD/Khoa sau thực nghiệm | Trước khi kích hoạt chặn `FINALIZE/FINAL_SUBMISSION`. |
| OPEN-06 | Deadline/timing cụ thể theo năm học có xung đột. | CONFLICT-002/004 và file kỳ cũ. | Calendar/notification. | NO | Cấu hình trên `ThesisRound`, lưu source/version. | TBM/Khoa | Trước khi mở round tương ứng. |
| OPEN-07 | Sửa điểm/biên bản sau khi đã in hoặc ký theo thủ tục nào? | Câu 15 chỉ xác nhận sửa trước khi Thư ký in; nguồn không nêu hậu ký. | Tính bất biến pháp lý. | NO cho Week 3; YES trước feature correction hậu ký | Sau `PRINTED/SIGNED` khóa tuyệt đối; không Admin bypass/endpoint sửa. | Trưởng khoa/Phòng Đào tạo | Trước khi phát sinh yêu cầu sửa hậu ký hoặc trước production scoring. |
| OPEN-08 | “TBM ký biên bản” là loại biên bản nào? | CONFLICT-009: GVHD answer khác QĐ2919/Mẫu9 đối với biên bản bảo vệ. | Chữ ký theo loại văn bản. | NO | Biên bản bảo vệ: Chủ tịch ký; không gán TBM cho cùng loại. | GVHD/TBM | Trước khi số hóa loại biên bản khác. |
| OPEN-09 | Chuẩn trích dẫn tự động cuối cùng cho KLTN đại học là Mẫu 5 hay APA/QĐ885? | CONFLICT-008; QĐ885 trực tiếp cho sau đại học. | Citation checker. | NO; blocking feature auto-reject | Checklist Mẫu 5; không auto-reject APA. | Khoa/Trường | Trước khi triển khai citation checker tự động. |
| OPEN-10 | IN4299N là tự chọn hay bắt buộc với toàn bộ SV năm cuối? | CONFLICT-007 trong cùng đề cương học phần. | Báo cáo/chương trình đào tạo. | NO | Eligibility + đăng ký round là nguồn vận hành, không dùng nhãn học phần để chặn. | Khoa/Phòng Đào tạo | Trước báo cáo chương trình đào tạo dùng trường này. |
| OPEN-11 | Cá nhân/chức vụ nào xác nhận snapshot đủ điều kiện đăng ký? | QĐ2919 giao Khoa phối hợp Phòng Đào tạo; GVHD nói SV tự nhập; không chỉ rõ người bấm xác nhận. | Quyền `confirmEligibility`. | NO; blocking feature confirm nếu chưa cấu hình assignment | Dùng assignment `ELIGIBILITY_VERIFIER` theo round; không mặc định TBM/Admin; dữ liệu chưa xác nhận không chốt. | Trưởng khoa/Phòng Đào tạo/TBM | Trước khi cấu hình người vận hành round đầu tiên. |
| OPEN-12 | Cơ cấu Mẫu 6 Khoa 2/4/4 có được phê duyệt thay cơ cấu QĐ2919 1/6/1/2 cho đợt chấm thực tế không? | CONFLICT-011; Mẫu 6 và QĐ2919 cùng là nguồn chính thức nhưng khác cơ cấu. | Rubric áp dụng khi chấm thật và tính hợp lệ của phiếu. | NO cho logical DB; YES trước production scoring | Schema lưu RubricTemplate version/source và hierarchy; baseline thiết kế dùng đầy đủ Mẫu 6 theo quyết định dự án, chưa tự tuyên bố hiệu lực pháp lý. | Trưởng khoa/GVHD/Phòng Đào tạo | Trước khi khóa rubric và mở phiên chấm thật. |

## Các vấn đề đã đóng bằng nguồn/quyết định

- Gemini với retrieved chunks: `CONFIRMED_PROJECT_DECISION`, có authorization/PII/key/log guardrail.
- Trưởng khoa ký sau TBM chốt và không xét nội dung thay TBM: đã chốt.
- Chủ tịch lấy từ quyết định và ký biên bản bảo vệ: đã chốt.
- `AcademicYear → ThesisRound` cho đợt chính/bổ sung: đã chấp nhận.
- Quorum: QĐ 2919 quy định không họp nếu vắng quá 2/5 hoặc vắng Chủ tịch/Thư ký.
- Điều kiện bảo vệ cấp Trường: Điều 7 QĐ 2919.

Các safe default trên chỉ phòng rủi ro; không biến nội dung OPEN thành `CONFIRMED`.
