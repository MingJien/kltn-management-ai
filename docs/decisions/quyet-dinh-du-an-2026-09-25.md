# Quyết định thiết kế nghiệp vụ NV4 — 25/09/2026

Tài liệu này tập hợp **những lựa chọn đã chốt để thiết kế hệ thống KLTN**. Nguồn trao đổi ngày 25/09/2026 có mã `SRC-PROJECT-DEC-20260925`; các văn bản Trường/Khoa và biểu mẫu được đối chiếu trong [đăng ký nguồn](../references/source-register.md). Quyết định thiết kế giúp mô hình dữ liệu, API và giao diện nhất quán; nó không tự thay đổi hiệu lực của quy định chính thức. Khi có văn bản mới, tạo phiên bản chính sách hoặc biểu mẫu tương ứng và giữ nguyên dữ liệu lịch sử.

## 1. Người tham gia và thẩm quyền

### Chuyên môn của giảng viên

Giảng viên tự khai lĩnh vực chuyên môn và nộp minh chứng. Trưởng bộ môn (TBM) đang giữ chức vụ ở **đúng bộ môn** kiểm chứng; người khai không được tự xác nhận hồ sơ của mình. Nếu người khai là TBM, Trưởng khoa hoặc người được Trưởng khoa giao kiểm chứng. Hệ thống phân biệt thông tin `SELF_DECLARED` với `VERIFIED`, lưu người xác nhận, thời điểm, minh chứng và audit. Đây là phân công trong thiết kế phần mềm; quy định Trường không chỉ đích danh người bấm nút này.

### Xác nhận đủ điều kiện đăng ký

Sinh viên có thể cung cấp thông tin ban đầu, nhưng không tự xác nhận mình đủ điều kiện. Theo từng đợt, Khoa giao một người giữ quyền `ELIGIBILITY_VERIFIER`; người này đối chiếu nguồn chính thức từ Phòng Đào tạo, Điều 15–16 QĐ2919 và các ngưỡng trong QĐ5964 trước khi xác nhận snapshot. Mỗi lần xác nhận lưu nguồn, người thực hiện, thời điểm và lý do. Admin hay TBM không mặc nhiên có quyền này chỉ vì tên vai trò; Khoa phải phân công người cụ thể khi triển khai.

### Lựa chọn học phần và quyền theo ngữ cảnh

IN4299N/KLTN là **lựa chọn** của sinh viên đủ điều kiện theo QĐ2919 và khung chương trình được đối chiếu, không áp dụng bắt buộc cho toàn bộ sinh viên năm cuối. `KLTN_COORDINATOR` là quyền được giao theo Khoa/đợt để điều phối lịch và hồ sơ, khác Thư ký của một Hội đồng bảo vệ. Cùng một người có thể giữ hai trách nhiệm ở hai ngữ cảnh; không tạo vai trò nền mới chỉ vì họ kiêm nhiệm.

## 2. Đề tài, nhóm và đăng ký

Sinh viên tự lập nhóm **1–3 người**; người tạo là người điều phối. Với nhóm nhiều người, **từng thành viên đăng nhập và tự xác nhận tham gia** trước khi nhóm được gửi chính thức. Không được coi việc người điều phối nhập tên bạn mình là bằng chứng đồng ý. Phản hồi `ACCEPTED` hoặc `DECLINED` phải lưu đúng tài khoản và thời điểm; người từ chối được rời bản nháp. Giảng viên không tự thêm hoặc ghép sinh viên. Danh sách thành viên khóa khi đăng ký chuyển `SUBMITTED`; nếu một quy định mới cho đổi người, phải thiết kế thủ tục duyệt và audit riêng thay vì sửa ngầm lịch sử. CSDL chặn một sinh viên có hai đăng ký còn hiệu lực trong cùng đợt; service kiểm số lượng nhóm, từng phản hồi và trạng thái trước khi gửi.

