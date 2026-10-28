from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from backend.api.auth import allowed_frontend_origins, router as auth_router
from backend.api.account import router as account_router
from backend.api.roster import router as roster_router, assignment_router
from backend.api.account_admin import router as account_admin_router
from backend.api.lecturer_import import router as lecturer_import_router
from backend.api.core import router as thesis_workspace_router
from backend.api.activity import router as activity_router
from backend.api.school_forms import router as school_forms_router
from backend.api.dependencies import current_user, get_session
from backend.api.schemas import (
    ContextOut, ErrorOut, HealthOut, LecturerDecision, RejectedProposalResolution, MemberResponse,
    RegistrationCreate, RegistrationOut, PendingRegistrationSummaryOut, TopicOut, TopicCreate, TopicUpdate, TopicDecision, OpenRoundOut,
    SimilarTopicRequest, SearchResult, ChatRequest, ChatOut, EligibleStudentOut, StudentProposalCreate, LecturerOut, MyEligibilityOut,
    NotificationSummaryOut,
)
from backend.db.models import entities as m
from backend.services.registration import (
    _is_department_head, cancel_registration, create_registration,
    withdraw_registration,
    get_registration, lecturer_decision, resolve_rejected_student_proposal, profile, registration_out, registrations_out,
    respond_to_registration, submit_registration,
    confirmed_student_ids,
)
from backend.services.account_directory import lecturer_duties_for_user
from backend.services.topics import (
    create_topic, department_decision, get_visible_topic, open_rounds,
    submit_topic, update_topic, visible_topics, round_out,
)

app = FastAPI(
    title="KLTN API",
    version="0.3.0",
    description="Quy trình đề tài và đăng ký KLTN; các chức năng AI còn ở mức thử nghiệm. Development identity chỉ bật trong development/test.",
)
_session_secret = os.getenv("AUTH_SESSION_SECRET") or secrets.token_urlsafe(48)
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    session_cookie="kltn_session",
    same_site="lax",
    https_only=os.getenv("KLTN_ENV") == "production",
    max_age=8 * 60 * 60,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_frontend_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Dev-User-Id", "If-Match", "X-File-Name", "X-Form-Code", "X-Preview-SHA256", "X-CSRF-Token"],
    expose_headers=["X-Document-Code", "X-Exported-At", "X-Print-SHA256", "Content-Disposition"],
)
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(roster_router)
app.include_router(assignment_router)
app.include_router(account_admin_router)
app.include_router(lecturer_import_router)
app.include_router(thesis_workspace_router)
app.include_router(activity_router)
app.include_router(school_forms_router)


@app.get("/api/v1/notifications", response_model=NotificationSummaryOut)
def notifications(limit: int = Query(default=20, ge=1, le=100),
                  offset: int = Query(default=0, ge=0),
                  unread_only: bool = False,
                  user: m.UserAccount = Depends(current_user),
                  session: Session = Depends(get_session)) -> NotificationSummaryOut:
    from backend.services.notifications import list_notices

    return list_notices(session, user.id, limit=limit, offset=offset, unread_only=unread_only)


@app.post("/api/v1/notifications/{notification_id}/read", status_code=204)
def read_notification(notification_id: UUID, user: m.UserAccount = Depends(current_user),
                      session: Session = Depends(get_session)) -> None:
    from backend.services.notifications import mark_notice_read

    mark_notice_read(session, user.id, notification_id)


@app.middleware("http")
async def private_api_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.post("/api/v1/topic-registrations/{registration_id}/evidence", response_model=RegistrationOut)
async def registration_evidence_upload(registration_id: UUID, request: Request,
    user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)):
    from backend.services.evidence import upload_evidence
    return await upload_evidence(session, user, registration_id, request)


@app.get("/api/v1/topic-registrations/{registration_id}/members/{student_id}/evidence")
def registration_evidence_download(registration_id: UUID, student_id: UUID,
    user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)):
    from backend.services.evidence import download_evidence
    return download_evidence(session, user, registration_id, student_id)


