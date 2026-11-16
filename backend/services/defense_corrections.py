"""Propose and independently approve corrections without unlocking results."""
from copy import deepcopy
from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace
from fastapi import HTTPException
from sqlalchemy import select, func
from backend.db.models import entities as m
from backend.services import defense, workflow_notices
from backend.services.registration import _is_department_head, row_version
from backend.services.theses import audit


def access(session,user,identifier,write=False):
    slot,council,member,own,manager=defense.load_slot(session,user,identifier,write=write)
    if own or not (manager or member and member['role'] in {'CHAIR','SECRETARY'}):
        raise HTTPException(403,'Chỉ chủ tịch, thư ký hoặc người quản lý được xử lý đính chính')
    return slot,council


def workspace(session,user,identifier):
    slot,council=access(session,user,identifier)
    lecturer=defense.lecturer_for(session,user)
    head=bool(lecturer and _is_department_head(session,lecturer.id,council.department_id))
    rows=session.scalars(select(m.DefenseCorrection).where(m.DefenseCorrection.slot_id==slot.id)
        .order_by((m.DefenseCorrection.state=='PENDING').desc(),m.DefenseCorrection.created_at.desc(),m.DefenseCorrection.id.desc())).all()
    return {'can_approve':head,'missing':defense.minutes_blockers(slot), 'items':[
        {'id':r.id,'version':r.row_version,'state':r.state,'reason':r.reason,'reference':r.reference,
         'proposal':r.proposal,'before':r.before,'requested_by':str(r.requested_by),
         'source_version':r.source_version,'requested_by_name':workflow_notices.actor_name(session,r.requested_by),
         'decided_by_name':workflow_notices.actor_name(session,r.decided_by) if r.decided_by else None,'decided_at':r.decided_at,
         'created_at':r.created_at,'decision_note':r.decision_note,'can_decide':head and r.requested_by!=user.id,
         'can_cancel':r.requested_by==user.id} for r in rows]}


def validate(slot,council,data):
    if data.kind=='BALLOT':
        key=str(data.student_id); person=str(data.lecturer_id)
        if slot.attendance.get(key,{}).get('status')!='PRESENT' or person not in slot.attendance.get('_council',{}).get('present_ids',[]):
            raise HTTPException(422,'Chỉ đính chính phiếu của SV và giảng viên có mặt')
        if not slot.marks.get(key,{}).get(person):
            raise HTTPException(422,'Không có phiếu gốc để đính chính')
        if len(data.scores)!=12:
            raise HTTPException(422,'Nhập đủ 12 tiêu chí')
        for value,(code,_,maximum) in zip(data.scores,defense.CRITERIA):
            if not value.is_finite() or not Decimal(0)<=value<=Decimal(maximum) or value!=value.quantize(Decimal('.01')):
                raise HTTPException(422,f'Điểm tiêu chí {code} không hợp lệ')
    elif data.minutes is None:
        raise HTTPException(422,'Nhập nội dung biên bản đề nghị đính chính')
    else:
        students={r['id'] for r in slot.roster}
        if not set(map(str,data.minutes.classifications))<=students:
            raise HTTPException(422,'Xếp loại chỉ dành cho SV trong phiên')
        if data.minutes.no_recommendations and data.minutes.recommendations:
            raise HTTPException(422,'Không vừa nhập kiến nghị vừa xác nhận không có kiến nghị')
        present=set(slot.attendance.get('_council',{}).get('present_ids',[]))
        if any(str(k) not in students or not set(map(str,v))<=present for k,v in data.minutes.oral_comments.items()):
            raise HTTPException(422,'Ý kiến chỉ thuộc SV trong phiên và giảng viên hiện diện')
        blockers=defense.minutes_blockers(SimpleNamespace(minutes=data.minutes.model_dump(mode='json'),roster=slot.roster,attendance=slot.attendance))
        if blockers:raise HTTPException(422,'. '.join(blockers))


def recalculated_results(slot,council,student):
    previous=deepcopy(defense.results(slot,council))
    frozen=slot.finalized_at
    try:
        slot.finalized_at=None
        corrected=defense.results(slot,council)[student]
    finally:
        slot.finalized_at=frozen
    return {**previous,student:corrected}


