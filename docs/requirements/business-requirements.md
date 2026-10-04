# Yêu cầu nghiệp vụ — NV4

## Trạng thái

- `CONFIRMED`: được nguồn chính thức hoặc quyết định thiết kế của đề tài xác nhận.
- `DERIVED`: suy ra trực tiếp từ nhiều nguồn đã đọc, không mở rộng thẩm quyền.
- `PROPOSED`: phương án thiết kế có thể đổi khi Khoa chốt chính sách.

## Tài khoản và thẩm quyền

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-AUTH-001 | Mỗi người dùng dùng một tài khoản; base role chỉ gồm `ADMIN`, `LECTURER`, `STUDENT`. | CONFIRMED | SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 |
| REQ-AUTH-002 | GVHD, GVPB, TBM, Trưởng khoa, Chủ tịch, Thư ký và thành viên Hội đồng là position/assignment/resource role theo phạm vi, không có tài khoản/mật khẩu riêng. | CONFIRMED | SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 |
| REQ-AUTH-003 | `ADMIN` là vai trò kỹ thuật nền tảng, không mặc nhiên được duyệt/chốt nghiệp vụ. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-MASTER-001 |
| REQ-AUTH-004 | Chọn đăng ký/đăng nhập email và mật khẩu do ứng dụng KLTN quản lý; CSDL chỉ lưu mã băm. Xác minh email và đối chiếu danh sách SV/GV trước khi cấp quyền nghiệp vụ; người dùng không tự chọn chức vụ. | CONFIRMED_PROJECT_DESIGN 03/10; runtime pending | Góp ý GV 30/09–07/10 và quyết định 03/10 |

## Năm học, đợt và điều kiện

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-ROUND-001 | Một `AcademicYear` có nhiều `ThesisRound`; đợt chính và bổ sung dùng chung mô hình, khác mã/type/thời gian/trạng thái. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-QD-2919, SRC-PROJECT-MASTER-001 |
| REQ-ELIG-001 | Lập danh sách/khảo sát SV đủ điều kiện theo đợt. Điều kiện chung hiện hành: không bị xử lý theo Điều 2, có ít nhất 70% tín chỉ đạt và GPA từ 2,50/4; Khoa có thể bổ sung tiêu chí. | CONFIRMED | SRC-QD-5964, SRC-GVHD-NV4-001 |
| REQ-ELIG-002 | Phòng Đào tạo cấp dữ liệu; Khoa giao người `ELIGIBILITY_VERIFIER` theo đợt để đối chiếu và xác nhận đạt/không đạt. CSDL ứng dụng giữ kết quả, nguồn tham chiếu, người/thời gian, lý do ngắn và có thể giữ tỷ lệ tín chỉ/GPA để đối chiếu ngưỡng; không giữ chi tiết kỷ luật/án tích. Admin/TBM không mặc nhiên xác nhận. | CONFIRMED_BY_ADVISOR_2026-10-03 | SRC-QD-2919, SRC-QD-5964, SRC-PROJECT-DEC-20260925 |

