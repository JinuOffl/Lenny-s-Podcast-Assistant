# Lenny's Growth Assistant

A full-stack AI conversational web app that answers product/growth questions grounded in Lenny's Podcast transcripts, generates Ship30for30-style atomic essays, and renders HTML/Markdown artifacts in a split-pane viewer.

**Stack:** FastAPI · Supabase Postgres + pgvector · Ollama · React + Vite + Tailwind

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** installed and running → [ollama.ai](https://ollama.ai)
- A **Supabase** project with the `pgvector` extension enabled
  - Create free project at [supabase.com](https://supabase.com) → Settings → Database → Extensions → enable `vector`
- (Optional) An **Anthropic API key** — the app runs fully on Ollama without one

### Pull required Ollama models

```bash
# Required: embedding model
ollama pull nomic-embed-text

# Required: chat model (recommended)
ollama pull qwen3:4b          # ~2.5GB, best instruction following for essays

# Alternatives:
ollama pull llama3.2          # ~2GB, faster but lower quality
ollama pull llama3.3:8b       # ~5GB, higher quality
```

---

## Setup

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd lenny-growth-assistant
cp .env.example .env
```

Edit `.env` and fill in:
```
DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
OLLAMA_CHAT_MODEL=qwen3:4b          # recommended for best essay quality
ANTHROPIC_API_KEY=                  # leave blank to use Ollama only
```

> **DATABASE_URL:** Supabase Dashboard → Settings → Database → Connection string → URI mode

### 2. Python environment

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

cd backend
pip install -r requirements.txt
```

### 3. Bootstrap the database

```bash
# Still in backend/
python db.py
# Expected output: ✅ Schema applied successfully.
```

### 4. Ingest transcripts

This clones the Lenny's Podcast transcript repo, chunks ~180 curated episodes, embeds them with `nomic-embed-text`, and upserts to Supabase.

**Ollama must be running first** (`ollama serve` or the Ollama desktop app).

```bash
cd ../scripts
python ingest.py
# Takes 10-20 minutes depending on machine speed
# Expected: "Ingest complete! Total chunks stored: XXXX"
```

### 5. Start the backend

```bash
cd ../backend
uvicorn main:app --reload --port 8000
```

Verify: open http://localhost:8000/health — should return `{"status":"ok","database":true,"ollama":true,...}`

### 6. Start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open: **http://localhost:5173**

---

## Using the app

| What you want | What to type |
|---|---|
| **Q&A** | "What did Brian Chesky say about company culture?" |
| **Q&A** | "How do the best growth teams measure retention?" |
| **Essay** | "Write a Ship30for30 essay on product-market fit" |
| **Artifact** | "Create an HTML dashboard of top growth frameworks" |
| **Artifact** | "Build me a landing page summarizing Lenny's lessons on PLG" |
| **Multi-skill** | "Write an essay on retention AND create an HTML visualization of the key metrics" |

- **LLM toggle** (header) — switch between Local (Ollama) and Cloud (Anthropic)
- **Sources** — click "X sources cited" under any response to see episode citations with YouTube links
- **Artifact pane** — Preview tab renders HTML in a sandboxed iframe; Source tab shows raw code with copy button

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `database: false` in `/health` | Check DATABASE_URL in `.env` — must be `postgresql://` not `postgres://` |
| `ollama: false` in `/health` | Run `ollama serve` in a separate terminal |
| Empty sources in responses | Ingest hasn't finished yet — wait for "Ingest complete!" |
| PowerShell `curl` errors | Use `Invoke-WebRequest -Uri URL -UseBasicParsing` instead |
| 401 from Anthropic | Add valid `ANTHROPIC_API_KEY` to `.env` and restart backend |
| Frontend can't reach backend | Ensure uvicorn is running on port 8000 before opening the UI |

---

## Scaling to all 269 episodes

In `scripts/ingest.py`, change `CURATED_INDEX_FILES` to include more topic files:

```python
CURATED_INDEX_FILES = [
    "product-management.md",
    "growth-strategy.md",
    "product-market-fit.md",
    "leadership.md",
    # Add any from the repo's index/ directory:
    # "ai.md", "career-development.md", "sales.md", ...
]
```

This is a config change, not an architecture change.

---

## Project Structure

```
lenny-growth-assistant/
├── backend/
│   ├── main.py           # FastAPI app + all 6 endpoints
│   ├── config.py         # Pydantic settings from .env
│   ├── db.py             # psycopg3 async pool + schema DDL
│   ├── rag.py            # nomic-embed-text + pgvector retrieval
│   ├── llm.py            # OllamaProvider / AnthropicProvider
│   ├── router.py         # classify_skill() — LLM-based agentic classifier (5 skills + fallback)
│   ├── models.py         # Pydantic request/response schemas
│   ├── requirements.txt
│   └── skills/
│       ├── qa.py         # Grounded Q&A with retrieval-sourced citations
│       ├── ship30for30.py # Atomic essay generation (Ship30for30 framework)
│       └── artifact.py   # HTML/Markdown artifact generation + tag parsing
├── frontend/             # Vite + React 18 + Tailwind v3
│   └── src/
│       ├── App.jsx       # Root shell: sidebar + chat + artifact pane
│       ├── api.js        # HTTP client (all backend calls)
│       └── components/   # ChatMessage, ArtifactPane, SessionSidebar, ...
├── scripts/
│   └── ingest.py         # Clone → chunk → embed → upsert pipeline
├── docs/
│   ├── PRD.md            # Product requirements
│   ├── architecture.md   # System design + key decisions
│   └── design.md         # UI/UX design system
├── agent-transcripts/
│   └── LESSONS.md        # 8+ real failures from the build + fixes
├── .env.example
└── README.md
```

---

## API Endpoints

### Classic Mode

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | DB + LLM connectivity check |
| POST | `/sessions` | Create a new chat session |
| GET | `/sessions` | List all sessions (most recent first) |
| PATCH | `/sessions/{id}` | Rename a session |
| DELETE | `/sessions/{id}` | Permanently delete a session + messages |
| GET | `/sessions/{id}/messages` | Full message history for a session |
| POST | `/sessions/{id}/chat` | Blocking chat (router → skill → LLM) |
| POST | `/sessions/{id}/chat/stream` | Same as above, token-by-token SSE |
| GET | `/config/llm` | Get current provider + model name |
| POST | `/config/llm` | Switch provider (`{"llm_provider": "ollama"\|"anthropic"}`) |

### Research Mode (Agentic Pipeline)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions/{id}/chat/research/stream` | 5-agent SSE stream |

#### Research stream event types

```jsonc
// Agent status update (fires multiple times as each agent runs)
{"agent": "OrchestratorAgent", "step": "🧠 Analyzing your research request..."}
{"agent": "ResearchAgent",     "step": "✅ Found 5 chunks from 4 episodes (1 search hop)", "sources_found": 4}
{"agent": "WriterAgent",       "step": "✍️  Generating answer from 5 sources..."}
{"agent": "ArtifactAgent",     "step": "⚙️  Building interactive dashboard..."}
{"agent": "ValidatorAgent",    "step": "✅ QA valid — 242 words, 1 guests cited"}

// Self-healing (ValidatorAgent catches a broken artifact)
{"agent": "ValidatorAgent",    "step": "🔧 Self-healing artifact (attempt 1/2) — Script tag is self-closing"}

// Token stream (WriterAgent streams text)
{"token": "Based"}
{"token": " on"}

// Done — final event with full metadata
{
  "done": true,
  "skill_used": "qa",
  "sources": [{"guest": "Brian Chesky", "episode_title": "...", "youtube_url": "..."}],
  "artifact": null,
  "confidence": "medium",
  "healing_attempts": 0,
  "agent_steps": [...],
  "research_stats": {
    "chunks_found": 5,
    "episodes": 4,
    "search_hops": 1,
    "word_count": 242
  },
  "new_title": "Brian Chesky on Company Culture"
}
```

---

## Research Mode

The app ships two modes accessible from the same chat interface.

### Classic Mode (default)
- Keyword router → single skill (QA / Essay / Artifact)
- Response time: ~5–15s
- No toggle required — just send a message

### Research Mode (5-agent pipeline)
- Click **🔬 Research** button next to the chat input (glows amber when active)
- Response time: ~60–120s (Ollama local) / ~15–30s (Anthropic)
- Pipeline: **Orchestrator → Research → Writer + Artifact (parallel) → Validator**

#### What each agent does

| Agent | Role |
|---|---|
| **OrchestratorAgent** | Analyzes query, builds execution plan (crew type, search queries, complexity) |
| **ResearchAgent** | 1–2 hop vector search across transcript chunks; quality assessment |
| **WriterAgent** | Streams the answer token-by-token (QA or Ship30for30 essay) |
| **ArtifactAgent** | Generates interactive HTML dashboards (runs in parallel with Writer) |
| **ValidatorAgent** | QC check on output; triggers self-healing loop if artifact is broken (max 2 retries) |

#### AgentTracker UI
While streaming, a live pipeline visualization appears above the response:
```
Plan ──→ Search ──→ Write ──→ Build ──→ QC
 ✓         ✓        ⟳         ●        ●
```
Each node transitions: `pending (dim)` → `active (orange spinner)` → `done (green ✓)` → `healing (amber ⚠)`

#### Self-healing
If the ArtifactAgent generates broken HTML, ValidatorAgent:
1. Detects the specific error (e.g., "self-closing script tag")
2. Injects the error + broken output prefix back into a retry prompt
3. ArtifactAgent regenerates a targeted fix
4. A **"⚡ Self-healed"** amber banner appears below the response

---

## Project Structure

```
lenny-growth-assistant/
├── backend/
│   ├── main.py               # FastAPI app — all endpoints
│   ├── router.py             # Classic mode keyword router
│   ├── rag.py                # retrieve() + build_context()
│   ├── llm.py                # LLMProvider ABC, OllamaProvider, AnthropicProvider
│   ├── db.py                 # Supabase connection pool
│   ├── skills/               # Classic mode skills (qa, ship30for30, artifact)
│   ├── agents/               # Research Mode agents
│   │   ├── shared_context.py # SharedContext + ExecutionPlan dataclasses
│   │   ├── orchestrator.py   # OrchestratorAgent
│   │   ├── research.py       # ResearchAgent (multi-hop RAG)
│   │   ├── writer.py         # WriterAgent (streaming)
│   │   ├── artifact_agent.py # ArtifactAgent (HTML generation)
│   │   ├── validator.py      # ValidatorAgent (QC + self-healing)
│   │   └── crew_runner.py    # Pipeline orchestrator (asyncio.gather)
│   └── tools/                # Pure-Python agent tools (search, validate, count)
├── frontend/
│   └── src/
│       ├── App.jsx            # Root shell — streaming state, Research Mode routing
│       ├── api.js             # streamChat() + streamResearchChat()
│       └── components/
│           ├── ChatMessage.jsx       # Message rendering + AgentTracker
│           ├── ChatInput.jsx         # Composer + ResearchModeToggle
│           ├── ResearchModeToggle.jsx # Amber pill toggle
│           ├── AgentTracker.jsx      # Live pipeline visualization
│           ├── ConfidenceBadge.jsx   # Source confidence indicator
│           ├── ResearchStats.jsx     # Expandable stats + self-heal banner
│           ├── ArtifactPane.jsx      # HTML iframe + Markdown renderer
│           ├── SessionSidebar.jsx    # Session list + new chat
│           ├── SkillBadge.jsx        # Skill pill (QA/Essay/Artifact/🔬 Research)
│           └── SourcesAccordion.jsx  # Collapsible source citations
├── scripts/
│   └── ingest.py             # Transcript chunking + embedding pipeline
├── docs/
│   ├── PRD.md                # Product requirements
│   ├── architecture.md       # System design + Research Mode pipeline
│   └── design.md             # UI/UX design system + component library
├── agent-transcripts/
│   ├── README.md                     # Folder overview
│   ├── writer-agent-zero-tokens.md   # WriterAgent 0-token streaming bug
│   ├── orchestrator-json-failure.md  # OrchestratorAgent JSON parse failure
│   └── artifact-self-healing-demo.md # ValidatorAgent self-healing in action
├── .env.example
└── README.md
```
