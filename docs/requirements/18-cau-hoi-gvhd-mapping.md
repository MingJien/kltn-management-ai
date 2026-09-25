# Đối chiếu 18 câu hỏi GVHD

Nguồn trả lời: `SRC-GVHD-NV4-001`, bản Drive mới nhất. Phần trả lời là một đoạn liên tục, không đánh số theo câu hỏi; mapping dưới đây chỉ gắn nội dung khi có căn cứ ngữ nghĩa rõ. Quyết định riêng của chủ dự án được ghi `CONFIRMED_PROJECT_DECISION`, không gán cho GVHD.

## 1. Còn quy trình/hướng dẫn/biểu mẫu nội bộ nào khác?

- **Câu hỏi:** Ngoài quy định chung và file Drive, Khoa còn quy trình, hướng dẫn, biểu mẫu hoặc báo cáo nội bộ nào cần bám theo?
- **Trả lời thực tế:** Đoạn trả lời mô tả quy trình vận hành, nhắc phiếu nhận xét GVHD/GVPB, phiếu chấm, biên bản, bảng điểm và cụm “Có mẫu 3 (4 sau này)”; chưa liệt kê một bộ tài liệu nội bộ bổ sung hoàn chỉnh.
- **Kết luận chắc chắn:** Bộ Drive hiện có là nguồn làm việc; các biểu mẫu 1a–11 đã được kiểm kê. Không được khẳng định không còn tài liệu khác.
- **Requirement:** REQ-EVAL-001, REQ-MIN-001, REQ-RPT-001.
- **Business Rule:** BR-AUDIT-001.
- **Actor/quyền:** GVHD, GVPB, Thư ký, Chủ tịch; quyền theo assignment.
- **Use Case:** UC-RPT-001, UC-EVAL-001, UC-MIN-001.
- **Entity/data:** SourceRecord, ReviewForm, CouncilMinute, FinalResult.
- **Trạng thái:** `OPEN` về nguồn nội bộ có thể chưa được cung cấp; bộ nguồn Drive hiện tại đã được kiểm kê.
- **Chưa rõ:** “Mẫu 3 (4 sau này)” chỉ mẫu nào và còn báo cáo nội bộ nào chưa có trên Drive.


## 2. Phân trách nhiệm giữa cán bộ KLTN, TBM và Trưởng khoa

- **Câu hỏi:** Ai chịu trách nhiệm/chốt duyệt đề tài, GVHD, đề cương, Hội đồng và kết quả?
- **Trả lời thực tế:** “Không còn vai trò của cán bộ, chỉ người dùng”; TBM duyệt/chỉnh topic, phân công GVHD, chốt đề cương; Trưởng khoa duyệt danh sách/ký đề cương; Hội đồng cập nhật sau quyết định; Thư ký lập biên bản; Chủ tịch ký.
- **Kết luận chắc chắn:** Không tạo base role “cán bộ KLTN”. TBM chốt nghiệp vụ; Trưởng khoa ký/xác nhận văn bản, không xét nội dung thay TBM. Hội đồng đến từ quyết định.
- **Requirement:** REQ-AUTH-001..003, REQ-REG-003, REQ-PROP-002..003, REQ-COUNCIL-001, REQ-MIN-001.
- **Business Rule:** BR-AUTH-002, BR-PROP-002, BR-COUNCIL-001, BR-MIN-002.
- **Actor/quyền:** TBM duyệt/chốt; Trưởng khoa ký; Thư ký lập; Chủ tịch chủ trì/ký; Admin không duyệt.
- **Use Case:** UC-TOPIC-003, UC-ASSIGN-001, UC-PROP-004, UC-COUNCIL-001, UC-MIN-001.
- **Entity/data:** OrganizationalPosition, PositionAssignment, AdvisorAssignment, CouncilMember, CouncilMinute.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION`.
- **Ghi chú chủ dự án cần xác nhận:** Bạn hiểu cụm “TBM ký biên bản Hội đồng” là biên bản bảo vệ sau chấm điểm. QĐ2919/Mẫu 9 hiện gắn chữ ký biên bản bảo vệ với Chủ tịch; chưa đổi người ký theo ghi chú này. Xem OPEN-08.

## 3. Số đợt KLTN trong năm học

- **Câu hỏi:** Một đợt chính hay có nhiều đợt/đăng ký bổ sung?
- **Trả lời thực tế:** “Mỗi năm 1 đợt chính (có đợt bổ sung), quản lý theo năm học dành cho SV năm cuối.”
- **Kết luận chắc chắn:** Đợt chính và bổ sung cùng thuộc một năm học, dùng chung quy trình.
- **Requirement:** REQ-ROUND-001.
- **Business Rule:** BR-ROUND-001.
- **Actor/quyền:** TBM/Trưởng khoa cấu hình nghiệp vụ theo thẩm quyền; Admin chỉ hỗ trợ kỹ thuật.
- **Use Case:** UC-ROUND-001.
- **Entity/data:** AcademicYear, ThesisRound.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION`.
- **Chưa rõ:** Số đợt bổ sung tối đa và lịch cụ thể từng năm. Chủ dự án dự kiến chỉ một đợt bổ sung; cần Khoa xác nhận trước khi giới hạn cứng.