## Đề tài, chuyên môn và đăng ký

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-TOPIC-001 | Giảng viên đề xuất đề tài theo chuyên môn; TBM duyệt và có thể chỉnh tên cho chính xác. | CONFIRMED | SRC-GVHD-NV4-001, SRC-QD-2919 |
| REQ-TOPIC-002 | SV có thể lập đề tài và đăng ký nhóm trước; TBM xét nội dung đề tài sau khi nhóm gửi, có thể yêu cầu sửa/từ chối/duyệt. GVHD được phân công đồng ý rồi TBM mới chốt để tạo Thesis. | CONFIRMED_PROJECT_DESIGN | SRC-GVHD-NV4-001, SRC-QD-2919, SRC-PROJECT-DEC-20260925 |
| REQ-TOPIC-003 | Đề tài có thể lưu GPA mong muốn, kỹ năng, công nghệ, kiến thức và yêu cầu khác của GVHD. GPA cao hơn 2,50 là tiêu chí mong muốn, không tự biến thành điều kiện chung của Khoa. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-MASTER-001 |
| REQ-EXP-001 | GV tự khai chuyên môn/lĩnh vực/từ khóa với minh chứng; TBM đúng bộ môn kiểm chứng, trừ hồ sơ của chính TBM thì Trưởng khoa/người được giao kiểm. Không tự xác nhận. | CONFIRMED_PROJECT_DESIGN | SRC-GVHD-NV4-001, SRC-PROJECT-DEC-20260925 |
| REQ-REG-001 | SV đủ điều kiện chọn đúng một đề tài và có tối đa một đăng ký còn hiệu lực trong một đợt; không có nguyện vọng xếp hạng thứ hai. | CONFIRMED | SRC-GVHD-NV4-001 |
| REQ-REG-002 | Một đề tài có 1–3 SV. Nhóm trưởng chỉ điều phối, không phải chủ nhiệm đề tài. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001 |
| REQ-REG-003 | Với đề tài do GV đề xuất, GV đề xuất nhận/từ chối nhóm rồi TBM chốt. Với đề tài do SV đề xuất, TBM xét đề tài sau đăng ký, người được phân công làm GVHD đồng ý rồi TBM chốt. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 |
| REQ-REG-004 | Nhóm khai phân công công việc theo từng SV; GVHD duyệt. Phân công là căn cứ đánh giá cá nhân. | CONFIRMED | SRC-GVHD-NV4-001, SRC-MAU-02 |
| REQ-REG-005 | SV tự lập nhóm 1–3; từng thành viên tự xác nhận bằng tài khoản của mình trước SUBMITTED. Từ SUBMITTED không thêm/ghép/đổi thành viên; giảng viên không có thao tác thêm thành viên. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-DEC-20260925 |
| REQ-REG-006 | Lưu PENDING/ACCEPTED/DECLINED, tài khoản và thời điểm phản hồi cho từng RegistrationMember. Service chỉ cho gửi khi mọi thành viên active đã ACCEPTED bởi chính tài khoản của mình; chưa triển khai trong prototype. | CONFIRMED_PROJECT_DESIGN / RUNTIME_PENDING | SRC-PROJECT-DEC-20260925 |

## Đề cương, tiến độ và thay đổi

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-PROP-001 | SV upload đề cương gắn mã/tên đề tài; mỗi lần nộp/sửa tạo version và history bất biến. | CONFIRMED | SRC-GVHD-NV4-001, SRC-MAU-03 |
| REQ-PROP-002 | Workflow: SV nộp → GVHD nhận xét → GVPB/Hội đồng góp ý → SV sửa → GVHD xác nhận → TBM chốt nghiệp vụ → Trưởng khoa ký/xác nhận văn bản. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-PROJECT-MASTER-001 |
| REQ-PROP-003 | Hệ thống lưu nhận xét/biểu mẫu góp ý và cho in đề cương để ký trực tiếp. Trưởng khoa ký không đồng nghĩa xét nội dung thay TBM. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-QD-2919 |
| REQ-PROG-001 | GVHD quản lý báo cáo tiến độ thường kỳ của Thesis mình hướng dẫn. Lần nội bộ 1 góp ý đề cương; lần 2 dự kiến tháng 12 khi sản phẩm đạt khoảng 70%, có GVHD khác được phân công góp ý chéo; ý kiến chéo không thay xác nhận của GVHD chính. | CONFIRMED_PROJECT_DECISION | SRC-GVHD-NV4-001, SRC-KH-2026, SRC-PROJECT-DEC-20260925 |
| REQ-PROG-002 | Lưu hai checkpoint nội bộ và các mốc trong kế hoạch SV/GVHD bằng milestone có version theo đợt. Tháng 12 là kỳ dự kiến cho lần 2; ngày giờ cụ thể phải lấy từ kế hoạch đợt đã xác nhận, không dùng ngày mâu thuẫn trong mẫu cũ. | CONFIRMED_PROJECT_DECISION / ROUND_CONFIG_REQUIRED | SRC-PROJECT-DEC-20260925, SRC-KH-2026, CONFLICT-002 |
| REQ-CHANGE-001 | Đổi đề tài thực hiện trên hệ thống, phải theo thời hạn/đồng ý quy định. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001 |
| REQ-CHANGE-002 | Rút KLTN xử lý thủ tục bên ngoài; hệ thống ghi kết quả và TBM cập nhật danh sách. | CONFIRMED | SRC-GVHD-NV4-001 |
| REQ-CHANGE-003 | Gia hạn xử lý bên ngoài; hệ thống ghi kết quả, đợt, thời gian và tài liệu minh chứng nếu có. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001 |

