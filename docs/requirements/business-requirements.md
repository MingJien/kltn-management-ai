# Yêu cầu nghiệp vụ — NV4 Tuần 1

## Trạng thái

- `CONFIRMED`: được nguồn chính thức hoặc quyết định chủ dự án xác nhận.
- `DERIVED`: suy ra trực tiếp từ nhiều nguồn đã đọc, không mở rộng thẩm quyền.
- `PROPOSED`: phương án thiết kế có thể đổi khi Khoa chốt chính sách.
- `OPEN`: chưa đủ căn cứ để chốt.

## Tài khoản và thẩm quyền

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-AUTH-001 | Mỗi người dùng dùng một tài khoản; base role chỉ gồm `ADMIN`, `LECTURER`, `STUDENT`. | CONFIRMED | SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 |
| REQ-AUTH-002 | GVHD, GVPB, TBM, Trưởng khoa, Chủ tịch, Thư ký và thành viên Hội đồng là position/assignment/resource role theo phạm vi, không có tài khoản/mật khẩu riêng. | CONFIRMED | SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 |
| REQ-AUTH-003 | `ADMIN` là vai trò kỹ thuật nền tảng, không mặc nhiên được duyệt/chốt nghiệp vụ. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-MASTER-001 |

## Năm học, đợt và điều kiện

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-ROUND-001 | Một `AcademicYear` có nhiều `ThesisRound`; đợt chính và bổ sung dùng chung mô hình, khác mã/type/thời gian/trạng thái. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-QD-2919, SRC-PROJECT-MASTER-001 |
| REQ-ELIG-001 | Lập danh sách/khảo sát SV đủ điều kiện theo đợt. Điều kiện chung hiện hành: không bị xử lý theo Điều 2, có ít nhất 70% tín chỉ đạt và GPA từ 2,50/4; Khoa có thể bổ sung tiêu chí. | CONFIRMED | SRC-QD-5964, SRC-GVHD-NV4-001 |
| REQ-ELIG-002 | Dữ liệu tự khai của SV phải được lưu cùng nguồn/thời điểm và qua bước xác nhận trước khi dùng chốt danh sách. Nguồn chỉ giao trách nhiệm phối hợp cho Khoa/Phòng Đào tạo, chưa chỉ rõ cá nhân/chức vụ thao tác; quyền xác nhận là assignment cấu hình và còn `OPEN-11`. | DERIVED / OPEN_ACTOR | SRC-GVHD-NV4-001, SRC-QD-2919, SRC-QD-5964 |

## Đề tài, chuyên môn và đăng ký

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-TOPIC-001 | Giảng viên đề xuất đề tài theo chuyên môn; TBM duyệt và có thể chỉnh tên cho chính xác. | CONFIRMED | SRC-GVHD-NV4-001, SRC-QD-2919 |
| REQ-TOPIC-002 | SV có thể đề xuất đề tài; đề tài chỉ dùng sau khi GVHD đồng ý và TBM chấp nhận/chốt. | CONFIRMED | SRC-GVHD-NV4-001, SRC-QD-2919 |
| REQ-TOPIC-003 | Đề tài có thể lưu GPA mong muốn, kỹ năng, công nghệ, kiến thức và yêu cầu khác của GVHD. GPA cao hơn 2,50 là tiêu chí mong muốn, không tự biến thành điều kiện chung của Khoa. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-MASTER-001 |
| REQ-EXP-001 | Giảng viên tự khai chuyên môn/lĩnh vực/từ khóa. Người xác nhận hồ sơ chuyên môn chưa được nguồn chốt; phương án là TBM. | OPEN / PROPOSED | SRC-GVHD-NV4-001 |
| REQ-REG-001 | SV đủ điều kiện chọn đúng một đề tài và có tối đa một đăng ký còn hiệu lực trong một đợt; không có nguyện vọng xếp hạng thứ hai. | CONFIRMED | SRC-GVHD-NV4-001 |
| REQ-REG-002 | Một đề tài có 1–3 SV. Nhóm trưởng chỉ điều phối, không phải chủ nhiệm đề tài. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001 |
| REQ-REG-003 | GVHD đồng ý/từ chối đăng ký; TBM chốt đề tài và phân công GVHD. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 |
| REQ-REG-004 | Nhóm khai phân công công việc theo từng SV; GVHD duyệt. Phân công là căn cứ đánh giá cá nhân. | CONFIRMED | SRC-GVHD-NV4-001, SRC-MAU-02 |
| REQ-REG-005 | Có cho ghép thêm SV sau khi đăng ký hay không chưa rõ; hệ thống không cung cấp lệnh ghép tự do cho đến khi có chính sách. | OPEN | SRC-GVHD-NV4-001 |

