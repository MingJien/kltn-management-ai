"""Administrative recording of department head appointments."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

from backend.api.dependencies import current_user, get_session
from backend.services import positions as service

router = APIRouter(prefix="/api/v1/admin/positions", tags=["Organizational appointments"])
Basis = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)]


class Appointment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lecturer_id: UUID
    effective_from: AwareDatetime | None = None
    effective_to: AwareDatetime | None = None
    basis_ref: Basis
    reason: Reason


class Grant(Appointment):
    department_id: UUID


class Revoke(BaseModel):
    model_config = ConfigDict(extra="forbid")
    basis_ref: Basis
    reason: Reason


def transaction(session=Depends(get_session)):
    try:
        yield session
    except Exception:
        session.rollback()
        raise


@router.get("/catalog")
def catalog(user=Depends(current_user), session=Depends(transaction)):
    return service.catalog(session, user)


@router.get("")
def listing(department_id: UUID | None = None, offset: int = Query(default=0, ge=0, le=100000),
            limit: int = Query(default=50, ge=1, le=100),
            user=Depends(current_user), session=Depends(transaction)):
    return service.listing(session, user, department_id, offset, limit)


@router.get("/available")
def available(user=Depends(current_user), session=Depends(transaction)):
    return service.available_appointments(session, user)


@router.post("", status_code=201)
def grant(data: Grant, user=Depends(current_user), session=Depends(transaction)):
    return service.grant(session, user, data)


@router.post("/{identifier}/replace", status_code=201)
def replace(identifier: UUID, data: Appointment, if_match: int = Header(alias="If-Match", ge=1),
            user=Depends(current_user), session=Depends(transaction)):
    return service.replace(session, user, identifier, data, if_match)


@router.post("/{identifier}/revoke")
def revoke(identifier: UUID, data: Revoke, if_match: int = Header(alias="If-Match", ge=1),
           user=Depends(current_user), session=Depends(transaction)):
    return service.revoke(session, user, identifier, data, if_match)