## Tài liệu, tương đồng, kho và AI

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-DOC-001 | Tệp đề cương/báo cáo lưu theo document + version; bản đã nộp không bị ghi đè. | DERIVED | SRC-GVHD-NV4-001, SRC-MAU-03, SRC-QD-2919 |
| REQ-SIM-001 | Khi SV nộp báo cáo, hệ thống chạy kiểm tra tương đồng, trả bằng chứng/mức “tương đồng cao”, cho GVHD xem và cho SV nộp lại. | CONFIRMED | SRC-GVHD-NV4-001 |
| REQ-SIM-002 | Tách ngưỡng nghiệp vụ “90%” khỏi metric kỹ thuật. Không map `cosine = 0.9` thành 90%; lexical + semantic, semantic chỉ tìm candidate, tỷ lệ tài liệu phải là coverage metric được đánh giá thực nghiệm. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-MASTER-001 |
| REQ-SIM-003 | Upload bản hợp lệ luôn được tiếp nhận; kiểm tra tương đồng sau upload chỉ trả bằng chứng tham khảo, GVHD đọc và SV có thể nộp bản mới. Bản hiện tại không có ngưỡng tự chặn nộp/bảo vệ; gate tương lai là thay đổi policy có nguồn, version và kiểm thử. | CONFIRMED_PROJECT_DESIGN | SRC-PROJECT-DEC-20260925 |
| REQ-REPO-001 | Theo nguồn hiện tại, kho cho xem và tải; quyền vẫn phải qua authorization và visibility của tài liệu. KLTN được quản lý theo Bộ môn/chuyên ngành. | CONFIRMED / DERIVED | SRC-GVHD-NV4-001, SRC-QD-2919 |
| REQ-AI-001 | Chatbot tra cứu, trả kết quả kèm link; file được xem/tải trên web, chatbot không phát tệp trực tiếp. | CONFIRMED | SRC-GVHD-NV4-001 |
| REQ-AI-002 | Gemini chưa kết nối. Bản thiết kế chỉ cho phép câu hỏi đã lọc và đoạn từ quy định chính thức/tài liệu đã công bố; không gửi dữ liệu cá nhân hoặc báo cáo chưa công bố của người khác. Backend phải chặn nguồn không hợp lệ trước lời gọi ngoài. | CONFIRMED_BY_ADVISOR_2026-10-03 / RUNTIME_PENDING | SRC-PROJECT-MASTER-001 |

