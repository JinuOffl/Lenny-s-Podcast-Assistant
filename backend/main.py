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
from router import classify_skill, SHIP30_KEYWORDS, ARTIFACT_KEYWORDS
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
    fallback = first_message.strip()[:60] or "New conversation"
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
        cleaned = title.strip().strip('"').strip("'").strip()
        return cleaned[:80] if cleaned else fallback
    except Exception:
        return fallback


async def _run_multi(user_message: str, provider, conn, history=None) -> dict:
    """
    Multi-skill orchestrator — chains skills for complex queries.

    Execution plan:
      1. Retrieve rich RAG context (8 chunks)
      2. Determine needed outputs from message intent
      3. Generate primary response (essay if requested, else grounded Q&A)
      4. If artifact also requested: generate it with full essay as context
      5. Return combined result
    """
    from rag import retrieve, build_context, dedupe_sources

    msg_lower = user_message.lower()
    needs_essay    = any(k in msg_lower for k in SHIP30_KEYWORDS)
    needs_artifact = any(k in msg_lower for k in ARTIFACT_KEYWORDS)

    # Step 1: Rich RAG retrieval
    chunks  = await retrieve(user_message, conn, top_k=8)
    context = build_context(chunks)
    sources = dedupe_sources(chunks)

    # Step 2: Generate primary response
    if needs_essay:
        from skills.ship30for30 import SYSTEM_PROMPT as SP
        user_content = (
            f"TRANSCRIPT CONTEXT (ground your essay in this):\n{context}\n\n---\n\n"
            f"ESSAY REQUEST: {user_message}\n\n"
            f"Write the full Ship30for30 essay following the template above. ~1000-1250 words."
        )
        _max_tokens = 3500
    else:
        from skills.qa import SYSTEM_PROMPT as SP
        user_content = (
            f"TRANSCRIPT CONTEXT:\n{context}\n\n---\n\nQUESTION: {user_message}"
        )
        _max_tokens = 2048

    messages = list(history or []) + [{"role": "user", "content": user_content}]
    primary_response = await provider.chat(messages, system_prompt=SP, max_tokens=_max_tokens)

    # Step 3: If artifact needed, chain it with the primary response as context
    artifact = None
    if needs_artifact:
        enriched_history = list(history or []) + [
            {"role": "user",      "content": user_message},
            {"role": "assistant", "content": primary_response},
        ]
        art_result = await run_artifact(user_message, provider, conn, history=enriched_history)
        artifact = art_result.get("artifact")
        if art_result.get("sources"):
            sources = art_result["sources"]

    print(f"[multi] essay={needs_essay} artifact={needs_artifact} sources={len(sources)}")

    return {
        "response":   primary_response,
        "skill_used": "multi",
        "sources":    sources,
        "artifact":   artifact,
    }


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

    # 4. Route to skill via LLM-based agentic router
    provider = get_llm_provider(_current_provider)
    skill = await classify_skill(body.message, provider, history=history)

    async with get_conn() as conn:
        if skill == "ship30for30":
            result = await run_ship30(body.message, provider, conn, history=history)
        elif skill == "artifact":
            result = await run_artifact(body.message, provider, conn, history=history)
        elif skill == "followup":
            result = await run_qa(body.message, provider, conn, history=history, rag_context=False)
        elif skill == "multi":
            result = await _run_multi(body.message, provider, conn, history=history)
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

    provider = get_llm_provider(_current_provider)
    skill = await classify_skill(body.message, provider, history=history)
    is_first_message = len(history) == 0

    async def generate():
        full_response = []
        sources = []
        artifact = None
        skill_used = skill
        smart_title = None   # set on first message only, piped into done event

        try:
            # ── Artifact: blocking (full response needed for tag parsing) ──────
            if skill == "artifact":
                yield f"data: {json.dumps({'step': 'Searching'})}\n\n"
                async with get_conn() as conn:
                    result = await run_artifact(body.message, provider, conn, history=history)
                response_text = result["response"]
                sources = result["sources"]
                artifact = result.get("artifact")
                skill_used = result["skill_used"]
                yield f"data: {json.dumps({'token': response_text})}\n\n"
                full_response = [response_text]

            # ── Follow-up: skip RAG, history only ─────────────────────────────
            elif skill == "followup":
                yield f"data: {json.dumps({'step': 'Continuing'})}\n\n"
                from skills.qa import SYSTEM_PROMPT as SP
                messages = list(history)
                messages.append({"role": "user", "content": body.message})
                skill_used = "followup"
                async for token in provider.stream(messages, system_prompt=SP, max_tokens=2048):
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

            # ── Multi: Q&A → stream essay → artifact ──────────────────────────
            elif skill == "multi":
                skill_used = "multi"
                from rag import retrieve, build_context, dedupe_sources
                msg_lower = body.message.lower()
                needs_essay    = any(k in msg_lower for k in SHIP30_KEYWORDS)
                needs_artifact = any(k in msg_lower for k in ARTIFACT_KEYWORDS)

                # Step 1: Retrieve rich context (more chunks for multi)
                yield f"data: {json.dumps({'step': 'Searching'})}\n\n"
                async with get_conn() as conn:
                    chunks = await retrieve(body.message, conn, top_k=8)
                    context = build_context(chunks)
                    sources = dedupe_sources(chunks)

                # Step 2: Stream primary response (essay if requested, else QA)
                if needs_essay:
                    yield f"data: {json.dumps({'step': 'Writing...'})}\n\n"
                    from skills.ship30for30 import SYSTEM_PROMPT as SP
                    primary_suffix = "\n\nWrite the full Ship30for30 essay following the template. ~1000-1250 words."
                    _max_tokens = 3500
                else:
                    yield f"data: {json.dumps({'step': 'Generating...'})}\n\n"
                    from skills.qa import SYSTEM_PROMPT as SP
                    primary_suffix = ""
                    _max_tokens = 2048

                messages = list(history) + [{
                    "role": "user",
                    "content": (
                        f"TRANSCRIPT CONTEXT:\n{context}\n\n---\n\n"
                        f"{'ESSAY REQUEST' if needs_essay else 'QUESTION'}: {body.message}"
                        + primary_suffix
                    ),
                }]

                async for token in provider.stream(messages, system_prompt=SP, max_tokens=_max_tokens):
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

                # Step 3: Generate artifact if requested (blocking, after essay done)
                if needs_artifact:
                    yield f"data: {json.dumps({'step': 'Building...'})}\n\n"
                    complete_essay = "".join(full_response)
                    enriched_history = list(history) + [
                        {"role": "user",      "content": body.message},
                        {"role": "assistant", "content": complete_essay},
                    ]
                    async with get_conn() as conn:
                        art_result = await run_artifact(
                            body.message, provider, conn, history=enriched_history
                        )
                    artifact = art_result.get("artifact")

            # ── Q&A / Ship30: stream with RAG context ─────────────────────────
            else:
                yield f"data: {json.dumps({'step': 'Searching...'})}\n\n"
                from rag import retrieve, build_context, dedupe_sources
                async with get_conn() as conn:
                    chunks = await retrieve(body.message, conn, top_k=6 if skill == "ship30for30" else 5)
                    context = build_context(chunks)
                    sources = dedupe_sources(chunks)

                if skill == "ship30for30":
                    yield f"data: {json.dumps({'step': 'Writing..'})}\n\n"
                    from skills.ship30for30 import SYSTEM_PROMPT as SP
                else:
                    yield f"data: {json.dumps({'step': 'Generating...'})}\n\n"
                    from skills.qa import SYSTEM_PROMPT as SP

                messages = list(history) + [{
                    "role": "user",
                    "content": (
                        f"TRANSCRIPT CONTEXT:\n{context}\n\n---\n\n"
                        f"{'ESSAY REQUEST' if skill == 'ship30for30' else 'QUESTION'}: {body.message}"
                        + ("\n\nWrite the full Ship30for30 essay following the template above. ~1000-1250 words." if skill == "ship30for30" else "")
                    ),
                }]

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

        # Title generation OUTSIDE conn block
        # LLM call must not hold a DB connection open for 10+ seconds
        if is_first_message:
            smart_title = await _generate_title(provider, body.message)
            # Guard: never save an empty title to DB
            if not smart_title or not smart_title.strip():
                smart_title = body.message.strip()[:60] or "New conversation"
            async with get_conn() as conn2:
                await conn2.execute(
                    "UPDATE sessions SET title = %s WHERE id = %s",
                    (smart_title, session_id),
                )
            print(f"[title] generated: {smart_title!r}")

        # Final event — include new_title so frontend can update sidebar without a listSessions() call
        yield f"data: {json.dumps({'done': True, 'skill_used': skill_used, 'sources': sources, 'artifact': artifact, 'new_title': smart_title})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
