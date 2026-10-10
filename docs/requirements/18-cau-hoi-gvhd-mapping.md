# Vấn đề đối chiếu

Nguồn trả lời: `SRC-GVHD-NV4-001`, bản Drive mới nhất. Phần trả lời là một đoạn liên tục, không đánh số theo câu hỏi

## 1. Còn quy trình/hướng dẫn/biểu mẫu nội bộ nào khác?

- **Câu hỏi:** Ngoài quy định chung và file Drive, Khoa còn quy trình, hướng dẫn, biểu mẫu hoặc báo cáo nội bộ nào cần bám theo?
- **Trả lời thực tế:** Đoạn trả lời mô tả quy trình vận hành, nhắc phiếu nhận xét GVHD/GVPB, phiếu chấm, biên bản, bảng điểm 
- **Kết luận chắc chắn:** Bộ Drive hiện tại https://drive.google.com/drive/folders/1cqHQJiAM8gZyMwssqx3ur5fAR1upEiVX?usp=sharing hiện có là nguồn làm việc; các biểu mẫu 1a–11 
- **Requirement:** REQ-EVAL-001, REQ-MIN-001, REQ-RPT-001.
- **Business Rule:** BR-AUDIT-001.
- **Actor/quyền:** GVHD, GVPB, Thư ký, Chủ tịch; quyền theo assignment.
- **Use Case:** UC-RPT-001, UC-EVAL-001, UC-MIN-001.
- **Entity/data:** SourceRecord, ReviewForm, CouncilMinute, FinalResult.
- **Trạng thái:** Đã kiểm kê bộ nguồn Drive hiện có; nếu Khoa cung cấp thêm biểu mẫu thì đối chiếu và phiên bản hóa.


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
** Mẫu 9 là “Biên bản họp Hội đồng chấm khóa luận tốt nghiệp/đồ án tốt nghiệp”, tức biên bản bảo vệ sau chấm điểm. Chủ tịch và Thư ký ký theo đúng biểu mẫu; không gán TBM. Với phạm vi Mẫu 9, quyết định về người ký đã chốt; văn bản khác nếu phát sinh sẽ phân tích riêng.

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
- **Cần làm rõ sau hoặc tự thiết kế* Số đợt bổ sung tối đa và lịch cụ thể từng năm. Kế hoạch hiện dự kiến chỉ một đợt bổ sung; cần xác nhận trước khi giới hạn cứng.

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

## 5. Đăng ký nhóm và ghép thêm SV

- **Câu hỏi:** Nhóm đăng ký ngay từ đầu hay có thể ghép thêm sau?
- **Trả lời thực tế:** Một đề tài tối đa 3 SV, SV tự đăng ký, có nhóm trưởng nhưng không là chủ nhiệm; Không ghép thêm SV sau khi đăng ký; SV tự ghép nhóm trước khi gửi và giảng viên không tự thêm người.( Mô hình/endpoint không cho sửa membership hậu SUBMITTED.)
- **Requirement:** REQ-REG-002, REQ-REG-005.
- **Business Rule:** BR-REG-002, BR-REG-005.
- **Actor/quyền:** SV lập nhóm; GVHD/TBM xem/duyệt theo workflow; không ai có lệnh ghép tự do ở safe default.
- **Use Case:** UC-REG-002.
- **Entity/data:** Thesis, ThesisMember, TopicRegistration.
- **Trạng thái:** `CONFIRMED` cho giới hạn/nhóm trưởng; `CONFIRMED_PROJECT_DECISION` cho khóa thành viên từ khi gửi.
- **Làm rõ thêm:** Mỗi thành viên phải tự xác nhận bằng tài khoản của mình trước khi gửi. Nếu nhóm do SV đề xuất đề tài, nhóm đăng ký trước; TBM xét nội dung đề tài sau.
- **Trạng thái triển khai:** Migration 0007 lưu phản hồi và người/thời điểm xác nhận; prototype API/UI chưa buộc từng SV xác nhận và chưa hỗ trợ nhánh đề tài SV đề xuất. (Đây là phần code còn thiếu, không phải quyết định nghiệp vụ còn mở.)

