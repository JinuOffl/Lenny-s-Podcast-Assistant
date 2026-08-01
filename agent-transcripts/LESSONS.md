# Agent Transcripts & Lessons

This folder documents the actual AI-assisted build process — including failures, corrections, and lessons learned.
Required deliverable per assignment spec.

Format: `[date] Symptom → Root cause → Fix`

---

## Lessons

### 2026-07-31 — Brief corrections (pre-build)

- **MiniLM 256-token truncation** → Using `all-MiniLM-L6-v2` embeds a 10k-word transcript as its first ~200 words. Retrieval on anything past minute 3 of the episode fails silently. → Switched to `nomic-embed-text` (8k context window, 768 dims) via Ollama.
- **`claude-sonnet-4.6` is not a real model string** → The original brief named a non-existent Anthropic model. → Corrected to `claude-sonnet-5` (verified against Anthropic docs).
- **SQLite was proposed** → The assignment rubric explicitly requires "persistently stored in a Postgres database... Supabase or Railway." → Changed to Supabase Postgres.
- **ChromaDB was proposed as a separate vector store** → Unnecessary second database once Supabase is the primary DB. → Used `pgvector` extension in the same Supabase instance — one connection string, one schema.

---

### 2026-08-01 — Windows async event loop crash

- **Symptom:** `uvicorn` crashed on startup with `NotImplementedError` immediately after `init_pool()` was called.
- **Root cause:** Windows defaults to `ProactorEventLoop` in Python 3.10+. `psycopg3`'s `AsyncConnectionPool` requires `SelectorEventLoop` on Windows — it uses `select()` internally, which `ProactorEventLoop` doesn't support.
- **Fix:** Added `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` at the top of `db.py`, before any psycopg imports. Also added it to the `if __name__ == "__main__"` block for standalone `python db.py` runs.

---

### 2026-08-01 — `.env` location confusion (backend couldn't find DATABASE_URL)

- **Symptom:** App started without errors but `/health` returned `database: false`. DB pool had no connection string.
- **Root cause:** The user created `.env` at `backend/.env`. `config.py` (using `pydantic-settings`) searched for it relative to the file's location, but the path resolution was wrong when uvicorn was started from the `backend/` directory.
- **Fix:** Updated `config.py` to check both `../.env` (project root) and `./.env` (backend/) in that order. Also confirmed `.env.example` documents both valid locations.

---

### 2026-08-01 — Router misclassified broad queries as `artifact`

- **Symptom:** "Generate a list of retention frameworks" and "Build a case for product-led growth" opened the artifact pane instead of answering as Q&A.
- **Root cause:** `ARTIFACT_KEYWORDS` included overly broad terms: `"generate"`, `"table"`, `"render"`, `"build a"`, `"build an"`. These match common Q&A phrasing.
- **Fix:** Removed all broad terms from `ARTIFACT_KEYWORDS`. Artifact routing now requires specific HTML/visual/code intent (e.g., `"create an html"`, `"build a dashboard"`, `"generate a chart"`). Verified with 15-case test suite: 15/15 pass.

---

### 2026-08-01 — Empty `sources: []` despite app running

- **Symptom:** Chat returned responses but `sources` was always an empty array. LLM said it had "no context from the podcast."
- **Root cause:** `ingest.py` had not finished running when the app was first tested. The `transcript_chunks` table was empty, so `retrieve()` returned 0 rows, and `build_context()` produced an empty string.
- **Fix:** Waited for ingest to complete (~15 min for 180 episodes × ~25 chunks each = 4,604 chunks). After ingest, retrieval returned relevant chunks correctly.

---

### 2026-08-01 — PowerShell `curl` alias conflict

- **Symptom:** Running `curl http://localhost:8000/health` in PowerShell returned: `Invoke-WebRequest: A positional parameter cannot be found that accepts argument 'http://localhost:8000/health'`
- **Root cause:** PowerShell aliases `curl` to `Invoke-WebRequest`, not the system `curl.exe`. `Invoke-WebRequest` uses named parameters, not positional URL.
- **Fix:** Used `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing | Select-Object -ExpandProperty Content` throughout. Documented this in the README troubleshooting section.

---

### 2026-08-01 — pgvector `::vector` cast required for psycopg3

- **Symptom:** pgvector cosine distance query (`embedding <=> %s`) raised a type error: `cannot cast type double precision[] to vector`.
- **Root cause:** psycopg3 sends Python lists as `double precision[]` (Postgres array type). pgvector's `<=>` operator expects the `vector` type specifically.
- **Fix:** Format the embedding list as a bracketed string and explicitly cast: `embedding <=> %s::vector`. Pass the embedding as `"[0.1, 0.2, ...]"` string rather than a Python list.

---

