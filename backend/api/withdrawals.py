from uuid import UUID
from fastapi import APIRouter, Depends, Header, Request
from backend.api.dependencies import current_user, get_session
from backend.api.withdrawal_schemas import AdvisorDecision, ExternalOutcome, StartDate, WithdrawalCreate
from backend.services import withdrawals as service

router = APIRouter(prefix="/api/v1", tags=["Xin thôi KLTN"])


def transaction(session=Depends(get_session)):
    try:
        yield session
    except Exception:
        session.rollback()
        raise


@router.get("/withdrawals")
def listing(user=Depends(current_user), session=Depends(transaction)):
    return service.workspace(session, user)


@router.put("/withdrawal-rounds/{round_id}/start")
def start(round_id: UUID, data: StartDate, if_match: int = Header(alias="If-Match", ge=1),
          user=Depends(current_user), session=Depends(transaction)):
    return service.set_start(session, user, round_id, data, if_match)


@router.post("/theses/{thesis_id}/withdrawals", status_code=201)
def create(thesis_id: UUID, data: WithdrawalCreate, user=Depends(current_user), session=Depends(transaction)):
    return service.create(session, user, thesis_id, data)


@router.post("/withdrawals/{identifier}/advisor-decision")
def advisor(identifier: UUID, data: AdvisorDecision, if_match: int = Header(alias="If-Match", ge=1),
            user=Depends(current_user), session=Depends(transaction)):
    return service.advisor_decision(session, user, identifier, data, if_match)


@router.post("/withdrawals/{identifier}/cancel")
def cancel(identifier: UUID, if_match: int = Header(alias="If-Match", ge=1),
           user=Depends(current_user), session=Depends(transaction)):
    return service.cancel(session, user, identifier, if_match)


@router.post("/withdrawals/{identifier}/signed-copy")
async def upload(identifier: UUID, request: Request, if_match: int = Header(alias="If-Match", ge=1),
                 user=Depends(current_user), session=Depends(transaction)):
    return await service.upload(session, user, identifier, request, if_match)


@router.post("/withdrawals/{identifier}/scan")
def scan(identifier: UUID, if_match: int = Header(alias="If-Match", ge=1),
         user=Depends(current_user), session=Depends(transaction)):
    return service.rescan(session, user, identifier, if_match)


@router.post("/withdrawals/{identifier}/outcome")
def outcome(identifier: UUID, data: ExternalOutcome, if_match: int = Header(alias="If-Match", ge=1),
            user=Depends(current_user), session=Depends(transaction)):
    return service.record(session, user, identifier, data, if_match)


@router.get("/withdrawals/{identifier}/signed-copy")
def download(identifier: UUID, user=Depends(current_user), session=Depends(transaction)):
    return service.download(session, user, identifier)


@router.post("/withdrawals/{identifier}/print-copy")
def print_copy(identifier: UUID, user=Depends(current_user), session=Depends(transaction)):
    return service.print_copy(session, user, identifier)