## 4. Một hay nhiều nguyện vọng đề tài

- **Câu hỏi:** SV chỉ đăng ký một đề tài, không xếp nhiều nguyện vọng?
- **Trả lời thực tế:** “Chỉ được đăng kí 1 đề tài, không được đề tài thứ 2 theo kiểu nguyện vọng.”
- **Kết luận chắc chắn:** Một đăng ký hoạt động/SV/đợt, chứa đúng một đề tài.
- **Requirement:** REQ-REG-001.
- **Business Rule:** BR-REG-001.
- **Actor/quyền:** SV tạo/hủy theo trạng thái; GVHD accept/reject; TBM finalize.
- **Use Case:** UC-REG-001.
- **Entity/data:** TopicRegistration, StudentProfile, ThesisRound.
- **Trạng thái:** `CONFIRMED`.
- **Chưa rõ:** Không.

## 5. Đăng ký nhóm và ghép thêm SV

- **Câu hỏi:** Nhóm đăng ký ngay từ đầu hay có thể ghép thêm sau?
- **Trả lời thực tế:** Một đề tài tối đa 3 SV, SV tự đăng ký, có nhóm trưởng nhưng không là chủ nhiệm; không có câu trả lời rõ về ghép thêm sau đăng ký.
- **Kết luận chắc chắn:** 1–3 SV; coordinator chỉ điều phối. Không suy diễn quyền ghép thêm.
- **Requirement:** REQ-REG-002, REQ-REG-005.
- **Business Rule:** BR-REG-002, BR-REG-005.
- **Actor/quyền:** SV lập nhóm; GVHD/TBM xem/duyệt theo workflow; không ai có lệnh ghép tự do ở safe default.
- **Use Case:** UC-REG-002.
- **Entity/data:** Thesis, ThesisMember, TopicRegistration.
- **Trạng thái:** `CONFIRMED` cho giới hạn/nhóm trưởng; `OPEN` cho ghép sau.
- **Chưa rõ:** Thời điểm khóa danh sách và điều kiện ghép thêm.

## 6. Điểm riêng hay chung cho nhóm

- **Câu hỏi:** KLTN 2–3 SV được quản lý điểm riêng hay chung?
- **Trả lời thực tế:** SV tự chia việc dưới sự đồng ý GVHD; GVHD/GVPB đánh giá; cùng khóa luận có thể khác điểm vì phân công và câu hỏi riêng.
- **Kết luận chắc chắn:** Điểm/kết quả theo từng SV; phải lưu work allocation theo thành viên.
- **Requirement:** REQ-REG-004, REQ-EVAL-002.
- **Business Rule:** BR-REG-004, BR-EVAL-001..002.
- **Actor/quyền:** GVHD duyệt phân công; thành viên HĐ tự chấm từng SV.
- **Use Case:** UC-WORK-001, UC-EVAL-002.
- **Entity/data:** MemberWorkAssignment, Evaluation, FinalResult.
- **Trạng thái:** `CONFIRMED`.
- **Chưa rõ:** Trọng số trực tiếp của work allocation trong rubric nếu có.

