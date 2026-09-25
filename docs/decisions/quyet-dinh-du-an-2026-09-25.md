# Quyết định dự án ngày 25 tháng 9 năm 2026

**Nguồn:** `SRC-PROJECT-DEC-20260925` — chỉ đạo hiện tại của chủ dự án trong bản kế hoạch NV4. 

| Chủ đề | Quyết định và lý do | Trạng thái |
| --- | --- | --- |
| Nhóm đăng ký | Sinh viên tự lập nhóm 1–3 người; người tạo là điều phối nhóm. Giảng viên không tự thêm/ghép sinh viên. Thành viên khóa tại lúc gửi. Chưa tự cho phép đổi sau gửi. Tránh sai quyền và bảo vệ ràng buộc một đăng ký còn hiệu lực/sinh viên/đợt. | CONFIRMED_PROJECT_DECISION; không đổi thành viên sau gửi trong phạm vi hiện tại |
| Mẫu 9 | “Biên bản họp Hội đồng chấm khóa luận tốt nghiệp/đồ án tốt nghiệp”; biểu mẫu có vị trí chữ ký Chủ tịch **và** Thư ký. Chỉ chuyển SIGNED khi cả hai đúng CouncilMember của phiên đã xác nhận; không gán TBM làm người ký Mẫu 9. | CONFIRMED_PROJECT_DECISION; được sửa sau in trước chữ ký đầu, khóa từ chữ ký đầu tiên |
| Cán bộ điều phối KLTN | `KLTN_COORDINATOR` là ResourceAssignment theo ThesisRound/Khoa, khác vai trò Thư ký Hội đồng theo CouncilMember. Một người có thể giữ cả hai ngữ cảnh; không tạo base role mới. Người này quản lý mốc đợt từ nguồn chính thức, GVHD chỉ xác nhận tiến độ khóa luận được phân công. | CONFIRMED_PROJECT_DECISION |
| Expertise và eligibility | Giảng viên tự khai; TBM đúng bộ môn kiểm chứng bằng minh chứng, trường hợp tự kiểm chứng chuyển Trưởng khoa/người được giao. Snapshot đăng ký do người Khoa được giao theo đợt xác nhận sau đối chiếu nguồn Phòng Đào tạo. | CONFIRMED_PROJECT_DESIGN; vận hành cần assignment thực tế |
| Đủ điều kiện bảo vệ | Xét tổ hợp điều kiện Trường, mức hoàn thành, xác nhận GVHD, điều kiện Khoa nếu được ban hành, và similarity chỉ khi policy có hiệu lực. Không tự tạo ngưỡng. | CONFIRMED_PROJECT_DECISION; similarity chỉ advisory ở bản hiện tại |
| Similarity | Upload luôn nhận file hợp lệ; kiểm tra chạy sau upload và trả bằng chứng, tách lexical coverage với semantic score. Ngưỡng 90% không đồng nghĩa cosine 0,9. Chưa có policy thì advisory, không khóa nộp. | CONFIRMED_PROJECT_DECISION; không có ngưỡng chặn tự động ở bản hiện tại |
| Corpus | KLTN cũ là nguồn chính của thử nghiệm; các bài tập/đồ án/niên luận là bổ sung riêng loại. Khoảng 7 KLTN đủ thử pipeline nhưng không đủ kết luận chất lượng tổng quát. Giữ nguồn, phiên bản, visibility và phạm vi quyền cho từng chunk. | CONFIRMED_PROJECT_DECISION |
| Schema corpus | `RepositoryItem` hỗ trợ MANAGED_THESIS, IMPORTED_DOCUMENT, OFFICIAL_SOURCE; tài liệu nhập không được giả thành Thesis. `SearchIndexMetadata.document_version_id` tùy chọn; SimilarityMatch trỏ được RepositoryItem. | CONFIRMED_PROJECT_DECISION; migration 0003 |
| Tài liệu quy định trong RAG | Chỉ tài liệu được phép, có provenance/citation và lọc quyền; văn bản truy xuất là dữ liệu không đáng tin để ra lệnh cho LLM. | CONFIRMED_PROJECT_DECISION |
| Trích dẫn/TLTK | File “Quy định trích dẫn và trình bày tài liệu tham khảo” của Trường được dùng làm chuẩn dự án; không thay bằng APA 7 thuần. Phạm vi hiệu lực chính thức cho KLTN đại học cần xác nhận riêng, đặc biệt khi metadata QĐ 885 nêu sau đại học. | CONFIRMED_PROJECT_DECISION; phần hiệu lực OPEN-09 |
| Xuất biểu mẫu | Dữ liệu có kiểu → adapter mẫu/version → DOCX/XLSX → PDF khi cần → StoredFile/audit. Đúng bố cục nguồn chính thức; không tự dựng bản trông gần giống. | CONFIRMED_PROJECT_DECISION; runtime Mẫu 9 chờ mẫu trắng/field map có thể xác minh |
| Công cụ ngoài | Chỉ link-out HTTPS trong allowlist cấu hình, tab mới, không iframe/scrape mặc định, không open redirect theo URL người dùng. | CONFIRMED_PROJECT_DECISION |
| AI generation | Chưa có Gemini key. Retrieval/citations hoạt động không cần key; FakeLLM chỉ kiểm thử. Không tuyên bố Gemini đã chạy. | CONFIRMED_PROJECT_DECISION |
| Prototype | Giữ một lát cắt dùng tiếp: SV nộp nhóm → GV đề xuất duyệt → TBM chốt tạo Thesis/Member/AdvisorAssignment trong một transaction; React → FastAPI → PostgreSQL. Qdrant là chỉ mục có thể dựng lại. | CONFIRMED_PROJECT_DECISION; prototype không phải sản phẩm production |

