# Giải thích CSDL KLTN bằng ngôn ngữ dễ hiểu

Tài liệu này giải thích CSDL kltn_management hiện tại: **34 bảng nghiệp vụ**. Bảng alembic_version là bảng kỹ thuật để Alembic nhớ phiên bản cấu trúc đã cập nhật; không tính vào 34 bảng nghiệp vụ. Nội dung đối chiếu theo [từ điển dữ liệu](database-dictionary.md), được sinh từ revision 20261021_0004.

Đây là tài liệu đọc để hiểu mô hình. Kiểu dữ liệu, cột bắt buộc, giá trị mặc định, khóa ngoại và điều kiện giới hạn chính xác xem trong từ điển dữ liệu. Có bảng trong CSDL không đồng nghĩa chức năng tương ứng đã hoàn thiện trên giao diện.

## Cách đọc các cột

- **id**: mã nội bộ riêng của mỗi dòng. Các cột kết thúc bằng _id thường trỏ tới mã này ở bảng khác.
- **created_at** và **updated_at**: lúc tạo và lần gần nhất cập nhật dòng. Hầu hết bảng có hai cột này; audit_event dùng occurred_at để ghi thời điểm sự kiện.
- **row_version**: số phiên bản của dòng để ứng dụng theo dõi cập nhật khi cần; đây không phải phiên bản tài liệu.
- **state** hoặc **status**: trạng thái hiện tại. Backend còn kiểm tra ai được đổi trạng thái và bước nào được phép tiếp theo.
- Các cột kết thúc bằng **_by** ghi người thực hiện; **_at** ghi thời điểm; **_ref** ghi mã hoặc căn cứ tham chiếu.

row_version có trong: academic_year, advisor_assignment, document, document_version, member_work_assignment, position_assignment, progress_milestone, progress_report, proposal, resource_assignment, reviewer_assignment, thesis, thesis_round, topic, topic_registration, user_account.

## 1. Khoa, tài khoản và quyền

### faculty — Khoa
Lưu đơn vị cấp Khoa để Bộ môn thuộc đúng Khoa và dữ liệu có phạm vi tổ chức rõ ràng. Tách riêng vì một Khoa có thể có nhiều Bộ môn.

- **code**, **name**, **active**: mã, tên và trạng thái còn sử dụng của Khoa.

### department — Bộ môn
Lưu Bộ môn và mã ngành liên quan. Bộ môn là phạm vi để quản lý đề tài, giảng viên và quyền duyệt; không gắn quyền vào một tên chức vụ cố định.

- **faculty_id**: Khoa quản lý Bộ môn này.
- **code**, **name**: mã và tên Bộ môn.
- **major_code**: mã ngành thuộc phạm vi Bộ môn, nếu có.
- **active**: Bộ môn còn được dùng hay đã ngừng.

### user_account — Tài khoản người dùng
Lưu danh tính đăng nhập và trạng thái tài khoản dùng chung cho Admin, giảng viên và sinh viên. Tách khỏi hồ sơ để thông tin đăng nhập và thông tin học tập có mục đích riêng.

- **email**: email đăng nhập/liên hệ đã được chuẩn hóa.
- **password_hash**: bản băm mật khẩu; hệ thống không cần lưu mật khẩu đọc được.
- **email_verified_at**: thời điểm xác minh email; chưa có giá trị nghĩa là email chưa xác minh.
- **external_subject**: mã tài khoản do nhà cung cấp đăng nhập ngoài cấp, để trống khi không dùng đăng nhập ngoài.
- **base_role**: vai trò nền ADMIN, LECTURER hoặc STUDENT; quyền theo đợt/đề tài còn được cấp riêng.
- **status**: tài khoản đang hoạt động, bị khóa hay bị vô hiệu hóa.

### student_profile — Hồ sơ sinh viên
Thông tin sinh viên cần dùng trong quy trình KLTN. Tách khỏi tài khoản vì hồ sơ sinh viên còn gắn với đăng ký, khóa luận và đợt.

- **user_id**: nối hồ sơ với tài khoản đăng nhập.
- **student_code**: MSSV.
- **department_id**: Bộ môn quản lý.
- **display_name**: họ tên hiển thị.
- **class_name**, **major_code**: lớp và mã ngành.

### lecturer_profile — Hồ sơ giảng viên
Thông tin giảng viên và Bộ môn để đề xuất đề tài, nhận đăng ký hoặc được phân công. Tách khỏi tài khoản để dữ liệu chuyên môn/tổ chức không lẫn với thông tin đăng nhập.

- **user_id**: nối hồ sơ với tài khoản.
- **lecturer_code**: mã giảng viên.
- **department_id**: Bộ môn.
- **display_name**: họ tên hiển thị.

