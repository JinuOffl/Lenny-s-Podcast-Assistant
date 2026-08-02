# Architecture: Lensight (Lenny's Growth Assistant)

**Version:** 0.5 — Dual-Mode: Classic (Agentic Router) + Research Mode (5-Agent Pipeline)  
**Status:** Production-complete

---

## System Overview

```
+-----------------------------------------------------------------------------------+
|                                  USER BROWSER                                     |
|   React 18 + Vite + Tailwind CSS                         localhost:5173            |
|                                                                                   |
|  +---------------------+  +----------------------------+  +--------------------+  |
|  |   Session Sidebar   |  |   Chat Pane  (SSE Stream)  |  |  Artifact Pane     |  |
|  |   [SessionSidebar]  |  |   [ChatMessage]            |  |  [ArtifactPane]    |  |
|  |                     |  |   Streaming tokens +        |  |  Sandboxed iframe  |  |
|  |  - Chat history     |  |   Agent step trackers      |  |  HTML preview      |  |
|  |  - Rename / Delete  |  |   [AgentTracker]           |  |  Source toggle     |  |
|  |  - New Chat         |  |   [ResearchStats]          |  |                    |  |
|  +---------------------+  +----------------------------+  +--------------------+  |
|                                                                                   |
|  +----------------------------+          +-----------------------------------+    |
|  |  ChatInput [ChatInput.jsx] |          |  Toggles                          |    |
|  |  Text area + submit        |          |  [ResearchModeToggle]             |    |
|  +----------------------------+          |  [ProviderToggle] Ollama/Anthropic |    |
|                                          +-----------------------------------+    |
+------------------------------------------+----------------------------------------+
                                           |
                       HTTP / Server-Sent Events (SSE)
                       POST /sessions/{id}/chat/stream
                       POST /sessions/{id}/chat/research/stream
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             FASTAPI BACKEND  [main.py]                            |
|                              Python 3.11 . Uvicorn . :8000                        |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                         EXECUTION MODE SELECTOR                             |  |
|  |                                                                             |  |
|  |  +------------------------------------+  +--------------------------------+ |  |
|  |  |          CLASSIC MODE              |  |       RESEARCH MODE            | |  |
|  |  |   (Direct skill pipeline)          |  |   (5-Agent Pipeline)           | |  |
|  |  |   [router.py]                      |  |   [agents/crew_runner.py]      | |  |
|  |  |                                    |  |                                | |  |
|  |  |  Stage 1: instant followup check   |  |  Phase 1: OrchestratorAgent   | |  |
|  |  |  Stage 2: LLM classify (12 tokens) |  |           -> ExecutionPlan    | |  |
|  |  |                                    |  |  Phase 2: ResearchAgent        | |  |
|  |  |  -> qa          [skills/qa.py]     |  |           -> multi-hop RAG    | |  |
|  |  |  -> ship30for30 [skills/ship30.py] |  |  Phase 3: WriterAgent (stream)| |  |
|  |  |  -> artifact    [skills/artifact.py|  |         + ArtifactAgent (bg)  | |  |
|  |  |  -> multi       (ship30 + artifact)|  |  Phase 4: ValidatorAgent      | |  |
|  |  |  -> followup    (history-only)     |  |           -> self-healing loop | |  |
|  |  +------------------------------------+  +--------------------------------+ |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  +---------------------------+  +---------------------------------------------+  |
|  |  REST ENDPOINTS           |  |  SHARED CONTEXT (Working Memory)            |  |
|  |  GET  /sessions           |  |  [agents/shared_context.py]                 |  |
|  |  POST /sessions           |  |                                             |  |
|  |  PATCH/DELETE /sessions   |  |  ExecutionPlan  . chunks  . sources         |  |
|  |  GET  /sessions/{id}/msgs |  |  context_text   . primary_response          |  |
|  |  POST /config/llm         |  |  artifact  . confidence . agent_steps       |  |
|  |  GET  /health             |  |  heal_attempts . search_hops . word_count   |  |
|  +---------------------------+  +---------------------------------------------+  |
|                                                                                   |
+------------------+------------------------+-----------------------+---------------+
                   |                        |                       |
                   v                        v                       v
+------------------+------+  +-------------+--------+  +----------+--------------+
|  RAG & VECTOR ENGINE    |  |   PERSISTENCE LAYER  |  |    LLM PROVIDERS        |
|  [rag.py]               |  |   [db.py]            |  |    [llm.py]             |
|                         |  |                      |  |                         |
|  get_embedding(text)    |  |  Supabase Postgres   |  |  LLMProvider  (ABC)     |
|  -> nomic-embed-text    |  |  psycopg3 async pool |  |                         |
|  -> 768-dim float vector|  |  min=1  max=10 conns |  |  +----------+           |
|                         |  |                      |  |  | Ollama   |  local    |
|  retrieve(query, top_k) |  |  +----------------+  |  |  | qwen3:4b |  :11434  |
|  -> cosine sim  <=>     |  |  | sessions       |  |  |  +----------+           |
|  -> pgvector index      |  |  | messages       |  |  |  +----------+           |
|  -> top-K chunks        |  |  | transcript_    |  |  |  |Anthropic |  cloud   |
|                         |  |  |   chunks       |  |  |  |claude-   |          |
|  build_context(chunks)  |  |  | embedding      |  |  |  |sonnet-5  |          |
|  -> formatted prompt ctx|  |  | vector(768)    |  |  |  +----------+           |
|                         |  |  +----------------+  |  |                         |
+-------------------------+  +----------------------+  +-------------------------+
```