### 2026-08-01 — IVFFlat index must be created AFTER data exists

- **Symptom:** Attempted to create the IVFFlat index in the schema DDL bootstrap (`python db.py`), but it failed silently — the index wasn't created.
- **Root cause:** IVFFlat's `lists` parameter (number of clusters) requires existing data to compute cluster centroids. Creating the index on an empty table produces a degenerate index that doesn't speed up queries.
- **Fix:** Commented out the index creation in `SCHEMA_SQL`. Created a separate `check_db.py` script that creates the index only after confirming `transcript_chunks` has rows. Final index: `USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`.

---

### 2026-08-01 — Ollama `/api/chat` default returns streaming NDJSON

- **Symptom:** `urllib.request.urlopen` on Ollama's `/api/chat` returned a partial response — `json.loads()` failed with `JSONDecodeError: Extra data`.
- **Root cause:** Ollama's `/api/chat` streams responses as newline-delimited JSON by default. `urllib` reads the full byte stream, which contains multiple JSON objects concatenated.
- **Fix:** Added `"stream": false` to the Ollama request payload. This returns a single JSON object with the complete response.

---

---

### 2026-08-01 — Claude Sonnet 4.6 hit token limit mid-execution (Phase 1 handoff)

- **Symptom:** The coding agent (Claude Sonnet 4.6) was executing the Phase 1 implementation plan — fixing the race condition, adding streaming, session rename/delete, smart title generation, and conversation history. It completed all of those but hit its context window limit before finishing P3 (LLM-based agentic router).
- **Root cause:** The combined token count of the full codebase (read into context), the implementation plan, and the generated code exceeded the model's context window mid-way through P3.
- **Fix / Lesson:** Always break large implementation plans into phases with explicit handoff documents. The `phase0_handoff.md` and `phase1_plan.md` files were generated *before* execution so the next agent session could resume without re-reading all code from scratch. The new session picked up from `phase 1 implementation_plan` and continued.
- **What was lost:** None — all work was committed before the limit hit. The handoff file contained a precise "left off at P3" marker.

---

### 2026-08-01 — First user message disappeared (optimistic UI race condition)

- **Symptom:** When a user typed their first message in a new session, the message bubble briefly appeared then vanished.
- **Root cause:** `App.jsx` was calling `setMessages([userMsg])` (optimistic update) *before* `createSession()` resolved. The session creation returned a new ID, which triggered a re-render that cleared the message list.
- **Fix:** Moved session creation to happen *first* with `await createSession()`, stored the returned `session.id`, *then* called `setMessages()` to add the user bubble. Sequence: `createSession → setActiveSessionId → setMessages → streamChat`.

---

### 2026-08-01 — `<think>...</think>` blocks leaking into UI (qwen3:4b)

- **Symptom:** qwen3:4b prefixes its reasoning with `<think>I need to consider...</think>` before giving the actual answer. This raw XML appeared in the chat UI.
- **Root cause:** qwen3's "thinking mode" is enabled by default. The blocking `chat()` call returned the full raw string including think tags.
- **Fix (blocking):** Added `strip_thinking_tags()` in `llm.py` using `re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)` applied after every `provider.chat()` call.
- **Fix (streaming):** The stream handler needed state-machine logic — buffering tokens and detecting `<think>`/`</think>` open/close to suppress the thinking block mid-stream without buffering the entire response.

---

### 2026-08-01 — Keyword router couldn't handle complex multi-intent queries

- **Symptom:** User query "Write a Ship30for30 essay about retention AND create an HTML visualization" — the keyword router returned `ship30for30` (first match wins), discarding the artifact request entirely.
- **Root cause:** `router.py` used sequential `if/elif` keyword matching. It couldn't detect that a message had *two* intents.
- **Fix:** Replaced with an LLM-based classifier (`classify_skill()` is now `async`). The LLM is given a prompt listing 5 skill types including `multi` (for compound requests). A keyword fallback preserves reliability if the LLM fails. Multi-skill chaining: the backend runs RAG → essays stream → artifact is generated after stream completes → returned in the SSE `done` event.

---

### 2026-08-01 — Streaming SSE buffering on Windows / Nginx-less setup

- **Symptom:** Streaming responses from `/chat/stream` appeared to buffer and deliver all at once, not token-by-token.
- **Root cause:** FastAPI's `StreamingResponse` works correctly, but some HTTP clients and proxies buffer SSE by default. Also, Ollama's streaming generator on Windows runs in a thread executor — the `asyncio.Queue` bridge between the sync thread and async generator had a subtle race.
- **Fix:** Added `headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}` to `StreamingResponse`. Also ensured `loop.call_soon_threadsafe(queue.put_nowait, token)` is used (not `await queue.put()`) from the thread executor to avoid cross-thread asyncio violations.