## 6. Điểm riêng hay chung cho nhóm

- **Câu hỏi:** KLTN 2–3 SV được quản lý điểm riêng hay chung?
- **Trả lời thực tế:** SV tự chia việc dưới sự đồng ý GVHD; GVHD/GVPB đánh giá; cùng khóa luận có thể khác điểm vì phân công GVPB và câu hỏi riêng.
- **Kết luận chắc chắn:** Điểm/kết quả theo từng SV; phải lưu work allocation theo thành viên.
- **Requirement:** REQ-REG-004, REQ-EVAL-002.
- **Business Rule:** BR-REG-004, BR-EVAL-001..002.
- **Actor/quyền:** GVHD duyệt phân công; thành viên HĐ tự chấm từng SV.
- **Use Case:** UC-WORK-001, UC-EVAL-002.
- **Entity/data:** MemberWorkAssignment, Evaluation, FinalResult.
- **Trạng thái:** `CONFIRMED`.
- **Đã chốt baseline thiết kế:** Mẫu 6 Khoa theo nhóm tiêu chí 2/4/4; điểm thưởng tối đa 1,0 và tổng không quá 10. Đây là baseline của dự án, không hỏi lại như vấn đề còn mở.

## 7. Ai phê duyệt phân công GVHD

- **Câu hỏi:** Cán bộ KLTN, TBM hay Trưởng khoa phê duyệt chính thức?
- **Trả lời thực tế:** “Phê duyệt và chốt đề tài, phân công GVHD là Trưởng Bộ môn.”(cần thêm chữ ký danh sách ở từng đợt)
- **Kết luận chắc chắn:** TBM chốt/phân công; Trưởng khoa ký/xác nhận danh sách/văn bản nếu quy trình yêu cầu.
- **Requirement:** REQ-REG-003.
- **Business Rule:** BR-REG-003.
- **Actor/quyền:** TBM `A`; GVHD accept/reject trước đó; Admin không có quyền duyệt.
- **Use Case:** UC-ASSIGN-001.
- **Entity/data:** AdvisorAssignment, PositionAssignment.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION`.

## 8. Nguồn và người quản lý chuyên môn giảng viên

- **Câu hỏi:** GVHD tự khai báo chuyên môn trên hồ sơ; ai xác nhận?
- **Trả lời thực tế:** “GVHD tự khai báo chuyên môn, TBM là người xác nhận.”
- **Kết luận chắc chắn:** GVHD tự khai; TBM đúng Bộ môn xác nhận sau khi kiểm chứng bằng minh chứng. Nếu người tự khai là TBM, Trưởng khoa/người được giao kiểm để tránh tự xác nhận. Đã có trả lời và quyết định thiết kế; không cần hỏi lại câu này.
- **Requirement:** REQ-EXP-001.
- **Business Rule:** tự khai có nhãn SELF_DECLARED; VERIFIED cần minh chứng, actor/time, đúng scope và không tự xác nhận.
- **Actor/quyền:** Giảng viên C/U hồ sơ mình; TBM đúng Bộ môn kiểm, Trưởng khoa/người được giao xử lý hồ sơ của TBM.
- **Use Case:** UC-EXP-001.
- **Entity/data:** LecturerExpertise, ExpertiseEvidence, VerificationStatus.
- **Trạng thái:** `CONFIRMED_PROJECT_DESIGN`.
- **Ghi chú thiết kế:** Đã chọn TBM đúng Bộ môn, chống tự kiểm bằng Trưởng khoa/người được giao; đây là quyết định phần mềm

## 9. Quy trình xét duyệt đề cương

- **Câu hỏi:** GVHD xác nhận trước hay TBM xét trước; ai chốt cuối?
- **Trả lời thực tế:** SV upload; GVHD sửa/nhận xét có lịch sử; GVPB/Hội đồng góp ý; SV sửa; GVHD kiểm tra/công nhận; TBM nhận xét/chốt; đề cương in ký; Trưởng khoa ký.
- **Kết luận chắc chắn:** Chuỗi đã được làm rõ đúng ý nghĩa, tách chốt nội dung của TBM và ký văn bản của Trưởng khoa.
- **Requirement:** REQ-PROP-001..003.
- **Business Rule:** BR-PROP-001..002.
- **Actor/quyền:** SV nộp/sửa; GVHD nhận xét/xác nhận; GVPB/HĐ góp ý; TBM chốt; Trưởng khoa ký.
- **Use Case:** UC-PROP-001..004.
- **Entity/data:** Proposal, ProposalVersion, ProposalReview, SignatureConfirmation.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION`.
- **Đã biết:** Nhóm đăng ký có 1–3 sinh viên (REQ-REG-002); Hội đồng bảo vệ có 5 người theo cơ cấu đã ghi ở BR-COUNCIL-002. Không áp số người Hội đồng bảo vệ cho buổi góp ý đề cương vì đây là hai hoạt động khác nhau.
- **Còn cần hỏi:** Buổi góp ý đề cương có phải Hội đồng chính thức không? Nếu có thì cần tối thiểu bao nhiêu người, gồm vai trò nào? Nếu là buổi góp ý theo phân công, ai phân công và tổng hợp ý kiến?