### organizational_position — Chức vụ tổ chức
Danh mục chức vụ như Trưởng Bộ môn. Tách danh mục để có thể đổi tên hoặc thêm chức vụ mà không sửa cấu trúc tài khoản.

- **code**, **name**: mã và tên chức vụ.

### position_assignment — Phân công chức vụ
Ghi giảng viên nào giữ chức vụ nào, ở Khoa/Bộ môn nào và trong thời gian nào. Lưu theo thời hạn để tra cứu lịch sử khi chức vụ thay đổi.

- **lecturer_id**, **position_id**: giảng viên và chức vụ được giao.
- **faculty_id**, **department_id**: phạm vi tổ chức của chức vụ.
- **effective_from**, **effective_to**: thời gian bắt đầu và kết thúc hiệu lực.
- **state**: tình trạng phân công.

### resource_assignment — Phân công quyền theo phạm vi
Ghi quyền được giao cho một người trên một đợt hoặc khóa luận cụ thể, ví dụ nhập danh sách hay xác nhận điều kiện theo đợt. Tách khỏi vai trò nền để quyền nghiệp vụ được cấp có phạm vi và thời hạn.

- **assignment_type**: loại nhiệm vụ/quyền được giao.
- **user_id**: người nhận nhiệm vụ.
- **round_id**, **thesis_id**: đợt hoặc khóa luận nằm trong phạm vi; tùy loại phân công có thể không cần cả hai.
- **effective_from**, **effective_to**: thời gian hiệu lực.
- **state**: phân công còn hiệu lực hay đã kết thúc/thu hồi.

### audit_event — Nhật ký thao tác
Lưu dấu vết một thao tác quan trọng để biết ai làm gì, vào lúc nào và vì sao. Tách thành bảng riêng vì một đối tượng có thể có nhiều sự kiện; trạng thái cuối không thay thế được lịch sử.

- **actor_id**: người thực hiện; có thể để trống với sự kiện không gắn người dùng.
- **action**: tên hành động.
- **resource_type**, **resource_id**: loại và mã đối tượng bị tác động.
- **before_hash**, **after_hash**: dấu băm trước/sau để đối chiếu thay đổi, không phải bản sao nội dung.
- **reason**: lý do hoặc căn cứ.
- **occurred_at**: lúc sự kiện xảy ra.
- **correlation_id**: mã nhóm các sự kiện thuộc cùng một lần xử lý.

## 2. Năm học, đợt và điều kiện tham gia

### academic_year — Năm học
Lưu khoảng thời gian của năm học. Một năm học có thể có đợt chính và đợt bổ sung nên không gộp thông tin đợt vào bảng này.

- **code**: mã năm học.
- **starts_on**, **ends_on**: ngày bắt đầu và kết thúc.
- **state**: năm học đang soạn, hoạt động hay đã đóng.

### thesis_round — Đợt KLTN
Lưu từng đợt đăng ký trong một năm học, gồm lịch mở/đóng. Tách khỏi năm học vì mỗi đợt có thời hạn và trạng thái riêng.

- **academic_year_id**: năm học chứa đợt.
- **code**: mã đợt.
- **round_type**: đợt chính hay bổ sung.
- **opens_at**, **closes_at**: thời gian bắt đầu và kết thúc nhận đăng ký.
- **state**: đợt đang chuẩn bị, mở, đóng hay lưu trữ.

### eligibility_snapshot — Kết quả đủ điều kiện theo đợt
Lưu kết quả Khoa xác nhận một sinh viên có được tham gia một đợt hay không, kèm người xác nhận và căn cứ. Gọi là snapshot vì đó là kết quả tại một thời điểm/phiên bản, không phải hồ sơ điểm luôn thay đổi của sinh viên.

- **student_id**, **round_id**: sinh viên và đợt được xét.
- **version**: số lần ghi nhận kết quả cho cùng hồ sơ/đợt.
- **state**: kết quả/trạng thái xác nhận.
- **evidence_ref**: mã văn bản hoặc nguồn danh sách được đối chiếu.
- **captured_at**: lúc ghi nhận thông tin nguồn.
- **confirmed_by**, **confirmed_at**: người và thời điểm xác nhận.
- **decision_reason**: lý do hoặc ghi chú cho kết quả.
- **passed_credit_ratio**, **gpa_4**: hai cột cũ được giữ để tương thích dữ liệu; hiện có thể để trống và quy trình nhập danh sách hiện tại không cần nạp điểm hay tỷ lệ tín chỉ.

## 3. Đề tài, đăng ký và khóa luận

