from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from backend.api.dependencies import current_user
from backend.api.defense_schemas import AttendanceInput, BonusInput, CouncilInput, MarkInput, MinutesInput, SlotInput
from backend.api.evaluation import transaction
from backend.api.evaluation_schemas import Reason
from backend.services import defense, defense_export
from backend.api.defense_schemas import CouncilAttendance, ReopenInput

router = APIRouter(prefix="/api/v1/defense", tags=["Hội đồng và bảo vệ"])


@router.get("")
def workspace(user=Depends(current_user),session=Depends(transaction)):
    return defense.workspace(session,user)


@router.post("/councils",status_code=201)
def council(data:CouncilInput,user=Depends(current_user),session=Depends(transaction)):
    return defense.manage_council(session,user,data)


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
def slot_form(identifier:UUID,form:Literal["6","9"],request:Request,student_id:UUID|None=None,lecturer_id:UUID|None=None,
              user=Depends(current_user),session=Depends(transaction)):
    return defense_export.export_slot(session,user,identifier,int(form),str(request.base_url),student_id,lecturer_id)


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