## 7. Ai phê duyệt phân công GVHD

- **Câu hỏi:** Cán bộ KLTN, TBM hay Trưởng khoa phê duyệt chính thức?
- **Trả lời thực tế:** “Phê duyệt và chốt đề tài, phân công GVHD là Trưởng Bộ môn.”
- **Kết luận chắc chắn:** TBM chốt/phân công; Trưởng khoa ký/xác nhận danh sách/văn bản nếu quy trình yêu cầu.
- **Requirement:** REQ-REG-003.
- **Business Rule:** BR-REG-003.
- **Actor/quyền:** TBM `A`; GVHD accept/reject trước đó; Admin không có quyền duyệt.
- **Use Case:** UC-ASSIGN-001.
- **Entity/data:** AdvisorAssignment, PositionAssignment.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION`.
- **Chưa rõ:** Có cần thêm chữ ký danh sách ở từng đợt hay không.

## 8. Nguồn và người quản lý chuyên môn giảng viên

- **Câu hỏi:** Dữ liệu chuyên môn nào đủ tin cậy, ai quản lý/cập nhật?
- **Trả lời thực tế:** “GVHD tự khai báo chuyên môn, thì” và dòng rời “Trưởng bộ môn”. Cấu trúc câu không đủ chắc để kết luận TBM là người xác nhận.
- **Kết luận chắc chắn:** Giảng viên tự khai. Xác nhận/publish chưa có căn cứ chắc; TBM là phương án thiết kế.
- **Requirement:** REQ-EXP-001.
- **Business Rule:** chưa có rule xác nhận; safe design gắn nhãn self-declared.
- **Actor/quyền:** Giảng viên C/U hồ sơ mình; TBM A ở mức `PROPOSED`.
- **Use Case:** UC-EXP-001.
- **Entity/data:** LecturerExpertise, ExpertiseEvidence, VerificationStatus.
- **Trạng thái:** `OPEN`; `PROPOSED_TBM`.
- **Chưa rõ:** Người xác nhận, nguồn minh chứng và chu kỳ review.
- **Ghi chú chủ dự án:** Cần chọn rõ người xác nhận chuyên môn (tự lưu, TBM hay Trưởng khoa). Hiện vẫn OPEN-01; không tự cấp quyền xác nhận.

## 9. Quy trình xét duyệt đề cương

- **Câu hỏi:** GVHD xác nhận trước hay TBM xét trước; ai chốt cuối?
- **Trả lời thực tế:** SV upload; GVHD sửa/nhận xét có lịch sử; GVPB/Hội đồng góp ý; SV sửa; GVHD kiểm tra/công nhận; TBM nhận xét/chốt; đề cương in ký; Trưởng khoa ký.
- **Kết luận chắc chắn:** Chuỗi đã được chủ dự án khóa đúng ý nghĩa, tách chốt nội dung của TBM và ký văn bản của Trưởng khoa.
- **Requirement:** REQ-PROP-001..003.
- **Business Rule:** BR-PROP-001..002.
- **Actor/quyền:** SV nộp/sửa; GVHD nhận xét/xác nhận; GVPB/HĐ góp ý; TBM chốt; Trưởng khoa ký.
- **Use Case:** UC-PROP-001..004.
- **Entity/data:** Proposal, ProposalVersion, ProposalReview, SignatureConfirmation.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION`.
- **Chưa rõ:** Tên chính thức và số người bắt buộc của nhóm/Hội đồng góp ý đề cương. Chủ dự án nêu cơ cấu Hội đồng bảo vệ gồm Chủ tịch, hai phản biện, một ủy viên, một thư ký; chưa áp cơ cấu bảo vệ cho bước góp ý đề cương khi nguồn chưa xác nhận.

## 10. Theo dõi tiến độ và milestone