### topic — Đề tài
Lưu đề tài do giảng viên hoặc sinh viên đề xuất và trạng thái xét duyệt. Tách khỏi đăng ký vì một đề tài có thể được nhiều sinh viên xem, còn đăng ký là yêu cầu tham gia cụ thể.

- **round_id**: đợt đề tài được mở.
- **code**: mã đề tài để tra cứu.
- **receiving_lecturer_id**: giảng viên dự kiến tiếp nhận đăng ký.
- **department_id**: Bộ môn quản lý và xét duyệt.
- **proposer_user_id**, **proposer_type**: người đề xuất và loại người đề xuất.
- **current_title**, **description**: tên hiện tại và mô tả đề tài.
- **max_students**: số sinh viên tối đa.
- **state**: đề tài đang soạn, gửi duyệt, được duyệt, trả lại, từ chối hay khóa.
- **decided_by**, **decided_at**: người và thời điểm ra quyết định của Bộ môn.

### topic_requirement — Yêu cầu mong muốn của đề tài
Lưu kỹ năng/kiến thức hoặc yêu cầu bổ sung do người đề xuất nêu để sinh viên tham khảo. Tách riêng để một đề tài có thể có nhiều yêu cầu và để phân biệt mong muốn của GV với điều kiện chính thức của Khoa.

- **topic_id**: đề tài có yêu cầu này.
- **requirement_type**: loại yêu cầu như kỹ năng, công nghệ, kiến thức hoặc GPA mong muốn.
- **value_text**: nội dung mô tả.
- **preferred_gpa**: GPA mong muốn nếu có; không tự biến nó thành điều kiện chính thức.
- **enforcement**: tính chất yêu cầu; hiện thiết kế là yêu cầu tham khảo (DESIRED).

### topic_title_version — Lịch sử tên đề tài
Giữ các tên đề tài đã dùng qua từng lần chỉnh sửa. Tách khỏi topic.current_title để xem lại tên cũ và người/lý do đổi tên.

- **topic_id**: đề tài được đổi tên.
- **version_no**: thứ tự phiên bản tên.
- **title**: tên ở phiên bản đó.
- **changed_by**, **change_reason**: người đổi và lý do.

### topic_registration — Đăng ký đề tài
Lưu yêu cầu đăng ký của cá nhân/nhóm và các quyết định trong luồng. Tách khỏi đề tài vì một đề tài và một lần đăng ký có vòng đời khác nhau.

- **round_id**, **topic_id**: đợt và đề tài được chọn.
- **created_by**: sinh viên tạo yêu cầu.
- **expected_member_count**: quy mô nhóm dự kiến.
- **state**: bản nháp, đã gửi, GV đã nhận/từ chối, Bộ môn đã chốt, trả lại hoặc hủy.
- **submitted_at**: lúc gửi yêu cầu.
- **lecturer_decided_by**, **lecturer_decided_at**, **lecturer_reason**: GV quyết định, thời điểm và lý do.
- **department_finalized_by**, **department_finalized_at**: người Bộ môn chốt và thời điểm chốt.

### registration_member — Thành viên đăng ký
Ghi từng sinh viên tham gia vào yêu cầu đăng ký và phản hồi của chính sinh viên đó. Tách riêng vì mỗi thành viên có thể có trạng thái tham gia/minh chứng khác nhau.

- **registration_id**, **round_id**: yêu cầu đăng ký và đợt.
- **student_id**: sinh viên tham gia.
- **evidence_file_id**: tệp minh chứng riêng của sinh viên nếu cần.
- **is_coordinator**: sinh viên có vai trò điều phối nhóm hay không.
- **active**: thành viên còn trong yêu cầu đăng ký hay không.
- **consent_status**: trạng thái tự xác nhận tham gia.
- **responded_by_user_id**, **responded_at**: tài khoản và lúc sinh viên phản hồi.

### thesis — Khóa luận
Hồ sơ khóa luận được hình thành sau khi đăng ký được chốt. Tách khỏi đề tài để lưu vòng đời thực hiện khóa luận, còn đề tài là phần mô tả/chào đăng ký.

- **round_id**, **topic_id**, **registration_id**: đợt, đề tài gốc và yêu cầu đăng ký đã tạo ra khóa luận.
- **department_id**: Bộ môn quản lý.
- **current_title**: tên khóa luận đang dùng.
- **state**: trạng thái thực hiện.

### thesis_member — Thành viên khóa luận
Lưu danh sách sinh viên chính thức của khóa luận sau khi chốt. Tách khỏi registration_member để giữ phân biệt giữa người đang đăng ký và thành viên khóa luận đã được xác lập.