---

## Key Design Decisions

### 1. LLM-based Agentic Router

**Decision:** Classify user intent with a real LLM call, with keyword-match fallback.

**Why:** Keyword matching cannot detect multi-intent queries (e.g., "write an essay AND create a chart") or understand conversational context (e.g., "convert this into an essay" referring to a prior QA answer). An LLM classifier reasons about the full message + last 2 turns of history.

**Implementation:**
- `classify_skill(message, provider, history)` is async
- Stage 1: instant string matching — chitchat, followup signals, pronoun + short message (no LLM)
- Stage 2: LLM call with `max_tokens=12` — returns one word
- Valid outputs: `qa`, `ship30for30`, `artifact`, `multi`, `followup`
- If LLM returns unexpected output or fails → falls back to keyword matching
- `multi` triggers a 3-step chain: RAG retrieval → stream primary response → generate artifact with essay as context

**Trade-off:** Adds ~1-2s latency per message for the routing LLM call. Acceptable since the main skill LLM call takes 10-60s anyway. The `followup` fast-path keeps short messages instant.

### 2. Retrieval-sourced Citations

**Decision:** Sources (`guest`, `episode_title`, `youtube_url`) come from the retrieval step, not from LLM output.

**Reasoning:** LLMs hallucinate citations. The retrieval step already has ground truth — we just surface it. Citations are 100% accurate (they point to chunks actually used as context).

### 3. nomic-embed-text over MiniLM

**Decision:** Use `nomic-embed-text` (8192 token context, 768 dims) for embeddings.

**Reasoning:** `all-MiniLM-L6-v2` truncates at 256 tokens (~200 words). A 10,000-word podcast transcript embedded with MiniLM is only represented by its first 200 words — retrieval on anything said later is effectively random. `nomic-embed-text` handles our 700-token chunks with full fidelity and runs locally via Ollama.

### 4. Two-Call Artifact Split (Option B)

**Decision:** Generate artifacts with two separate LLM calls instead of tag-based extraction.

**Reasoning:** The original approach asked the model to wrap HTML in `<artifact type="html">` tags and regex-extracted the content. qwen3's `<think>` block confused the regex, and truncation left unclosed tags. Two-call split eliminates the parsing problem entirely:
- Call 1 → short intro sentence (shown in chat message)
- Call 2 → raw HTML page only (entire response = artifact, nothing to parse)
- ValidatorAgent self-healing handles any remaining malformed HTML

### 5. pgvector in Same DB

**Decision:** Vector search via pgvector extension in the same Supabase Postgres, not a separate vector DB.

**Reasoning:** At ~5,000-10,000 chunks, pgvector's IVFFlat index is fast enough (sub-100ms cosine queries). A separate vector DB adds a second external dependency, a second connection string to manage, and a second failure mode.

### 6. asyncio.gather for Writer + Artifact Parallelism

**Decision:** In Research Mode Phase 3, WriterAgent streams to the user while ArtifactAgent builds HTML in the background.

**Reasoning:** Both agents need only Phase 2 research output (no dependency on each other). Running them concurrently cuts total Research Mode latency by ~30-40%. The user sees streaming text immediately while the dashboard renders silently.

---

## Low-Level System Design

### 1. Classic Mode — Full Request Lifecycle

