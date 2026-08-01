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

# Required: chat model — use whichever you have. Examples:
ollama pull llama3.2          # ~2GB, fast
ollama pull llama3.3:8b       # ~5GB, better quality
ollama pull qwen3:4b          # ~2.5GB, good alternative
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
OLLAMA_CHAT_MODEL=llama3.2          # match what you pulled above
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
│   ├── router.py         # classify_skill() — rule-based, deterministic
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

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | DB + LLM connectivity check |
| POST | `/sessions` | Create a new chat session |
| GET | `/sessions` | List all sessions (most recent first) |
| GET | `/sessions/{id}/messages` | Get full message history for a session |
| POST | `/sessions/{id}/chat` | Send message → router → skill → LLM → persist → return |
| GET | `/config/llm` | Get current LLM provider + model name |
| POST | `/config/llm` | Switch provider (`{"llm_provider": "ollama"\|"anthropic"}`) |

### Chat response shape

```json
{
  "response": "Brian Chesky told Lenny that culture is...",
  "skill_used": "qa",
  "sources": [
    { "guest": "Brian Chesky", "episode_title": "...", "youtube_url": "https://..." }
  ],
  "artifact": null
}
```
