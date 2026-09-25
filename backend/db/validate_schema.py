from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError

from backend.db.models import entities as m


ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        raise RuntimeError("Missing local .env")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def uid() -> uuid.UUID:
    return uuid.uuid4()


def expect_integrity(conn, action, label: str) -> None:
    nested = conn.begin_nested()
    try:
        action()
        nested.commit()
    except IntegrityError:
        nested.rollback()
        return
    raise AssertionError(label + " was not blocked")


def main() -> int:
    load_env()
    engine = create_engine(os.environ["DATABASE_URL"], future=True)
    passed = []
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        outer = conn.begin()
        try:
            tables = set(inspect(conn).get_table_names())
            assert len(tables) == 63 and "alembic_version" in tables
            assert conn.execute(text("select version_num from alembic_version")).scalar_one() == "20260925_0006"

            # DB-41: the real Mẫu 6 baseline is present but cannot be used live
            # until the Faculty resolves its conflict with QĐ 2919.
            baseline = conn.execute(text("""
                SELECT id, source_ref, state FROM rubric_template
                WHERE code = 'MAU-06-HOIDONG' AND version_no = 1
            """)).mappings().one()
            assert baseline["source_ref"] == "SRC-MAU-06"
            criteria = conn.execute(text("""
                SELECT id, parent_id, code, label, max_points, criterion_type, order_no
                FROM rubric_criterion WHERE rubric_template_id = :template_id
                ORDER BY order_no
            """), {"template_id": baseline["id"]}).mappings().all()
            assert len(criteria) == 16
            by_code = {row["code"]: row for row in criteria}
            assert len(by_code) == 16
            assert [row["code"] for row in criteria] == [
                "1", "1.1", "1.2", "1.3", "2", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6",
                "3", "3.1", "3.2", "3.3", "4",
            ]
            expected_groups = {"1": Decimal("2"), "2": Decimal("4"), "3": Decimal("4")}
            for code, maximum in expected_groups.items():
                group = by_code[code]
                children = [row for row in criteria if row["parent_id"] == group["id"]]
                assert group["criterion_type"] == "GROUP" and group["max_points"] == maximum
                assert sum(row["max_points"] for row in children) == maximum
            assert sum(row["criterion_type"] == "NORMAL" for row in criteria) == 12
            assert by_code["1.1"]["label"] == "Chuyên cần"
            assert by_code["3.3"]["label"].startswith("Thuyết trình lưu loát")
            assert by_code["4"]["criterion_type"] == "BONUS"
            assert by_code["4"]["max_points"] == Decimal("1")
            passed.append("DB-41")

            faculty_id, department_id = uid(), uid()
            conn.execute(m.Faculty.__table__.insert().values(id=faculty_id, code="SYN-FAC", name="Khoa gia lap"))
            conn.execute(m.Department.__table__.insert().values(id=department_id, faculty_id=faculty_id, code="SYN-DEP", name="Bo mon gia lap", major_code="SYN"))

            user_ids = [uid() for _ in range(10)]
            for i, user_id in enumerate(user_ids):
                role = "STUDENT" if i < 4 else "LECTURER"
                conn.execute(m.UserAccount.__table__.insert().values(
                    id=user_id, external_subject=f"synthetic-{i}-{user_id}", base_role=role, status="ACTIVE"
                ))
            student_ids = [uid() for _ in range(4)]
            for i, student_id in enumerate(student_ids):
                conn.execute(m.StudentProfile.__table__.insert().values(
                    id=student_id, user_id=user_ids[i], student_code=f"SYN-SV-{i+1}",
                    department_id=department_id, display_name=f"Sinh vien gia lap {i+1}"
                ))
            lecturer_ids = [uid() for _ in range(6)]
            for i, lecturer_id in enumerate(lecturer_ids):
                conn.execute(m.LecturerProfile.__table__.insert().values(
                    id=lecturer_id, user_id=user_ids[i+4], lecturer_code=f"SYN-GV-{i+1}",
                    department_id=department_id, display_name=f"Giang vien gia lap {i+1}"
                ))
            passed.append("DB-02")

            year_id, round_id = uid(), uid()
            conn.execute(m.AcademicYear.__table__.insert().values(
                id=year_id, code="SYN-2026-2027", starts_on=date(2026, 9, 1),
                ends_on=date(2027, 8, 31), state="ACTIVE"
            ))
            conn.execute(m.ThesisRound.__table__.insert().values(
                id=round_id, academic_year_id=year_id, code="SYN-MAIN",
                round_type="MAIN", opens_at=now, closes_at=now+timedelta(days=90), state="OPEN"
            ))
            passed.append("DB-01")

            assignment_id = uid()
            conn.execute(m.ResourceAssignment.__table__.insert().values(
                id=assignment_id, assignment_type="ELIGIBILITY_VERIFIER", user_id=user_ids[4],
                round_id=round_id, effective_from=now, state="ACTIVE"
            ))
            for i, student_id in enumerate(student_ids):
                conn.execute(m.EligibilitySnapshot.__table__.insert().values(
                    id=uid(), student_id=student_id, round_id=round_id, version=1,
                    passed_credit_ratio=Decimal("0.80"), gpa_4=Decimal("3.00"),
                    discipline_status="CLEAR", criminal_case_status="CLEAR",
                    evidence_ref=f"SYN-EVIDENCE-{i}", captured_at=now,
                    confirmed_by=user_ids[4], confirmed_at=now, state="CONFIRMED"
                ))

            topic_id = uid()
            conn.execute(m.Topic.__table__.insert().values(
                id=topic_id, round_id=round_id, department_id=department_id,
                proposer_user_id=user_ids[4], proposer_type="LECTURER",
                current_title="De tai KLTN gia lap", max_students=3, state="APPROVED"
            ))
            conn.execute(m.TopicRequirement.__table__.insert().values(
                id=uid(), topic_id=topic_id, requirement_type="PREFERRED_GPA",
                preferred_gpa=Decimal("3.20"), enforcement="DESIRED"
            ))
            passed.append("DB-03")

            registration_id = uid()
            conn.execute(m.TopicRegistration.__table__.insert().values(
                id=registration_id, round_id=round_id, topic_id=topic_id,
                created_by=student_ids[0], state="FINALIZED", submitted_at=now,
                lecturer_decided_by=lecturer_ids[0], lecturer_decided_at=now,
                department_finalized_by=user_ids[4], department_finalized_at=now
            ))
            for i, student_id in enumerate(student_ids[:3]):
                conn.execute(m.RegistrationMember.__table__.insert().values(
                    id=uid(), registration_id=registration_id, round_id=round_id,
                    student_id=student_id, is_coordinator=(i==0), active=True
                ))
            passed.append("DB-04")

            topic2_id, registration2_id = uid(), uid()
            conn.execute(m.Topic.__table__.insert().values(
                id=topic2_id, round_id=round_id, department_id=department_id,
                proposer_user_id=user_ids[5], proposer_type="LECTURER",
                current_title="De tai gia lap thu hai", max_students=3, state="APPROVED"
            ))
            conn.execute(m.TopicRegistration.__table__.insert().values(
                id=registration2_id, round_id=round_id, topic_id=topic2_id,
                created_by=student_ids[3], state="SUBMITTED", submitted_at=now
            ))
            expect_integrity(conn, lambda: conn.execute(m.RegistrationMember.__table__.insert().values(
                id=uid(), registration_id=registration2_id, round_id=round_id,
                student_id=student_ids[0], active=True
            )), "duplicate active student/round")
            passed.append("DB-05")

            thesis_id = uid()
            conn.execute(m.Thesis.__table__.insert().values(
                id=thesis_id, round_id=round_id, topic_id=topic_id, registration_id=registration_id,
                department_id=department_id, current_title="De tai KLTN gia lap", state="ACTIVE"
            ))
            thesis_member_ids=[]
            for i, student_id in enumerate(student_ids[:3]):
                member_id=uid(); thesis_member_ids.append(member_id)
                conn.execute(m.ThesisMember.__table__.insert().values(
                    id=member_id, thesis_id=thesis_id, student_id=student_id,
                    is_coordinator=(i==0), active=True, joined_at=now
                ))
            assert conn.execute(select(m.ThesisMember.__table__.c.id).where(m.ThesisMember.__table__.c.thesis_id==thesis_id)).all().__len__()==3
            passed.append("DB-06")
            expect_integrity(conn, lambda: conn.execute(m.ThesisMember.__table__.insert().values(
                id=uid(), thesis_id=thesis_id, student_id=student_ids[0], active=True, joined_at=now
            )), "duplicate thesis member")
            passed.append("DB-07")

            advisor_assignment_id=uid()
            conn.execute(m.AdvisorAssignment.__table__.insert().values(
                id=advisor_assignment_id, thesis_id=thesis_id, lecturer_id=lecturer_ids[0],
                assignment_type="PRIMARY", assigned_by=user_ids[4], effective_from=now, state="ACTIVE"
            ))
            proposal_id=uid()
            conn.execute(m.Proposal.__table__.insert().values(id=proposal_id, thesis_id=thesis_id, current_version_no=2, state="UNDER_REVIEW"))
            reviewer_assignment_id=uid()
            conn.execute(m.ReviewerAssignment.__table__.insert().values(
                id=reviewer_assignment_id, lecturer_id=lecturer_ids[1], proposal_id=proposal_id,
                review_scope="PROPOSAL", assigned_by=user_ids[4], assigned_at=now, state="ACTIVE"
            ))
            passed.append("DB-10")

            department_position_id, faculty_position_id = uid(), uid()
            conn.execute(m.OrganizationalPosition.__table__.insert().values(
                id=department_position_id, code="DEPARTMENT_HEAD", name="Truong bo mon gia lap"
            ))
            conn.execute(m.OrganizationalPosition.__table__.insert().values(
                id=faculty_position_id, code="FACULTY_DEAN", name="Truong khoa gia lap"
            ))
            for position_id, scope in ((faculty_position_id, {"faculty_id": faculty_id}),
                                       (department_position_id, {"department_id": department_id})):
                values = dict(id=uid(), lecturer_id=lecturer_ids[0], position_id=position_id,
                              effective_from=now, state="ACTIVE", **scope)
                conn.execute(m.PositionAssignment.__table__.insert().values(**values))
                expect_integrity(conn, lambda v=values: conn.execute(
                    m.PositionAssignment.__table__.insert().values(**{**v, "id": uid(), "effective_from": now + timedelta(days=1)})
                ), "duplicate position assignment with nullable scope")
            passed.append("DB-21")

            expect_integrity(conn, lambda: conn.execute(m.ResourceAssignment.__table__.insert().values(
                id=uid(), assignment_type="ELIGIBILITY_VERIFIER", user_id=user_ids[4],
                round_id=round_id, effective_from=now + timedelta(days=1), state="ACTIVE"
            )), "duplicate round resource assignment")
            resource_thesis = dict(id=uid(), assignment_type="TEST_SCOPE", user_id=user_ids[4],
                                   thesis_id=thesis_id, effective_from=now, state="ACTIVE")
            conn.execute(m.ResourceAssignment.__table__.insert().values(**resource_thesis))
            expect_integrity(conn, lambda: conn.execute(m.ResourceAssignment.__table__.insert().values(
                **{**resource_thesis, "id": uid(), "effective_from": now + timedelta(days=1)}
            )), "duplicate thesis resource assignment")
            passed.append("DB-22")

            expect_integrity(conn, lambda: conn.execute(m.ReviewerAssignment.__table__.insert().values(
                id=uid(), lecturer_id=lecturer_ids[1], proposal_id=proposal_id,
                review_scope="PROPOSAL", assigned_by=user_ids[4], assigned_at=now, state="ACTIVE"
            )), "duplicate proposal reviewer assignment")
            reviewer_thesis = dict(id=uid(), lecturer_id=lecturer_ids[2], thesis_id=thesis_id,
                                   review_scope="THESIS", assigned_by=user_ids[4],
                                   assigned_at=now, state="ACTIVE")
            conn.execute(m.ReviewerAssignment.__table__.insert().values(**reviewer_thesis))
            expect_integrity(conn, lambda: conn.execute(m.ReviewerAssignment.__table__.insert().values(
                **{**reviewer_thesis, "id": uid()}
            )), "duplicate thesis reviewer assignment")
            passed.append("DB-23")

            file_ids=[]
            for i in range(5):
                file_id=uid(); file_ids.append(file_id)
                conn.execute(m.StoredFile.__table__.insert().values(
                    id=file_id, storage_key=f"synthetic/{uid()}", original_name=f"synthetic-{i}.pdf",
                    media_type="application/pdf", byte_size=100+i, sha256=(f"{i+1:064x}")[-64:],
                    scan_state="CLEAN", scanned_at=now
                ))
            for version in (1,2):
                conn.execute(m.ProposalVersion.__table__.insert().values(
                    id=uid(), proposal_id=proposal_id, version_no=version, stored_file_id=file_ids[version-1],
                    submitted_by=student_ids[0], submitted_at=now, content_sha256=(f"{version:064x}")[-64:]
                ))
            assert conn.execute(select(m.ProposalVersion.__table__.c.id).where(m.ProposalVersion.__table__.c.proposal_id==proposal_id)).all().__len__()==2
            passed.append("DB-09")
            conn.execute(m.SignatureConfirmation.__table__.insert().values(
                id=uid(), proposal_id=proposal_id, proposal_version_no=2,
                signature_type="DEPARTMENT_FINALIZATION", signer_user_id=user_ids[4],
                confirmed_at=now,
            ))
            expect_integrity(conn, lambda: conn.execute(
                m.SignatureConfirmation.__table__.insert().values(
                    id=uid(), proposal_id=proposal_id, proposal_version_no=99,
                    signature_type="DEAN_CONFIRMATION", signer_user_id=user_ids[5],
                    confirmed_at=now,
                )
            ), "signature referencing a nonexistent proposal version")
            passed.append("DB-26")

            milestone_id=uid()
            conn.execute(m.ProgressMilestone.__table__.insert().values(
                id=milestone_id, round_id=round_id, code="SYN-70", title="Bao cao gia lap 70%",
                version_no=1, due_at=now+timedelta(days=30), expected_ratio=Decimal("70"),
                source_type="ROUND_POLICY", state="OPEN"
            ))
            report_id=uid()
            conn.execute(m.ProgressReport.__table__.insert().values(
                id=report_id, thesis_id=thesis_id, milestone_id=milestone_id, version_no=1,
                summary="Noi dung gia lap", reported_ratio=Decimal("70"), submitted_by=student_ids[0],
                state="SUBMITTED"
            ))
            conn.execute(m.ProgressReview.__table__.insert().values(
                id=uid(), progress_report_id=report_id, reviewer_id=lecturer_ids[0],
                decision="CONFIRM", comment="Nhan xet gia lap"
            ))
            conn.execute(m.ProgressReview.__table__.insert().values(
                id=uid(), progress_report_id=report_id, reviewer_id=lecturer_ids[1],
                decision="COMMENT_ONLY", comment="Gop y cheo gia lap, khong xac nhan thay GVHD"
            ))
            expect_integrity(conn, lambda: conn.execute(m.ProgressReview.__table__.insert().values(
                id=uid(), progress_report_id=report_id, reviewer_id=lecturer_ids[2],
                decision="APPROVE_FOR_ADVISOR", comment="Gia tri khong hop le"
            )), "invalid cross-review decision")
            passed.append("DB-40")

            document_id=uid()
            conn.execute(m.Document.__table__.insert().values(
                id=document_id, thesis_id=thesis_id, document_type="FINAL_REPORT",
                title="Bao cao gia lap", visibility="PRIVATE", state="ACTIVE"
            ))
            document_version_ids=[]
            for version in (1,2):
                version_id=uid(); document_version_ids.append(version_id)
                conn.execute(m.DocumentVersion.__table__.insert().values(
                    id=version_id, document_id=document_id, version_no=version,
                    stored_file_id=file_ids[version+1], submitted_by=student_ids[0],
                    submitted_at=now, content_sha256=(f"{version+10:064x}")[-64:], state="SUBMITTED"
                ))
            assert len(conn.execute(select(m.DocumentVersion.__table__.c.id).where(m.DocumentVersion.__table__.c.document_id==document_id)).all())==2
            passed.append("DB-08")

            policy_id=uid()
            conn.execute(m.SimilarityPolicy.__table__.insert().values(
                id=policy_id, round_id=round_id, version_no=1, metric_code=None,
                threshold_value=None, decision_mode="ADVISORY", config_json={}, state="DRAFT"
            ))
            check_id=uid()
            conn.execute(m.SimilarityCheck.__table__.insert().values(
                id=check_id, document_version_id=document_version_ids[1], policy_id=policy_id,
                metric_code="LEXICAL_COVERAGE_V1", lexical_coverage_pct=Decimal("12.300"),
                semantic_candidate_score=Decimal("0.920000"), business_status="ADVISORY",
                model_version="synthetic", index_version="synthetic", corpus_snapshot="synthetic",
                state="COMPLETED", completed_at=now
            ))
            conn.execute(m.SimilarityMatch.__table__.insert().values(
                id=uid(), check_id=check_id, source_ref="synthetic-source",
                input_start=0, input_end=100, lexical_score=Decimal("0.500000"),
                semantic_score=Decimal("0.920000")
            ))
            passed.append("DB-19")
            # Corpus imported from outside this system must not fabricate an operational Thesis.
            managed_item_id = uid()
            conn.execute(m.RepositoryItem.__table__.insert().values(
                id=managed_item_id, thesis_id=thesis_id,
                published_document_version_id=document_version_ids[1],
                origin_type="MANAGED_THESIS", source_type="THESIS",
                title="Synthetic managed thesis", keywords=[], visibility="INTERNAL"
            ))
            passed.append("DB-27")
            imported = {}
            for source_type, label in (
                ("THESIS", "DB-28"), ("CAPSTONE_PROJECT", "DB-29"),
                ("TERM_PROJECT", "DB-30"), ("COURSE_PROJECT", "DB-31"),
                ("REGULATION", "DB-32"), ("FORM", "DB-33"),
            ):
                item_id = uid()
                imported[source_type] = item_id
                conn.execute(m.RepositoryItem.__table__.insert().values(
                    id=item_id,
                    origin_type="OFFICIAL_SOURCE" if source_type in ("REGULATION", "FORM") else "IMPORTED_DOCUMENT",
                    source_type=source_type, source_ref="SYN-" + source_type,
                    provenance="Synthetic validation source v1", source_version="v1",
                    title="Synthetic " + source_type, keywords=[], visibility="INTERNAL"
                ))
                passed.append(label)
            expect_integrity(conn, lambda: conn.execute(m.RepositoryItem.__table__.insert().values(
                id=uid(), origin_type="OFFICIAL_SOURCE", source_type="THESIS",
                source_ref="SYN-BAD", title="invalid", keywords=[]
            )), "invalid origin/source combination")
            expect_integrity(conn, lambda: conn.execute(m.RepositoryItem.__table__.insert().values(
                id=uid(), origin_type="IMPORTED_DOCUMENT", source_type="THESIS",
                title="missing provenance reference", keywords=[]
            )), "missing corpus source reference")
            passed.append("DB-34")
            conn.execute(m.SearchIndexMetadata.__table__.insert().values(
                id=uid(), repository_item_id=imported["THESIS"],
                index_name="synthetic-corpus", index_version="v1", state="INDEXED"
            ))
            passed.append("DB-35")
            conn.execute(m.SimilarityMatch.__table__.insert().values(
                id=uid(), check_id=check_id, source_repository_item_id=imported["THESIS"],
                source_ref="SYN-THESIS", input_start=101, input_end=150
            ))
            passed.append("DB-36")
            conn.execute(m.RepositoryItem.__table__.update().where(
                m.RepositoryItem.__table__.c.id == imported["THESIS"]
            ).values(external_source_id="SYN-SOURCE-THESIS", source_url="https://example.invalid/synthetic"))
            expect_integrity(conn, lambda: conn.execute(m.RepositoryItem.__table__.insert().values(
                id=uid(), external_source_id="SYN-SOURCE-THESIS",
                origin_type="IMPORTED_DOCUMENT", source_type="THESIS",
                source_ref="SYN-DUP", title="duplicate", keywords=[]
            )), "duplicate external source ID")
            passed.append("DB-38")
            expect_integrity(conn, lambda: conn.execute(m.RepositoryItem.__table__.insert().values(
                id=uid(), external_source_id="SYN-BAD-URL",
                origin_type="IMPORTED_DOCUMENT", source_type="THESIS",
                source_url="http://example.invalid", title="bad URL", keywords=[]
            )), "non-HTTPS corpus URL")
            passed.append("DB-39")

            council_id=uid()
            conn.execute(m.Council.__table__.insert().values(
                id=council_id, round_id=round_id, department_id=department_id,
                code="SYN-COUNCIL", decision_ref="SYN-DECISION", decision_date=date.today(), state="VALIDATED"
            ))
            roles=[("CHAIR",1),("SECRETARY",1),("REVIEWER",1),("REVIEWER",2),("MEMBER",1)]
            council_member_ids=[]
            for i,(role,slot) in enumerate(roles):
                cm=uid(); council_member_ids.append(cm)
                conn.execute(m.CouncilMember.__table__.insert().values(
                    id=cm, council_id=council_id, lecturer_id=lecturer_ids[i+1],
                    role_code=role, role_slot=slot, active=True
                ))
            session_ids=[]
            for i in range(2):
                sid=uid(); session_ids.append(sid)
                conn.execute(m.DefenseSession.__table__.insert().values(
                    id=sid, council_id=council_id, code=f"SYN-SESSION-{i+1}",
                    scheduled_at=now+timedelta(days=60+i), location="Phong gia lap", state="READY"
                ))
            conn.execute(m.SessionThesis.__table__.insert().values(id=uid(), session_id=session_ids[0], thesis_id=thesis_id, order_no=1))
            passed.append("DB-11")

            for i,cm in enumerate(council_member_ids):
                conn.execute(m.CouncilAttendance.__table__.insert().values(
                    id=uid(), session_id=session_ids[0], council_member_id=cm, present=True,
                    recorded_by=user_ids[5], recorded_at=now, note="synthetic"
                ))
            passed.append("DB-12")

            rubric_id=uid()
            conn.execute(m.RubricTemplate.__table__.insert().values(
                id=rubric_id, code="SYN-M6", name="Rubric gia lap", version_no=1,
                source_ref="SRC-MAU-06", state="ACTIVE"
            ))
            group_specs = [("1", "Hinh thuc", "2.0"), ("2", "Noi dung", "4.0"),
                           ("3", "Demo va tra loi", "4.0")]
            group_ids = {}
            for order, (code, label, maximum) in enumerate(group_specs, 1):
                group_ids[code] = uid()
                conn.execute(m.RubricCriterion.__table__.insert().values(
                    id=group_ids[code], rubric_template_id=rubric_id, code=code,
                    label=label, max_points=Decimal(maximum),
                    criterion_type="GROUP", order_no=order
                ))
            leaf_specs = [
                ("1.1", "1.0"), ("1.2", "0.5"), ("1.3", "0.5"),
                ("2.1", "0.5"), ("2.2", "0.5"), ("2.3", "1.0"),
                ("2.4", "1.0"), ("2.5", "0.5"), ("2.6", "0.5"),
                ("3.1", "1.0"), ("3.2", "2.0"), ("3.3", "1.0"),
            ]
            leaf_ids = {}
            for order, (code, maximum) in enumerate(leaf_specs, 4):
                leaf_ids[code] = uid()
                conn.execute(m.RubricCriterion.__table__.insert().values(
                    id=leaf_ids[code], rubric_template_id=rubric_id,
                    parent_id=group_ids[code[0]], code=code, label=f"Tieu chi Mau 6 {code}",
                    max_points=Decimal(maximum), criterion_type="NORMAL", order_no=order
                ))
            criterion_bonus = uid()
            conn.execute(m.RubricCriterion.__table__.insert().values(
                id=criterion_bonus, rubric_template_id=rubric_id, code="4",
                label="Diem thuong", max_points=Decimal("1.0"),
                criterion_type="BONUS", order_no=16
            ))
            for group_code, _, maximum in group_specs:
                assert sum(Decimal(points) for code, points in leaf_specs
                           if code.startswith(group_code + ".")) == Decimal(maximum)
            criterion_rows = conn.execute(select(m.RubricCriterion.__table__).where(
                m.RubricCriterion.__table__.c.rubric_template_id == rubric_id
            )).mappings().all()
            assert len(criterion_rows) == 16
            assert len([row for row in criterion_rows if row["criterion_type"] == "GROUP"]) == 3
            assert len([row for row in criterion_rows if row["criterion_type"] == "NORMAL"]) == 12
            stored = {row["code"]: row for row in criterion_rows}
            for group_code, _, maximum in group_specs:
                children = [row for row in criterion_rows if row["parent_id"] == group_ids[group_code]]
                assert sum(row["max_points"] for row in children) == Decimal(maximum)
            assert stored["4"]["criterion_type"] == "BONUS"
            assert stored["4"]["max_points"] == Decimal("1.0")
            passed.append("DB-24")
            rubric_assignment_id=uid()
            conn.execute(m.RubricAssignment.__table__.insert().values(
                id=rubric_assignment_id, rubric_template_id=rubric_id,
                session_id=session_ids[0], state="ACTIVE"
            ))
            evaluation_ids=[]
            for member_id in thesis_member_ids[:2]:
                eid=uid(); evaluation_ids.append(eid)
                conn.execute(m.Evaluation.__table__.insert().values(
                    id=eid, session_id=session_ids[0], evaluator_member_id=council_member_ids[0],
                    thesis_member_id=member_id, rubric_assignment_id=rubric_assignment_id,
                    total_points=Decimal("9.0"), bonus_points=Decimal("0.5"),
                    status="SUBMITTED", submitted_at=now
                ))
                awarded = {code: Decimal(maximum) for code, maximum in leaf_specs}
                awarded.update({"3.1": Decimal("0.5"), "3.2": Decimal("1.5"),
                                "3.3": Decimal("0.5")})
                assert sum(awarded.values()) == Decimal("8.5")
                for code, points in awarded.items():
                    conn.execute(m.EvaluationItem.__table__.insert().values(
                        id=uid(), evaluation_id=eid, criterion_id=leaf_ids[code], points=points
                    ))
                conn.execute(m.EvaluationItem.__table__.insert().values(
                    id=uid(), evaluation_id=eid, criterion_id=criterion_bonus, points=Decimal("0.5")
                ))
            passed.append("DB-13")
            expect_integrity(conn, lambda: conn.execute(m.RubricCriterion.__table__.insert().values(
                id=uid(), rubric_template_id=rubric_id, code="BONUS-INVALID",
                label="Thuong sai", max_points=Decimal("1.1"),
                criterion_type="BONUS", order_no=17
            )), "bonus criterion above one")
            expect_integrity(conn, lambda: conn.execute(m.Evaluation.__table__.insert().values(
                id=uid(), session_id=session_ids[0], evaluator_member_id=council_member_ids[1],
                thesis_member_id=thesis_member_ids[0], rubric_assignment_id=rubric_assignment_id,
                total_points=Decimal("9.0"), bonus_points=Decimal("1.1"), status="DRAFT"
            )), "bonus above one")
            expect_integrity(conn, lambda: conn.execute(m.Evaluation.__table__.insert().values(
                id=uid(), session_id=session_ids[0], evaluator_member_id=council_member_ids[1],
                thesis_member_id=thesis_member_ids[0], rubric_assignment_id=rubric_assignment_id,
                total_points=Decimal("10.1"), bonus_points=Decimal("0.5"), status="DRAFT"
            )), "total above ten")
            passed.append("DB-25")
            expect_integrity(conn, lambda: conn.execute(m.Evaluation.__table__.insert().values(
                id=uid(), session_id=session_ids[0], evaluator_member_id=council_member_ids[0],
                thesis_member_id=thesis_member_ids[0], rubric_assignment_id=rubric_assignment_id,
                total_points=Decimal("7"), bonus_points=Decimal("0"), status="SUBMITTED"
            )), "duplicate evaluation")
            passed.append("DB-14")

            conn.execute(m.FinalResult.__table__.insert().values(
                id=uid(), session_id=session_ids[0], thesis_member_id=thesis_member_ids[0],
                scorer_count=1, average_score=Decimal("9.00"), bonus_average=Decimal("0.50"),
                final_score=Decimal("9.0"), calculation_version=1, calculated_at=now
            ))
            passed.append("DB-15")

            minute_id,minute_version_id=uid(),uid()
            conn.execute(m.CouncilMinute.__table__.insert().values(
                id=minute_id, session_id=session_ids[0], minute_no="SYN-MINUTE",
                current_version_no=1, state="SIGNED", printed_at=now, signed_at=now
            ))
            conn.execute(m.MinuteVersion.__table__.insert().values(
                id=minute_version_id, minute_id=minute_id, version_no=1,
                stored_file_id=file_ids[4], generated_by=user_ids[5], state="SIGNED"
            ))
            conn.execute(m.MinuteSignature.__table__.insert().values(
                id=uid(), minute_version_id=minute_version_id,
                signer_member_id=council_member_ids[0], signed_at=now, signature_ref="SYN-SIGN"
            ))
            conn.execute(m.MinuteSignature.__table__.insert().values(
                id=uid(), minute_version_id=minute_version_id,
                signer_member_id=council_member_ids[1], signed_at=now, signature_ref="SYN-SECRETARY-SIGN"
            ))
            assert conn.execute(select(m.MinuteSignature.__table__.c.id).where(
                m.MinuteSignature.__table__.c.minute_version_id == minute_version_id
            )).fetchall().__len__() == 2
            passed.append("DB-37")
            passed.append("DB-16")

            expect_integrity(conn, lambda: conn.execute(m.StudentProfile.__table__.insert().values(
                id=uid(), user_id=uid(), student_code="SYN-BAD-FK",
                department_id=department_id, display_name="Synthetic invalid"
            )), "invalid FK")
            passed.append("DB-17")

            expect_integrity(conn, lambda: conn.execute(
                m.UserAccount.__table__.delete().where(m.UserAccount.__table__.c.id==user_ids[0])
            ), "delete referenced account")
            passed.append("DB-18")

            expected={f"DB-{i:02d}" for i in range(1,20)} | {f"DB-{i:02d}" for i in range(21,42)}
            assert set(passed)==expected, sorted(expected-set(passed))
        except Exception as exc:
            print("FAIL "+type(exc).__name__+": "+str(exc))
            return 1
        finally:
            outer.rollback()

    try:
        with engine.connect() as verification_connection:
            remaining = verification_connection.execute(
                select(m.StudentProfile.__table__.c.id).where(
                    m.StudentProfile.__table__.c.student_code == "SYN-SV-1"
                )
            ).first()
            assert remaining is None, "synthetic validation data persisted after rollback"
        passed.append("DB-20")
        for item in sorted(passed):
            print("PASS "+item)
        print("PASS ALL database validation cases")
        return 0
    except Exception as exc:
        print("FAIL "+type(exc).__name__+": "+str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
