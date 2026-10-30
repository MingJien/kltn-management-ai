from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import current_user, get_session
from backend.services.activity import list_activity

router = APIRouter(prefix="/api/v1", tags=["activity history"])


class ActivityItem(BaseModel):
    id: UUID
    action: str
    actor_name: str
    resource_type: str
    resource_id: UUID
    resource_label: str
    reason: str | None
    source_reference: str | None
    occurred_at: datetime


class ActivityPage(BaseModel):
    items: list[ActivityItem]
    total: int
    actions: list[str]
    scope: str


@router.get("/activity", response_model=ActivityPage)
def activity(search: str = Query(default="", max_length=200),
             action: str = Query(default="", max_length=100),
             resource_type: str = Query(default="", max_length=100), resource_id: UUID | None = None,
             date_from: date | None = None, date_to: date | None = None,
             limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0),
             user=Depends(current_user), session: Session = Depends(get_session)):
    if date_to == date.max or (date_from and date_to and date_from > date_to):
        raise HTTPException(422, "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")
    vietnam = timezone(timedelta(hours=7))
    return list_activity(session, user, search=search, action=action, limit=limit, offset=offset,
        resource_type=resource_type, resource_id=resource_id,
        date_from=datetime.combine(date_from, time.min, vietnam) if date_from else None,
        date_to=datetime.combine(date_to + timedelta(days=1), time.min, vietnam) if date_to else None)