- **Câu hỏi:** Bám kế hoạch SV/GVHD hay có mốc riêng; GVHD có xác nhận/nhận xét?
- **Trả lời thực tế:** GVHD quản lý tiến độ; lần 1 góp ý đề cương; lần 2 báo cáo nội bộ khoảng 70% giữa các GVHD. Không liệt kê toàn bộ milestone.
- **Kết luận chắc chắn:** Kế hoạch SV được GVHD duyệt là baseline; GVHD nhận xét/xác nhận; có checkpoint đề cương và khoảng 70%.
- **Requirement:** REQ-PROG-001..002.
- **Business Rule:** BR-PROG-001.
- **Actor/quyền:** SV cập nhật; GVHD nhận xét/xác nhận; GV khác chỉ góp ý khi được phân công.
- **Use Case:** UC-PROG-001, UC-PROG-002.
- **Entity/data:** ProgressMilestone, ProgressReport, ProgressReview.
- **Trạng thái:** `CONFIRMED` phần quản lý; `OPEN` milestone chi tiết.
- **Chưa rõ:** Danh sách mốc, tỷ lệ hoàn thành chính xác, hạn theo đợt.

## 11. Đổi đề tài, rút và gia hạn

- **Câu hỏi:** Số hóa toàn bộ hay chỉ ghi kết quả thủ tục ngoài?
- **Trả lời thực tế:** Đổi đề tài làm trên hệ thống; rút làm thủ tục ngoài rồi cập nhật/xóa danh sách bởi TBM; gia hạn xử lý/cập nhật bên ngoài khi báo cáo tiến độ.
- **Kết luận chắc chắn:** Ba loại có hai workflow khác nhau; không giả lập phê duyệt nội bộ cho rút/gia hạn.
- **Requirement:** REQ-CHANGE-001..003.
- **Business Rule:** BR-CHANGE-001.
- **Actor/quyền:** SV gửi đổi đề tài; GVHD xác nhận; TBM duyệt/cập nhật kết quả ngoài.
- **Use Case:** UC-CHANGE-001, UC-EXT-001.
- **Entity/data:** ChangeRequest, ExternalProcedureOutcome, EvidenceDocument.
- **Trạng thái:** `CONFIRMED`.
- **Chưa rõ:** Cơ quan ký cuối cùng và bộ metadata bắt buộc của kết quả ngoài từng loại.

## 12. Quyền xem/tải kho KLTN

- **Câu hỏi:** SV/GV được xem toàn bộ hay theo phạm vi?
- **Trả lời thực tế:** “Được xem được tải, không giới hạn phạm vi.”
- **Kết luận chắc chắn:** Nguồn hiện tại cho phép xem/tải kho; hệ thống vẫn kiểm tra đăng nhập, trạng thái công bố và visibility để không lộ bản nháp/PII.
- **Requirement:** REQ-REPO-001.
- **Business Rule:** BR-REPO-001.
- **Actor/quyền:** Người dùng đã xác thực xem/tải bản được công bố; chủ tài liệu/TBM quản lý trạng thái theo thẩm quyền.
- **Use Case:** UC-REPO-001.
- **Entity/data:** RepositoryItem, RepositoryVisibility, SearchIndexMetadata.
- **Trạng thái:** `CONFIRMED` về nghiệp vụ hiện tại; kiểm soát kỹ thuật `DERIVED`.
- **Chưa rõ:** Có cho khách chưa đăng nhập và tài liệu nào bị loại khỏi công bố. Mặc định thiết kế: chỉ tài khoản đã đăng nhập và được cấp quyền xem/tải; quyền khách công khai cần Khoa chốt danh mục tài liệu và phạm vi trước khi bật.

## 13. Một Hội đồng đánh giá bao nhiêu KLTN

- **Câu hỏi:** Một Hội đồng cho một KLTN hay nhiều KLTN/buổi/đợt?
- **Trả lời thực tế:** KLTN theo Bộ môn; một Hội đồng đánh giá nhiều SV cùng chuyên ngành, nhiều buổi; ngành/Bộ môn khác tổ chức riêng.
- **Kết luận chắc chắn:** `Council` có nhiều `DefenseSession`; mỗi session có nhiều KLTN/SV phù hợp phạm vi.
- **Requirement:** REQ-COUNCIL-002.
- **Business Rule:** BR-COUNCIL-001..002.
- **Actor/quyền:** Thành viên theo quyết định và phiên.
- **Use Case:** UC-COUNCIL-001, UC-SESSION-001.
- **Entity/data:** Council, CouncilMember, DefenseSession, SessionThesis.
- **Trạng thái:** `CONFIRMED`.
- **Chưa rõ:** Giới hạn số KLTN/phiên và lịch cụ thể. Chủ dự án mô tả một ngày có thể một hoặc hai buổi; mô hình DefenseSession cho phép cấu hình lịch, không khóa cứng số buổi.