- **thesis_id**, **student_id**: khóa luận và sinh viên.
- **is_coordinator**: nhóm trưởng điều phối.
- **active**: còn là thành viên hay không.
- **joined_at**, **left_at**: thời điểm tham gia và rời nhóm.

### advisor_assignment — Phân công GVHD
Lưu phân công GVHD chính thức cho khóa luận và lịch sử hiệu lực. Tách khỏi GV tiếp nhận đăng ký vì nhận đăng ký không đồng nghĩa đã được Bộ môn chốt làm GVHD.

- **thesis_id**, **lecturer_id**: khóa luận và GVHD.
- **assignment_type**: loại phân công; thiết kế hiện giới hạn là GVHD chính (PRIMARY).
- **assigned_by**: người thực hiện phân công.
- **effective_from**, **effective_to**: thời gian có hiệu lực.
- **state**: phân công đang hiệu lực, đã kết thúc hay bị thu hồi.

## 4. Đề cương, tiến độ và tài liệu

### proposal — Hồ sơ đề cương
Đại diện cho hồ sơ đề cương của một khóa luận. Tách khỏi từng tệp vì một hồ sơ có thể có nhiều lần nộp/sửa.

- **thesis_id**: khóa luận sở hữu đề cương.
- **current_version_no**: số phiên bản đang được xem là hiện hành.
- **state**: trạng thái chung của hồ sơ đề cương.

### proposal_version — Phiên bản đề cương
Lưu từng bản đề cương đã nộp, người nộp, thời điểm và dấu băm. Tách riêng để giữ bản cũ khi sinh viên nộp bản sửa.

- **proposal_id**, **version_no**: hồ sơ và số phiên bản.
- **stored_file_id**: tệp của phiên bản.
- **submitted_by**, **submitted_at**: người và lúc nộp.
- **content_sha256**: dấu băm để kiểm tra đúng nội dung tệp.

### reviewer_assignment — Phân công người góp ý đề cương
Ghi giảng viên được giao góp ý đề cương nào và phạm vi góp ý. Tách khỏi nhận xét để lưu việc phân công ngay cả trước khi có phản hồi.

- **lecturer_id**: giảng viên góp ý.
- **proposal_id**, **thesis_id**: hồ sơ đề cương và khóa luận liên quan.
- **review_scope**: phạm vi/nội dung được giao.
- **assigned_by**, **assigned_at**: người phân công và thời điểm.
- **state**: phân công còn hiệu lực hay đã kết thúc.

### proposal_review — Nhận xét đề cương
Lưu quyết định và nhận xét của từng người trên một phiên bản đề cương. Tách khỏi phân công vì người được giao có thể chưa gửi nhận xét, hoặc cần lưu nhiều lần phản hồi.

- **proposal_version_id**: phiên bản được nhận xét.
- **reviewer_assignment_id**: nhiệm vụ góp ý tương ứng.
- **reviewer_user_id**: tài khoản người nhận xét.
- **decision**, **comment**: kết quả và nội dung nhận xét.

### signature_confirmation — Xác nhận chữ ký đề cương
Ghi nhận việc đối chiếu/xác nhận chữ ký bên ngoài gắn với đúng phiên bản đề cương. Bảng này lưu thông tin xác nhận, không tự tạo chữ ký điện tử.

- **proposal_id**, **proposal_version_no**: hồ sơ và phiên bản được xác nhận.
- **signature_type**: loại xác nhận/chữ ký.
- **signer_user_id**, **confirmed_at**: người ghi nhận và thời điểm.
- **official_ref**: số hoặc mã văn bản làm căn cứ.

### progress_milestone — Mốc tiến độ
Lưu mốc công việc và hạn cần đạt trong một đợt. Tách mốc khỏi báo cáo để nhiều khóa luận có thể cùng báo cáo theo mốc chung, và mốc có thể được cập nhật theo phiên bản.

- **round_id**: đợt áp dụng.
- **code**, **title**: mã và tên mốc.
- **version_no**: phiên bản cấu hình mốc.
- **due_at**: hạn hoàn thành.
- **expected_ratio**: tỷ lệ tiến độ dự kiến.
- **source_type**: mốc do nguồn/quy định nào đặt ra.
- **state**: mốc đang áp dụng hay đã đóng.

### progress_report — Báo cáo tiến độ
Lưu báo cáo của khóa luận tại một mốc và phiên bản nộp. Tách khỏi nhận xét để giữ nội dung SV đã gửi độc lập với đánh giá của GV.

