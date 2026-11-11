"""Immutable submissions, scoped academic decisions and per-student approved bonus."""
from decimal import Decimal
from uuid import UUID, uuid4
from fastapi import HTTPException
from sqlalchemy import select
from backend.db.models import entities as m
from backend.services import workflow_notices as notices
from backend.services.theses import thesis_access, rights, primary_advisor, now, audit
from backend.services.registration import row_version


def rows(session, thesis_id):
    return session.scalars(select(m.PublicationClaim).where(m.PublicationClaim.thesis_id == thesis_id)
        .order_by(m.PublicationClaim.created_at.desc())).all()


def output(item):
    return dict(id=str(item.id), state=item.state, row_version=item.row_version,
        evidence_version_id=str(item.evidence_version_id), details=item.details, history=item.history)


def listing(session, user, thesis_id):
    thesis = thesis_access(session, user, thesis_id)
    actions = rights(session, user, thesis)
    return {"items": [output(r) for r in rows(session, thesis_id)],
        "can_submit": "document:submit" in actions and open_for_edit(session, thesis),
        "can_review": "evaluation:advisor" in actions and open_for_edit(session, thesis),
        "can_approve": "evaluation:manage" in actions and open_for_edit(session, thesis)}


def open_for_edit(session, thesis, *, lock=False):
    round_ = session.get(m.ThesisRound, thesis.round_id)
    if thesis.state not in {"ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED", "READY_FOR_DEFENSE"} or round_.state == "ARCHIVED":
        return False
    query = select(m.DefenseSlot).where(m.DefenseSlot.thesis_id == thesis.id).order_by(m.DefenseSlot.id)
    slots = session.scalars(query.with_for_update() if lock else query).all()
    return not any(slot.finalized_at or slot.marks for slot in slots)


def evidence(session, thesis_id, version_id):
    version = session.get(m.DocumentVersion, version_id)
    doc = session.get(m.Document, version.document_id) if version else None
    file = session.get(m.StoredFile, version.stored_file_id) if version else None
    if not doc or doc.thesis_id != thesis_id or doc.document_type != "SUPPORTING" or doc.state != "ACTIVE" or not file or file.scan_state != "CLEAN":
        raise HTTPException(422, "Chọn minh chứng thuộc hồ sơ này, đã quét an toàn và chưa rút")
    return version


def record(session, user, thesis, item, reason):
    item.history = [*item.history, {"state": item.state, "reason": reason, "actor": notices.actor_name(session, user.id),
        "actor_id": str(user.id), "at": now().isoformat()}]
    advisor = primary_advisor(session, thesis.id)
    recipients = notices.department_heads(session, thesis.department_id) | {item.submitted_by}
    if advisor:
        recipients.add(session.get(m.LecturerProfile, advisor.lecturer_id).user_id)
    recipients.update(session.scalars(select(m.StudentProfile.user_id).where(m.StudentProfile.id.in_(
        [UUID(s) for s in item.details["student_ids"]]))))
    labels = {"SUBMITTED": "chờ GVHD kiểm tra", "ADVISOR_CONFIRMED": "GVHD đã xác nhận, chờ TBM duyệt",
        "REVISION_REQUIRED": "cần bổ sung, xem nhận xét và gửi hồ sơ mới", "APPROVED": "TBM đã duyệt mức thưởng", "REJECTED": "không được duyệt"}
    notices.emit(session, user.id, recipients, "PUBLICATION_" + item.state, "thesis", thesis.id,
        f"Minh chứng điểm thưởng: {labels[item.state]}. {reason}", "/theses/" + str(thesis.id) + "?section=submissions&kind=SUPPORTING")
    audit(session, user, "PUBLICATION_" + item.state, "publication_claim", item.id, reason)


def submit(session, user, thesis_id, data):
    thesis = thesis_access(session, user, thesis_id, action="document:submit", lock=True)
    if user.base_role != "STUDENT" or not open_for_edit(session, thesis, lock=True):
        raise HTTPException(409, "Chỉ SV đang thực hiện được gửi minh chứng trước khi Hội đồng chấm điểm")
    selected = {str(s) for s in data.student_ids}
    active = {str(s) for s in session.scalars(select(m.ThesisMember.student_id).where(m.ThesisMember.thesis_id == thesis.id, m.ThesisMember.active.is_(True)))}
    if len(selected) != len(data.student_ids) or not selected <= active:
        raise HTTPException(422, "Chỉ chọn các thành viên đang thực hiện đề tài, mỗi SV một lần")
    for old in rows(session, thesis.id):
        if old.state in {"SUBMITTED", "ADVISOR_CONFIRMED", "APPROVED"} and selected.intersection(old.details["student_ids"]):
            raise HTTPException(409, "SV đã có hồ sơ đang chờ xử lý hoặc đã được duyệt; không nộp trùng")
    evidence(session, thesis.id, data.evidence_version_id)
    item = m.PublicationClaim(id=uuid4(), thesis_id=thesis.id, submitted_by=user.id,
        evidence_version_id=data.evidence_version_id, state="SUBMITTED", details=data.model_dump(mode="json", exclude={"evidence_version_id"}), history=[])
    session.add(item)
    record(session, user, thesis, item, "SV gửi thông tin công bố và đóng góp của các thành viên")
    session.commit()
    return output(item)