```
+------------------------------------------------------------------------------------+
|                        CLASSIC MODE REQUEST FLOW                                   |
+------------------------------------------------------------------------------------+

  Browser                  FastAPI [main.py]          Router [router.py]
     |                           |                           |
     |  POST /chat/stream        |                           |
     |  {message: "..."}         |                           |
     |-------------------------->|                           |
     |                           |  classify_skill(msg,      |
     |                           |   provider, history)      |
     |                           |-------------------------->|
     |                           |                           |
     |                           |         STAGE 1 (no LLM) |
     |                           |  chitchat / followup?---->| "followup"
     |                           |  both essay+artifact? --->| "multi"
     |                           |                           |
     |                           |         STAGE 2 (LLM)    |
     |                           |  prompt -> one word result|
     |                           |  fallback: keyword match  |
     |                           |<--- skill name -----------|
     |                           |                           |
     |   +-------------------------------------------------------+
     |   |   SKILL DISPATCH                                       |
     |   |                                                        |
     |   |   "qa"          -> run_qa()   RAG + LLM stream        |
     |   |   "ship30for30" -> run_ship30() RAG + essay format    |
     |   |   "artifact"    -> run_artifact() 2-call: intro+HTML  |
     |   |   "multi"       -> run_ship30() + run_artifact()      |
     |   |   "followup"    -> run_qa()  history only, skip RAG   |
     |   +-------------------------------------------------------+
     |                           |
     |                           |  retrieve(query, conn)
     |                           |  1. embed query -> 768d vector
     |                           |  2. pgvector cosine search
     |                           |  3. top-K transcript chunks
     |                           |
     |                           |  LLM stream (Ollama / Anthropic)
     |                           |
     |  SSE: data:{token:"..."}  |
     |<--------------------------|
     |  SSE: data:{done:true,    |
     |    skill_used, sources,   |
     |    artifact, new_title}   |
     |<--------------------------|
```

---

### 2. Research Mode — 5-Agent Pipeline

```
+------------------------------------------------------------------------------------+
|                      RESEARCH MODE PIPELINE  [crew_runner.py]                      |
|                                                                                    |
|  SharedContext (working memory) flows through every phase                          |
+------------------------------------------------------------------------------------+

  Phase 1 -- ORCHESTRATOR AGENT [agents/orchestrator.py]  (sequential)

    Input:  user_query + last 2 history turns
    Action: Pure LLM call -> produces JSON ExecutionPlan

    +---------------------------------------------------------------------+
    |                       ExecutionPlan fields                          |
    |  crew_type            "qa" | "essay" | "full_research"             |
    |  complexity           "simple" | "deep" | "multi"                  |
    |  needs_essay          bool                                          |
    |  needs_artifact       bool                                          |
    |  primary_search_query    refined vector-search string               |
    |  secondary_search_query  optional 2nd query for multi-hop           |
    +---------------------------------------------------------------------+
    Fallback: keyword-based plan if LLM fails or times out

  Phase 2 -- RESEARCH AGENT [agents/research.py]  (sequential, no LLM)

    Hop 1:  embed(primary_query) -> pgvector cosine -> top-K chunks

    Quality check:
      chunks < 4  OR  single episode  OR  complexity = deep/multi
                            |
                            v  trigger Hop 2
    Hop 2:  embed([primary, secondary]) -> merge + dedupe
            max 10 total chunks  from multiple episodes

    Output: chunks . sources . context_text . research_summary
            confidence: "high" (>=5 eps) | "medium" (>=2) | "low"

  Phase 3 -- PARALLEL GENERATION  [asyncio.gather]

    +----------------------------------+  +--------------------------------+
    |  WRITER AGENT (foreground)       |  |  ARTIFACT AGENT (background)   |
    |  [agents/writer.py]              |  |  [agents/artifact_agent.py]    |
    |                                  |  |  (only if needs_artifact=True) |
    |  Streams tokens -> SSE -> Browser|  |                                |
    |                                  |  |  Call 1 -> intro sentence      |
    |  QA mode:    grounded answer     |  |  Call 2 -> raw HTML page only  |
    |  Essay mode: Ship30for30 format  |  |  Output: {type:"html",         |
    |  Followup:   history-only reply  |  |   content:"<!DOCTYPE..."}      |
    +----------------------------------+  +--------------------------------+

  Phase 4 -- VALIDATOR AGENT [agents/validator.py]  (sequential)

    Checks:
    [1] HTML artifact   -- parse structure, detect broken tags
    [2] Markdown        -- basic structure check
    [3] Essay           -- word count, bold phrases, guest citations
    [4] QA response     -- guest name citations, length

    Self-Healing Loop (HTML only, max 2 attempts):

      validate_html(content)
            | error found
            v
      emit SSE: "Self-healing attempt N/2 -- <error summary>"
            |
      re-run ArtifactAgent with error injected into prompt
            |
      validate again -> pass? done  |  fail? -> next attempt

    Final SSE event:
      { done:true, confidence, sources, artifact,
        agent_steps, research_stats, healing_attempts }
```