## Hội đồng, bảo vệ, chấm điểm và biên bản

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-COUNCIL-001 | Hội đồng và vai trò Chủ tịch/Thư ký/2 phản biện/Ủy viên được cập nhật từ quyết định thật; hệ thống không tự chọn Chủ tịch. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001, SRC-MAU-09 |
| REQ-COUNCIL-002 | Một Hội đồng có thể đánh giá nhiều KLTN và có nhiều phiên/buổi; mỗi phiên gắn thời gian, địa điểm và danh sách KLTN. | CONFIRMED | SRC-GVHD-NV4-001, SRC-MAU-04, SRC-MAU-09 |
| REQ-COUNCIL-003 | Ghi attendance; không tổ chức nếu vắng quá 2/5 hoặc vắng Chủ tịch/Thư ký. Sau khi đủ quorum, chỉ tính phiếu hợp lệ của thành viên thực sự hiện diện/chấm. | CONFIRMED | SRC-QD-2919, SRC-GVHD-NV4-001 |
| REQ-DEF-001 | Đợt hiện tại chỉ dùng điều kiện bảo vệ cấp Trường: không bị kỷ luật từ cảnh cáo toàn Trường, hoàn thành KLTN và có GVHD đồng ý bằng văn bản. Khoa hiện không bổ sung tiêu chí riêng; tiêu chí mới nếu được ban hành về sau phải có nguồn và version theo đợt. | CONFIRMED / CONFIRMED_PROJECT_DECISION | SRC-QD-2919, SRC-MAU-07, SRC-PROJECT-DEC-20260925 |
| REQ-EVAL-001 | GVHD có phiếu nhận xét/quyết định cho bảo vệ; GVPB có phiếu nhận xét; mỗi phiếu lưu theo đúng assignment và version. | CONFIRMED | SRC-MAU-07, SRC-MAU-08, SRC-GVHD-NV4-001 |
| REQ-EVAL-002 | Mỗi thành viên Hội đồng tự nhập điểm cho từng SV; hệ thống tổng hợp trung bình cộng và làm tròn 1 chữ số thập phân. SV cùng đề tài có điểm riêng. | CONFIRMED | SRC-QD-2919, SRC-HP-IN4299N, SRC-GVHD-NV4-001 |
| REQ-EVAL-003 | Rubric theo Mẫu 6 phải lưu ba nhóm Hình thức 2,0 (1.1–1.3), Nội dung 4,0 (2.1–2.6), Demo/trả lời 4,0 (3.1–3.3), thứ tự và điểm tối đa từng tiêu chí. Điểm thưởng là mục riêng tối đa 1,0 trong phiếu; tổng phiếu kể cả thưởng không quá 10. Điểm cuối là trung bình tổng điểm các phiếu hợp lệ, làm tròn một chữ số, không cộng thưởng lần hai. | CONFIRMED baseline Mẫu 6 của dự án; khác biệt nguồn QĐ2919 được lưu để truy vết, không còn là câu hỏi thiết kế NV4 | SRC-MAU-06, SRC-QD-2919 |
| REQ-MIN-001 | Thư ký lập/xuất Mẫu 9; Chủ tịch và Thư ký đúng CouncilMember ký. Sau in nhưng trước chữ ký đầu tiên, Thư ký đối chiếu bản giấy; sai thì chính người chấm sửa phiếu của mình, ghi lý do/audit, bản in cũ VOID và tạo version mới để in lại. Chỉ SIGNED khi đủ hai chữ ký. | CONFIRMED_PROJECT_DECISION | SRC-MAU-09, SRC-PROJECT-DEC-20260925 |
| REQ-MIN-002 | Từ chữ ký đầu tiên trên giấy hoặc điện tử, khóa điểm/nội dung/biên bản; sau đó chỉ cấp bản sao đúng bản đã ký và ghi lần xuất, không tạo bản sửa nội dung. Thư ký không sửa điểm thay người chấm. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-DEC-20260925 |
| REQ-RPT-001 | Chỉ giữ thống kê/báo cáo trace được về quản lý danh sách, tiến độ, Hội đồng, điểm, kho và kế hoạch; báo cáo mới ngoài phạm vi là `PROPOSED`. | DERIVED | SRC-HP-IN4299N, SRC-MAU-04, SRC-MAU-10, SRC-MAU-11 |

## Ma trận thuộc tính triển khai

Phần mô tả ở các mục trên là nội dung normative. Bảng này bổ sung actor, input, output và ghi chú để mỗi requirement đủ dữ liệu dẫn xuất Use Case/CSDL mà không lặp lại toàn văn.