## Đề cương, tiến độ và thay đổi

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-PROP-001 | SV upload đề cương gắn mã/tên đề tài; mỗi lần nộp/sửa tạo version và history bất biến. | CONFIRMED | SRC-GVHD-NV4-001, SRC-MAU-03 |
| REQ-PROP-002 | Workflow: SV nộp → GVHD nhận xét → GVPB/Hội đồng góp ý → SV sửa → GVHD xác nhận → TBM chốt nghiệp vụ → Trưởng khoa ký/xác nhận văn bản. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 |
| REQ-PROP-003 | Hệ thống lưu nhận xét/biểu mẫu góp ý và cho in đề cương để ký trực tiếp. Trưởng khoa ký không đồng nghĩa xét nội dung thay TBM. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-QD-2919 |
| REQ-PROG-001 | GVHD quản lý tiến độ, nhận xét/xác nhận báo cáo; có lần góp ý đề cương và báo cáo nội bộ khoảng 70%. | CONFIRMED | SRC-GVHD-NV4-001, SRC-MAU-02, SRC-HP-IN4299N |
| REQ-PROG-002 | Milestone chi tiết ngoài kế hoạch SV/GVHD chưa được chốt; cấu hình theo đợt, không hard-code lịch mẫu. | OPEN | SRC-GVHD-NV4-001, CONFLICT-002, CONFLICT-004 |
| REQ-CHANGE-001 | Đổi đề tài thực hiện trên hệ thống, phải theo thời hạn/đồng ý quy định. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001 |
| REQ-CHANGE-002 | Rút KLTN xử lý thủ tục bên ngoài; hệ thống ghi kết quả và TBM cập nhật danh sách. | CONFIRMED | SRC-GVHD-NV4-001 |
| REQ-CHANGE-003 | Gia hạn xử lý bên ngoài; hệ thống ghi kết quả, đợt, thời gian và tài liệu minh chứng nếu có. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001 |

## Tài liệu, tương đồng, kho và AI

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-DOC-001 | Tệp đề cương/báo cáo lưu theo document + version; bản đã nộp không bị ghi đè. | DERIVED | SRC-GVHD-NV4-001, SRC-MAU-03, SRC-QD-2919 |
| REQ-SIM-001 | Khi SV nộp báo cáo, hệ thống chạy kiểm tra tương đồng, trả bằng chứng/mức “tương đồng cao”, cho GVHD xem và cho SV nộp lại. | CONFIRMED | SRC-GVHD-NV4-001 |
| REQ-SIM-002 | Tách ngưỡng nghiệp vụ “90%” khỏi metric kỹ thuật. Không map `cosine = 0.9` thành 90%; lexical + semantic, semantic chỉ tìm candidate, tỷ lệ tài liệu phải là coverage metric được đánh giá thực nghiệm. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-MASTER-001 |
| REQ-SIM-003 | Khi Khoa chốt metric/policy, hệ thống có thể chặn chốt/nộp bản cuối nếu vượt ngưỡng; không kết luận “đạo văn”. Exact metric hiện `OPEN`. | CONFIRMED_PROJECT_DECISION / OPEN_METRIC | SRC-PROJECT-MASTER-001 |
| REQ-REPO-001 | Theo nguồn hiện tại, kho cho xem và tải; quyền vẫn phải qua authorization và visibility của tài liệu. KLTN được quản lý theo Bộ môn/chuyên ngành. | CONFIRMED / DERIVED | SRC-GVHD-NV4-001, SRC-QD-2919 |
| REQ-AI-001 | Chatbot tra cứu, trả kết quả kèm link; file được xem/tải trên web, chatbot không phát tệp trực tiếp. | CONFIRMED | SRC-GVHD-NV4-001 |
| REQ-AI-002 | Cho phép Gemini trên dữ liệu nội bộ theo project decision: authorization trước retrieval, chỉ gửi retrieved chunks cần thiết, giảm PII, key backend-only, log an toàn. Đây không phải quy định Trường. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-MASTER-001 |