## 14. Điều kiện riêng của Khoa để bảo vệ

- **Câu hỏi:** Ngoài điều kiện Trường, Khoa có điều kiện riêng nào?
- **Trả lời thực tế:** Không có câu trả lời trực tiếp, tách bạch. Đoạn khác nói GVHD quyết định cho bảo vệ và tương đồng cao phải sửa.
- **Kết luận chắc chắn:** Điều kiện cấp Trường lấy từ Điều 7 QĐ 2919: không bị kỷ luật ở mức cấm, hoàn thành KLTN, có GVHD đồng ý bằng văn bản. Điều kiện riêng Khoa vẫn chưa rõ.
- **Requirement:** REQ-DEF-001, REQ-SIM-003.
- **Business Rule:** BR-SIM-003.
- **Actor/quyền:** GVHD xác nhận; TBM/Khoa kiểm tra policy.
- **Use Case:** UC-DEF-001.
- **Entity/data:** DefenseEligibilityCheck, AdvisorReview, SimilarityCheck.
- **Trạng thái:** `CONFIRMED` điều kiện Trường; `OPEN` điều kiện riêng Khoa.
- **Chưa rõ:** Policy Khoa và thời điểm khóa danh sách bảo vệ. Gợi ý của chủ dự án: có cấu hình để người được Khoa giao quyền nhập điều kiện bổ sung; Admin kỹ thuật không tự tạo hay duyệt điều kiện nghiệp vụ.

## 15. Nhập/sửa điểm và khóa kết quả

- **Câu hỏi:** Thành viên tự nhập hay Thư ký nhập lại; ai sửa sau chốt?
- **Trả lời thực tế:** Thành viên mở form tự chấm/submit; hệ thống tổng hợp; Thư ký ghi/xuất biên bản. Nhập sai thì chính tác giả sửa trước khi Thư ký in; Thư ký void/thay biên bản sai; bản có chữ ký Chủ tịch.
- **Kết luận chắc chắn:** Không cho Thư ký sửa điểm thay người chấm. Khóa tại in/ký; sau đó chưa có thủ tục.
- **Requirement:** REQ-EVAL-002, REQ-MIN-001..002.
- **Business Rule:** BR-EVAL-001..002, BR-MIN-001..002.
- **Actor/quyền:** Thành viên sửa điểm mình trước khóa; Thư ký quản lý minute; Chủ tịch ký.
- **Use Case:** UC-EVAL-002, UC-EVAL-003, UC-MIN-001, UC-MIN-002.
- **Entity/data:** Evaluation, EvaluationItem, CouncilMinute, MinuteVersion, AuditEvent.
- **Trạng thái:** `CONFIRMED` trước in; `OPEN` sau in/ký.
- **Chưa rõ:** Thủ tục hậu ký, người phê duyệt và chứng từ điều chỉnh. Chủ dự án gợi ý Chủ tịch tham gia phê duyệt; chưa có nguồn quy định thủ tục nên OPEN-07 vẫn giữ khóa sửa sau ký.

## 16. Phiếu/rubric đang dùng

