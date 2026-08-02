# Architecture: Lenny's Growth Assistant

**Version:** 0.4 — Dual-Mode: Classic (Agentic Router) + Research Mode (5-Agent CrewAI Pipeline)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User's Browser                             │
│   React 18 + Vite + Tailwind                                        │
│   ┌──────────┐  ┌──────────────────────┐  ┌───────────────────┐   │
│   │ Sidebar  │  │      Chat Pane       │  │   Artifact Pane   │   │
│   │ sessions │  │ streaming messages   │  │ iframe / markdown │   │
│   │ 3-dot ⋯  │  │ ThinkingDots + SSE   │  │ Preview + Source  │   │
│   └──────────┘  └──────────────────────┘  └───────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │ SSE stream (token-by-token)
┌───────────────────────────▼─────────────────────────────────────────┐
│                    FastAPI Backend (port 8000)                       │
│                                                                      │
│   POST /sessions/{id}/chat/stream   ← primary endpoint              │
│        │                                                             │
│        ├─ fetch history (last 10 msgs) from DB                       │
│        │                                                             │
│        ▼                                                             │
│   router.classify_skill(msg, provider, history)                      │
│        │    LLM call (max_tokens=12) → one of 5 intents             │
│        │    keyword fallback if LLM fails                            │
│        │                                                             │
│        ├── "qa"          → RAG retrieve → qa.py → stream tokens     │
│        ├── "ship30for30" → RAG retrieve → ship30.py → stream tokens │
│        ├── "artifact"    → RAG retrieve → artifact.py → yield full  │
│        ├── "followup"    → history only → qa.py → stream tokens     │
│        └── "multi"       → RAG (top_k=8)                            │
│                              → stream essay/QA                      │
│                              → run_artifact() with essay as context  │
│                              → return artifact in done event         │
│                                                                      │
│        ▼ (after stream completes)                                    │
│   persist complete message → Supabase                                │
│   generate smart title on msg #1 (LLM, max_tokens=30)               │
│   emit: {done:true, skill_used, sources, artifact}                  │
└────────────┬─────────────────────────────────────────────────────────┘
             │
    ┌────────┴──────────────────────────────────────┐
    │           Supabase Postgres (pgvector)         │
    │   sessions │ messages │ transcript_chunks      │
    └────────────┴──────────────────────────────────┘
             │
    ┌────────┴───────────────────────┐
    │            Ollama              │
    │  qwen3:4b (chat + routing)     │
    │  nomic-embed-text (embeddings) │
    └────────────────────────────────┘
```

---

## Key Design Decisions

### 1. LLM-based Agentic Router

**Decision:** Classify user intent with a real LLM call, with keyword-match fallback.

**Why:** Keyword matching cannot detect multi-intent queries (e.g., "write an essay AND create a chart") or understand conversational context (e.g., "convert this into an essay" referring to a prior QA answer). An LLM classifier reasons about the full message + last 2 turns of history.

**Implementation:**
- `classify_skill(message, provider, history)` is async
- Makes one LLM call with `max_tokens=12` — returns one word
- Valid outputs: `qa`, `ship30for30`, `artifact`, `multi`, `followup`
- If LLM returns unexpected output or fails → falls back to keyword matching
- `multi` triggers a 3-step chain: RAG retrieval → stream primary response (essay/QA) → generate artifact with essay as context

**Trade-off:** Adds ~1-2s latency per message for the routing LLM call. Acceptable since the main skill LLM call takes 10-60s anyway. The `followup` fast-path (pure string matching, no LLM) keeps short messages instant.

### 2. Retrieval-sourced Citations

**Decision:** Sources (`guest`, `episode_title`, `youtube_url`) come from the retrieval step, not from the LLM's output.

**Reasoning:** LLMs hallucinate citations. The retrieval step already has the ground truth — we just surface it. This makes citations 100% accurate (they point to chunks that were actually used as context) and removes a whole class of hallucination risk.

### 3. nomic-embed-text over MiniLM

**Decision:** Use `nomic-embed-text` (8192 token context, 768 dims) for embeddings.

**Reasoning:** `all-MiniLM-L6-v2` truncates at 256 tokens (~200 words). A 10,000-word podcast transcript embedded with MiniLM is represented only by its first 200 words — retrieval on anything said after the opening is effectively random. `nomic-embed-text` handles our 700-token chunks comfortably with full fidelity, and it runs locally via Ollama (already a dependency).

### 4. No Streaming for MVP

**Decision:** Request/response JSON only — no SSE streaming.

**Reasoning:** The artifact skill wraps LLM output in `<artifact type="...">` tags. These tags can only be reliably regex-extracted from the *complete* response. Streaming would require buffering the full response anyway (negating the UX benefit), or a more complex state machine to detect tag boundaries mid-stream. Streaming is P2 (Sunday only, if time allows).

### 5. pgvector in Same DB

**Decision:** Vector search via pgvector extension in the same Supabase Postgres, not a separate vector DB.

**Reasoning:** At ~5,000-10,000 chunks, pgvector's IVFFlat index is fast enough (sub-100ms cosine queries). A separate vector DB (Pinecone, Chroma, Weaviate) adds a second external dependency, a second connection string to manage, and a second failure mode. The "one connection string, one schema, one thing to explain" argument is also strong for a solo demo.

---

## Data Flow: Chat Request

```
1. POST /sessions/{id}/chat {message: "What did Chesky say about culture?"}
2. classify_skill("...") → "qa"
3. rag.get_embedding(message) → [768 floats]  via nomic-embed-text
4. pgvector: SELECT chunks ORDER BY embedding <=> query_vec LIMIT 5
5. build_context(chunks) → formatted text block
6. llm.chat([{role:"user", content: context + question}], system_prompt)
7. OllamaProvider → POST /api/chat to local Ollama → response text
8. INSERT message (role=assistant, content, skill_used, sources) into Supabase
9. Return ChatResponse JSON to frontend
```

---

## Database Schema

See `backend/db.py` for full DDL. Three tables:
- `sessions` — conversation containers
- `messages` — user + assistant turns with skill metadata
- `transcript_chunks` — chunked transcript text + 768-dim embedding vectors

---

## Scaling Path (not implemented, documented for the demo)

| Dimension | Current MVP | Scale-up (no architecture change) |
|---|---|---|
| Episodes | ~60 curated | 269 — change CURATED_INDEX_FILES in ingest.py |
| Vector index | IVFFlat (lists=100) | HNSW for better recall at larger scale |
| Concurrent users | Single-process Uvicorn | Gunicorn workers + connection pool tuning |
| Provider | Ollama \| Anthropic | Add `GeminiProvider`, etc. — implement LLMProvider ABC |

---

## Research Mode — 5-Agent Multi-Agent Pipeline

**Version 0.4** adds a second execution mode accessible via the "Research" toggle near the chat input.
It runs a 5-agent pipeline that goes beyond the Classic mode's keyword router.

### Agent Roster

| Agent | Role | Runs When | Key Capability |
|---|---|---|---|
| **OrchestratorAgent** | Research Planner | Always, first | LLM-powered plan: decides crew type, refines search queries |
| **ResearchAgent** | Transcript Researcher | Always (except followup) | Multi-hop RAG: 1-2 search passes, cross-episode synthesis |
| **WriterAgent** | Content Generator | Always | Streams QA answers or Ship30for30 essays with guest comparisons |
| **ArtifactAgent** | Dashboard Builder | If artifact requested | Generates interactive HTML dashboards with Chart.js/Plotly |
| **ValidatorAgent** | QC + Self-Healer | Last, always | HTML validation + self-healing loop (max 2 attempts) |

### Execution Flow

```
Phase 1 ─► OrchestratorAgent (2-3s)
            LLM call → JSON plan: crew type, refined query, complexity