| ID | Actor chính | Input | Output kiểm chứng được | Ghi chú thiết kế |
| --- | --- | --- | --- | --- |
| REQ-AUTH-001 | Người dùng, quản trị tài khoản | Hồ sơ định danh, base role | Một account hoạt động/người | Unique identifier; không account theo chức vụ |
| REQ-AUTH-002 | Người có position/assignment | Position, assignment, scope, hiệu lực | Ngữ cảnh quyền theo tài nguyên | Không tạo password riêng cho GVHD/HĐ |
| REQ-AUTH-003 | Admin, actor nghiệp vụ | Action + resource context | Admin bị từ chối nếu thiếu thẩm quyền nghiệp vụ | Backend enforce |
| REQ-ROUND-001 | TBM/Trưởng khoa theo scope | Năm học, loại đợt, lịch, policy | Round MAIN/SUPPLEMENTARY có version | Deadline cấu hình |
| REQ-ELIG-001 | Phòng Đào tạo, người Khoa được giao | Dữ liệu nguồn Phòng Đào tạo | Snapshot kết quả đủ/không đủ và hai chỉ số học vụ nếu có | QĐ5964 |
| REQ-ELIG-002 | ELIGIBILITY_VERIFIER theo đợt | Snapshot, tham chiếu nguồn, assignment | Xác nhận/từ chối có actor/time | Người Khoa được giao theo round |
| REQ-TOPIC-001 | Giảng viên, TBM | Đề xuất, chuyên môn, title | Topic được duyệt/trả lại/từ chối | Lưu title history |
| REQ-TOPIC-002 | SV, TBM, GVHD được phân công | Đề tài SV, nhóm đã tự xác nhận | Đăng ký gửi trước; TBM xét đề tài sau; GVHD đồng ý trước khi chốt | Không yêu cầu Topic.APPROVED trước đăng ký nhánh SV |
| REQ-TOPIC-003 | GVHD/TBM | GPA/kỹ năng/công nghệ/kiến thức mong muốn | TopicRequirement có enforcement DESIRED | Không là eligibility hard rule |
| REQ-EXP-001 | Giảng viên; TBM đúng bộ môn hoặc Trưởng khoa/người được giao | Lĩnh vực, từ khóa, evidence | Hồ sơ self-declared/versioned và xác nhận có actor/time | Người khai không tự xác nhận |
| REQ-REG-001 | SV đủ điều kiện | Round, một topic, members | Một registration hoạt động/SV/round | Unique qua RegistrationMember |
| REQ-REG-002 | Nhóm SV | 1–3 member, coordinator | Nhóm hợp lệ, coordinator tối đa một | Coordinator không thêm quyền duyệt |
| REQ-REG-003 | GVHD, TBM | Registration, decision, reason | Lecturer decision rồi finalization/assignment | Transaction tạo Thesis |
| REQ-REG-004 | Thành viên, GVHD | Work description/output | Work assignment được duyệt | Theo từng ThesisMember |
| REQ-REG-005 | SV/GVHD/TBM | Danh sách nhóm tại thời điểm gửi | Không có mutation thành viên sau SUBMITTED | Quyết định thiết kế 25/09 |
| REQ-REG-006 | Từng SV được mời; service đăng ký | Phản hồi, tài khoản, thời điểm | PENDING/ACCEPTED/DECLINED có chứng cứ; chỉ gửi khi đủ ACCEPTED | CSDL đã lưu, API/UI và guard chưa triển khai |
| REQ-PROP-001 | SV | File sạch, proposal hiện tại | ProposalVersion bất biến | VersionNo unique |
| REQ-PROP-002 | SV/GVHD/GVPB/TBM/Trưởng khoa | Version, review, decision | Chuỗi state đúng thứ tự | Tách chốt nội dung và ký |
| REQ-PROP-003 | Reviewer/Trưởng khoa | Review form, confirmation | Review/signature metadata và bản in | Không overwrite version |
| REQ-PROG-001 | SV, GVHD | Milestone, report, evidence | ProgressReport + review/xác nhận | Có checkpoint khoảng 70% |
| REQ-PROG-002 | Người quản lý đợt theo assignment | Loại mốc, version, lịch được duyệt | Hai checkpoint và deadline cấu hình theo round | CONFLICT-002 chỉ là lỗi ngày nguồn |
| REQ-CHANGE-001 | SV, GVHD, TBM | Lý do, topic/title mới | ChangeRequest có review/decision | Trong cửa sổ policy |
| REQ-CHANGE-002 | TBM/actor được giao | Quyết định rút bên ngoài | ExternalOutcome WITHDRAWAL | Không xóa lịch sử |
| REQ-CHANGE-003 | TBM/actor được giao | Quyết định gia hạn, effective time | ExternalOutcome EXTENSION | Có official reference |
| REQ-DOC-001 | ThesisMember | Document metadata, file sạch | DocumentVersion bất biến | StoredFile tách metadata |
| REQ-SIM-001 | SV, GVHD, worker về sau | DocumentVersion, policy | Check/match/report và revision request | Vòng này chỉ schema record |
| REQ-SIM-002 | Nhóm kỹ thuật/chủ policy | Metric/version/corpus | Kết quả lexical/semantic tách biệt | Không đổi cosine thành % |
| REQ-SIM-003 | GVHD/TBM theo policy | Check result + policy hiệu lực | Advisory hoặc gate cấu hình | Baseline advisory, không auto-gate |
| REQ-REPO-001 | Người dùng được phép | Bản công bố, visibility, metadata | RepositoryItem xem/tải được | Bản nháp/PII không công bố |
| REQ-AI-001 | Người dùng | Câu hỏi/phạm vi | Answer + citation/link | Không triển khai vòng DB |
| REQ-AI-002 | Backend về sau | Câu hỏi đã lọc, nguồn chính thức/đã công bố | Invocation audit an toàn | Quyết định dự án, không phải quy định Trường |
| REQ-COUNCIL-001 | Actor nhập quyết định | Decision ref, 5 members/roles | Council đúng quyết định | Không auto Chair |
| REQ-COUNCIL-002 | Thư ký/Chủ tịch theo action | Hội đồng, lịch, danh sách Thesis | Nhiều DefenseSession và SessionThesis | Phạm vi Bộ môn/chuyên ngành |
| REQ-COUNCIL-003 | Thư ký/Chủ tịch | Attendance 5 thành viên | READY hoặc POSTPONED; scorer set hợp lệ | QĐ2919 quorum |
| REQ-DEF-001 | GVHD/actor kiểm tra | Kỷ luật, completion, xác nhận GVHD, policy theo round | Eligibility per ThesisMember | Hiện chỉ điều kiện Trường |
| REQ-EVAL-001 | GVHD/GVPB | Form, member, document version | Review versioned theo assignment | Mẫu7/8 |
| REQ-EVAL-002 | Thành viên HĐ hiện diện | Rubric items cho từng SV | Evaluation riêng + FinalResult | Chỉ evaluator sửa phiếu mình |
| REQ-EVAL-003 | Thành viên HĐ/hệ thống | Criterion + bonus evidence | total ≤10; final mean rounded 1 digit | Bonus không cộng lần hai |
| REQ-MIN-001 | Thư ký, Chủ tịch | Completeness, minute data, signature | Minute versions, export/print/sign/lock | Void/replacement trước chữ ký đầu |
| REQ-MIN-002 | Khoa/Trường | Thư ký đối chiếu giấy, evaluator sửa trước chữ ký đầu | Version cũ VOID, in bản mới | Từ chữ ký đầu khóa |
| REQ-RPT-001 | Actor báo cáo theo scope | Bộ lọc, field authorization | Read model/export có audit | Không tạo report ngoài nguồn |

