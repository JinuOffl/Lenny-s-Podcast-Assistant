# Phase 1 Plan — Lenny's Growth Assistant
## Goal: Full end-to-end working app (backend + frontend + both LLMs + all 3 skills)

---

## Pre-flight checklist (do first, in order)

- [ ] Ingest finished → terminal shows "Ingest complete! Total chunks stored: X"
- [ ] Run this SQL in Supabase SQL Editor (builds vector index — needs data to exist first):
  ```sql
  CREATE INDEX ON transcript_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
  ```
- [ ] Confirm `.env` exists at `D:\Lenny's Growth Assistant\` (project root) with all vars set
- [ ] Ollama running: `ollama ps` should show `llama3.3:8b` or it should start on first request
- [ ] Bootstrap DB schema (if not already done):
  ```powershell
  cd "D:\Lenny's Growth Assistant\backend"
  python db.py
  # Expected: "Schema applied successfully."
  ```

---

## Step 1 — Install backend deps and start server

```powershell
cd "D:\Lenny's Growth Assistant\backend"
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

If it errors on startup → likely a missing dep or wrong DATABASE_URL. Fix before continuing.

---

## Step 2 — Verify /health endpoint

```powershell
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "ok",
  "database": true,
  "ollama_llm": true,
  "ollama": true,
  "active_provider": "ollama"
}
```

**If `database: false`** → DATABASE_URL wrong or Supabase unreachable  
**If `ollama_llm: false`** → Ollama not running, run `ollama serve` in another terminal  
**Do not proceed to Step 3 until health is all true.**

---

## Step 3 — Test session creation

```powershell
curl -X POST http://localhost:8000/sessions `
  -H "Content-Type: application/json" `
  -d '{"title": "test session"}'
```

Copy the `id` from the response. Use it as `SESSION_ID` below.

---

## Step 4 — Test all 3 skills via curl

### Skill 1: Q&A (default)
```powershell
curl -X POST http://localhost:8000/sessions/SESSION_ID/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "What did Brian Chesky say about company culture?"}'
```
Expected: `skill_used: "qa"`, `sources` array with YouTube URLs, `artifact: null`

### Skill 2: Ship30for30 essay
```powershell
curl -X POST http://localhost:8000/sessions/SESSION_ID/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "Write a Ship30for30 essay about product-market fit"}'
```
Expected: `skill_used: "ship30for30"`, long essay in `response`, `artifact: null`

### Skill 3: Artifact
```powershell
curl -X POST http://localhost:8000/sessions/SESSION_ID/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "Create an HTML page summarizing the top growth frameworks from the podcast"}'
```
Expected: `skill_used: "artifact"`, `artifact.type: "html"`, `artifact.content` contains full HTML

---

## Step 5 — Test LLM provider switch

```powershell
# Switch to Anthropic
curl -X POST http://localhost:8000/config/llm `
  -H "Content-Type: application/json" `
  -d '{"llm_provider": "anthropic"}'

# Ask same question — should use Claude now
curl -X POST http://localhost:8000/sessions/SESSION_ID/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "What do podcast guests say about retention?"}'

# Switch back to Ollama
curl -X POST http://localhost:8000/config/llm `
  -H "Content-Type: application/json" `
  -d '{"llm_provider": "ollama"}'
```

---

## Step 6 — Verify frontend wiring

Frontend is already running at `http://localhost:5173`

Checklist:
- [ ] Page loads without console errors
- [ ] Click "New chat" → creates session, sidebar updates
- [ ] Type a message → thinking dots appear → response renders with markdown
- [ ] Skill badge shows (QA / Essay / Artifact)
- [ ] Sources accordion expands with episode links
- [ ] Send artifact request → artifact pane slides in on right
- [ ] Preview tab shows rendered HTML (in iframe) or markdown
- [ ] Source tab shows raw code with copy button
- [ ] LLM toggle in header switches provider
- [ ] Refresh page → sessions still in sidebar (DB persistence confirmed)

---

## Known failure points + fixes

| Symptom | Cause | Fix |
|---|---|---|
| `uvicorn` crashes on import | Missing package | `pip install -r requirements.txt` |
| `asyncpg` or pool error on startup | Wrong DB URL format | Must be `postgresql://` not `postgres://` |
| `/chat` returns 500, logs show embedding error | Ollama not running | `ollama serve` in separate terminal |
| `/chat` returns empty `sources: []` | Ingest not finished yet | Wait for ingest, then retry |
| Artifact pane doesn't open | LLM forgot `<artifact>` tags | Already handled by fallback in `artifact.py` |
| `anthropic` returns 401 | Bad API key | Check `.env` ANTHROPIC_API_KEY |
| Frontend `fetch` errors (CORS) | Backend not running | Start `uvicorn` first |
| Router sends "write me a table" to artifact instead of qa | Known edge case | Add "table" to qa keywords in `router.py` if needed |

---

## Files you may need to debug/edit in Phase 1

| File | Why you'd touch it |
|---|---|
| `backend/main.py` | Add missing error handling, fix 422 validation errors |
| `backend/rag.py` | Tune `RAG_TOP_K`, fix pgvector query if retrieval returns empty |
| `backend/router.py` | Adjust keywords if skill routing misfires |
| `backend/skills/artifact.py` | Tweak regex if `<artifact>` extraction fails |
| `frontend/src/api.js` | Change `BASE_URL` if port changes |
| `frontend/src/App.jsx` | Fix any state bugs in message flow |

---

## Phase 1 done criteria (all must pass before Phase 2)

- [ ] `/health` returns `status: ok` with DB + Ollama both true
- [ ] All 3 skills return correct `skill_used` value
- [ ] Q&A response cites a specific guest by name
- [ ] Essay response is ~1000+ words with Ship30for30 structure
- [ ] Artifact response renders in the iframe/markdown pane
- [ ] Both Ollama and Anthropic work end-to-end
- [ ] Sessions persist after browser refresh
- [ ] No unhandled 500 errors on normal usage

---

## What Phase 2 covers (don't start this in Phase 1)
- Ship30for30 + artifact skill polish
- Frontend UX polish (empty states, loading, error toasts)
- docs/README final pass
- Video recording
- agent-transcripts/LESSONS.md update