## Giới hạn của bản triển khai hiện tại

Lát cắt API chỉ nhận đề tài đã duyệt do giảng viên đề xuất: giảng viên đề xuất là người nhận/từ chối đăng ký trước khi TBM phân công GVHD chính thức. Quy trình đề tài do sinh viên đề xuất và xác nhận đồng thuận của từng bạn cùng nhóm chưa đủ nguồn, nên chưa mở runtime. Quyền do backend kiểm tra, định danh bằng UUID chỉ dùng DEV/TEST và tự tắt ở production.

Tệp Mẫu 9 local có sáu cụm biên bản và dữ liệu điền sẵn; chưa phải một template trắng được gắn field có thể xuất an toàn. Chủ dự án xác nhận ngày 25/09 hiện chưa có mẫu trắng. Vì vậy thiết kế DTO/mapping đã ghi, còn **xuất Mẫu 9 đúng mẫu** chưa PASS. Không đưa binary nguồn hoặc bản chứa thông tin cá nhân lên Git.

Embedding trên dữ liệu giả chứng minh được nạp và truy xuất Qdrant. Không dùng điểm xếp hạng làm phần trăm đạo văn. Quyết định bản thử nghiệm không tự xác nhận tiêu chí bảo vệ, điểm chấm thật hay chữ ký ngoài hệ thống.

## Bổ sung quyết định từ chủ dự án ngày 25/09/2026

- **Nhóm:** Không ghép thêm sinh viên sau khi nhóm đã gửi đăng ký. Sinh viên tự lập nhóm trước khi gửi; giảng viên không thêm thành viên. Đây là quyết định dự án cho phạm vi hiện tại.
- **Tiến độ:** GVHD quản lý báo cáo thường kỳ của khóa luận. Lần nội bộ 1 là góp ý đề cương; lần nội bộ 2 dự kiến trong tháng 12 khi sản phẩm đạt khoảng 70%, có các GVHD góp ý chéo. Mốc ngày cụ thể phải nhập theo đợt từ lịch được phê duyệt; kế hoạch nguồn có năm/ngày mâu thuẫn nên không hard-code ngày cũ.
- **Bảo vệ:** Hiện chỉ áp dụng điều kiện cấp Trường trong QĐ2919 Điều 7; Khoa chưa bổ sung điều kiện riêng cho đợt đang thiết kế. Nếu Khoa ban hành tiêu chí sau này, dùng RoundPolicy có version/source thay vì đổi ngầm điều kiện cũ.
- **Trích dẫn:** Dùng hướng dẫn APA trong QĐ885 làm chuẩn thiết kế theo chỉ đạo chủ dự án. QĐ885 nêu phạm vi sau đại học, vì vậy không ghi rằng văn bản này tự động có hiệu lực bắt buộc đối với KLTN đại học; Mẫu 5 vẫn là nguồn trực tiếp về hình thức trình bày KLTN. Chưa tự động từ chối bài chỉ vì checker này.
- **Học phần IN4299N:** Sinh viên đủ điều kiện có thể chọn KLTN/ĐATN hoặc học phần thay thế theo QĐ2919 Điều 4.2; khung CTĐT Công nghệ phần mềm khóa 2024 tách hai đường. IN4299N không bắt buộc cho toàn bộ sinh viên năm cuối.
- **Chấm điểm:** Baseline phần mềm dùng đúng Mẫu 6 của Khoa: Hình thức 2, Nội dung 4, Demo/trả lời 4; thưởng tối đa 1 nhưng tổng phiếu không vượt 10. Đây là quyết định thiết kế dự án; xung đột với cơ cấu trong QĐ2919 vẫn cần văn bản/phê duyệt có thẩm quyền trước khi chấm thật.