- **thesis_id**, **milestone_id**: khóa luận và mốc được báo cáo.
- **version_no**: lần nộp báo cáo tại mốc.
- **summary**: phần tóm tắt công việc.
- **reported_ratio**: mức tiến độ SV tự báo cáo.
- **evidence_file_id**: tệp minh chứng nếu có.
- **submitted_by**: người nộp.
- **state**: trạng thái xử lý báo cáo.

### progress_review — Nhận xét tiến độ
Lưu nhận xét/quyết định của giảng viên trên một báo cáo tiến độ. Tách riêng để có thể xem báo cáo gốc và phản hồi tương ứng.

- **progress_report_id**: báo cáo được nhận xét.
- **reviewer_id**: giảng viên nhận xét.
- **decision**, **comment**: kết quả và nội dung góp ý.

### member_work_assignment — Phân công việc thành viên
Ghi phần việc dự kiến của từng thành viên trong khóa luận và nhận xét kết quả. Tách riêng để thể hiện đóng góp cá nhân bên trong một khóa luận chung.

- **thesis_member_id**: thành viên được giao việc.
- **version_no**: phiên bản phân công.
- **work_description**, **expected_output**: việc cần làm và sản phẩm mong đợi.
- **state**: trạng thái phần việc.
- **reviewed_by**, **reviewed_at**, **review_comment**: người, lúc và nội dung nhận xét.

### document — Hồ sơ tài liệu KLTN
Đại diện một loại hồ sơ/tài liệu thuộc khóa luận, chẳng hạn báo cáo. Tách khỏi tệp cụ thể để một hồ sơ có thể có nhiều phiên bản.

- **thesis_id**: khóa luận sở hữu hồ sơ.
- **document_type**, **title**: loại và tên hồ sơ.
- **visibility**: nhóm người được phép xem theo chính sách ứng dụng.
- **state**: hồ sơ đang soạn, sử dụng, lưu trữ hay bị thu hồi.

### document_version — Phiên bản tài liệu
Lưu mỗi lần nộp tệp của một hồ sơ tài liệu. Tách riêng để không ghi đè bản nộp trước và có thể đối chiếu nội dung.

- **document_id**, **version_no**: hồ sơ và số phiên bản.
- **stored_file_id**: tệp được lưu.
- **submitted_by**, **submitted_at**: người và lúc nộp.
- **content_sha256**: dấu băm của nội dung tệp.
- **state**: trạng thái bản nộp, ví dụ đã gửi, yêu cầu sửa hay được chấp nhận.

### stored_file — Thông tin tệp lưu trữ
Lưu thông tin để ứng dụng tìm, nhận diện và kiểm tra tệp; nội dung tệp được lưu ở kho tệp theo storage_key. Tách riêng để các phiên bản/tác vụ có thể tham chiếu tệp mà không sao chép nội dung vào nhiều bảng.

- **storage_key**: vị trí/khóa nội bộ để tìm tệp.
- **original_name**: tên tệp khi người dùng tải lên.
- **media_type**, **byte_size**: loại nội dung và kích thước.
- **sha256**: dấu băm để kiểm tra tệp có bị thay đổi.
- **scan_state**, **scanned_at**: trạng thái và thời điểm ghi nhận quét. Có các cột này chưa đủ để kết luận hệ thống đã tích hợp công cụ diệt mã độc.

## Một vài điểm cần phân biệt

- topic là đề tài được đưa ra; topic_registration là yêu cầu của sinh viên muốn tham gia; thesis là hồ sơ khóa luận sau khi đăng ký được chốt.
- registration_member là thành viên trong yêu cầu đăng ký; thesis_member là thành viên chính thức của khóa luận.
- receiving_lecturer_id trên đề tài/giảng viên quyết định đăng ký không tự đồng nghĩa với phân công GVHD chính thức ở advisor_assignment.
- proposal/proposal_version quản lý đề cương; document/document_version quản lý các hồ sơ tài liệu khác của khóa luận.
- eligibility_snapshot giữ kết quả đủ điều kiện và căn cứ xác nhận theo đợt. Hai cột GPA/tỷ lệ tín chỉ được giữ vì tương thích cấu trúc; quy trình hiện tại không cần nhập các dữ liệu này.
- alembic_version chỉ ghi revision cấu trúc CSDL đã áp dụng; không phải dữ liệu nghiệp vụ.

## Tài liệu tra cứu chính xác

Muốn xem kiểu dữ liệu, cột bắt buộc, mặc định, giá trị hợp lệ, PK/FK, UNIQUE, CHECK và index, mở [database-dictionary.md](database-dictionary.md). Tài liệu giải thích này dùng lời thường để hiểu vai trò bảng/cột và lý do tách bảng; không thay thế định nghĩa kỹ thuật trong từ điển.
