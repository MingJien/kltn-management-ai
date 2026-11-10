from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from backend.api.dependencies import current_user
from backend.api.defense_schemas import AttendanceInput, BonusInput, CouncilInput, MarkInput, MinutesInput, SlotInput
from backend.api.evaluation import transaction
from backend.api.evaluation_schemas import Reason
from backend.services import defense, defense_export
from backend.api.defense_schemas import CouncilAttendance, ReopenInput
from backend.api.defense_schemas import AbsenceDecision

router = APIRouter(prefix="/api/v1/defense", tags=["Hội đồng và bảo vệ"])


@router.get("")
def workspace(user=Depends(current_user),session=Depends(transaction)):
    return defense.workspace(session,user)


@router.post("/councils",status_code=201)
def council(data:CouncilInput,user=Depends(current_user),session=Depends(transaction)):
    return defense.manage_council(session,user,data)


@router.put("/councils/{identifier}")
def update_council(identifier:UUID,data:CouncilInput,signature:str=Header(alias="If-Match"),user=Depends(current_user),session=Depends(transaction)):
    return defense.manage_council(session,user,data,identifier,signature)


@router.post("/councils/{identifier}/close",status_code=204)
def close(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    defense.close_council(session,user,identifier)


@router.post("/slots",status_code=201)
def schedule(data:SlotInput,user=Depends(current_user),session=Depends(transaction)):
    return defense.schedule(session,user,data)


@router.put("/slots/{identifier}")
def reschedule(identifier:UUID,data:SlotInput,version:int=Header(alias="If-Match",ge=1),
               user=Depends(current_user),session=Depends(transaction)):
    return defense.schedule(session,user,data,identifier,version)


@router.post("/slots/{identifier}/cancel",status_code=204)
def cancel(identifier:UUID,data:Reason,version:int=Header(alias="If-Match",ge=1),
           user=Depends(current_user),session=Depends(transaction)):
    defense.cancel_schedule(session,user,identifier,version,data.reason)


@router.put("/slots/{identifier}/marks",status_code=204)
def mark(identifier:UUID,data:MarkInput,version:int=Header(alias="If-Match",ge=1),
         user=Depends(current_user),session=Depends(transaction)):
    defense.save_marks(session,user,identifier,version,data)


@router.put("/slots/{identifier}/attendance/{member_id}",status_code=204)
def attendance(identifier:UUID,member_id:UUID,data:AttendanceInput,version:int=Header(alias="If-Match",ge=1),
               user=Depends(current_user),session=Depends(transaction)):
    defense.save_attendance(session,user,identifier,version,member_id,data)


@router.put("/slots/{identifier}/bonus/{member_id}",status_code=204)
def bonus(identifier:UUID,member_id:UUID,data:BonusInput,version:int=Header(alias="If-Match",ge=1),
          user=Depends(current_user),session=Depends(transaction)):
    defense.save_bonus(session,user,identifier,version,member_id,data)


@router.put("/slots/{identifier}/minutes",status_code=204)
def minutes(identifier:UUID,data:MinutesInput,version:int=Header(alias="If-Match",ge=1),
            user=Depends(current_user),session=Depends(transaction)):
    defense.save_minutes(session,user,identifier,version,data)


@router.post("/slots/{identifier}/finalize",status_code=204)
def finalize(identifier:UUID,version:int=Header(alias="If-Match",ge=1),
             user=Depends(current_user),session=Depends(transaction)):
    defense.finalize(session,user,identifier,version)


@router.get("/slots/{identifier}/forms/{form}")
def slot_form(identifier:UUID,form:Literal["6","9"],request:Request,student_id:UUID|None=None,lecturer_id:UUID|None=None,blank:bool=False,
              user=Depends(current_user),session=Depends(transaction)):
    return defense_export.export_slot(session,user,identifier,int(form),str(request.base_url),student_id,lecturer_id,blank=blank)


@router.get("/slots/{identifier}/report")
def report(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    return defense.report_download(session,user,identifier)


@router.get("/slots/{identifier}/evidence/{version_id}")
def bonus_evidence(identifier:UUID,version_id:UUID,user=Depends(current_user),session=Depends(transaction)):
    from backend.db.models import entities as m
    from backend.services import documents
    slot,_,_,_,_=defense.load_slot(session,user,identifier)
    if str(version_id) not in {str(row["id"]) for row in defense.evidence_options(session,slot.thesis_id)}:
        from fastapi import HTTPException
        raise HTTPException(404,"Không tìm thấy minh chứng trong hồ sơ này")
    return documents.stored_download(session,session.get(m.DocumentVersion,version_id))


@router.post("/slots/{identifier}/marks/{student}/{lecturer}/void",status_code=204)
def void_mark(identifier:UUID,student:UUID,lecturer:UUID,data:Reason,version:int=Header(alias="If-Match",ge=1),
              user=Depends(current_user),session=Depends(transaction)):
    defense.clear_mark(session,user,identifier,version,student,lecturer,data.reason)


@router.post("/slots/{identifier}/absence/{student}",status_code=204)
def absence_decision(identifier:UUID,student:UUID,data:AbsenceDecision,user=Depends(current_user),session=Depends(transaction)):
    defense.decide_absence(session,user,identifier,student,data)


@router.put("/slots/{identifier}/council-attendance",status_code=204)
def council_attendance(identifier:UUID,data:CouncilAttendance,version:int=Header(alias="If-Match",ge=1),
                       user=Depends(current_user),session=Depends(transaction)):
    defense.save_council_attendance(session,user,identifier,version,data)


@router.post("/slots/{identifier}/reopen-unsigned",status_code=204)
def reopen_unsigned(identifier:UUID,data:ReopenInput,version:int=Header(alias="If-Match",ge=1),
                    user=Depends(current_user),session=Depends(transaction)):
    defense.reopen_unsigned(session,user,identifier,version,data)


@router.get("/councils/{identifier}/forms/{form}")
def council_form(identifier:UUID,form:Literal["10","11"],request:Request,user=Depends(current_user),session=Depends(transaction)):
    return defense_export.export_council(session,user,identifier,int(form),str(request.base_url))