Với **đề tài do giảng viên đề xuất và đã duyệt**, giảng viên đề xuất nhận hoặc từ chối nhóm đăng ký; sau đó TBM đúng bộ môn chốt phân công GVHD. Với **đề tài do sinh viên đề xuất**, nhóm lập đề tài và đăng ký trước; sau khi từng thành viên xác nhận, nhóm gửi đăng ký để TBM xét **nội dung đề tài sau đó**. TBM có thể yêu cầu sửa, từ chối hoặc duyệt đề tài; không yêu cầu đề tài đã APPROVED trước bước đăng ký. Sau khi duyệt nội dung đề tài, TBM đề xuất người hướng dẫn phù hợp; giảng viên được phân công đồng ý trước khi TBM chốt đăng ký. Cả hai nhánh khi chốt đều tạo `Thesis`, các `ThesisMember` và `AdvisorAssignment` trong một transaction. Nhánh sinh viên đề xuất và thao tác xác nhận của từng thành viên là **hợp đồng thiết kế mới**, chưa có endpoint runtime trong prototype hiện tại.

## 3. Tiến độ và điều kiện bảo vệ

GVHD chính quản lý và xác nhận báo cáo tiến độ thường kỳ của khóa luận được phân công. Buổi nội bộ lần 1 là góp ý đề cương; lần 2 dự kiến tháng 12, khi sản phẩm đạt khoảng 70%, để các GVHD được giao **góp ý chéo**. Người góp ý chéo lưu `ProgressReview.decision=COMMENT_ONLY`, không xác nhận tiến độ thay GVHD chính. Các ngày cụ thể là dữ liệu của từng đợt lấy từ kế hoạch đã duyệt, không hard-code ngày cũ trong CSDL.

Đợt đang thiết kế dùng điều kiện bảo vệ trong **Điều 7 QĐ2919**; chưa tự thêm điều kiện riêng của Khoa. Nếu Khoa ban hành điều kiện mới, lưu `RoundPolicy` có nguồn và phiên bản, áp dụng cho đúng đợt. Kết quả similarity hiện chỉ là thông tin tham khảo, không tự biến thành điều kiện đủ hoặc không đủ bảo vệ.

## 4. Kiểm tra tương đồng và kho nguồn

Tệp hợp lệ được nhận trước; kiểm tra tương đồng chạy sau upload. Semantic score chỉ dùng xếp hạng nguồn/đoạn ứng viên, **không phải phần trăm đạo văn**: cosine `0,9` không có nghĩa 90% văn bản giống. Nếu hiển thị tỷ lệ trùng, cần định nghĩa tỷ lệ token hợp lệ nằm trong hợp các đoạn khớp đã căn chỉnh, cùng corpus, phần loại trừ và phiên bản thuật toán. Báo cáo phải cho GVHD xem nguồn và đoạn chứng cứ. Chưa có chính sách ngưỡng được phê duyệt thì kết quả ở trạng thái `ADVISORY`, không tự chặn nộp hay bảo vệ. Chức năng chặn tự động về sau chỉ bật sau khi Khoa duyệt metric, corpus, loại trừ, ngưỡng và bộ đánh giá độ chính xác.

KLTN cũ là nguồn thử nghiệm chính; niên luận, đồ án học phần và tài liệu chính thức được phân loại riêng. Khoảng bảy KLTN cũ có thể thử pipeline nhưng chưa đủ kết luận chất lượng tổng quát. `RepositoryItem` tách `MANAGED_THESIS`, `IMPORTED_DOCUMENT`, `OFFICIAL_SOURCE`; tài liệu nhập không tạo `Thesis`/sinh viên giả. Mỗi nguồn và chunk lưu định danh, phiên bản, provenance, quyền xem và citation. Văn bản lấy từ kho là **dữ liệu không đáng tin để ra lệnh cho AI**. Truy xuất trên dữ liệu giả có thể chạy không cần Gemini key; chưa được coi là đã kiểm nghiệm AI trên KLTN thật.

## 5. Chấm điểm và biên bản Hội đồng

Baseline rubric dự án dùng Mẫu 6 của Khoa: **Hình thức 2 điểm, Nội dung 4 điểm, Demo/trả lời 4 điểm**, đủ 12 tiêu chí con; điểm thưởng tối đa 1 và tổng mỗi phiếu không quá **10**. Điểm nhóm chỉ tổng hợp tiêu chí con, không cộng lặp; thưởng nằm trong tổng phiếu. Đây là lựa chọn đã chốt cho phân tích, thiết kế và baseline CSDL; khác biệt với cách diễn đạt trong QĐ2919 được giữ lại trong sổ nguồn để truy vết, không còn là câu hỏi mở của NV4. CSDL nạp [rubric Mẫu 6 đầy đủ](../design/rubric-mau-6.md) ở trạng thái `DRAFT` vì runtime chấm điểm và việc gán đúng version cho đợt thật chưa được xây dựng. Nếu sau này có biểu mẫu/chính sách mới, tạo version rubric mới và giữ nguyên lịch sử.