## 10. Theo dõi tiến độ và milestone

- **Câu hỏi:** Bám kế hoạch SV/GVHD hay có mốc riêng; GVHD có xác nhận/nhận xét?
- **Trả lời thực tế:** GVHD quản lý tiến độ; lần 1 góp ý đề cương; lần 2 báo cáo nội bộ khoảng 70% giữa các GVHD. Không liệt kê toàn bộ milestone.
- **Kết luận chắc chắn:** Kế hoạch SV được GVHD duyệt là baseline; GVHD nhận xét/xác nhận; có checkpoint đề cương và khoảng 70%.
- **Requirement:** REQ-PROG-001..002.
- **Business Rule:** BR-PROG-001.
- **Actor/quyền:** SV cập nhật; GVHD nhận xét/xác nhận; GV khác chỉ góp ý khi được phân công.
- **Use Case:** UC-PROG-001, UC-PROG-002.
- **Entity/data:** ProgressMilestone, ProgressReport, ProgressReview.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION` cho hai checkpoint; lịch cụ thể là dữ liệu cấu hình của từng đợt.
- **Làm rõ trong thiết kế ngày 25/09:** GVHD quản lý tiến độ thường kỳ. Lần 1 là góp ý đề cương; lần 2 là báo cáo tiến độ nội bộ dự kiến tháng 12 khi dự án đạt khoảng 70%, giữa các GVHD để góp ý chéo. Đây không phải Hội đồng bảo vệ theo quyết định.
- **Còn cần hỏi:** Buổi nội bộ khoảng 70% có lập Hội đồng riêng không, hay GVHD khác được phân công góp ý `COMMENT_ONLY`? Nếu có Hội đồng thì số người/vai trò nào và ai tổng hợp kết luận? Ngày giờ, người cụ thể lấy từ kế hoạch/phân công theo từng đợt.

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
 Mặc định thiết kế: chỉ tài khoản đã đăng nhập và được cấp quyền xem/tải; quyền khách công khai cần Khoa chốt danh mục tài liệu và phạm vi trước khi bật.

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
- **Chưa rõ:** Giới hạn số KLTN/phiên và lịch cụ thể. Phương án hiện tại cho phép một ngày có thể một hoặc hai buổi; mô hình DefenseSession cho phép cấu hình lịch, không khóa cứng số buổi.

## 14. Điều kiện riêng của Khoa để bảo vệ

- **Câu hỏi:** Ngoài điều kiện Trường, Khoa có điều kiện riêng nào?
- **Trả lời thực tế:**. Đoạn khác nói GVHD quyết định cho bảo vệ và tương đồng cao phải sửa.
- **Kết luận chắc chắn:** Điều kiện cấp Trường lấy từ Điều 7 QĐ 2919: không bị kỷ luật ở mức cấm, hoàn thành KLTN, có GVHD đồng ý bằng văn bản. Điều kiện riêng Khoa vẫn chưa rõ.
- **Requirement:** REQ-DEF-001, REQ-SIM-003.
- **Business Rule:** BR-SIM-003.
- **Actor/quyền:** GVHD xác nhận; TBM/Khoa kiểm tra policy.
- **Use Case:** UC-DEF-001.
- **Entity/data:** DefenseEligibilityCheck, AdvisorReview, SimilarityCheck.
- **Trạng thái:** `CONFIRMED` điều kiện Trường; `CONFIRMED_PROJECT_DECISION` rằng hiện chưa thêm tiêu chí Khoa.
- **Làm rõ trong thiết kế ngày 25/09:** Trước mắt chỉ dùng điều kiện trong QĐ2919 Điều 7. QĐ5964 cho phép Khoa bổ sung sau này, nhưng chưa có tiêu chí mới được cung cấp.
- **Chưa rõ:** Thời điểm khóa danh sách bảo vệ do kế hoạch từng đợt quy định; Admin kỹ thuật không tự ban hành tiêu chí.

## 15. Nhập/sửa điểm và khóa kết quả

- **Câu hỏi:** Thành viên tự nhập hay Thư ký nhập lại; ai sửa sau chốt?
- **Trả lời thực tế:** Thành viên mở form tự chấm/submit; hệ thống tổng hợp; Thư ký ghi/xuất biên bản. Nhập sai thì chính tác giả sửa trước khi Thư ký in; Thư ký void/thay biên bản sai; bản có chữ ký Chủ tịch.
- **Kết luận chắc chắn:** Không cho Thư ký sửa điểm thay người chấm. Theo quyết định mới, in chưa khóa: Thư ký đối chiếu bản giấy, nếu sai và chưa ai ký thì evaluator tự sửa; từ chữ ký đầu khóa điểm/nội dung.
- **Requirement:** REQ-EVAL-002, REQ-MIN-001..002.
- **Business Rule:** BR-EVAL-001..002, BR-MIN-001..002.
- **Actor/quyền:** Thành viên sửa điểm mình trước khóa; Thư ký quản lý và ký minute Mẫu 9; Chủ tịch cùng ký.
- **Use Case:** UC-EVAL-002, UC-EVAL-003, UC-MIN-001, UC-MIN-002.
- **Entity/data:** Evaluation, EvaluationItem, CouncilMinute, MinuteVersion, AuditEvent.
- **Trạng thái:** `CONFIRMED_PROJECT_DECISION`: sửa sau in trước chữ ký đầu; từ chữ ký đầu khóa.
- **Quyết định thiết kế ngày 25/09:** Nếu phát hiện sai sau in nhưng trước chữ ký đầu, Thư ký xác nhận giấy chưa ký, VOID bản cũ, evaluator tự sửa phiếu, hệ thống tính lại và in MinuteVersion mới có mã/giờ, liên kết bản cũ và audit. Sau chữ ký đầu chỉ cấp bản sao đúng bản đã ký.
- **Theo mẫu 9:** 

## 16. Phiếu/rubric đang dùng

- **Câu hỏi:** Khoa có mẫu cụ thể cho tiêu chí/trọng số không?
- **Trả lời thực tế:** Đoạn trả lời xác nhận có form chấm; Mẫu 6 Khoa có nhóm Hình thức 2,0 (1.1–1.3), Nội dung 4,0 (2.1–2.6), Demo/trả lời 4,0 (3.1–3.3), điểm thưởng tối đa 1,0 và tổng phiếu tối đa 10. QĐ 2919 Điều 10 khoản 4 lại nêu cơ cấu 1–6–1–2; xem CONFLICT-011.
- **Kết luận chắc chắn:** RubricTemplate/RubricCriterion phải lưu đủ nhóm, tiêu chí con, thứ tự, max point và source/version Mẫu 6; nhóm không được cộng lặp với tiêu chí con. Điểm thưởng nằm trong tổng phiếu, tối đa 1; tổng tối đa 10; điểm cuối từng SV là trung bình phiếu hợp lệ, làm tròn một chữ số, không cộng thưởng lần hai.
- **Requirement:** REQ-EVAL-003.
- **Business Rule:** BR-EVAL-003.
- **Actor/quyền:** Thành viên HĐ chấm; TBM/Khoa quản lý rubric version theo thẩm quyền.
- **Use Case:** UC-RUBRIC-001, UC-EVAL-002.
- **Entity/data:** RubricTemplate, RubricCriterion, EvaluationItem, BonusEvidence.
- **Trạng thái:** `CONFIRMED` — Mẫu 6 Khoa 2/4/4, đủ 12 tiêu chí con, thưởng tối đa 1 và tổng phiếu không quá 10 là baseline của dự án. Không còn quyết định thiết kế mở ở mục này.
- **Tình trạng triển khai:** Rubric trong CSDL ở `DRAFT` vì chưa có runtime chấm điểm và chưa gán version cho đợt chấm thật; đây là trạng thái chức năng, không phải chờ chọn lại cơ cấu.
- **Truy vết nguồn:** QĐ2919 có mô tả cơ cấu khác; giữ khác biệt trong `CONFLICT-011` để không làm mất căn cứ nguồn.
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

- **Câu hỏi:** Chính sách Trường/Khoa cho phép gửi loại dữ liệu nào tới Gemini?
- **Trả lời thực tế:**chatbot tra cứu/link và phạm vi full text.
- **Kết luận chắc chắn:** Không giả đây là quy định Trường. Thiết kế đã chọn ở cấp thiết kế: authorization trước retrieval, chỉ gửi chunks cần thiết, giảm PII, key backend-only, log an toàn.
- **Requirement:** REQ-AI-002.
- **Business Rule:** BR-AI-001.
- **Actor/quyền:** Backend RAG; người dùng chỉ nhận nội dung được phép; Admin quản trị key kỹ thuật.
- **Use Case:** UC-AI-001.
- **Entity/data:** RetrievalRequest, RetrievedChunk, AiInvocationAudit, SearchIndexMetadata.
- **Trạng thái:** Baseline dự án đã chọn backend kiểm quyền trước retrieval và chỉ gửi đoạn cần thiết đã giảm PII; đây chưa phải chấp thuận của Trường cho dữ liệu thật.
- **Còn cần hỏi:** Văn bản của Trường/Khoa về nhà cung cấp, nơi xử lý/lưu dữ liệu, thời gian lưu và danh mục tài liệu không được gửi; trước khi được duyệt chỉ dùng dữ liệu tổng hợp/giả lập.
- **Giải nghĩa “đoạn truy xuất”:** vài câu/đoạn liên quan được backend tìm thấy trong đề cương, báo cáo hoặc tài liệu hướng dẫn để Gemini trả lời có trích dẫn. Ví dụ, hỏi “đề cương thiếu mục nào?” có thể gửi các đoạn liên quan của đề cương. Metadata chỉ là thông tin mô tả như mã tài liệu, loại, phiên bản, ngày; nó không chứa phần văn bản để AI đọc. Ẩn danh tên/mã SV vẫn không chắc làm đoạn nội dung hết nhận diện được.
- **Ghi chú thiết kế:** Chỉ gửi đoạn tài liệu người dùng được phép xem, đã giảm PII; giữ citation/source/version và không log nguyên văn mặc định. Phải có chính sách Trường/Khoa trước khi gửi dữ liệu thật thuộc diện hạn chế.

## Làm rõ từ các quyết định thiết kế cập nhật đến ngày 28/09/2026

Đây là các lựa chọn thiết kế đã được phản ánh trong yêu cầu, CSDL và API hiện hành.

| Liên quan câu | Quyết định thiết kế đã chốt | Trạng thái triển khai hoặc điều kiện còn lại |
| --- | --- | --- |
| 2, 5 | SV tự lập nhóm 1–3; mỗi thành viên tự xác nhận bằng tài khoản riêng trước khi gửi; không ghép/thêm người sau khi gửi. Với đề tài SV đề xuất, nhóm đăng ký trước rồi TBM xét đề tài sau. Với đề tài GV đã duyệt, GV đề xuất nhận/từ chối trước khi TBM chốt. | Luồng API/UI tự xác nhận đã có cho đề tài GV đã duyệt; nhánh SV đề xuất vẫn chưa có runtime và luồng mới cần kiểm browser trực tiếp. |
| 2, 7, 8 | Khoa giao người `ELIGIBILITY_VERIFIER` theo đợt để đối chiếu nguồn Phòng Đào tạo rồi xác nhận snapshot; TBM đúng Bộ môn kiểm chứng chuyên môn GV bằng minh chứng, còn hồ sơ tự khai của TBM do Trưởng khoa/người được giao kiểm. Điều phối viên KLTN khác Thư ký Hội đồng. TBM đúng Bộ môn chốt phân công GVHD. | Người thật, lịch và scope phân quyền phải được Khoa phân công. API xác nhận snapshot, kiểm chứng chuyên môn và quản lý assignment đầy đủ chưa chạy. |
| 10 | GVHD quản lý tiến độ; lần 1 góp ý đề cương, lần 2 dự kiến tháng 12 khoảng 70% để GVHD khác góp ý chéo `COMMENT_ONLY`. | Luồng báo cáo/duyệt tiến độ chưa chạy. Ngày/giờ và người tham gia mỗi đợt lấy từ kế hoạch/phân công được duyệt. |
| 11, 14 | Thay đổi đề tài đi theo workflow; rút/gia hạn ghi kết quả thủ tục ngoài. Đợt hiện tại chỉ dùng Điều 7 QĐ2919 để xét bảo vệ, không thêm điều kiện riêng của Khoa. | Runtime thay đổi đề tài, snapshot điều kiện và người xác nhận thật chưa đầy đủ. Danh sách, thời điểm khóa và kết quả thủ tục ngoài lấy theo nguồn được duyệt. |
| Quyết định similarity | Kiểm tra tương đồng chỉ là thông tin tham khảo; không tự chặn nộp/bảo vệ và không gọi cosine 0,9 là 90% giống. | Chưa đánh giá trên tập văn bản được phép, chưa có metric/ngưỡng được duyệt và chưa có kiểm tra toàn văn đủ chuẩn. |
| 12, 17, 18 | Người dùng được truy xuất nội dung đã công bố theo quyền; chatbot trả nguồn/link. Thiết kế APA theo QĐ885 là baseline; lần thử hiện dùng retrieval-only, chưa cần Gemini. | Cần xác định quyền công bố/tải và chính sách gửi dữ liệu/retention. Khoa xác nhận APA có áp dụng cho KLTN đại học trước khi bật auto-reject; chưa đánh giá chất lượng AI trên khoảng 7 KLTN thật. |
| 15 | Được sửa sau khi in nếu chưa có chữ ký; Thư ký đối chiếu giấy, bản cũ được đánh dấu hết hiệu lực và phát hành phiên bản mới có dấu vết. Từ chữ ký đầu tiên khóa điểm/nội dung. | Quy tắc đã chốt nhưng service/versioning và kiểm thử runtime chưa có. |
| 15, Mẫu 9 | Biên bản họp Hội đồng chấm KLTN/ĐATN có Chủ tịch và Thư ký ký; không gán TBM thay vai trò này. | Chưa có mẫu trắng chính thức để kiểm xuất. Không dùng bản đã điền thông tin thật làm template hoặc đưa lên Git. |
| 16 | Baseline Mẫu 6 của Khoa đã chốt: 2/4/4, 12 tiêu chí con, thưởng tối đa 1, tổng phiếu không quá 10. | `DRAFT` chỉ vì runtime chấm điểm/gán version cho đợt thật chưa được triển khai; không còn câu hỏi thiết kế chờ trả lời. |
| 1, 17, 18 | APA theo QĐ885 là baseline thiết kế. Kho phân loại nguồn và chatbot chỉ truy xuất tài liệu được quyền xem, có nguồn trích dẫn; bản thử nghiệm chưa cần Gemini. | Cần xác nhận phạm vi áp dụng APA cho KLTN đại học, chính sách quyền công bố/PII và việc gửi nội dung tới nhà cung cấp AI. Chất lượng chưa được đánh giá trên khoảng 7 KLTN thật. |