def propose(session,user,identifier,expected,data):
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    slot,council=access(session,user,identifier,True)
    row_version(expected,slot.row_version)
    if not slot.finalized_at or not council.closed_at:
        raise HTTPException(409,'Chỉ lập đính chính cho hồ sơ đã khóa điểm hội đồng')
    if session.scalar(select(m.DefenseCorrection.id).where(m.DefenseCorrection.slot_id==slot.id,m.DefenseCorrection.state=='PENDING')):
        raise HTTPException(409,'Còn đề nghị chờ xử lý; hãy duyệt, từ chối hoặc hủy trước')
    validate(slot,council,data)
    if data.kind=='BALLOT':
        old=slot.marks[str(data.student_id)][str(data.lecturer_id)]
        if [Decimal(v) for v in old['scores']]==data.scores and old.get('note','')==data.note:
            raise HTTPException(422,'Phiếu chưa có thay đổi so với bản đang khóa')
    row=m.DefenseCorrection(id=uuid4(),slot_id=slot.id,requested_by=user.id,source_version=slot.row_version,
        state='PENDING',proposal=data.model_dump(mode='json'),before={'marks':deepcopy(slot.marks),'minutes':deepcopy(slot.minutes)},
        reason=data.reason,reference=data.reference)
    session.add(row)
    audit(session,user,'DEFENSE_CORRECTION_REQUESTED','defense_slot',slot.id,data.reason,source_reference=data.reference)
    defense.notify(session,user,slot,council,'DEFENSE_CORRECTION_REQUESTED','Có đề nghị đính chính sau khóa; TBM khác người lập cần đối chiếu và quyết định')
    session.commit()


def decide(session,user,identifier,expected,data):
    from backend.api.defense_schemas import CorrectionInput
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    row=session.scalar(select(m.DefenseCorrection).where(m.DefenseCorrection.id==identifier).with_for_update())
    if not row:raise HTTPException(404,'Không tìm thấy đề nghị')
    slot,council=access(session,user,row.slot_id,True)
    row_version(expected,row.row_version)
    if row.state!='PENDING':raise HTTPException(409,'Đề nghị đã được xử lý')
    if data.decision=='CANCELLED':
        if user.id!=row.requested_by:raise HTTPException(403,'Chỉ người lập được hủy đề nghị')
    else:
        lecturer=defense.lecturer_for(session,user)
        if not lecturer or not _is_department_head(session,lecturer.id,council.department_id) or user.id==row.requested_by:
            raise HTTPException(403,'TBM duyệt trong bộ môn; người lập không tự duyệt đề nghị')
    if data.decision=='APPROVED':
        if not slot.finalized_at or not council.closed_at:
            raise HTTPException(409,'Hồ sơ không còn ở trạng thái khóa cần đính chính')
        if slot.row_version!=row.source_version:raise HTTPException(409,'Nguồn đã đổi; từ chối đề nghị cũ và lập lại trên dữ liệu mới')
        proposal=CorrectionInput.model_validate(row.proposal)
        validate(slot,council,proposal)
        if proposal.kind=='BALLOT':
            if defense.invalid_bonus(session,slot):
                raise HTTPException(409,'Căn cứ điểm thưởng đã đổi; cần đối chiếu trước khi duyệt đính chính điểm')
            student,person=str(proposal.student_id),str(proposal.lecturer_id)
            old=slot.marks[student][person]
            slot.marks={**slot.marks,student:{**slot.marks[student],person:{**old,
                'scores':[str(v) for v in proposal.scores],'note':proposal.note,'revision':old.get('revision',0)+1,
                'recorded_at':defense.now().isoformat(),'recorded_by':str(user.id),'correction_id':str(row.id)}}}
            slot.minutes={**slot.minutes,'results_snapshot':recalculated_results(slot,council,student)}
        else:
            slot.minutes={**slot.minutes,**proposal.minutes.model_dump(mode='json')}
        slot.row_version+=1
    row.state,row.decided_by,row.decided_at,row.decision_note=data.decision,user.id,defense.now(),data.reason
    row.row_version+=1
    audit(session,user,'DEFENSE_CORRECTION_'+data.decision,'defense_slot',slot.id,data.reason,source_reference=row.reference)
    label={'APPROVED':'Đã duyệt','REJECTED':'Không duyệt','CANCELLED':'Đã hủy'}[data.decision]
    defense.notify(session,user,slot,council,'DEFENSE_CORRECTION_'+data.decision,
        f'{label} đề nghị đính chính · Căn cứ {row.reference} · Phiên bản hồ sơ v{slot.row_version}. Đối chiếu kết quả và bản in hiện hành')
    session.commit()
