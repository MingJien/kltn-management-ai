from __future__ import annotations

import os
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.api.auth import router as auth_router
from backend.api.dependencies import current_user, get_session
from backend.api.schemas import (
    ContextOut, ErrorOut, HealthOut, LecturerDecision, MemberResponse,
    RegistrationCreate, RegistrationOut, TopicOut, SimilarTopicRequest, SearchResult, ChatRequest, ChatOut, EligibleStudentOut, ThesisOut,
)
from backend.db.models import entities as m
from backend.services.registration import (
    _is_department_head, cancel_registration, create_registration, finalize_registration,
    get_registration, lecturer_decision, profile, registration_out,
    respond_to_registration, submit_registration,
)

app = FastAPI(
    title="KLTN prototype API",
    version="0.3.0",
    description="NV4 prototype. Development identity is disabled outside development/test.",
)
_session_secret = os.getenv("AUTH_SESSION_SECRET")
if _session_secret and len(_session_secret) >= 32:
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
    allow_origins=list(dict.fromkeys([
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        os.getenv("KLTN_FRONTEND_URL", "http://localhost:5173").rstrip("/"),
    ])),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Dev-User-Id", "If-Match"],
)
app.include_router(auth_router)


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
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> ContextOut:
    student = session.scalar(select(m.StudentProfile).where(m.StudentProfile.user_id == user.id))
    lecturer = session.scalar(select(m.LecturerProfile).where(m.LecturerProfile.user_id == user.id))
    actions: list[str] = []
    if student:
        actions.append("registration:create")
    if lecturer:
        if session.scalar(select(m.Topic.id).where(
            m.Topic.proposer_user_id == user.id, m.Topic.state == "APPROVED"
        ).limit(1)) is not None:
            actions.append("registration:lecturer_decide")
        department_ids = session.scalars(select(m.Department.id)).all()
        if any(_is_department_head(session, lecturer.id, department_id) for department_id in department_ids):
            actions.append("registration:department_finalize")
    return ContextOut(
        user_id=user.id, base_role=user.base_role,
        student_id=student.id if student else None,
        lecturer_id=lecturer.id if lecturer else None, actions=actions,
    )


