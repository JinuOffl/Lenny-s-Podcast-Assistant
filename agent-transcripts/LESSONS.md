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

*(Append new lessons here as the build progresses)*