Mẫu 9 là **Biên bản họp Hội đồng chấm KLTN/ĐATN**, do **Chủ tịch và Thư ký** của đúng Hội đồng ký; không gán TBM ký Mẫu 9. Sau khi in nhưng **trước chữ ký đầu tiên**, Thư ký đối chiếu thực tế và xác nhận bản giấy chưa ai ký. Nếu sai, chính người chấm sửa phiếu của mình với lý do; hệ thống ghi audit, tính lại kết quả, đánh dấu `MinuteVersion` cũ `VOID`, tạo bản mới có liên kết `replacement_for_id`, mã phiên bản và thời gian phát hành rồi in lại. Tệp/hash bản cũ được giữ. **Từ chữ ký đầu tiên trên giấy hoặc điện tử**, khóa điểm, nội dung và phiên bản, kể cả khi biên bản tổng vẫn đang ở `PRINTED`; đủ hai chữ ký mới chuyển `SIGNED`. Lần tải hoặc in bản sao sau ký chỉ dùng đúng nội dung bản đã ký và được ghi nhận, không tạo bản nội dung khác.

## 6. Trích dẫn, biểu mẫu và công cụ ngoài

Thiết kế trích dẫn theo hướng dẫn APA trong QĐ885 theo lựa chọn của đề tài; Mẫu 5 vẫn là nguồn trình bày trực tiếp cho KLTN. QĐ885 ghi phạm vi sau đại học, nên không tuyên bố văn bản này tự động bắt buộc với KLTN đại học và chưa dùng checker để tự từ chối bài. Khoa cần xác nhận văn bản áp dụng trước khi có kiểm tra tự động mang tính quyết định.

Luồng xuất biểu mẫu đi từ dữ liệu có kiểu → adapter theo biểu mẫu/phiên bản → DOCX hoặc XLSX → PDF khi cần → `StoredFile` và audit. Tệp nguồn phải là mẫu chính thức có thể xác định field; không tạo bản gần giống rồi gọi là đúng mẫu. Các công cụ ngoài chỉ mở qua link HTTPS trong allowlist cấu hình, tab mới; không nhúng iframe, scrape mặc định hay nhận URL chuyển hướng tùy ý từ người dùng.

## 7. Điều kiện trước khi vận hành với hồ sơ thật

Các lựa chọn trên đã đủ để tiếp tục thiết kế và phát triển. Trước khi hệ thống xác nhận quyền, chấm điểm hoặc tự từ chối hồ sơ thật, cần:

1. Khoa phân công người giữ quyền xác nhận chuyên môn và đủ điều kiện theo đúng bộ môn/đợt; nhập lịch đợt chính thức.
2. Khi triển khai chấm thật, cấu hình đúng version rubric cho đợt được phép chấm; baseline hiện tại của dự án là Mẫu 6 như đã chốt. Nếu có văn bản hoặc biểu mẫu mới, thêm version mới, không sửa rubric đã dùng. Checker trích dẫn không được tự từ chối bài khi chưa có chính sách áp dụng cho đợt.
3. Hoàn thiện service xác nhận từng thành viên và nhánh đề tài do sinh viên đề xuất, có test về quyền và thứ tự duyệt, trước khi mở đăng ký thật.
4. Có mẫu trắng Mẫu 9 được duyệt, map field và kiểm xuất đúng bố cục; lưu chứng cứ chữ ký giấy/điện tử để khóa nội dung từ chữ ký đầu tiên.
5. Chỉ xem xét chặn tự động bằng similarity khi đã có chính sách và bộ kiểm thử được phê duyệt.

**Trạng thái phần mềm đã chạy và việc cần hoàn thiện cho bản nộp cuối** được theo dõi tại [README](../../README.md) và [minh chứng prototype](../evidence/prototype-validation.md). Tài liệu quyết định này không dùng kết quả thiết kế để tuyên bố các chức năng chưa xây xong đã hoạt động.