Phase 2 ─► ResearchAgent (5-8s)
            execute_search() → assess_quality() → multi-hop if thin
            Fills SharedContext: chunks, sources, context_text

Phase 3 ─► WriterAgent ──────┐  asyncio.gather() — PARALLEL
            (streams tokens) │
            ArtifactAgent ───┘  (background — builds HTML silently)

Phase 4 ─► ValidatorAgent (2-3s)
            validate_html() → self-heal loop if broken → confidence score
```

### Parallelism Design

WriterAgent and ArtifactAgent both need the same research output (Phase 2 result).
Once Phase 2 completes, they run concurrently using `asyncio.gather()`:
- WriterAgent streams tokens immediately → user sees text at ~8s
- ArtifactAgent builds silently in background → appears when writer finishes

### New SSE Event Types (Research Mode)

```json
{"agent": "ResearchAgent", "step": "🔍 Searching transcripts...", "sources_found": 6}
{"agent": "ValidatorAgent", "step": "🔧 Self-healing artifact (attempt 1/2) — Unclosed script tag"}
{"token": "When Brian Chesky told Lenny..."}
{"done": true, "skill_used": "research:ship30for30", "confidence": "high",
 "healing_attempts": 1, "agent_steps": [...], "research_stats": {...}}
```

### SharedContext — Agent Working Memory

```python
@dataclass
class SharedContext:
    user_query: str          # Original user message
    history: list            # Conversation history
    plan: ExecutionPlan      # OrchestratorAgent's plan
    chunks: list             # Raw transcript chunks from ResearchAgent
    sources: list            # Deduped episode sources
    context_text: str        # Formatted context for LLM prompts
    primary_response: str    # WriterAgent's output (accumulated from stream)
    artifact: dict | None    # ArtifactAgent's HTML/MD output
    confidence: str          # "high" | "medium" | "low" (based on source count)
    heal_attempts: int       # How many self-healing attempts ran
    agent_steps: list        # Full trace of all agent actions
```

### Self-Healing Architecture

```
ArtifactAgent generates HTML
         │
ValidatorAgent.validate_html(content)
         │
    Error?  ──── No ──► ✅ Done
         │
        Yes
         │
         ▼
Emit SSE: {"step": "🔧 Self-healing — [error description]"}
         │
ArtifactAgent re-runs with error injected into prompt
         │
ValidatorAgent.validate_html(new_content)
         │
    Error?  ──── No ──► ✅ Healed! Emit success event
         │
    Attempt 2 → on failure → graceful degradation
```

### Endpoint

```
POST /sessions/{session_id}/chat/research/stream
```

Classic endpoint (`/chat/stream`) is **unchanged** — Research Mode is purely additive.

### New File Structure

```
backend/
├── agents/
│   ├── shared_context.py   ← SharedContext + ExecutionPlan dataclasses
│   ├── orchestrator.py     ← OrchestratorAgent (LLM JSON planner)
│   ├── research.py         ← ResearchAgent (multi-hop RAG)
│   ├── writer.py           ← WriterAgent (streaming QA + essay)
│   ├── artifact_agent.py   ← ArtifactAgent (HTML generation + self-heal)
│   ├── validator.py        ← ValidatorAgent (QC + self-healing loop)
│   └── crew_runner.py      ← Pipeline orchestrator (parallel execution)
└── tools/
    ├── search_tool.py      ← execute_search(), execute_multi_hop_search()
    ├── validate_tool.py    ← validate_html(), validate_essay()
    └── count_tool.py       ← word/citation counting utilities
```
