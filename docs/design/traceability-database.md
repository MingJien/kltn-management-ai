# Truy vết nghiệp vụ → CSDL

## Ma trận Use Case → entity/constraint

| Use Case | Requirement / Rule | Entity chính | Relation / constraint kiểm chứng |
| --- | --- | --- | --- |
| UC-AUTH-001 | REQ-AUTH-001..003; BR-AUTH-001/002 | UserAccount, profiles, PositionAssignment, ResourceAssignment | Unique subject/profile; explicit scope/assignment; Admin không có FK bypass |
| UC-ROUND-001 | REQ/BR-ROUND-001 | AcademicYear, ThesisRound, RoundPolicy | 1:N; unique year+code; type CHECK; policy version |
| UC-ELIG-001 | REQ-ELIG-001/002; BR-ELIG-001/002 | EligibilitySnapshot, EligibilityException, ResourceAssignment | Unique student+round+version; ranges; decision metadata |
| UC-EXP-001 | REQ-EXP-001 | LecturerExpertise, ExpertiseEvidence | Unique lecturer+version; state SELF_DECLARED; verifier nullable |
| UC-TOPIC-001/002 | REQ-TOPIC-001/002 | Topic, TopicTitleVersion | Topic→versions 1:N; proposer FK; title version unique |
| UC-TOPIC-003 | BR-TOPIC-001 | Topic, TopicTitleVersion, PositionAssignment | state/version; decision actor; title history |
| UC-REG-001/002 | REQ-REG-001/002/005; BR-REG-001/002/005 | TopicRegistration, RegistrationMember | Composite FK; unique active student+round; one coordinator; count app |
| UC-ASSIGN-001 | REQ/BR-REG-003 | Thesis, ThesisMember, AdvisorAssignment | Atomic finalize; unique Thesis topic/round; active primary advisor |
| UC-WORK-001 | REQ/BR-REG-004 | MemberWorkAssignment | FK ThesisMember; unique member+version; review state |
| UC-PROP-001 | REQ-PROP-001; BR-PROP-001 | Proposal, ProposalVersion, StoredFile | 1:1 Thesis; unique version; immutable hash |
| UC-PROP-002/003 | REQ-PROP-002; BR-PROP-001/002 | ProposalReview, ReviewerAssignment, ProposalVersion | Review trỏ exact version/assignment |
| UC-PROP-004 | REQ-PROP-003; BR-PROP-002 | SignatureConfirmation, ProposalVersion | unique signature type; composite FK khóa đúng phiên bản đề cương; guarded state |
| UC-PROG-001 | REQ-PROG-002; BR-PROG-001 | ProgressMilestone, RoundPolicy | unique round+code+version; date configurable |
| UC-PROG-002 | REQ-PROG-001 | ProgressReport, ProgressReview | unique thesis+milestone+version; reviewer FK |
| UC-CHANGE-001 | REQ-CHANGE-001; BR-CHANGE-001 | TopicChangeRequest | target present CHECK; state/reviewer/decision metadata |
| UC-EXT-001 | REQ-CHANGE-002/003 | ExternalProcedureOutcome | type CHECK; official ref/effective time; no delete Thesis |
| UC-DOC-001 | REQ-DOC-001; BR-DOC-001 | StoredFile, Document, DocumentVersion | scan state; unique doc+version; immutable checksum |
| UC-SIM-001 | REQ-SIM-001..003; BR-SIM-001..003 | SimilarityPolicy, SimilarityCheck, SimilarityMatch | policy/metric provenance; nullable threshold; ranges; no plagiarism field |
| UC-COUNCIL-001 | REQ-COUNCIL-001; BR-COUNCIL-001/002 | Council, CouncilMember | decision ref; unique lecturer/role-slot; exact 5 app guard |
| UC-SESSION-001 | REQ-COUNCIL-002/003 | DefenseSession, SessionThesis, CouncilAttendance | unique thesis/order; unique attendance; quorum app guard |
| UC-DEF-001 | REQ-DEF-001 | DefenseEligibilityCheck, AdvisorReview | per member result, local/similarity policy nullable |
| UC-EVAL-001 | REQ-EVAL-001 | AdvisorReview, ReviewerReview, assignments | unique assignment+member+version; document version FK |
| UC-RUBRIC-001 | REQ-EVAL-003; BR-EVAL-003 | RubricTemplate, RubricCriterion, RubricAssignment | template version/source; parent_id và thứ tự cho 3 nhóm 2/4/4 + 12 tiêu chí Mẫu 6; bonus ≤1; một round/session scope; tổng nhóm kiểm ở application |
| UC-EVAL-002 | REQ-EVAL-002/003; BR-EVAL-001/003 | Evaluation, EvaluationItem, BonusEvidence | unique evaluator+member+session; total/bonus CHECK; owner/present app |
| UC-EVAL-003 | BR-EVAL-002/003 | FinalResult, Evaluation, Attendance | unique session+member; scorerCount; calculationVersion |
| UC-MIN-001/002 | REQ-MIN-001/002; BR-MIN-001/002 | CouncilMinute, MinuteVersion, MinuteSignature | unique versions; replacement relation; signer CouncilMember; state lock |
| UC-REPO-001 | REQ-REPO-001; BR-REPO-001 | RepositoryItem, SearchIndexMetadata | exact published DocumentVersion; visibility/index state |
| UC-AI-001 | REQ-AI-001/002; BR-AI-001/002 | RetrievalAudit, SearchIndexMetadata | chỉ hash/scope/count/provider; không raw prompt/secret |
| UC-RPT-001 | REQ-RPT-001; BR-AUDIT-001 | FinalResult, progress/council read models, AuditEvent | nguồn giao dịch chuẩn; audit correlation |

