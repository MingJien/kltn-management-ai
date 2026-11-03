"""Institutional forms and round publications, managed by explicit assignment."""
from typing import Annotated, Literal
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Header, Request, UploadFile, File, Form
from pydantic import BaseModel, Field, StringConstraints
from backend.api.dependencies import current_user, get_session
from backend.services import school_forms as service

router=APIRouter(prefix="/api/v1/school-forms",tags=["Faculty forms"])
Reason=Annotated[str,StringConstraints(strip_whitespace=True,min_length=5,max_length=2000)]
Source=Annotated[str,StringConstraints(strip_whitespace=True,min_length=3,max_length=500)]


class FormCreate(BaseModel):
    round_id:UUID
    code:str=Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,49}$")
    title:Annotated[str,StringConstraints(strip_whitespace=True,min_length=3,max_length=255)]
    document_kind:Literal["FORM","PUBLICATION"]
    audience:Literal["STUDENT_AND_LECTURER","LECTURER"]
    reason:Reason


class FormUpdate(BaseModel):
    title:Annotated[str,StringConstraints(strip_whitespace=True,min_length=3,max_length=255)]
    audience:Literal["STUDENT_AND_LECTURER","LECTURER"]
    state:Literal["ACTIVE","ARCHIVED"]
    reason:Reason


class FormAction(BaseModel):
    reason:Reason


class VersionOut(BaseModel):
    id:UUID
    version_no:int
    row_version:int
    state:Literal["DRAFT","PUBLISHED","SUPERSEDED","WITHDRAWN"]
    file_name:str
    byte_size:int
    scan_state:str
    uploaded_at:datetime
    uploaded_by_name:str
    source_reference:str
    change_reason:str
    published_at:datetime|None


class FormOut(BaseModel):
    id:UUID
    round_id:UUID
    code:str
    title:str
    document_kind:Literal["FORM","PUBLICATION"]
    audience:Literal["STUDENT_AND_LECTURER","LECTURER"]
    state:Literal["ACTIVE","ARCHIVED"]
    row_version:int
    versions:list[VersionOut]


class AccessOut(BaseModel):
    id:UUID
    label:str
    state:str
    can_manage:bool
    can_view_publications:bool
    can_export_list:bool


class BootstrapOut(BaseModel):
    created:int
    published:int
    drafts:int
    missing:list[str]
    remaining:int


class SheetOut(BaseModel):
    name:str
    rows:list[list[str]]
    truncated:bool


class SpreadsheetOut(BaseModel):
    sheets:list[SheetOut]
    truncated:bool


@router.get("/access",response_model=list[AccessOut])
def access(user=Depends(current_user),session=Depends(get_session)):
    return service.access(session,user)


@router.post("/rounds/{round_id}/mau-04")
def export_round_list(round_id:UUID,user=Depends(current_user),session=Depends(get_session)):
    from backend.services.school_form_list_export import export_mau_04
    return export_mau_04(session,user,round_id)


@router.get("",response_model=list[FormOut])
def listing(round_id:UUID,user=Depends(current_user),session=Depends(get_session)):
    return service.listing(session,user,round_id)


@router.post("",status_code=201,response_model=FormOut)
def create(data:FormCreate,user=Depends(current_user),session=Depends(get_session)):
    return service.create(session,user,data)


@router.post("/bootstrap/{round_id}",response_model=BootstrapOut)
def bootstrap(round_id:UUID,user=Depends(current_user),session=Depends(get_session)):
    return service.bootstrap(session,user,round_id,batch_limit=1)


@router.patch("/{form_id}",response_model=FormOut)
def update(form_id:UUID,data:FormUpdate,if_match:int=Header(alias="If-Match",ge=1),
        user=Depends(current_user),session=Depends(get_session)):
    return service.update(session,user,form_id,data,if_match)


@router.post("/{form_id}/versions",status_code=201,response_model=FormOut)
async def upload(form_id:UUID,request:Request,file:UploadFile=File(...),source_reference:Source=Form(...),reason:Reason=Form(...),
        if_match:int=Header(alias="If-Match",ge=1),user=Depends(current_user),session=Depends(get_session)):
    return await service.upload(session,user,form_id,request,if_match,source_reference,reason,file)


@router.post("/{form_id}/versions/{version_id}/publish",response_model=FormOut)
def publish(form_id:UUID,version_id:UUID,data:FormAction,if_match:int=Header(alias="If-Match",ge=1),
        user=Depends(current_user),session=Depends(get_session)):
    return service.publish(session,user,form_id,version_id,data,if_match)


@router.post("/{form_id}/versions/{version_id}/withdraw",response_model=FormOut)
def withdraw(form_id:UUID,version_id:UUID,data:FormAction,if_match:int=Header(alias="If-Match",ge=1),
        user=Depends(current_user),session=Depends(get_session)):
    return service.withdraw(session,user,form_id,version_id,data,if_match)


@router.post("/{form_id}/versions/{version_id}/scan",response_model=FormOut)
def scan(form_id:UUID,version_id:UUID,if_match:int=Header(alias="If-Match",ge=1),
        user=Depends(current_user),session=Depends(get_session)):
    return service.rescan(session,user,form_id,version_id,if_match)


@router.get("/{form_id}/versions/{version_id}/download")
def download(form_id:UUID,version_id:UUID,user=Depends(current_user),session=Depends(get_session)):
    return service.downloadable(session,user,form_id,version_id)[3]


@router.get("/{form_id}/versions/{version_id}/spreadsheet",response_model=SpreadsheetOut)
def spreadsheet(form_id:UUID,version_id:UUID,user=Depends(current_user),session=Depends(get_session)):
    return service.spreadsheet(session,user,form_id,version_id)