- **Câu hỏi:** Khoa có mẫu cụ thể cho tiêu chí/trọng số không?
- **Trả lời thực tế:** Đoạn trả lời xác nhận có form chấm; Mẫu 6 Khoa có nhóm Hình thức 2,0 (1.1–1.3), Nội dung 4,0 (2.1–2.6), Demo/trả lời 4,0 (3.1–3.3), điểm thưởng tối đa 1,0 và tổng phiếu tối đa 10. QĐ 2919 Điều 10 khoản 4 lại nêu cơ cấu 1–6–1–2; xem CONFLICT-011.
- **Kết luận chắc chắn:** RubricTemplate/RubricCriterion phải lưu đủ nhóm, tiêu chí con, thứ tự, max point và source/version Mẫu 6; nhóm không được cộng lặp với tiêu chí con. Điểm thưởng nằm trong tổng phiếu, tối đa 1; tổng tối đa 10; điểm cuối từng SV là trung bình phiếu hợp lệ, làm tròn một chữ số, không cộng thưởng lần hai.
- **Requirement:** REQ-EVAL-003.
- **Business Rule:** BR-EVAL-003.
- **Actor/quyền:** Thành viên HĐ chấm; TBM/Khoa quản lý rubric version theo thẩm quyền.
- **Use Case:** UC-RUBRIC-001, UC-EVAL-002.
- **Entity/data:** RubricTemplate, RubricCriterion, EvaluationItem, BonusEvidence.
- **Trạng thái:** `CONFIRMED` baseline thiết kế Mẫu 6; `OPEN` xung đột cơ cấu với QĐ 2919 trước khi vận hành chấm thật.
- **Chưa rõ:** Khoa xác nhận hiệu lực Mẫu 6 so với QĐ 2919 và version áp dụng cho từng đợt.
- **Quyết định phạm vi thiết kế:** Dùng đầy đủ Mẫu 6 của Khoa làm baseline mô hình; vẫn giữ OPEN-12 về hiệu lực so với QĐ2919 trước khi chấm thật.

## 17. Phạm vi kho và AI được khai thác

- **Câu hỏi:** AI/đối tượng khác dùng metadata hay toàn văn; file được xem/tải thế nào?
- **Trả lời thực tế:** Tên, tóm tắt, từ khóa và toàn văn được xem; chatbot tra cứu và trả kết quả/link; người dùng mở web để xem/tải, chatbot chỉ cấp đường dẫn.
- **Kết luận chắc chắn:** Repository có full text cho item được công bố; chatbot không bypass download authorization.
- **Requirement:** REQ-REPO-001, REQ-AI-001.
- **Business Rule:** BR-REPO-001, BR-AI-002.
- **Actor/quyền:** Người dùng tra cứu theo quyền; chatbot là dịch vụ read-only.
- **Use Case:** UC-REPO-001, UC-AI-001.
- **Entity/data:** RepositoryItem, DocumentVersion, SearchIndexMetadata, ChatCitation.
- **Trạng thái:** `CONFIRMED`.
- **Chưa rõ:** Tài liệu nào không được công bố vì bản quyền/PII và quyền khách ngoài Khoa. Mặc định an toàn: khách chưa đăng nhập không xem/tải nội dung; chính sách công bố/tải cho khách cần quyết định riêng, không suy ra từ khả năng xem.

## 18. Có được gửi retrieved chunks sang Gemini?

- **Câu hỏi:** Có được gửi nội dung/đoạn truy xuất sang Gemini hay chỉ metadata/ẩn danh?
- **Trả lời thực tế:** File GVHD không có câu trả lời riêng, rõ và đủ căn cứ cho việc truyền dữ liệu sang Gemini. Các câu sau chỉ nói chatbot tra cứu/link và phạm vi full text.
- **Kết luận chắc chắn:** Không giả đây là quy định Trường. Chủ dự án đã cho phép ở cấp thiết kế: authorization trước retrieval, chỉ gửi chunks cần thiết, giảm PII, key backend-only, log an toàn.
- **Requirement:** REQ-AI-002.
- **Business Rule:** BR-AI-001.
- **Actor/quyền:** Backend RAG; người dùng chỉ nhận nội dung được phép; Admin quản trị key kỹ thuật.
- **Use Case:** UC-AI-001.
- **Entity/data:** RetrievalRequest, RetrievedChunk, AiInvocationAudit, SearchIndexMetadata.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION`; chính sách Trường `OPEN` nhưng không cản thiết kế.
- **Chưa rõ:** Văn bản tổ chức về nhà cung cấp/retention và danh mục tài liệu cấm gửi nếu có.
- **Ghi chú thiết kế:** Chỉ gửi đoạn tài liệu đã được kiểm quyền và giảm PII, giữ citation/source/version và nhật ký truy xuất; cần Khoa xác nhận chính sách nhà cung cấp/retention trước khi gửi dữ liệu thuộc diện hạn chế.