@app.get("/api/v1/topics", response_model=list[TopicOut])
def topics(
    round_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[TopicOut]:
    query = select(m.Topic).where(m.Topic.state == "APPROVED")
    if user.base_role == "STUDENT":
        viewer = profile(session, user, "STUDENT")
        query = query.where(m.Topic.department_id == viewer.department_id)
    elif user.base_role == "LECTURER":
        viewer = profile(session, user, "LECTURER")
        query = query.where(m.Topic.department_id == viewer.department_id)
    else:
        return []
    if round_id is not None:
        query = query.where(m.Topic.round_id == round_id)
    rows = session.scalars(query.order_by(m.Topic.current_title, m.Topic.id).limit(limit)).all()
    return [TopicOut(
        id=row.id, round_id=row.round_id, title=row.current_title,
        description=row.description, max_students=row.max_students, state=row.state,
    ) for row in rows]


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
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[RegistrationOut]:
    if user.base_role == "STUDENT":
        student = profile(session, user, "STUDENT")
        ids = session.scalars(select(m.RegistrationMember.registration_id).where(
            m.RegistrationMember.student_id == student.id
        )).all()
        rows = session.scalars(select(m.TopicRegistration).where(m.TopicRegistration.id.in_(ids))).all()
    elif user.base_role == "LECTURER":
        lecturer = profile(session, user, "LECTURER")
        topics = session.scalars(select(m.Topic).where(m.Topic.proposer_user_id == user.id)).all()
        departments = session.scalars(select(m.Department.id)).all()
        head_departments = {dep for dep in departments if _is_department_head(session, lecturer.id, dep)}
        topic_ids = [t.id for t in topics]
        topic_ids += session.scalars(select(m.Topic.id).where(m.Topic.department_id.in_(head_departments))).all()
        rows = session.scalars(select(m.TopicRegistration).where(
            m.TopicRegistration.topic_id.in_(topic_ids),
            m.TopicRegistration.state != "DRAFT",
        )).all()
    else:
        rows = []
    return [registration_out(session, row) for row in rows]


@app.get("/api/v1/topic-registrations/{registration_id}", response_model=RegistrationOut)
def registration(
    registration_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return get_registration(session, user, registration_id)


@app.post("/api/v1/topic-registrations/{registration_id}/member-response", response_model=RegistrationOut)
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


@app.post("/api/v1/topic-registrations/{registration_id}/lecturer-decision", response_model=RegistrationOut)
def decide(
    registration_id: UUID,
    payload: LecturerDecision,
    if_match: int = Header(alias="If-Match"),
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return lecturer_decision(session, user, registration_id, payload, if_match)


@app.post("/api/v1/topic-registrations/{registration_id}/department-finalization", response_model=RegistrationOut)
def finalize(
    registration_id: UUID,
    if_match: int = Header(alias="If-Match"),
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> RegistrationOut:
    return finalize_registration(session, user, registration_id, if_match)


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


@app.get("/api/v1/eligible-students", response_model=list[EligibleStudentOut])
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
        .join(m.EligibilitySnapshot, m.EligibilitySnapshot.student_id == m.StudentProfile.id)
        .where(
            m.StudentProfile.department_id == me.department_id,
            m.EligibilitySnapshot.round_id == round_id,
            m.EligibilitySnapshot.state == "CONFIRMED",
        ).distinct()
        .order_by(m.StudentProfile.display_name)
        .limit(100)
    ).all()
    return [EligibleStudentOut(id=item.id, display_name=item.display_name, student_code=item.student_code) for item in students]


@app.get("/api/v1/topics/{topic_id}", response_model=TopicOut)
def topic_detail(
    topic_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> TopicOut:
    row = session.get(m.Topic, topic_id)
    if row is None or row.state != "APPROVED":
        raise HTTPException(404, "Topic not found")
    if user.base_role == "STUDENT":
        viewer = profile(session, user, "STUDENT")
    elif user.base_role == "LECTURER":
        viewer = profile(session, user, "LECTURER")
    else:
        raise HTTPException(404, "Topic not found")
    if viewer.department_id != row.department_id:
        raise HTTPException(404, "Topic not found")
    return TopicOut(id=row.id, round_id=row.round_id, title=row.current_title,
                    description=row.description, max_students=row.max_students, state=row.state)


@app.get("/api/v1/theses/{thesis_id}", response_model=ThesisOut)
def thesis_detail(
    thesis_id: UUID,
    user: m.UserAccount = Depends(current_user),
    session: Session = Depends(get_session),
) -> ThesisOut:
    thesis = session.get(m.Thesis, thesis_id)
    if thesis is None:
        raise HTTPException(404, "Thesis not found")
    members = session.scalars(select(m.ThesisMember).where(m.ThesisMember.thesis_id == thesis_id,
                                                           m.ThesisMember.active.is_(True))).all()
    advisor = session.scalar(select(m.AdvisorAssignment).where(
        m.AdvisorAssignment.thesis_id == thesis_id, m.AdvisorAssignment.state == "ACTIVE",
        m.AdvisorAssignment.assignment_type == "PRIMARY",
    ))
    allowed = False
    if user.base_role == "STUDENT":
        student = profile(session, user, "STUDENT")
        allowed = any(member.student_id == student.id for member in members)
    elif user.base_role == "LECTURER":
        lecturer = profile(session, user, "LECTURER")
        allowed = (advisor is not None and advisor.lecturer_id == lecturer.id) or _is_department_head(
            session, lecturer.id, thesis.department_id
        )
    if not allowed:
        raise HTTPException(404, "Thesis not found")
    if advisor is None:
        raise HTTPException(409, "Primary advisor assignment missing")
    return ThesisOut(id=thesis.id, title=thesis.current_title, state=thesis.state,
                     member_student_ids=[member.student_id for member in members],
                     advisor_lecturer_id=advisor.lecturer_id)