---

### 3. Skill Router — 2-Stage Classification  [router.py]

```
+------------------------------------------------------------------------------------+
|                         SKILL ROUTER DECISION TREE                                 |
+------------------------------------------------------------------------------------+

  User Message
       |
       v
  +-----------------------------------+
  |  STAGE 1  -- Zero LLM (instant)  |
  |                                   |
  |  Chitchat set match?              |---YES---> "followup"
  |  ("ok", "thanks", "sure"...)      |
  |                                   |
  |  Followup signal in text?         |---YES---> "followup"
  |  ("turn this into", "expand on")  |
  |                                   |
  |  Short msg + pronoun + history?   |---YES---> "followup"
  |  (< 8 words + "this/that/it")     |
  |                                   |
  |  Has BOTH essay keywords          |---YES---> "multi"
  |  AND artifact keywords?           |
  +-----------------------------------+
       | none matched
       v
  +-----------------------------------+
  |  STAGE 2  -- LLM Classification  |
  |                                   |
  |  max_tokens = 12  (one word)      |
  |  classify into:                   |
  |    qa | ship30for30 | artifact    |
  |    multi | followup               |
  |                                   |
  |  validated against allowed set    |
  |  fallback: keyword matching       |
  +-----------------------------------+
       |
       v
  +-----------------------------------------------------------+
  |  SKILL DISPATCH                                           |
  |                                                           |
  |  qa           -> run_qa()                                 |
  |                 RAG retrieve -> LLM stream                |
  |                                                           |
  |  ship30for30  -> run_ship30()                             |
  |                 RAG retrieve -> Ship30 essay prompt       |
  |                                                           |
  |  artifact     -> run_artifact()                           |
  |                 RAG -> Call 1 intro -> Call 2 raw HTML    |
  |                                                           |
  |  multi        -> run_ship30() + run_artifact()  (parallel)|
  |                                                           |
  |  followup     -> run_qa() with history only (skip RAG)   |
  +-----------------------------------------------------------+
```

---

### 4. RAG Vector Search Pipeline  [rag.py]

```
+------------------------------------------------------------------------------------+
|                         RAG PIPELINE DETAIL                                        |
+------------------------------------------------------------------------------------+

  Query String
       |
       v
  +-----------------------------------------+
  |  get_embedding(text)   [rag.py]          |
  |                                          |
  |  POST :11434/api/embeddings (Ollama)     |
  |  model: nomic-embed-text                 |
  |  -> 768-dimensional float vector         |
  |                                          |
  |  (sync urllib in thread pool executor    |
  |   keeps async event loop unblocked)      |
  +-----------------------------------------+
       | 768-dim vector
       v
  +-----------------------------------------+
  |  pgvector cosine similarity search       |
  |                                          |
  |  SELECT content, guest, episode_title,   |
  |         youtube_url, episode_slug,       |
  |         1 - (embedding <=> %s::vector)   |
  |           AS similarity                  |
  |  FROM transcript_chunks                  |
  |  ORDER BY embedding <=> %s::vector       |
  |  LIMIT top_k                             |
  |    simple -> 5   deep/multi -> 6         |
  +-----------------------------------------+
       | top-K chunks
       v
  +-----------------------------------------+
  |  build_context(chunks)                   |
  |                                          |
  |  --- Source N: {guest}                   |
  |      "{episode_title}" ---               |
  |  {chunk.content}                         |
  |                                          |
  |  Joined and passed as context_text       |
  |  into LLM system prompt                  |
  +-----------------------------------------+
       |
       v
  +-----------------------------------------+
  |  dedupe_sources(chunks)                  |
  |                                          |
  |  Unique episodes by youtube_url          |
  |  -> sources list sent in done event      |
  |  -> displayed in SourcesAccordion        |
  +-----------------------------------------+
```

---

### 5. Database Schema  [db.py]

