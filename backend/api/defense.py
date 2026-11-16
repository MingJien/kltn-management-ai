from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query
from backend.services.defense_templates import LineBreaks, PrintLayout
from pydantic import TypeAdapter, ValidationError

from backend.api.dependencies import current_user
from backend.api.defense_schemas import AttendanceInput, BonusInput, CouncilInput, MarkInput, MinutesInput, SlotInput
from backend.api.evaluation import transaction
from backend.api.evaluation_schemas import Reason
from backend.services import defense, defense_export, defense_register
from backend.api.defense_schemas import AcademicProfileInput, CouncilAttendance, ReopenInput
from backend.api.defense_schemas import AbsenceDecision

router = APIRouter(prefix="/api/v1/defense", tags=["Hội đồng và bảo vệ"])


def parse_line_breaks(value):
    try:return TypeAdapter(LineBreaks).validate_json(value) if value else {}
    except ValidationError as exc:
        raise HTTPException(422,"Dữ liệu ngắt dòng không hợp lệ. Chỉ nhận vị trí ngắt dòng, không nhận nội dung thay thế") from exc


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


@router.put("/slots/{identifier}/academic-profile/{member_id}",status_code=204)
def academic_profile(identifier:UUID,member_id:UUID,data:AcademicProfileInput,version:int=Header(alias="If-Match",ge=1),
                     user=Depends(current_user),session=Depends(transaction)):
    defense.correct_academic_profile(session,user,identifier,version,member_id,data)


@router.post("/slots/{identifier}/finalize",status_code=204)
def finalize(identifier:UUID,version:int=Header(alias="If-Match",ge=1),
             user=Depends(current_user),session=Depends(transaction)):
    defense.finalize(session,user,identifier,version)


@router.get("/slots/{identifier}/forms/{form}")
@router.post("/slots/{identifier}/forms/{form}")
def slot_form(identifier:UUID,form:Literal["6","9"],request:Request,student_id:UUID|None=None,lecturer_id:UUID|None=None,blank:bool=False,
              font_size: Annotated[int|None,Query(ge=11,le=14)]=None,
              line_spacing: Annotated[float|None,Query(ge=1,le=1.5)]=None,
              paragraph_space: Annotated[int|None,Query(ge=0,le=8)]=None,break_recommendations:bool=False,preview_sheet:bool=False,
              narrative_bold:bool|None=None,narrative_italic:bool|None=None,
              line_breaks:Annotated[str|None,Query(max_length=6000)]=None,layout_fields:bool=False,preview_revision:bool=False,expected_revision:str|None=None,
              user=Depends(current_user),session=Depends(transaction)):
    if request.method == "POST" and preview_sheet:
        raise HTTPException(422, "Dùng bản xem trước để kiểm tra cách trình bày")
    result = defense_export.export_slot(session,user,identifier,int(form),str(request.base_url),student_id,lecturer_id,blank=blank,layout_fields=layout_fields,
        record=request.method == "POST",expected_revision=expected_revision,
        layout=PrintLayout(font_size=font_size,line_spacing=line_spacing,paragraph_space=paragraph_space,break_recommendations=break_recommendations,
            narrative_bold=narrative_bold,narrative_italic=narrative_italic,line_breaks=parse_line_breaks(line_breaks)))
    if preview_revision:
        return {'revision':result.headers.get('X-Preview-Revision')}
    return defense_export.preview_sheet(result) if preview_sheet and form=="6" and not layout_fields else result


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


@router.get("/round-register")
def register_rounds(user=Depends(current_user),session=Depends(transaction)):
    return [{"id": round_.id, "code": round_.code} for round_ in defense_register.rounds_for_export(session,user)]


@router.get("/round-register/{identifier}")
def register_workspace(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    return defense_register.workspace(session,user,identifier)


@router.get("/round-register/{identifier}/forms/{form}")
@router.post("/round-register/{identifier}/forms/{form}")
def round_form(identifier:UUID,form:Literal["10","11"],request:Request,
                 font_size: Annotated[int|None,Query(ge=11,le=14)]=None,
                 line_spacing: Annotated[float|None,Query(ge=1,le=1.5)]=None,
                 paragraph_space: Annotated[int|None,Query(ge=0,le=8)]=None,break_recommendations:bool=False,preview_sheet:bool=False,
                 course_code: Annotated[str|None,Query(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")]=None,preview_revision:bool=False,expected_revision:str|None=None,
                 user=Depends(current_user),session=Depends(transaction)):
    if request.method == "POST" and preview_sheet:
        raise HTTPException(422, "Dùng bản xem trước để kiểm tra cách trình bày")
    result = defense_export.export_round(session,user,identifier,int(form),str(request.base_url),
        course_code=course_code.upper() if course_code else None,record=request.method == "POST",expected_revision=expected_revision,
        layout=PrintLayout(font_size=font_size,line_spacing=line_spacing,paragraph_space=paragraph_space,break_recommendations=break_recommendations))
    if preview_revision:
        return {'revision':result.headers.get('X-Preview-Revision')}
    return defense_export.preview_sheet(result) if preview_sheet and form=="11" else result


@router.get("/round-register/{identifier}/prints")
def round_prints(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    return defense_export.print_history(session,user,round_id=identifier)


@router.get("/slots/{identifier}/prints")
def slot_prints(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    return defense_export.print_history(session,user,slot_id=identifier)


@router.get("/prints/{identifier}")
def recorded_print(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    return defense_export.download_print(session,user,identifier)


from backend.api.defense_schemas import CorrectionInput, CorrectionDecision
from backend.services import defense_corrections


@router.get('/slots/{identifier}/corrections')
def corrections(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    return defense_corrections.workspace(session,user,identifier)


@router.post('/slots/{identifier}/corrections',status_code=204)
def propose_correction(identifier:UUID,data:CorrectionInput,version:int=Header(alias='If-Match',ge=1),user=Depends(current_user),session=Depends(transaction)):
    defense_corrections.propose(session,user,identifier,version,data)


@router.post('/corrections/{identifier}/decision',status_code=204)
def decide_correction(identifier:UUID,data:CorrectionDecision,version:int=Header(alias='If-Match',ge=1),user=Depends(current_user),session=Depends(transaction)):
    defense_corrections.decide(session,user,identifier,version,data)
