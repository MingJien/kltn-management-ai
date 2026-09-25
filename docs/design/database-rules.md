# Quy tắc và ràng buộc CSDL

## Nguyên tắc

PostgreSQL bảo đảm invariant trong một hàng hoặc giữa các hàng có thể biểu diễn bằng PK/FK/UNIQUE/CHECK/partial unique index. Invariant cần đếm nhiều hàng, kiểm thẩm quyền hoặc đổi nhiều aggregate được thực hiện trong một transaction ở application service, có khóa hàng và kiểm tra lại trước commit. `DATABASE_ENFORCED` nghĩa là schema thực sự chặn; `APPLICATION_ENFORCED` nghĩa là backend tương lai phải kiểm; `DATABASE + APPLICATION` là cả hai lớp cùng tham gia. Không tuyên bố DB enforce nếu schema không làm được.

## Danh mục ràng buộc

| ID | Quy tắc nghiệp vụ | Cơ chế | Mức enforce | Bảng/constraint |
| --- | --- | --- | --- | --- |
| DBR-01 | Một account cho một subject; base role chỉ 3 giá trị | UNIQUE + CHECK | DATABASE_ENFORCED | `user_account.external_subject`, `ck_user_account_base_role` |
| DBR-02 | Profile SV/GV một-một với account | UNIQUE FK | DATABASE_ENFORCED | `student_profile.user_id`, `lecturer_profile.user_id` |
| DBR-03 | Position có đúng scope Khoa hoặc Bộ môn; tối đa một assignment `ACTIVE` cho cùng GV/vị trí/scope | XOR CHECK + FK + 2 partial unique index | DATABASE_ENFORCED | `position_assignment`; `uq_position_assignment_*_scope` |
| DBR-04 | ResourceAssignment có đúng một resource; tối đa một assignment `ACTIVE` cho cùng user/type/resource | XOR CHECK + FK + 3 partial unique index | DATABASE_ENFORCED | `resource_assignment`; `uq_resource_assignment_*_scope` |
| DBR-05 | MAIN/SUPPLEMENTARY chung mô hình; time window hợp lệ | CHECK + UNIQUE | DATABASE_ENFORCED | `thesis_round` |
| DBR-06 | Snapshot GPA/credit trong miền hợp lệ, decision có actor/time | CHECK + FK | DATABASE_ENFORCED | `eligibility_snapshot` |
| DBR-07 | Threshold đăng ký 70%/2,50 theo policy hiện hành | Tính từ snapshot + policy version | APPLICATION_ENFORCED | Không hard-code threshold làm CHECK để còn policy Khoa/ngoại lệ |
| DBR-08 | Preferred GPA/kỹ năng chỉ là mong muốn | CHECK `enforcement=DESIRED` | DATABASE_ENFORCED | `topic_requirement` |
| DBR-09 | Một SV chỉ ở một registration hoạt động/round, kể cả member nhóm | Composite FK + partial UNIQUE | DATABASE + APPLICATION | `uq_registration_member_student_round_active`; service đồng bộ `active` với state |
| DBR-10 | Registration/Thesis có 1–3 member và không vượt topic capacity | COUNT + row lock khi submit/finalize | APPLICATION_ENFORCED (transaction) | Khóa Topic/Registration; DB giữ unique member và max_students 1..3 |
| DBR-11 | Tối đa một coordinator hoạt động | Partial UNIQUE | DATABASE_ENFORCED | Hai index `*_one_coordinator` |
| DBR-12 | Một Thesis/topic/round; một Thesis/registration | UNIQUE | DATABASE_ENFORCED | `thesis(round_id,topic_id)`, `thesis.registration_id` |
| DBR-13 | Một GVHD chính hoạt động/Thesis | Partial UNIQUE | DATABASE_ENFORCED | `uq_advisor_assignment_active_primary` |
| DBR-14 | Work allocation có version theo member | UNIQUE + FK | DATABASE_ENFORCED | `member_work_assignment` |
| DBR-15 | Proposal/document/minute version không trùng | UNIQUE + immutable policy | DATABASE + APPLICATION | Các bảng `*_version`; không UPDATE byte sau submit |
| DBR-16 | StoredFile chỉ được dùng submit khi scan CLEAN | State guard | APPLICATION_ENFORCED | DB giới hạn scan_state |
| DBR-17 | Similarity không hard-code cosine=90% | Metric/policy/version là dữ liệu | DATABASE + APPLICATION | threshold nullable, metric_code, ADVISORY/GATE |
| DBR-18 | Council đúng 5 người/role slot | UNIQUE lecturer, UNIQUE role/slot; kiểm count/role | DATABASE + APPLICATION | `council_member`; service kiểm 1 Chair, 1 Secretary, 2 Reviewer, 1 Member |
| DBR-19 | Một session nhiều Thesis, không lặp/thứ tự không trùng | UNIQUE | DATABASE_ENFORCED | `session_thesis` |
| DBR-20 | Attendance một record/member/session | UNIQUE FK | DATABASE_ENFORCED | `council_attendance` |
| DBR-21 | Không mở phiên nếu vắng >2/5 hoặc vắng Chair/Secretary | Query + transaction guard | APPLICATION_ENFORCED | CouncilMember + Attendance |
| DBR-22 | Một evaluator chấm một SV một lần/session | UNIQUE | DATABASE_ENFORCED | `evaluation(session_id,evaluator_member_id,thesis_member_id)` |
| DBR-23 | Evaluator thuộc Council và present | Cross-table query + lock | APPLICATION_ENFORCED | Kiểm trước create/submit |
| DBR-24 | Mẫu 6 có ba nhóm 2/4/4, 12 tiêu chí con và bonus ≤1; group chỉ tổng hợp, không cộng hai lần; từng item không vượt max, tổng phiếu 0..10 | CHECK cục bộ cho bonus/tổng, FK hierarchy + đối chiếu rubric đầy đủ ở backend | DATABASE + APPLICATION | `rubric_template`, `rubric_criterion.parent_id`, `evaluation_item`, `evaluation`; SRC-MAU-06, CONFLICT-011 |
| DBR-25 | FinalResult từng SV/session; mean hợp lệ, làm tròn 1 số | UNIQUE + calculation service versioned | DATABASE + APPLICATION | `final_result` |
| DBR-26 | Bonus nằm trong total; không cộng lần hai | Calculation contract + CHECK | APPLICATION_ENFORCED | `bonus_average` chỉ giải thích |
| DBR-27 | Minute version/replacement không self-loop; bản in chưa ký được VOID, khóa từ chữ ký đầu | CHECK/UNIQUE + state guard | DATABASE + APPLICATION | `minute_version`, `council_minute` |
| DBR-28 | Chỉ Chair đúng Council ký minute | FK + role/scope query | APPLICATION_ENFORCED | `minute_signature.signer_member_id` |
| DBR-29 | Không cascade delete lịch sử | FK `ON DELETE RESTRICT` | DATABASE_ENFORCED | Toàn bộ FK nghiệp vụ |
| DBR-30 | Audit không chứa body/secret/PII thô | Chỉ hash/ID/reason tối thiểu | APPLICATION_ENFORCED + REVIEW | `audit_event`, `retrieval_audit` |
| DBR-31 | GVPB không trùng assignment active cho cùng proposal/thesis; scope phải khớp đối tượng | XOR/scope CHECK + 2 partial unique index | DATABASE_ENFORCED | `reviewer_assignment`; `uq_reviewer_assignment_proposal/thesis` |
| DBR-32 | Xác nhận/ký đề cương phải trỏ tới phiên bản thật của **cùng** hồ sơ đề cương | FK ghép `(proposal_id, proposal_version_no)` và CHECK dương; backend còn kiểm bản đó là bản được phép ký | DATABASE + APPLICATION | `signature_confirmation`, `fk_signature_confirmation_proposal_version_pair`; DB-26 |
| DBR-33 | `progress_review.decision=COMMENT_ONLY` cho GV góp ý chéo, không xác nhận tiến độ; CONFIRM/REVISION_REQUIRED chỉ GVHD chính | CHECK tập decision ở DB; quyền và đổi ProgressReport.state ở service | DATABASE + APPLICATION | `progress_review`, migration 0005; DB-40 |

