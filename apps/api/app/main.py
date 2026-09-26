"""Server-side safety boundary for the BrightPath MVP.

Learning replies can come from local templates or an LLM configured in
apps/api/.env. Harmful procedural and help-seeking messages never reach the
model. Production must replace the in-memory stores with Supabase-backed
repositories and enforce authenticated child ownership.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .admin_auth import hash_password, issue_admin_token, password_matches, require_admin
from .llm import generate_learning_reply, llm_ready
from .settings import settings
from .supabase_store import SafetyProfile, SupabaseStoreError, store

app = FastAPI(title="BrightPath API", docs_url=None if settings.app_env == "production" else "/docs")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Idempotency-Key", "Authorization"])


class ChatRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=1200)
    use_llm: bool | None = None
    safety_profile: Literal["Less than 10", "10-13", "13-15", "15-17"] = "Less than 10"


class ChatResponse(BaseModel):
    id: str
    content: str
    safety_state: Literal["safe", "guided"]
    topic: str
    source: Literal["local", "llm"] = "local"


class SafetyDecision(BaseModel):
    action: Literal["allow", "guided", "block", "support"]
    reason: str


MODERATION_CATEGORIES = {
    "harassment",
    "harassment/threatening",
    "hate",
    "hate/threatening",
    "illicit",
    "illicit/violent",
    "self-harm",
    "self-harm/intent",
    "self-harm/instructions",
    "sexual",
    "sexual/minors",
    "violence",
    "violence/graphic",
}


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class AdminUserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=256)
    safety_profile: Literal["Less than 10", "10-13", "13-15", "15-17"] = "Less than 10"


class AdminUserUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    username: str = Field(min_length=3, max_length=80)
    password: str | None = Field(default=None, min_length=8, max_length=256)
    safety_profile: Literal["Less than 10", "10-13", "13-15", "15-17"] = "Less than 10"


class SafetyProfileUpdate(BaseModel):
    prompt_content: str = Field(min_length=1, max_length=8000)
    input_thresholds: dict[str, float]
    output_thresholds: dict[str, float]


request_times: defaultdict[str, list[float]] = defaultdict(list)

HARD_BLOCK_PATTERNS = [
    r"\b(how (do|can) i|instructions?|steps?)\b.{0,80}\b(kill|hurt|poison|make a bomb|weapon)\b",
    r"\b(make|build)\b.{0,60}\b(bomb|explosive|weapon)\b",
]
SUPPORT_PATTERNS = [r"\b(kill myself|suicide|self harm|hurt myself|want to die)\b", r"\b(abuse[ds]?|someone is hurting me)\b"]
GUIDED_PATTERNS = [r"\b(violence|blood|fight|gun|puberty|sex|naked|bully|bullying)\b"]


def decide_input(text: str) -> SafetyDecision:
    lowered = text.lower()
    if any(re.search(pattern, lowered) for pattern in SUPPORT_PATTERNS):
        return SafetyDecision(action="support", reason="support_topic")
    if any(re.search(pattern, lowered) for pattern in HARD_BLOCK_PATTERNS):
        return SafetyDecision(action="block", reason="harmful_procedure")
    if any(re.search(pattern, lowered) for pattern in GUIDED_PATTERNS):
        return SafetyDecision(action="guided", reason="sensitive_topic")
    return SafetyDecision(action="allow", reason="normal_learning")


def safe_support_reply() -> str:
    return "I’m really glad you told me. You deserve help and don’t have to handle this alone. Please tell a trusted grown-up right now, like a parent, teacher, school counselor, or another adult you trust. If you are in immediate danger, call your local emergency number now."


def safe_block_reply() -> str:
    return "I can’t help with instructions that could hurt someone. If you’re learning about this for school, I can explain safety, laws, or how people can get help without giving dangerous steps."


def local_learning_reply(question: str, guided: bool) -> str:
    topic = classify_topic(question)
    prefix = "That’s an important question. Here’s a simple, non-graphic way to think about it: " if guided else "Great question! "
    examples = {
        "Space": "Space is very big, and scientists learn about it by watching light, using telescopes, and testing ideas. What part of space are you most curious about?",
        "Maths": "Try splitting the problem into small steps, then check each step. Tell me the numbers or a picture of the problem, and we can solve it together.",
        "Science": "Scientists begin by observing carefully, asking a testable question, and looking for evidence. We can explore the idea one piece at a time.",
        "History": "History is about people, places, and events from the past. We can look at what happened, why it mattered, and how we know about it.",
        "Reading": "Stories use characters, settings, and events to share ideas. Tell me the book or passage and I can help you understand it.",
    }
    return prefix + examples.get(topic, "Let’s explore it together. Can you tell me one more detail about what you want to learn? I’ll keep the explanation clear and age-appropriate.")


def classify_topic(question: str) -> str:
    text = question.lower()
    if any(word in text for word in ("star", "planet", "space", "moon", "galaxy")): return "Space"
    if any(word in text for word in ("add", "number", "fraction", "divide", "multiply", "math")): return "Maths"
    if any(word in text for word in ("plant", "animal", "water", "science", "body", "weather")): return "Science"
    if any(word in text for word in ("history", "ancient", "war", "king", "civilization")): return "History"
    if any(word in text for word in ("book", "story", "character", "read", "poem")): return "Reading"
    return "Learning"


def rate_limit(request: Request) -> None:
    identity = request.client.host if request.client else "unknown"
    current = time.monotonic()
    recent = [timestamp for timestamp in request_times[identity] if current - timestamp < 60]
    if len(recent) >= 20:
        raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": "Please wait a moment and try again."})
    recent.append(current)
    request_times[identity] = recent


def should_use_llm(requested: bool | None) -> bool:
    if not llm_ready():
        return False
    if requested is None:
        return settings.llm_enabled
    return requested


def _store_or_503(call):
    try:
        return call()
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail="Admin storage is unavailable") from exc


def _validate_thresholds(thresholds: dict[str, float]) -> None:
    if set(thresholds) != MODERATION_CATEGORIES or any(not 0 <= score <= 1 for score in thresholds.values()):
        raise HTTPException(status_code=422, detail="Every moderation category must have a score from 0 to 1")


@app.get("/health")
def health() -> dict[str, object]:
    ready = llm_ready()
    database = "ok"
    database_error = None
    try:
        store.get_response("__health_check__")
    except SupabaseStoreError as exc:
        database = "error"
        if settings.app_env != "production":
            database_error = str(exc)
    return {
        "status": "ok",
        "database": database,
        "database_error": database_error,
        "mode": "llm" if ready and settings.llm_enabled else "safe-local-demo",
        "llm_available": ready,
        "llm_enabled_default": settings.llm_enabled and ready,
        "model": settings.openai_chat_model if ready else None,
    }


@app.post("/v1/admin/login")
def admin_login(payload: AdminLoginRequest) -> dict[str, str]:
    if payload.username != "admin" or not password_matches(payload.password):
        raise HTTPException(status_code=401, detail="Invalid administrator credentials")
    return {"token": issue_admin_token()}


@app.get("/v1/admin/users", dependencies=[Depends(require_admin)])
def list_admin_users() -> list[dict[str, object]]:
    return _store_or_503(store.list_users)


@app.post("/v1/admin/users", dependencies=[Depends(require_admin)])
def create_admin_user(payload: AdminUserCreate) -> dict[str, object]:
    return _store_or_503(lambda: store.create_user(payload.name, payload.email, payload.username, hash_password(payload.password), payload.safety_profile))


@app.put("/v1/admin/users/{user_id}", dependencies=[Depends(require_admin)])
def update_admin_user(user_id: str, payload: AdminUserUpdate) -> dict[str, object]:
    values: dict[str, object] = {"display_name": payload.name, "email": payload.email, "username": payload.username}
    if payload.password:
        values["password_hash"] = hash_password(payload.password)
    return _store_or_503(lambda: store.update_user(user_id, values, payload.safety_profile))


@app.get("/v1/admin/safety-profiles", dependencies=[Depends(require_admin)])
def list_admin_safety_profiles() -> list[dict[str, object]]:
    return _store_or_503(store.list_safety_profiles)


@app.put("/v1/admin/safety-profiles/{profile_name}", dependencies=[Depends(require_admin)])
def update_admin_safety_profile(profile_name: Literal["Less than 10", "10-13", "13-15", "15-17"], payload: SafetyProfileUpdate) -> dict[str, object]:
    _validate_thresholds(payload.input_thresholds)
    _validate_thresholds(payload.output_thresholds)
    return _store_or_503(lambda: store.update_safety_profile(profile_name, payload.prompt_content, payload.input_thresholds, payload.output_thresholds))


@app.post("/v1/chat/messages", response_model=ChatResponse)
def create_message(payload: ChatRequest, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key")) -> ChatResponse:
    rate_limit(request)
    try:
        stored = store.get_response(idempotency_key)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail="Persistent storage is unavailable") from exc
    if stored is not None:
        return ChatResponse.model_validate(stored)
    decision = decide_input(payload.content)
    source: Literal["local", "llm"] = "local"
    if decision.action == "support":
        answer = safe_support_reply()
    elif decision.action == "block":
        answer = safe_block_reply()
    elif should_use_llm(payload.use_llm):
        try:
            safety_profile: SafetyProfile = store.get_active_safety_profile(payload.safety_profile)
        except SupabaseStoreError as exc:
            raise HTTPException(status_code=503, detail="Safety profile storage is unavailable") from exc
        generated = generate_learning_reply(payload.content, decision.action == "guided", safety_profile)
        if generated:
            answer = generated
            source = "llm"
        else:
            answer = local_learning_reply(payload.content, decision.action == "guided")
    else:
        answer = local_learning_reply(payload.content, decision.action == "guided")
    response = ChatResponse(
        id=str(uuid4()),
        content=answer,
        safety_state="guided" if decision.action in {"guided", "support", "block"} else "safe",
        topic=classify_topic(payload.content),
        source=source,
    )
    try:
        stored = store.save_response(idempotency_key, payload.conversation_id, response.model_dump(mode="json"))
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail="Persistent storage is unavailable") from exc
    return ChatResponse.model_validate(stored)