## Vertical slice CSDL

### VS-DB-01 — Điều kiện → topic → đăng ký → GVHD → TBM

`SRC-QD-5964 + SRC-GVHD-NV4-001` → REQ-ELIG/REG/TOPIC → BR-ELIG/REG/TOPIC → UC-ELIG/TOPIC/REG/ASSIGN → EligibilitySnapshot/Topic/RegistrationMember/Thesis/AdvisorAssignment → composite FK + partial unique + transaction finalize.

Không phải đoán cardinality. Người Khoa được giao `ELIGIBILITY_VERIFIER` theo round được lưu ở ResourceAssignment, không đổi schema. Quyết định dự án khóa thành viên sau SUBMITTED; GV không thêm/ghép.

### VS-DB-02 — Nhóm → coordinator → phân công việc → GVHD

`SRC-GVHD-NV4-001 + SRC-MAU-02` → REQ-REG-002/004 → BR-REG-002/004 → UC-REG-002/WORK-001 → ThesisMember/MemberWorkAssignment/AdvisorAssignment → unique member, partial unique coordinator, unique work version; count 1–3 và review ownership do transaction/application.

### VS-DB-03 — Proposal → versions → reviews → chốt/ký

`SRC-GVHD-NV4-001 + SRC-MAU-03 + SRC-PROJECT-MASTER-001` → REQ-PROP-001..003 → BR-PROP-001/002 → UC-PROP-001..004 → Proposal/Version/Review/SignatureConfirmation/StoredFile → unique version, exact file hash, review assignment, unique signature type; guarded order trong service.

### VS-DB-04 — Milestone → progress → GVHD review

`SRC-GVHD-NV4-001 + SRC-MAU-02 + SRC-HP-IN4299N` → REQ-PROG-001/002 → BR-PROG-001 → UC-PROG-001/002 → ProgressMilestone/Report/Review → versioned milestone, report version, reviewer FK. OPEN deadline không cản schema.

### VS-DB-05 — Document → versions → similarity record

`SRC-GVHD-NV4-001 + quyết định dự án` → REQ-DOC/SIM → BR-DOC/SIM → UC-DOC/SIM → StoredFile/Document/Version/SimilarityPolicy/Check/Match → immutable version, provenance, metric/threshold configurable. Không có cột plagiarism và không hard-code 90%.

### VS-DB-06 — Council → session → attendance → điểm từng SV → biên bản

`SRC-QD-2919 + SRC-MAU-06/07/08/09 + GVHD` → REQ-COUNCIL/DEF/EVAL/MIN → BR-COUNCIL/EVAL/MIN → UC-COUNCIL/SESSION/DEF/EVAL/MIN → Council/Member/Session/Attendance/Reviews/Rubric/Evaluation/FinalResult/Minute → unique role slot, attendance, evaluation owner, score bounds, result per student, minute version/signature/lock. Quorum và present evaluator là cross-table transaction guard đã chỉ rõ.

## Coverage

- 40/40 requirement có nguồn và ít nhất một UC/data concern.
- 33/33 use case canonical có entity hoặc được xác định không đổi state.
- 62/62 table trong metadata thuộc một aggregate của `domain-model.md`; không có table phục vụ API/UI vô nguồn.
- 62 PK UUID; tất cả quan hệ nghiệp vụ chính dùng FK cụ thể; FK mặc định RESTRICT.
- Các invariant không thể biểu diễn thuần DB đã ghi APPLICATION/TRANSACTION tại `database-rules.md`, không được quảng cáo là database-enforced.
- Test case: DB-01..DB-26 trong `database-validation.md`; ngày 24/09/2026 đã PASS 26/26 trên PostgreSQL 17.11 native, migration round-trip và Alembic check PASS. Các rule APPLICATION_ENFORCED chưa được các ca schema chứng minh.

- Migration 0003/0004: REQ-CORPUS-001/002 → BR-CORPUS-001/002 → UC-REPO-001 → repository_item (origin_type, source_type, external_source_id, source_ref, source_url, provenance, stored_file_id), search_index_metadata (document_version_id nullable), similarity_match (source_repository_item_id). DB-27..39 kiểm tra constraints và nguồn. Migration 0005 thêm `progress_review.decision=COMMENT_ONLY`, DB-40 kiểm tập giá trị.
