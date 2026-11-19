from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import Field

from backend.api.defense_schemas import AcademicProfileInput, Input
from backend.api.evaluation_schemas import Reason
from backend.api.dependencies import current_user
from backend.api.evaluation import transaction
from backend.services import nv6_reporting, thesis_archive


router = APIRouter(prefix="/api/v1", tags=["Báo cáo và lưu trữ KLTN"])


class ArchiveDecision(Input):
    decision: Literal["ACCEPTED", "RETURNED"]
    reason: str = Field(min_length=5, max_length=2000)


@router.get("/nv6-reports/scopes")
def scopes(user=Depends(current_user),session=Depends(transaction)):
    return nv6_reporting.scopes(session,user)


@router.get("/nv6-reports/{round_id}")
def report(round_id: UUID, department_id: UUID | None = None, refresh: bool = False,
           user=Depends(current_user), session=Depends(transaction)):
    return nv6_reporting.workspace(session, user, round_id, department_id, refresh=refresh)


@router.get("/nv6-reports/{round_id}/students/{member_id}")
def academic_profile(round_id:UUID,member_id:UUID,user=Depends(current_user),session=Depends(transaction)):
    return nv6_reporting.profile_for_check(session,user,round_id,member_id)


@router.put("/nv6-reports/{round_id}/students/{member_id}",status_code=204)
def correct_profile(round_id:UUID,member_id:UUID,data:AcademicProfileInput,signature:str=Header(alias="If-Match"),
                    user=Depends(current_user),session=Depends(transaction)):
    nv6_reporting.correct_profile(session,user,round_id,member_id,signature,data)


@router.get("/thesis-archive")
def archive(round_id:UUID|None=None,user=Depends(current_user),session=Depends(transaction)):
    return thesis_archive.workspace(session,user,round_id=round_id)


@router.get("/thesis-archive/search")
def archive_search(mode: Literal["catalog", "work"] = "catalog",
                   state: Literal["SUBMITTED", "RETURNED", "REOPENED", "ACCEPTED", "EMPTY"] | None = None,
                   q: Annotated[str, Query(max_length=150)] = "", round_id: UUID | None = None,
                   department_id: UUID | None = None, page: Annotated[int, Query(ge=1)] = 1,
                   limit: Annotated[int, Query(ge=1, le=50)] = 20,
                   user=Depends(current_user), session=Depends(transaction)):
    return thesis_archive.catalog_query(session, user, mode=mode, state=state, search=q.strip(),
        round_id=round_id, department_id=department_id, page=page, limit=limit)


@router.get("/thesis-archive/theses/{identifier}")
def archive_detail(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    return thesis_archive.details(session,user,identifier)


@router.post("/thesis-archive/theses/{identifier}",status_code=201)
async def submit_archive(identifier:UUID,request:Request,user=Depends(current_user),session=Depends(transaction)):
    return await thesis_archive.submit(session,user,identifier,request)


@router.post("/thesis-archive/versions/{identifier}/decision",status_code=204)
def archive_decision(identifier:UUID,data:ArchiveDecision,version:int=Header(alias="If-Match",ge=1),
                     user=Depends(current_user),session=Depends(transaction)):
    thesis_archive.decide(session,user,identifier,version,data.decision,data.reason)


@router.post("/thesis-archive/versions/{identifier}/reopen", status_code=204)
def reopen_archive_version(identifier: UUID, data: Reason, version: int = Header(alias="If-Match", ge=1),
                           user=Depends(current_user), session=Depends(transaction)):
    thesis_archive.reopen(session, user, identifier, version, data.reason)


@router.get("/thesis-archive/versions/{identifier}/file")
def archive_file(identifier:UUID,user=Depends(current_user),session=Depends(transaction)):
    return thesis_archive.download(session,user,identifier)
