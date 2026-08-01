"""
main.py — FastAPI application entry point.

Run with:
    cd backend
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations
import json
from uuid import UUID
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import init_pool, close_pool, get_conn
from llm import get_llm_provider
from router import classify_skill
from models import (
    SessionCreate, SessionOut,
    MessageOut,
    ChatRequest, ChatResponse, ArtifactPayload, SourceItem,
    LLMConfigOut, LLMConfigSet,
)
from skills.qa import run_qa
from skills.ship30for30 import run_ship30
from skills.artifact import run_artifact

# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Lenny's Growth Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory provider state (per-process, reset on restart) ─────────────────
# For a multi-worker setup, move this to the DB config table.
_current_provider: str = settings.llm_provider


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check():
    """
    Checks DB connectivity + Ollama/Anthropic reachability.
    Returns a status dict for each dependency.
    """
    db_ok = False
    try:
        async with get_conn() as conn:
            await conn.execute("SELECT 1")
            db_ok = True
    except Exception as e:
        # Pool exhausted, connection refused, or Supabase unreachable
        print(f"[health] DB check failed: {e}")

    provider = get_llm_provider(_current_provider)
    llm_ok = await provider.health_check()

    # Ollama always check (even if Anthropic is selected)
    from llm import OllamaProvider
    ollama_ok = await OllamaProvider().health_check()

    return {
        "status": "ok" if (db_ok and llm_ok) else "degraded",
        "database": db_ok,
        f"{_current_provider}_llm": llm_ok,
        "ollama": ollama_ok,
        "active_provider": _current_provider,
    }


# ── Config ────────────────────────────────────────────────────────────────────

@app.get("/config/llm", response_model=LLMConfigOut, tags=["config"])
async def get_llm_config():
    return LLMConfigOut(
        llm_provider=_current_provider,
        ollama_chat_model=settings.ollama_chat_model,
        anthropic_model=settings.anthropic_model,
    )


@app.post("/config/llm", response_model=LLMConfigOut, tags=["config"])
async def set_llm_config(body: LLMConfigSet):
    global _current_provider
    if body.llm_provider not in ("ollama", "anthropic"):
        raise HTTPException(400, "llm_provider must be 'ollama' or 'anthropic'")
    _current_provider = body.llm_provider
    return LLMConfigOut(
        llm_provider=_current_provider,
        ollama_chat_model=settings.ollama_chat_model,
        anthropic_model=settings.anthropic_model,
    )


# ── Sessions ──────────────────────────────────────────────────────────────────

@app.post("/sessions", response_model=SessionOut, status_code=201, tags=["sessions"])
async def create_session(body: SessionCreate):
    async with get_conn() as conn:
        cur = await conn.execute(
            "INSERT INTO sessions (title, llm_provider) VALUES (%s, %s) RETURNING *",
            (body.title, body.llm_provider),
        )
        row = await cur.fetchone()
    return SessionOut(**row)


@app.get("/sessions", response_model=List[SessionOut], tags=["sessions"])
async def list_sessions():
    async with get_conn() as conn:
        cur = await conn.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 50"
        )
        rows = await cur.fetchall()
    return [SessionOut(**r) for r in rows]


# ── Messages ──────────────────────────────────────────────────────────────────

@app.get(
    "/sessions/{session_id}/messages",
    response_model=List[MessageOut],
    tags=["messages"],
)
async def get_messages(session_id: UUID):
    async with get_conn() as conn:
        cur = await conn.execute(
            "SELECT * FROM messages WHERE session_id = %s ORDER BY created_at ASC",
            (session_id,),
        )
        rows = await cur.fetchall()
    return [MessageOut(**r) for r in rows]


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post(
    "/sessions/{session_id}/chat",
    response_model=ChatResponse,
    tags=["chat"],
)
async def chat(session_id: UUID, body: ChatRequest):
    # 1. Verify session exists
    async with get_conn() as conn:
        cur = await conn.execute(
            "SELECT * FROM sessions WHERE id = %s", (session_id,)
        )
        session = await cur.fetchone()
        if not session:
            raise HTTPException(404, "Session not found")

        # 2. Persist user message
        await conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, 'user', %s)",
            (session_id, body.message),
        )

    # 3. Route to skill
    skill = classify_skill(body.message)
    provider = get_llm_provider(_current_provider)

    async with get_conn() as conn:
        if skill == "ship30for30":
            result = await run_ship30(body.message, provider, conn)
        elif skill == "artifact":
            result = await run_artifact(body.message, provider, conn)
        else:
            result = await run_qa(body.message, provider, conn)

    # 4. Persist assistant message
    artifact_json = result.get("artifact")
    sources = result.get("sources", [])

    async with get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO messages
                (session_id, role, content, skill_used, artifact_json, sources)
            VALUES (%s, 'assistant', %s, %s, %s, %s)
            """,
            (
                session_id,
                result["response"],
                result["skill_used"],
                json.dumps(artifact_json) if artifact_json else None,
                json.dumps(sources) if sources else None,
            ),
        )

        # Update session title from first user message if still default
        await conn.execute(
            """
            UPDATE sessions
            SET title = LEFT(%s, 60)
            WHERE id = %s AND title = 'New chat'
            """,
            (body.message, session_id),
        )

    # 5. Build response
    artifact_payload = None
    if artifact_json:
        artifact_payload = ArtifactPayload(**artifact_json)

    return ChatResponse(
        response=result["response"],
        skill_used=result["skill_used"],
        sources=[SourceItem(**s) for s in sources],
        artifact=artifact_payload,
    )
