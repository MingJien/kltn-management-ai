from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query, Request
from backend.api.dependencies import current_user, get_session
from backend.api.lecturer_profile_schemas import Decision, IdentityUpdate, Note, ProfileData, Submission
from backend.services import lecturer_profiles as service

router=APIRouter(prefix="/api/v1",tags=["Lecturer profiles and approval"])


def transaction(session=Depends(get_session)):
    try:yield session
    except Exception:
        session.rollback()
        raise


@router.get("/lecturer-directory")
def directory(q:str=Query(default="",max_length=200),department_id:UUID|None=None,
        status:Literal["ACTIVE","LOCKED","DISABLED"]|None=None,limit:int=Query(default=20,ge=1,le=100),
        offset:int=Query(default=0,ge=0),user=Depends(current_user),session=Depends(transaction)):
    return service.directory(session,user,q.strip(),department_id,status,limit,offset)


@router.get("/lecturer-profiles/{lecturer_id}")
def detail(lecturer_id:UUID,user=Depends(current_user),session=Depends(transaction)):
    return service.detail(session,user,lecturer_id)


@router.get("/lecturer-profiles/{lecturer_id}/avatar")
def avatar(lecturer_id:UUID,user=Depends(current_user),session=Depends(transaction)):
    service.detail(session,user,lecturer_id)
    return service.image_response(session,service.lecturer_row(session,lecturer_id).avatar_file_id)


@router.get("/account/lecturer-profile")
def own(user=Depends(current_user),session=Depends(transaction)):
    return service.workspace(session,user)


@router.post("/account/lecturer-profile/changes",status_code=201)
def create(if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return service.new_request(session,user,if_match)


@router.get("/lecturer-profile-changes/{change_id}")
def request_detail(change_id:UUID,user=Depends(current_user),session=Depends(transaction)):
    lecturer,item=service.request_access(session,user,change_id)
    return service.request_out(session,user,item,lecturer)


@router.put("/lecturer-profile-changes/{change_id}")
def save(change_id:UUID,data:ProfileData,if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return service.save(session,user,change_id,data,if_match)


@router.post("/lecturer-profile-changes/{change_id}/submit")
def submit(change_id:UUID,data:Submission,if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return service.submit(session,user,change_id,data,if_match)


@router.post("/lecturer-profile-changes/{change_id}/withdraw")
def withdraw(change_id:UUID,data:Note,if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return service.withdraw(session,user,change_id,data,if_match)


@router.post("/lecturer-profile-changes/{change_id}/decision")
def decide(change_id:UUID,data:Decision,if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return service.decide(session,user,change_id,data,if_match)


@router.post("/lecturer-profile-changes/{change_id}/avatar",status_code=201,
    openapi_extra={"requestBody":{"required":True,"content":{"application/octet-stream":{"schema":{"type":"string","format":"binary"}}}}})
async def upload(change_id:UUID,request:Request,if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return await service.upload_avatar(session,user,change_id,request,if_match)


@router.delete("/lecturer-profile-changes/{change_id}/avatar")
def remove_avatar(change_id:UUID,if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return service.remove_avatar(session,user,change_id,if_match)


@router.post("/lecturer-profile-changes/{change_id}/avatar/scan")
def rescan(change_id:UUID,if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return service.rescan_avatar(session,user,change_id,if_match)


@router.get("/lecturer-profile-changes/{change_id}/avatar")
def request_avatar(change_id:UUID,user=Depends(current_user),session=Depends(transaction)):
    _,item=service.request_access(session,user,change_id)
    return service.image_response(session,item.avatar_file_id)


@router.get("/lecturer-profile-changes/{change_id}/original-avatar")
def original_avatar(change_id:UUID,user=Depends(current_user),session=Depends(transaction)):
    _,item=service.request_access(session,user,change_id)
    return service.image_response(session,item.original_avatar_file_id)


@router.get("/lecturer-profile-reviews")
def queue(state:Literal["SUBMITTED","APPROVED","RETURNED","WITHDRAWN"]="SUBMITTED",q:str=Query(default="",max_length=200),
        limit:int=Query(default=20,ge=1,le=100),offset:int=Query(default=0,ge=0),user=Depends(current_user),session=Depends(transaction)):
    return service.queue(session,user,state,q.strip(),limit,offset)


@router.put("/lecturer-directory/{lecturer_id}/identity")
def identity(lecturer_id:UUID,data:IdentityUpdate,if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(transaction)):
    return service.update_identity(session,user,lecturer_id,data,if_match)
