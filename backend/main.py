"""
main.py — FastAPI application entry point.

Run with:
    cd backend
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations
import json
import asyncio
from uuid import UUID
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import settings
from db import init_pool, close_pool, get_conn
from llm import get_llm_provider
from router import classify_skill
from models import (
    SessionCreate, SessionOut, SessionUpdate,
    MessageOut,
    ChatRequest, ChatResponse, ArtifactPayload, SourceItem,
    LLMConfigOut, LLMConfigSet,
)
from skills.qa import run_qa
from skills.ship30for30 import run_ship30
from skills.artifact import run_artifact

# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Lenny's Growth Assistant API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_current_provider: str = settings.llm_provider


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_history(conn, session_id: UUID, limit: int = 10) -> List[dict]:
    """Fetch last N messages for a session (oldest first)."""
    cur = await conn.execute(
        """SELECT role, content FROM messages
           WHERE session_id = %s
           ORDER BY created_at DESC LIMIT %s""",
        (session_id, limit),
    )
    rows = await cur.fetchall()
    # rows come newest-first; reverse for chronological order
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def _generate_title(provider, first_message: str) -> str:
    """Ask LLM to generate a short session title (4-6 words)."""
    try:
        title = await provider.chat(
            messages=[{
                "role": "user",
                "content": (
                    f"Generate a concise 4-6 word title for a conversation that starts with:\n"
                    f"\"{first_message[:200]}\"\n\n"
                    f"Reply with ONLY the title. No quotes, no punctuation at the end."
                ),
            }],
            system_prompt="You generate short, descriptive chat titles. Reply ONLY with the title text.",
            max_tokens=30,
        )
        return title.strip().strip('"').strip("'")[:80]
    except Exception:
        return first_message[:60]


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check():
    db_ok = False
    try:
        async with get_conn() as conn:
            await conn.execute("SELECT 1")
            db_ok = True
    except Exception as e:
        print(f"[health] DB check failed: {e}")

    provider = get_llm_provider(_current_provider)
    llm_ok = await provider.health_check()

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


@app.patch("/sessions/{session_id}", response_model=SessionOut, tags=["sessions"])
async def rename_session(session_id: UUID, body: SessionUpdate):
    """Rename a session."""
    async with get_conn() as conn:
        cur = await conn.execute(
            "UPDATE sessions SET title = %s WHERE id = %s RETURNING *",
            (body.title[:80], session_id),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Session not found")
    return SessionOut(**row)


@app.delete("/sessions/{session_id}", status_code=204, tags=["sessions"])
async def delete_session(session_id: UUID):
    """Permanently delete a session and all its messages."""
    async with get_conn() as conn:
        await conn.execute(
            "DELETE FROM messages WHERE session_id = %s", (session_id,)
        )
        await conn.execute(
            "DELETE FROM sessions WHERE id = %s", (session_id,)
        )


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


# ── Chat (blocking) ───────────────────────────────────────────────────────────

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

        # 2. Fetch conversation history BEFORE persisting current message
        history = await _get_history(conn, session_id, limit=10)

        # 3. Persist user message
        await conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, 'user', %s)",
            (session_id, body.message),
        )

    # 4. Route to skill (pass history to all skills)
    skill = classify_skill(body.message)
    provider = get_llm_provider(_current_provider)

    async with get_conn() as conn:
        if skill == "ship30for30":
            result = await run_ship30(body.message, provider, conn, history=history)
        elif skill == "artifact":
            result = await run_artifact(body.message, provider, conn, history=history)
        else:
            result = await run_qa(body.message, provider, conn, history=history)

    # 5. Persist assistant message
    artifact_json = result.get("artifact")
    sources = result.get("sources", [])

    is_first_message = len(history) == 0

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

        # 6. Generate smart title on first message
        if is_first_message and session.get("title") == "New chat":
            smart_title = await _generate_title(provider, body.message)
            await conn.execute(
                "UPDATE sessions SET title = %s WHERE id = %s",
                (smart_title, session_id),
            )

    # 7. Build response
    artifact_payload = None
    if artifact_json:
        artifact_payload = ArtifactPayload(**artifact_json)

    return ChatResponse(
        response=result["response"],
        skill_used=result["skill_used"],
        sources=[SourceItem(**s) for s in sources],
        artifact=artifact_payload,
    )


# ── Chat (streaming SSE) ──────────────────────────────────────────────────────

@app.post("/sessions/{session_id}/chat/stream", tags=["chat"])
async def chat_stream(session_id: UUID, body: ChatRequest):
    """
    Server-Sent Events endpoint for streaming chat responses.
    Events: data: {"token": "..."}\n\n
    Final:  data: {"done": true, "skill_used": "...", "sources": [...], "artifact": ...}\n\n
    """
    # 1. Verify session
    async with get_conn() as conn:
        cur = await conn.execute(
            "SELECT * FROM sessions WHERE id = %s", (session_id,)
        )
        session = await cur.fetchone()
        if not session:
            raise HTTPException(404, "Session not found")

        history = await _get_history(conn, session_id, limit=10)

        await conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, 'user', %s)",
            (session_id, body.message),
        )

    skill = classify_skill(body.message)
    provider = get_llm_provider(_current_provider)
    is_first_message = len(history) == 0

    async def generate():
        full_response = []
        sources = []
        artifact = None
        skill_used = skill

        try:
            # For artifact skill: use blocking (needs full response for parsing)
            if skill == "artifact":
                async with get_conn() as conn:
                    result = await run_artifact(body.message, provider, conn, history=history)
                response_text = result["response"]
                sources = result["sources"]
                artifact = result.get("artifact")
                skill_used = result["skill_used"]
                # Yield the full text as one chunk
                yield f"data: {json.dumps({'token': response_text})}\n\n"
                full_response = [response_text]
            else:
                # Q&A and Ship30 can stream
                from rag import retrieve, build_context, dedupe_sources
                async with get_conn() as conn:
                    chunks = await retrieve(body.message, conn, top_k=6 if skill == "ship30for30" else 5)
                    context = build_context(chunks)
                    sources_list = dedupe_sources(chunks)

                sources = sources_list
                if skill == "ship30for30":
                    from skills.ship30for30 import SYSTEM_PROMPT as SP
                else:
                    from skills.qa import SYSTEM_PROMPT as SP

                messages = list(history)
                messages.append({
                    "role": "user",
                    "content": (
                        f"TRANSCRIPT CONTEXT:\n{context}\n\n---\n\n"
                        f"{'ESSAY REQUEST' if skill == 'ship30for30' else 'QUESTION'}: {body.message}"
                        + ("\n\nWrite the full Ship30for30 essay following the template above. ~1000-1250 words." if skill == "ship30for30" else "")
                    ),
                })

                async for token in provider.stream(messages, system_prompt=SP, max_tokens=3500 if skill == "ship30for30" else 2048):
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # Persist assistant message
        complete_text = "".join(full_response)
        async with get_conn() as conn:
            await conn.execute(
                """INSERT INTO messages
                   (session_id, role, content, skill_used, artifact_json, sources)
                   VALUES (%s, 'assistant', %s, %s, %s, %s)""",
                (
                    session_id,
                    complete_text,
                    skill_used,
                    json.dumps(artifact) if artifact else None,
                    json.dumps(sources) if sources else None,
                ),
            )
            # Smart title on first message
            if is_first_message and session.get("title") == "New chat":
                smart_title = await _generate_title(provider, body.message)
                await conn.execute(
                    "UPDATE sessions SET title = %s WHERE id = %s",
                    (smart_title, session_id),
                )

        # Final event
        yield f"data: {json.dumps({'done': True, 'skill_used': skill_used, 'sources': sources, 'artifact': artifact})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