## Hội đồng, bảo vệ, chấm điểm và biên bản

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-COUNCIL-001 | Hội đồng và vai trò Chủ tịch/Thư ký/2 phản biện/Ủy viên được cập nhật từ quyết định thật; hệ thống không tự chọn Chủ tịch. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001, SRC-MAU-09 |
| REQ-COUNCIL-002 | Một Hội đồng có thể đánh giá nhiều KLTN và có nhiều phiên/buổi; mỗi phiên gắn thời gian, địa điểm và danh sách KLTN. | CONFIRMED | SRC-GVHD-NV4-001, SRC-MAU-04, SRC-MAU-09 |
| REQ-COUNCIL-003 | Ghi attendance; không tổ chức nếu vắng quá 2/5 hoặc vắng Chủ tịch/Thư ký. Sau khi đủ quorum, chỉ tính phiếu hợp lệ của thành viên thực sự hiện diện/chấm. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001 |
| REQ-DEF-001 | Điều kiện bảo vệ cấp Trường: không bị kỷ luật từ cảnh cáo toàn Trường, hoàn thành KLTN và có GVHD đồng ý bằng văn bản; tiêu chí riêng của Khoa nếu có vẫn cấu hình/OPEN. | CONFIRMED / OPEN_LOCAL | SRC-QD-2919, SRC-MAU-07 |
| REQ-EVAL-001 | GVHD có phiếu nhận xét/quyết định cho bảo vệ; GVPB có phiếu nhận xét; mỗi phiếu lưu theo đúng assignment và version. | CONFIRMED | SRC-MAU-07, SRC-MAU-08, SRC-GVHD-NV4-001 |
| REQ-EVAL-002 | Mỗi thành viên Hội đồng tự nhập điểm cho từng SV; hệ thống tổng hợp trung bình cộng và làm tròn 1 chữ số thập phân. SV cùng đề tài có điểm riêng. | CONFIRMED | SRC-QD-2919, SRC-HP-IN4299N, SRC-GVHD-NV4-001 |
| REQ-EVAL-003 | Rubric theo Mẫu 6 phải lưu ba nhóm Hình thức 2,0 (1.1–1.3), Nội dung 4,0 (2.1–2.6), Demo/trả lời 4,0 (3.1–3.3), thứ tự và điểm tối đa từng tiêu chí. Điểm thưởng là mục riêng tối đa 1,0 trong phiếu; tổng phiếu kể cả thưởng không quá 10. Điểm cuối là trung bình tổng điểm các phiếu hợp lệ, làm tròn một chữ số, không cộng thưởng lần hai. | CONFIRMED baseline Mẫu 6; CONFLICT-011 OPEN trước vận hành | SRC-MAU-06, SRC-QD-2919 |
| REQ-MIN-001 | Thư ký lập/xuất biên bản; Chủ tịch chủ trì và ký/xác nhận. Người nhập điểm được sửa trước khi Thư ký in; biên bản sai trước in phải version/void/replacement. | CONFIRMED_PROJECT_DECISION | SRC-QD-2919, SRC-MAU-09, SRC-GVHD-NV4-001 |
| REQ-MIN-002 | Sửa điểm/biên bản sau khi đã in/ký chưa có quy trình; hệ thống khóa và không cung cấp bypass cho đến khi có căn cứ. | OPEN | SRC-GVHD-NV4-001 |
| REQ-RPT-001 | Chỉ giữ thống kê/báo cáo trace được về quản lý danh sách, tiến độ, Hội đồng, điểm, kho và kế hoạch; báo cáo mới ngoài phạm vi là `PROPOSED`. | DERIVED | SRC-HP-IN4299N, SRC-MAU-04, SRC-MAU-10, SRC-MAU-11 |