## Chốt thiết kế bổ sung theo chỉ đạo mới

- **Sau khi in Mẫu 9:** Thư ký đối chiếu biên bản giấy với điểm/phiếu và thực tế buổi bảo vệ. Nếu phát hiện sai **trước chữ ký đầu tiên**, chính thành viên chấm sửa phiếu điểm của mình với lý do; Thư ký không nhập điểm thay. Hệ thống lưu AuditEvent, tính lại kết quả, đánh dấu bản in cũ VOID, tạo MinuteVersion mới liên kết `replacement_for_id`, mã hiển thị `minute_no` + `version_no` và thời gian phát hành, rồi in lại. Bản cũ giữ nguyên tệp/hash. Thư ký phải xác nhận bản giấy cũ chưa có chữ ký nào trước khi hủy bản in.
- **Sau khi có bất kỳ chữ ký nào trên biên bản giấy hoặc điện tử:** khóa điểm, nội dung và phiên bản; không có đường sửa hậu ký cho cả Thư ký, Chủ tịch hay Admin. Chữ ký đầu giữ state PRINTED cho tới khi đủ Chủ tịch và Thư ký nhưng vẫn khóa sửa. Nếu cần bản sao, xuất đúng bản đã ký và ghi nhận lần tải/in, không đổi nội dung/mã phiên bản.
- **OPEN-01:** TBM có chức vụ hiệu lực ở đúng bộ môn kiểm chứng hồ sơ chuyên môn GV dựa trên minh chứng; không tự kiểm hồ sơ của mình. Nếu GV khai là TBM, Trưởng khoa hoặc người được Trưởng khoa giao ở cùng Khoa kiểm. `SELF_DECLARED` vẫn tra cứu được với nhãn nguồn; `VERIFIED` chỉ sau khi có actor, time, evidence và audit. Đây là quy tắc phần mềm đề xuất, không gán rằng quy định Trường đã chỉ đích danh TBM.
- **OPEN-11:** Trưởng khoa/người có thẩm quyền của Khoa giao `ELIGIBILITY_VERIFIER` theo từng đợt cho cán bộ Khoa; người này đối chiếu danh sách/nguồn Phòng Đào tạo theo QĐ2919 Điều 15–16 và ngưỡng QĐ5964 trước khi xác nhận snapshot. SV chỉ tự khai, TBM/Admin không tự có quyền xác nhận. Mỗi quyết định lưu nguồn, actor, thời gian và lý do. Đây là cách phân công vận hành của dự án; người cụ thể phải được Khoa chỉ định khi triển khai.
- **OPEN-05:** Bản hiện tại chỉ **báo cáo tham khảo**, không dùng ngưỡng 90% để tự loại hay chặn nộp/bảo vệ. Semantic score chỉ tìm ứng viên; nếu tính phần trăm thì là tỷ lệ token hợp lệ thuộc hợp các đoạn trùng đã căn chỉnh, có corpus, phần loại trừ và phiên bản thuật toán. Báo cáo phải cho GVHD xem từng nguồn/đoạn. Tính năng chặn tự động là thay đổi chính sách tương lai, cần Khoa phê duyệt metric, corpus, phần loại trừ, ngưỡng và kiểm thử độ chính xác trước khi bật.
- **Mẫu 6 và APA/QĐ885:** Phần mềm thiết kế theo Mẫu 6 2/4/4, thưởng ≤1, tổng ≤10; và APA theo QĐ885 theo yêu cầu chủ dự án. Cơ cấu QĐ2919 khác Mẫu 6, còn QĐ885 ghi phạm vi sau đại học. Đây là baseline sản phẩm để nộp và thử; trước khi chấm/từ chối bài thật, Khoa cần xác nhận văn bản áp dụng. Hệ thống lưu nguồn/version để đổi chính sách sau mà không sửa dữ liệu lịch sử.