## Bổ sung yêu cầu theo quyết định 25/09/2026

Những yêu cầu này là quyết định dự án SRC-PROJECT-DEC-20260925, không tự coi là quy định Trường.

| ID | Yêu cầu | Trạng thái | Nguồn |
| --- | --- | --- | --- |
| REQ-ROUND-002 | Điều phối viên KLTN được gán theo đợt/Khoa, khác Thư ký Hội đồng; quản lý mốc chính thức của đợt, không nhận quyền GVHD tự động. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-DEC-20260925 |
| REQ-CORPUS-001 | Kho truy xuất hỗ trợ KLTN vận hành, KLTN lịch sử và tài liệu học thuật bổ sung/nguồn chính thức mà không tạo Thesis giả; giữ source_type và origin_type. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-DEC-20260925 |
| REQ-CORPUS-002 | Mỗi chunk/kết quả truy xuất giữ source_id, version, provenance, visibility và scope; tài liệu nguồn không được xem là instruction. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-DEC-20260925 |
| REQ-EXPORT-001 | Xuất đúng biểu mẫu Mẫu 3/6/9 theo template/version chính thức, qua DTO có kiểu và audit; Mẫu 9 đủ hai chữ ký. | CONFIRMED_PROJECT_DECISION | SRC-MAU-03/06/09, SRC-PROJECT-DEC-20260925 |
| REQ-EXT-001 | Chỉ liên kết công cụ ngoài qua HTTPS allowlist và tab mới, không iframe/scrape/open redirect mặc định. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-DEC-20260925 |
| REQ-AI-003 | Retrieval-only có citation khi không có Gemini key; semantic ranking và similarity chỉ tư vấn, không tự duyệt/chấm/ký hoặc kết luận đạo văn. | CONFIRMED_PROJECT_DECISION | SRC-PROJECT-DEC-20260925 |
| REQ-DEF-002 | Điều kiện bảo vệ ghép các điều kiện Trường và xác nhận GVHD; đợt hiện tại không có tiêu chí Khoa thêm. Similarity chỉ tác động khi policy được duyệt và ACTIVE, hiện trả advisory. | CONFIRMED_PROJECT_DECISION / SIMILARITY_POLICY_PENDING | SRC-QD-2919, SRC-PROJECT-DEC-20260925 |