@app.post("/api/v1/topic-registrations/{registration_id}/members/{student_id}/evidence/scan", response_model=RegistrationOut)
def registration_evidence_scan(registration_id: UUID, student_id: UUID,
    user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)):
    from backend.services.evidence import rescan_evidence
    return rescan_evidence(session, user, registration_id, student_id)


@app.get("/health/live", response_model=HealthOut)
def live() -> HealthOut:
    return HealthOut(status="ok")


@app.get("/health/ready", response_model=HealthOut)
def ready(session: Session = Depends(get_session)) -> HealthOut:
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "Database unavailable")
    return HealthOut(status="ok")


@app.get("/api/v1/me/context", response_model=ContextOut)
def context(
    request: Request,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> ContextOut:
    csrf_token = request.session.get("csrf_token") if request.session.get("user_id") else None
    student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == user.id))
    lecturer = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == user.id))
    student = student if user.base_role == "STUDENT" else None
    lecturer = lecturer if user.base_role == "LECTURER" else None
    actions: list[str] = []
    if student and user.base_role == "STUDENT":
        actions.append("registration:create")
    if user.base_role == "ADMIN":
        actions.append("account:manage")
    now = datetime.now(timezone.utc)
    assignment_types = session.scalars(select(m.ResourceAssignment.assignment_type).where(
        m.ResourceAssignment.user_id == user.id,
        m.ResourceAssignment.round_id.is_not(None),
        m.ResourceAssignment.state == "ACTIVE",
        m.ResourceAssignment.effective_from <= now,
        or_(m.ResourceAssignment.effective_to.is_(None), m.ResourceAssignment.effective_to > now),
        m.ResourceAssignment.assignment_type.in_(["ELIGIBILITY_IMPORTER", "ELIGIBILITY_VERIFIER", "ACCOUNT_MANAGER", "KLTN_COORDINATOR", "FORM_MANAGER"]),
    )).all()
    if "FORM_MANAGER" in assignment_types:
        actions.append("forms:manage")
    if "ELIGIBILITY_IMPORTER" in assignment_types:
        actions.append("eligibility:import")
    if "ELIGIBILITY_VERIFIER" in assignment_types:
        actions.append("eligibility:manage")
    if "ACCOUNT_MANAGER" in assignment_types:
        actions.append("account:manage")
    if lecturer and user.base_role == "LECTURER":
        actions.extend(["topic:create", "topic:submit"])
        if session.scalar(select(m.Topic.id).where(
            or_(m.Topic.proposer_user_id == user.id, m.Topic.receiving_lecturer_id == lecturer.id), m.Topic.state == "APPROVED"
        ).limit(1)) is not None:
            actions.append("registration:lecturer_decide")
        if _is_department_head(session, lecturer.id, lecturer.department_id):
            actions.append("topic:department_decide")
    profile_department_id = student.department_id if student else lecturer.department_id if lecturer else None
    profile_department = session.get(m.Department, profile_department_id) if profile_department_id else None
    profile_major = session.scalar(select(m.DepartmentMajor).where(
        m.DepartmentMajor.department_id == profile_department_id,
        m.DepartmentMajor.code == student.major_code,
        m.DepartmentMajor.active.is_(True))) if student and student.major_code else None
    return ContextOut(
        user_id=user.id, base_role=user.base_role,
        student_id=student.id if student else None,
        lecturer_id=lecturer.id if lecturer else None, actions=actions,
        display_name=(student.display_name if student else lecturer.display_name if lecturer else user.email or str(user.id)),
        department_id=profile_department_id,
        department_code=profile_department.code if profile_department else None,
        department_name=profile_department.name if profile_department else None,
        email=user.email,
        student_code=student.student_code if student else None,
        class_name=student.class_name if student else None,
        major_code=student.major_code if student else None,
        major_name=profile_major.name if profile_major else None,
        lecturer_code=lecturer.lecturer_code if lecturer else None,
        lecturer_duties=lecturer_duties_for_user(session, user.id) if lecturer else [],
        csrf_token=csrf_token,
        can_change_password=bool(user.email_verified_at and user.password_hash and user.password_hash.startswith("$argon2")),
    )