def decide(session, user, thesis_id, identifier, expected, data):
    thesis = thesis_access(session, user, thesis_id, lock=True)
    item = session.get(m.PublicationClaim, identifier)
    if not item or item.thesis_id != thesis.id:
        raise HTTPException(404, "Không tìm thấy hồ sơ minh chứng")
    row_version(expected, item.row_version)
    if not open_for_edit(session, thesis, lock=True):
        raise HTTPException(409, "Đã có phiếu chấm hoặc kết quả, không được thay đổi căn cứ điểm thưởng")
    actions = rights(session, user, thesis)
    advisor_stage = item.state == "SUBMITTED" and "evaluation:advisor" in actions
    head_stage = item.state == "ADVISOR_CONFIRMED" and "evaluation:manage" in actions
    if not advisor_stage and not head_stage:
        raise HTTPException(403, "Cần GVHD xác nhận trước, sau đó TBM duyệt đúng hồ sơ đang chờ")
    allowed = {"CONFIRM", "REVISION_REQUIRED"} if advisor_stage else {"APPROVE", "REJECT", "REVISION_REQUIRED"}
    if data.outcome not in allowed:
        raise HTTPException(422, "Quyết định không phù hợp bước xử lý")
    if data.outcome != "APPROVE" and data.points:
        raise HTTPException(422, "Chỉ TBM nhập mức thưởng khi duyệt")
    if data.outcome in {"CONFIRM", "APPROVE"}:
        evidence(session, thesis.id, item.evidence_version_id)
    active = {str(s) for s in session.scalars(select(m.ThesisMember.student_id).where(m.ThesisMember.thesis_id == thesis.id, m.ThesisMember.active.is_(True)))}
    if data.outcome in {"CONFIRM", "APPROVE"} and not set(item.details["student_ids"]) <= active:
        raise HTTPException(409, "Thành viên đã thay đổi; cần nộp lại hồ sơ theo nhóm hiện tại")
    advisor = primary_advisor(session, thesis.id)
    if data.outcome == "CONFIRM":
        item.details = {**item.details, "advisor_assignment_id": str(advisor.id)}
    if data.outcome == "APPROVE":
        if not advisor or item.details.get("advisor_assignment_id") != str(advisor.id):
            raise HTTPException(409, "GVHD đã thay đổi; yêu cầu bổ sung để GVHD hiện tại kiểm tra lại")
        points = {str(s): p for s, p in data.points.items()}
        if set(points) != set(item.details["student_ids"]) or any(not p.is_finite() or p < 0 or p > 1 or p != p.quantize(Decimal(".01")) for p in points.values()):
            raise HTTPException(422, "Nhập mức 0–1 điểm, tối đa hai chữ số thập phân cho từng SV được đề nghị")
        item.details = {**item.details, "points": {s: str(p) for s, p in points.items()}, "decision_reference": data.reason}
    item.state = {"CONFIRM": "ADVISOR_CONFIRMED", "APPROVE": "APPROVED", "REJECT": "REJECTED"}.get(data.outcome, data.outcome)
    item.row_version += 1
    record(session, user, thesis, item, data.reason)
    if item.state == "APPROVED":
        for slot in session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.thesis_id == thesis.id).with_for_update()):
            sync_slot(session, slot)
    session.commit()
    return output(item)


def approved_for(session, thesis_id, student_id):
    for item in rows(session, thesis_id):
        if item.state == "APPROVED" and str(student_id) in item.details.get("points", {}):
            evidence(session, thesis_id, item.evidence_version_id)
            return {"bonus": item.details["points"][str(student_id)], "bonus_reference": item.details["decision_reference"],
                "bonus_evidence_version_id": str(item.evidence_version_id), "bonus_claim_id": str(item.id),
                "bonus_approved_by": item.history[-1]["actor_id"], "bonus_approved_at": item.history[-1]["at"]}
    return {"bonus": "0"}


def sync_slot(session, slot):
    slot.attendance = {**slot.attendance, **{r["id"]: {**slot.attendance.get(r["id"], {}),
        **approved_for(session, slot.thesis_id, r["student_id"])} for r in slot.roster}}
    slot.row_version += 1