## Transaction boundary bắt buộc

1. **Finalize đăng ký:** khóa Topic + Registration + active RegistrationMember; kiểm eligibility, unique round, count/capacity; ghi FINALIZED, tạo Thesis/ThesisMember/AdvisorAssignment và AuditEvent trong một transaction.
2. **Nộp version:** kiểm StoredFile CLEAN; cấp versionNo dưới khóa aggregate; insert version bất biến và cập nhật current version trong một transaction.
3. **Mở phiên/chấm:** khóa DefenseSession; kiểm Council VALIDATED, attendance/quorum, rubric assignment; sau đó mới chuyển READY/SCORING.
4. **Submit/sửa phiếu:** xác định evaluator từ account→CouncilMember, kiểm present/owner; tính item/bonus/total phía server; dùng optimistic `row_version`.
5. **Tổng hợp/biên bản:** khóa session; chốt scorer set; ghi FinalResult, MinuteVersion và AuditEvent; sau in trước ký có thể sửa qua bản mới và audit; từ chữ ký đầu không sửa.
6. **Công bố/thu hồi:** cập nhật RepositoryItem và SearchIndexMetadata/outbox trong cùng transaction logic; index ngoài là dữ liệu dẫn xuất.

## Index phục vụ use case

- Unique/index định danh account/profile/code.
- `registration_member(student_id,round_id) WHERE active` cho UC-REG.
- FK columns và `stored_file.sha256`, correlation IDs có index.
- Composite index cho dashboard sẽ thêm sau khi có query plan; không đoán index cho API chưa thiết kế.
- Không tạo PostgreSQL RLS ở baseline; backend về sau enforce quyền bằng scope/assignment đã lưu.

## Xóa và lịch sử

Không cascade delete. Dữ liệu thử nghiệm có thể cleanup bằng transaction riêng trong validation; dữ liệu nghiệp vụ thật dùng state CANCELLED/REVOKED/VOID/ARCHIVED. Bảng version, Evaluation submitted, FinalResult, Signature và AuditEvent là append-only ở application layer.

## Quy tắc corpus 0003

- CHECK `origin_source_consistency` ngăn tài liệu lịch sử/biểu mẫu bị gắn Thesis giả hoặc nguồn chính thức bị gán loại THESIS.
- CHECK `has_source_reference` yêu cầu ít nhất một nội dung/nguồn tham chiếu; importer vẫn phải xác minh tệp, quyền dùng và provenance ngoài CHECK.
- Unique `published_document_version_id` vẫn giữ cho managed thesis; NULL cho imported/official được PostgreSQL cho phép nhiều hàng.
- `source_type` có vocab rõ. Không suy luận chất lượng tài liệu từ type; visibility và authorization ở service/query.
- Index Qdrant có thể xóa dựng lại từ nguồn đã duyệt; không ghi điểm tương đồng như điểm số nghiệp vụ.

- Migration 0004: `external_source_id` UNIQUE cho upsert manifest; `source_url` chỉ HTTPS; kiểm nguồn tham chiếu chấp nhận URL. Indexer ghi RepositoryItem/SearchIndexMetadata trong PostgreSQL trước, rồi upsert Qdrant; status FAILED khi index lỗi.