## Ma trận thuộc tính triển khai

Phần mô tả ở các mục trên là nội dung normative. Bảng này bổ sung actor, input, output và ghi chú để mỗi requirement đủ dữ liệu dẫn xuất Use Case/CSDL mà không lặp lại toàn văn.

| ID | Actor chính | Input | Output kiểm chứng được | Ghi chú thiết kế |
| --- | --- | --- | --- | --- |
| REQ-AUTH-001 | Người dùng, quản trị tài khoản | Hồ sơ định danh, base role | Một account hoạt động/người | Unique identifier; không account theo chức vụ |
| REQ-AUTH-002 | Người có position/assignment | Position, assignment, scope, hiệu lực | Ngữ cảnh quyền theo tài nguyên | Không tạo password riêng cho GVHD/HĐ |
| REQ-AUTH-003 | Admin, actor nghiệp vụ | Action + resource context | Admin bị từ chối nếu thiếu thẩm quyền nghiệp vụ | Backend enforce |
| REQ-ROUND-001 | TBM/Trưởng khoa theo scope | Năm học, loại đợt, lịch, policy | Round MAIN/SUPPLEMENTARY có version | Deadline cấu hình |
| REQ-ELIG-001 | SV, đơn vị xác nhận | GPA, tín chỉ, tình trạng, nguồn | Snapshot đủ/không đủ điều kiện | QĐ5964 |
| REQ-ELIG-002 | SV, ELIGIBILITY_VERIFIER | Snapshot, evidence, assignment | Xác nhận/từ chối có actor/time | Actor cụ thể OPEN-11 |
| REQ-TOPIC-001 | Giảng viên, TBM | Đề xuất, chuyên môn, title | Topic được duyệt/trả lại/từ chối | Lưu title history |
| REQ-TOPIC-002 | SV, GVHD, TBM | Đề xuất SV, GVHD dự kiến | Topic được chấp nhận trước đăng ký | Không tự mở đăng ký |
| REQ-TOPIC-003 | GVHD/TBM | GPA/kỹ năng/công nghệ/kiến thức mong muốn | TopicRequirement có enforcement DESIRED | Không là eligibility hard rule |
| REQ-EXP-001 | Giảng viên; verifier OPEN | Lĩnh vực, từ khóa, evidence | Hồ sơ self-declared/versioned | TBM verify chỉ PROPOSED |
| REQ-REG-001 | SV đủ điều kiện | Round, một topic, members | Một registration hoạt động/SV/round | Unique qua RegistrationMember |
| REQ-REG-002 | Nhóm SV | 1–3 member, coordinator | Nhóm hợp lệ, coordinator tối đa một | Coordinator không thêm quyền duyệt |
| REQ-REG-003 | GVHD, TBM | Registration, decision, reason | Lecturer decision rồi finalization/assignment | Transaction tạo Thesis |
| REQ-REG-004 | Thành viên, GVHD | Work description/output | Work assignment được duyệt | Theo từng ThesisMember |
| REQ-REG-005 | TBM/Khoa | Chính sách ghép thành viên | Chưa cung cấp mutation ghép sau submit | OPEN-02 |
| REQ-PROP-001 | SV | File sạch, proposal hiện tại | ProposalVersion bất biến | VersionNo unique |
| REQ-PROP-002 | SV/GVHD/GVPB/TBM/Trưởng khoa | Version, review, decision | Chuỗi state đúng thứ tự | Tách chốt nội dung và ký |
| REQ-PROP-003 | Reviewer/Trưởng khoa | Review form, confirmation | Review/signature metadata và bản in | Không overwrite version |
| REQ-PROG-001 | SV, GVHD | Milestone, report, evidence | ProgressReport + review/xác nhận | Có checkpoint khoảng 70% |
| REQ-PROG-002 | Actor quản lý đợt | Milestone/version/deadline | Lịch cấu hình, không hard-code | OPEN-03/06 |
| REQ-CHANGE-001 | SV, GVHD, TBM | Lý do, topic/title mới | ChangeRequest có review/decision | Trong cửa sổ policy |
| REQ-CHANGE-002 | TBM/actor được giao | Quyết định rút bên ngoài | ExternalOutcome WITHDRAWAL | Không xóa lịch sử |
| REQ-CHANGE-003 | TBM/actor được giao | Quyết định gia hạn, effective time | ExternalOutcome EXTENSION | Có official reference |
| REQ-DOC-001 | ThesisMember | Document metadata, file sạch | DocumentVersion bất biến | StoredFile tách metadata |
| REQ-SIM-001 | SV, GVHD, worker về sau | DocumentVersion, policy | Check/match/report và revision request | Vòng này chỉ schema record |
| REQ-SIM-002 | Nhóm kỹ thuật/chủ policy | Metric/version/corpus | Kết quả lexical/semantic tách biệt | Không đổi cosine thành % |
| REQ-SIM-003 | GVHD/TBM theo policy | Check result + policy hiệu lực | Advisory hoặc gate cấu hình | Metric OPEN-05 |
| REQ-REPO-001 | Người dùng được phép | Bản công bố, visibility, metadata | RepositoryItem xem/tải được | Bản nháp/PII không công bố |
| REQ-AI-001 | Người dùng | Câu hỏi/phạm vi | Answer + citation/link | Không triển khai vòng DB |
| REQ-AI-002 | Backend về sau | Authorized chunks, PII policy | Invocation audit an toàn | Quyết định dự án, không phải quy định Trường |
| REQ-COUNCIL-001 | Actor nhập quyết định | Decision ref, 5 members/roles | Council đúng quyết định | Không auto Chair |
| REQ-COUNCIL-002 | Thư ký/Chủ tịch theo action | Hội đồng, lịch, danh sách Thesis | Nhiều DefenseSession và SessionThesis | Phạm vi Bộ môn/chuyên ngành |
| REQ-COUNCIL-003 | Thư ký/Chủ tịch | Attendance 5 thành viên | READY hoặc POSTPONED; scorer set hợp lệ | QĐ2919 quorum |
| REQ-DEF-001 | GVHD/actor kiểm tra | Kỷ luật, completion, advisor review, local policy | Eligibility per ThesisMember | Local policy OPEN-04 |
| REQ-EVAL-001 | GVHD/GVPB | Form, member, document version | Review versioned theo assignment | Mẫu7/8 |
| REQ-EVAL-002 | Thành viên HĐ hiện diện | Rubric items cho từng SV | Evaluation riêng + FinalResult | Chỉ evaluator sửa phiếu mình |
| REQ-EVAL-003 | Thành viên HĐ/hệ thống | Criterion + bonus evidence | total ≤10; final mean rounded 1 digit | Bonus không cộng lần hai |
| REQ-MIN-001 | Thư ký, Chủ tịch | Completeness, minute data, signature | Minute versions, export/print/sign/lock | Void/replacement trước in |
| REQ-MIN-002 | Khoa/Trường | Thủ tục điều chỉnh hậu ký | Chưa có mutation; record khóa | OPEN-07 |
| REQ-RPT-001 | Actor báo cáo theo scope | Bộ lọc, field authorization | Read model/export có audit | Không tạo report ngoài nguồn |