```
+------------------------------------------------------------------------------------+
|                          POSTGRES (Supabase) SCHEMA                                |
+------------------------------------------------------------------------------------+

  +---------------------------+         +-----------------------------------+
  |         sessions          |         |             messages             |
  +---------------------------+         +-----------------------------------+
  |  id          UUID  PK     |<------->|  id           UUID  PK           |
  |  title       TEXT         |    1:N  |  session_id   UUID  FK           |
  |  llm_provider TEXT        |         |  role         TEXT  user|assistant|
  |  created_at  TIMESTAMPTZ  |         |  content      TEXT               |
  +---------------------------+         |  skill_used   TEXT               |
                                        |  artifact_json  JSONB            |
                                        |  sources        JSONB            |
                                        |  created_at   TIMESTAMPTZ        |
                                        +-----------------------------------+

  +-------------------------------------------------------------------+
  |                       transcript_chunks                           |
  +-------------------------------------------------------------------+
  |  id              UUID     PK                                      |
  |  episode_slug    TEXT     (e.g. "brian-chesky-airbnb-ep42")       |
  |  guest           TEXT     (e.g. "Brian Chesky")                   |
  |  episode_title   TEXT                                             |
  |  youtube_url     TEXT                                             |
  |  chunk_index     INT      (position within episode)               |
  |  content         TEXT     (700 chars, 100 char overlap)           |
  |  embedding       vector(768)  <- pgvector column                  |
  |                                                                   |
  |  INDEX: IVFFlat cosine ops  (activate when rows > 1000)          |
  +-------------------------------------------------------------------+
```

---

### 6. SSE Event Protocol

```
+------------------------------------------------------------------------------------+
|  CLASSIC MODE   POST /sessions/{id}/chat/stream                                    |
+------------------------------------------------------------------------------------+

  data: {"step": "Routing..."}                         <- status
  data: {"step": "Searching transcripts..."}
  data: {"token": "Based"}                             <- text chunk
  data: {"token": " on"}
  data: {"done": true,                                 <- final metadata
         "skill_used": "qa",
         "sources": [{"guest":..., "youtube_url":...}],
         "artifact": null,
         "new_title": "Brian Chesky on Culture"}

+------------------------------------------------------------------------------------+
|  RESEARCH MODE  POST /sessions/{id}/chat/research/stream                           |
+------------------------------------------------------------------------------------+

  data: {"agent":"OrchestratorAgent", "step":"Analyzing request..."}
  data: {"agent":"OrchestratorAgent", "step":"qa crew -- Simple factual lookup"}
  data: {"agent":"ResearchAgent",     "step":"Searching transcripts..."}
  data: {"agent":"ResearchAgent",     "step":"Found 8 chunks from 3 episodes (2 hops)",
         "sources_found": 3}
  data: {"agent":"WriterAgent",       "step":"Synthesizing..."}
  data: {"token": "Based"}
  data: {"agent":"ArtifactAgent",     "step":"Building dashboard..."}
  data: {"agent":"ValidatorAgent",    "step":"Validating output..."}
  data: {"agent":"ValidatorAgent",    "step":"Self-healing attempt 1/2 -- unclosed div"}
  data: {"agent":"ValidatorAgent",    "step":"Artifact self-healed successfully!"}
  data: {"done": true,
         "confidence": "high",
         "sources": [...],
         "artifact": {"type":"html", "content":"<!DOCTYPE html>..."},
         "healing_attempts": 1,
         "agent_steps": [...],
         "research_stats": {
           "chunks_found": 8,
           "episodes": 3,
           "search_hops": 2,
           "word_count": 412
         }}
```

---

### 7. Frontend Component Tree

```
+------------------------------------------------------------------------------------+
|                       FRONTEND COMPONENT HIERARCHY                                 |
+------------------------------------------------------------------------------------+

  App.jsx  -- root state: sessions, messages, streaming, mode, provider
  |
  +-- SessionSidebar.jsx
  |     Session list, rename, delete, new chat
  |
  +-- ChatMessage.jsx  (one per message)
  |   +-- SkillBadge.jsx        Q&A | Essay | Artifact | Multi
  |   +-- ConfidenceBadge.jsx   high | medium | low
  |   +-- SourcesAccordion.jsx  collapsible episode citations
  |   +-- ThinkingDots.jsx      animated dots while streaming
  |
  +-- AgentTracker.jsx           (Research Mode only)
  |     Live SSE steps: Orchestrator -> Research -> Writer
  |                      -> Artifact -> Validator
  |
  +-- ResearchStats.jsx
  |     chunks_found . episodes . search_hops . word_count
  |
  +-- ArtifactPane.jsx
  |     <iframe sandbox> rendering raw HTML artifact
  |     Preview tab | Source tab
  |
  +-- ChatInput.jsx
        +-- ResearchModeToggle.jsx   Classic  <->  Research Mode
        +-- ProviderToggle.jsx       Ollama   <->  Anthropic
```