@app.get("/api/v1/rounds/open", response_model=list[OpenRoundOut])
def rounds_open(
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[OpenRoundOut]:
    if user.base_role not in {"LECTURER", "STUDENT"}:
        return []
    return [round_out(session, row) for row in open_rounds(session)]


@app.get("/api/v1/topics", response_model=list[TopicOut])
def topics(
    round_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    view: str = Query(default="all", pattern="^(all|mine|pending|suggested)$"),
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[TopicOut]:
    return visible_topics(session, user, round_id, limit, offset, search, view)


@app.post("/api/v1/topics", response_model=TopicOut, status_code=201)
def topic_create(payload: TopicCreate, user: m.UserAccount = Depends(current_user),
                 session: Session = Depends(get_session)) -> TopicOut:
    return create_topic(session, user, payload)


@app.get("/api/v1/lecturers", response_model=list[LecturerOut])
def lecturers(user: m.UserAccount = Depends(current_user), session: Session = Depends(get_session)):
    if user.base_role not in {"STUDENT", "LECTURER"}:
        raise HTTPException(403, "Student or lecturer required")
    viewer = profile(session, user, user.base_role)
    rows = session.scalars(select(m.LecturerProfile).join(m.UserAccount, m.UserAccount.id == m.LecturerProfile.user_id)
        .where(m.LecturerProfile.department_id == viewer.department_id, m.UserAccount.status == "ACTIVE", m.UserAccount.base_role == "LECTURER")
        .order_by(m.LecturerProfile.display_name)).all()
    department = session.get(m.Department, viewer.department_id)
    faculty = session.get(m.Faculty, department.faculty_id) if department else None
    return [LecturerOut(id=row.id, display_name=row.display_name, lecturer_code=row.lecturer_code,
        department_name=department.name if department else None, faculty_name=faculty.name if faculty else None)
        for row in rows]


@app.post("/api/v1/student-proposals", response_model=RegistrationOut, status_code=201)
def student_proposal(payload: StudentProposalCreate, user: m.UserAccount = Depends(current_user),
                     session: Session = Depends(get_session)):
    try:
        topic = create_topic(session, user, payload, student_proposal=True)
        return create_registration(session, user, RegistrationCreate(topic_id=topic.id,
            member_student_ids=payload.member_student_ids, confirm_creator=payload.confirm_creator,
            expected_member_count=payload.expected_member_count))
    except Exception:
        session.rollback()
        raise


@app.patch("/api/v1/topics/{topic_id}", response_model=TopicOut)
def topic_update(topic_id: UUID, payload: TopicUpdate, if_match: int = Header(alias="If-Match"),
                 user: m.UserAccount = Depends(current_user),
                 session: Session = Depends(get_session)) -> TopicOut:
    return update_topic(session, user, topic_id, payload, if_match)


@app.post("/api/v1/topics/{topic_id}/submit", response_model=TopicOut)
def topic_submit(topic_id: UUID, if_match: int = Header(alias="If-Match"),
                 user: m.UserAccount = Depends(current_user),
                 session: Session = Depends(get_session)) -> TopicOut:
    return submit_topic(session, user, topic_id, if_match)


@app.post("/api/v1/topics/{topic_id}/department-decision", response_model=TopicOut)
def topic_department_decision(topic_id: UUID, payload: TopicDecision,
                              if_match: int = Header(alias="If-Match"),
                              user: m.UserAccount = Depends(current_user),
                              session: Session = Depends(get_session)) -> TopicOut:
    return department_decision(session, user, topic_id, payload, if_match)


@app.post(
    "/api/v1/topic-registrations", response_model=RegistrationOut, status_code=201,
    responses={403: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def register(
    payload: RegistrationCreate,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return create_registration(session, user, payload)


@app.get("/api/v1/topic-registrations", response_model=list[RegistrationOut])
def registrations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[RegistrationOut]:
    if user.base_role == "STUDENT":
        student = profile(session, user, "STUDENT")
        ids = session.scalars(select(m.RegistrationMember.registration_id).where(
            m.RegistrationMember.student_id == student.id
        )).all()
        query = select(m.TopicRegistration).where(m.TopicRegistration.id.in_(ids))
    elif user.base_role == "LECTURER":
        lecturer = profile(session, user, "LECTURER")
        topics = session.scalars(select(m.Topic).where(or_(m.Topic.proposer_user_id == user.id,
            m.Topic.receiving_lecturer_id == lecturer.id))).all()
        head_departments = {lecturer.department_id} if _is_department_head(session, lecturer.id, lecturer.department_id) else set()
        topic_ids = [t.id for t in topics]
        topic_ids += session.scalars(select(m.Topic.id).where(m.Topic.department_id.in_(head_departments))).all()
        query = select(m.TopicRegistration).where(
            m.TopicRegistration.topic_id.in_(topic_ids),
            m.TopicRegistration.state != "DRAFT",
            m.TopicRegistration.submitted_at.is_not(None),
        )
    else:
        return []
    rows = session.scalars(query.order_by(m.TopicRegistration.created_at.desc(), m.TopicRegistration.id)
        .offset(offset).limit(limit)).all()
    return registrations_out(session, rows)


@app.get("/api/v1/topic-registrations/pending-summary", response_model=PendingRegistrationSummaryOut)
def pending_registration_summary(
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> PendingRegistrationSummaryOut:
    if user.base_role != "LECTURER":
        raise HTTPException(403, "Only lecturers can view pending registrations")
    lecturer = profile(session, user, "LECTURER")
    receiving = or_(
        m.Topic.receiving_lecturer_id == lecturer.id,
        (m.Topic.receiving_lecturer_id.is_(None)) & (m.Topic.proposer_type == "LECTURER")
        & (m.Topic.proposer_user_id == user.id),
    )
    query = select(m.TopicRegistration).join(m.Topic, m.Topic.id == m.TopicRegistration.topic_id).where(
        m.TopicRegistration.state == "SUBMITTED",
        m.TopicRegistration.submitted_at.is_not(None),
        m.Topic.state == "APPROVED",
        receiving,
    )
    count = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.scalars(query.order_by(m.TopicRegistration.submitted_at.desc(),
        m.TopicRegistration.id).limit(5)).all()
    return PendingRegistrationSummaryOut(count=count, items=registrations_out(session, rows))


@app.get("/api/v1/topic-registrations/{registration_id}", response_model=RegistrationOut)
def registration(
    registration_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return get_registration(session, user, registration_id)


@app.post("/api/v1/topic-registrations/{registration_id}/member-response", response_model=RegistrationOut, deprecated=True)
def registration_member_response(
    registration_id: UUID,
    payload: MemberResponse,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return respond_to_registration(session, user, registration_id, payload)


@app.post("/api/v1/topic-registrations/{registration_id}/submit", response_model=RegistrationOut)
def registration_submit(
    registration_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return submit_registration(session, user, registration_id)


@app.post("/api/v1/topic-registrations/{registration_id}/cancel", response_model=RegistrationOut)
def registration_cancel(
    registration_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return cancel_registration(session, user, registration_id)


@app.post("/api/v1/topic-registrations/{registration_id}/withdraw", response_model=RegistrationOut)
def registration_withdraw(
    registration_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return withdraw_registration(session, user, registration_id)


@app.post("/api/v1/topic-registrations/{registration_id}/lecturer-decision", response_model=RegistrationOut)
def decide(
    registration_id: UUID,
    payload: LecturerDecision,
    if_match: int = Header(alias="If-Match"),
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return lecturer_decision(session, user, registration_id, payload, if_match)


@app.post("/api/v1/topic-registrations/{registration_id}/resolve-lecturer-rejection", response_model=RegistrationOut)
def resolve_lecturer_rejection(
    registration_id: UUID,
    payload: RejectedProposalResolution,
    if_match: int = Header(alias="If-Match"),
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return resolve_rejected_student_proposal(session, user, registration_id, payload, if_match)


from functools import lru_cache


@lru_cache(maxsize=1)
def _ai_index():
    import os
    from pathlib import Path
    from qdrant_client import QdrantClient
    from backend.ai.index import CorpusIndex, FastEmbedProvider
    url = os.getenv("QDRANT_URL")
    local_path = os.getenv("QDRANT_LOCAL_PATH")
    if not url and not local_path:
        raise HTTPException(503, "Qdrant is not configured")
    try:
        client = QdrantClient(url=url) if url else QdrantClient(path=str(Path(local_path)))
        return CorpusIndex(client, FastEmbedProvider())
    except Exception:
        raise HTTPException(503, "Embedding or Qdrant dependency unavailable")


@app.post("/api/v1/ai/similar-topics", response_model=list[SearchResult])
def similar_topics(
    payload: SimilarTopicRequest,
    user: m.UserAccount = Depends(current_user),
) -> list[SearchResult]:
    from backend.ai.processing import normalize
    index = _ai_index()
    query = normalize(" ".join([payload.title, payload.abstract or "", " ".join(payload.keywords), payload.domain or ""]))
    scope = "INTERNAL" if user.base_role == "LECTURER" else "PUBLIC"
    return [SearchResult(**hit.__dict__) for hit in index.search(
        query, scope=scope,
        source_types={"THESIS", "CAPSTONE_PROJECT", "TERM_PROJECT", "COURSE_PROJECT"},
        representation="TOPIC", limit=payload.limit,
    )]


@app.post("/api/v1/ai/chat", response_model=ChatOut)
def ai_chat(
    payload: ChatRequest,
    user: m.UserAccount = Depends(current_user),
) -> ChatOut:
    from backend.ai.rag import retrieve_answer
    scope = "INTERNAL" if user.base_role == "LECTURER" else "PUBLIC"
    result = retrieve_answer(_ai_index(), payload.question, scope=scope)
    return ChatOut(**result)


@app.get("/api/v1/me/eligibility", response_model=MyEligibilityOut)
def my_eligibility(round_id: UUID, user: m.UserAccount = Depends(current_user),
                   session: Session = Depends(get_session)):
    me = profile(session, user, "STUDENT")
    active = session.scalar(select(m.RegistrationMember.id).where(
        m.RegistrationMember.student_id == me.id, m.RegistrationMember.round_id == round_id,
        m.RegistrationMember.active.is_(True)).limit(1))
    return MyEligibilityOut(eligible=me.id in confirmed_student_ids(session, round_id, [me.id]),
                            has_active_registration=active is not None)


@app.get("/api/v1/eligible-students", response_model=list[EligibleStudentOut], deprecated=True)
def eligible_students(
    round_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[EligibleStudentOut]:
    if user.base_role != "STUDENT":
        raise HTTPException(403, "Student context required")
    me = profile(session, user, "STUDENT")
    students = session.scalars(
        select(m.StudentProfile)
        .join(m.UserAccount, m.UserAccount.id == m.StudentProfile.user_id)
        .join(m.EligibilitySnapshot, m.EligibilitySnapshot.student_id == m.StudentProfile.id)
        .where(
            m.StudentProfile.department_id == me.department_id,
            m.StudentProfile.id == me.id,
            m.EligibilitySnapshot.round_id == round_id,
            m.EligibilitySnapshot.state == "CONFIRMED",
            m.UserAccount.status == "ACTIVE",
            m.UserAccount.base_role == "STUDENT",
        ).distinct()
        .order_by(m.StudentProfile.display_name)
        .limit(100)
    ).all()
    eligible = confirmed_student_ids(session, round_id, [item.id for item in students])
    return [EligibleStudentOut(id=item.id, display_name=item.display_name, student_code=item.student_code) for item in students if item.id in eligible]


@app.get("/api/v1/topics/{topic_id}", response_model=TopicOut)
def topic_detail(
    topic_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> TopicOut:
    return get_visible_topic(session, user, topic_id)