---

## API Endpoints

### Classic Mode

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | DB + LLM connectivity check |
| POST | `/sessions` | Create a new chat session |
| GET | `/sessions` | List all sessions (most recent first, limit 50) |
| PATCH | `/sessions/{id}` | Rename a session (max 80 chars) |
| DELETE | `/sessions/{id}` | Permanently delete session + all messages |
| GET | `/sessions/{id}/messages` | Full message history ordered by created_at |
| POST | `/sessions/{id}/chat` | Blocking chat (router -> skill -> LLM) |
| POST | `/sessions/{id}/chat/stream` | Same, token-by-token SSE |
| GET | `/config/llm` | Get current provider + model name |
| POST | `/config/llm` | Switch provider (`{"llm_provider": "ollama"|"anthropic"}`) |

### Research Mode

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions/{id}/chat/research/stream` | 5-agent SSE stream |

---

## File Structure

```
backend/
+-- main.py               # FastAPI app -- all endpoints, lifespan
+-- config.py             # Pydantic settings (DATABASE_URL, models, etc.)
+-- db.py                 # psycopg3 async pool, schema DDL
+-- llm.py                # LLMProvider ABC + OllamaProvider + AnthropicProvider
+-- rag.py                # embed() + retrieve() + build_context() + dedupe_sources()
+-- router.py             # 2-stage skill classifier (instant + LLM)
+-- models.py             # Pydantic request/response schemas
+-- requirements.txt
+-- agents/
|   +-- shared_context.py  # SharedContext + ExecutionPlan dataclasses
|   +-- crew_runner.py     # Pipeline orchestrator (phases 1-4, asyncio.gather)
|   +-- orchestrator.py    # OrchestratorAgent (LLM -> JSON plan)
|   +-- research.py        # ResearchAgent (multi-hop RAG, no LLM)
|   +-- writer.py          # WriterAgent (streaming LLM, QA + essay)
|   +-- artifact_agent.py  # ArtifactAgent (2-call: intro + HTML)
|   +-- validator.py       # ValidatorAgent + self-healing loop (max 2x)
+-- skills/
|   +-- qa.py              # Classic Q&A skill
|   +-- ship30for30.py     # Essay writing skill
|   +-- artifact.py        # HTML artifact skill (2-call split)
+-- tools/
    +-- search_tool.py     # execute_search() + execute_multi_hop_search()
    +-- validate_tool.py   # validate_html() / validate_markdown() / validate_essay()
    +-- count_tool.py      # essay_stats() - word count, citations, bold phrases

frontend/src/
+-- App.jsx                # Root shell, state, SSE consumer
+-- api.js                 # Fetch wrapper, streamChat, streamResearchChat
+-- components/
    +-- SessionSidebar.jsx    # Chat history + session management
    +-- ChatMessage.jsx       # Message bubble + markdown render
    +-- ChatInput.jsx         # Text input + toggles
    +-- ArtifactPane.jsx      # iframe artifact renderer + source tab
    +-- AgentTracker.jsx      # Live pipeline step display (Research Mode)
    +-- ResearchStats.jsx     # Chunk/episode/hop counters
    +-- SourcesAccordion.jsx  # Collapsible episode citations
    +-- SkillBadge.jsx        # Q&A / Essay / Artifact / Multi badge
    +-- ConfidenceBadge.jsx   # High / Medium / Low confidence
    +-- ProviderToggle.jsx    # Ollama <-> Anthropic switcher
    +-- ResearchModeToggle.jsx# Classic <-> Research mode
    +-- ThinkingDots.jsx      # Loading animation
```

---

## Scaling Path

| Dimension | Current | Scale-up |
|---|---|---|
| Episodes | ~180 curated | 269 — extend `CURATED_INDEX_FILES` in `ingest.py` |
| Vector index | Exact cosine (no IVFFlat yet) | IVFFlat lists=100, then HNSW for >50k chunks |
| Concurrent users | Single-process Uvicorn | Gunicorn workers + connection pool tuning |
| LLM providers | Ollama + Anthropic | Add `GeminiProvider` — implement `LLMProvider` ABC |
| Self-healing | 2 attempts | Increase `MAX_HEAL_ATTEMPTS` in `validator.py` |
