# Handoff Prompt — Lenny's Growth Assistant (Phase 2: Frontend)

Paste this entire prompt to the new model to continue Phase 2.

---

## CONTEXT

You are continuing work on **"Lenny's Growth Assistant"** — a full-stack AI-powered
conversational web app built on Lenny Rachitsky's podcast transcripts.

**Project path:** `d:\Lenny's Growth Assistant`
**Backend:** FastAPI + psycopg3 + Supabase pgvector + Ollama/Anthropic
**Frontend:** React (Vite) + Tailwind CSS (custom tokens, NOT standard Tailwind)
**Running:** `uvicorn main:app --reload --port 8000` + `npm run dev` (port 5173)

---

## WHAT WAS JUST COMPLETED (Phase 1 — Backend ✅ VERIFIED)

A 5-agent Research Mode pipeline was added to the backend. ALL files are working and tested.

### New backend files created:
```
backend/
├── agents/
│   ├── __init__.py
│   ├── shared_context.py     ← SharedContext + ExecutionPlan dataclasses
│   ├── orchestrator.py       ← OrchestratorAgent (LLM JSON planner, keyword fallback)
│   ├── research.py           ← ResearchAgent (multi-hop RAG, quality assessment)
│   ├── writer.py             ← WriterAgent (streams QA + Ship30for30 essays)
│   ├── artifact_agent.py     ← ArtifactAgent (HTML dashboards, self-heal support)
│   ├── validator.py          ← ValidatorAgent (QC + self-healing loop, max 2 attempts)
│   └── crew_runner.py        ← Pipeline orchestrator (parallel WriterAgent+ArtifactAgent)
└── tools/
    ├── search_tool.py        ← execute_search(), execute_multi_hop_search()
    ├── validate_tool.py      ← validate_html(), validate_essay(), build_heal_prompt()
    └── count_tool.py         ← count_words(), essay_stats(), count_guest_citations()
```

### New endpoint added to backend/main.py:
```
POST /sessions/{session_id}/chat/research/stream
```
Classic endpoint `POST /sessions/{session_id}/chat/stream` is UNCHANGED.

### Verified SSE output format from the new endpoint:
```json
{"agent": "OrchestratorAgent", "step": "🧠 Analyzing your research request..."}
{"agent": "ResearchAgent", "step": "🔍 Searching Lenny's podcast transcripts..."}
{"agent": "ResearchAgent", "step": "✅ Found 5 chunks from 4 episodes (1 search hop)", "sources_found": 4}
{"agent": "WriterAgent", "step": "✍️  Generating answer from 5 sources..."}
{"token": "When Brian Chesky told Lenny..."}
{"token": " the key insight was..."}
{"agent": "ValidatorAgent", "step": "✅ Validating output quality..."}
{"agent": "ValidatorAgent", "step": "🔧 Self-healing artifact (attempt 1/2) — Unclosed script tag"}
{"done": true, "skill_used": "research:qa", "sources": [...], "artifact": null,
 "confidence": "medium", "healing_attempts": 0,
 "agent_steps": [...], "research_stats": {"chunks_found": 5, "episodes": 4, ...}}
```

---

## PHASE 2 — WHAT YOU NEED TO BUILD (Frontend)

**Goal:** Add "Research Mode" to the frontend. It is triggered by a new toggle near the
chat input (like GPT's "Search" or "Deep Research" button). When active, it calls the new
`/research/stream` endpoint instead of `/stream`, and shows the agent pipeline live.

### Design System (already in use — DO NOT change tokens)
The frontend uses custom CSS variables in `frontend/src/index.css`. Key tokens:
```css
--bg-base, --bg-surface, --bg-elevated
--text-primary, --text-secondary, --text-muted
--accent-primary (main orange/amber color)
--border, --border-subtle
--skill-artifact, --skill-essay, --skill-qa (skill badge colors)
```
Component classes already defined: `.btn-primary`, `.card`, `.badge`, etc.

### Existing components (DO NOT break these):
- `frontend/src/App.jsx` — main shell, session/streaming state
- `frontend/src/api.js` — API functions including `streamChat()`
- `frontend/src/components/ChatMessage.jsx` — renders messages, SkillBadge, sources
- `frontend/src/components/ArtifactPane.jsx` — 3-tab artifact viewer
- `frontend/src/components/SessionSidebar.jsx` — chat history
- `frontend/src/components/ChatInput.jsx` — user input bar
- `frontend/src/components/SkillBadge.jsx` — skill labels

### Files to CREATE (new components):

#### 1. `frontend/src/components/ResearchModeToggle.jsx`
A small pill button placed INSIDE the ChatInput area (right side of input, before Send button).
- Off state: subtle border, text "🔬 Research", muted color
- On state: glowing amber/orange, animated pulse dot, text "🔬 Research Active"
- Props: `{ researchMode: bool, onChange: (bool) => void, disabled: bool }`
- ID for testing: `id="research-mode-toggle"`

#### 2. `frontend/src/components/AgentTracker.jsx`
A horizontal strip that appears ABOVE the streaming assistant message when Research Mode
is active. Shows a mini pipeline of agents with their current status.
- Shows each agent step received from SSE `{"agent": "...", "step": "..."}` events
- Current agent: animated spinner + bright text
- Completed agents: checkmark + dimmed text
- Props: `{ steps: [{agent, step}], currentStep: string, isActive: bool }`
- Agents in order: OrchestratorAgent → ResearchAgent → WriterAgent → ArtifactAgent → ValidatorAgent
- Style: dark pill-shaped container, monospace font for agent names, compact

#### 3. `frontend/src/components/ConfidenceBadge.jsx`
A tiny badge shown next to the SkillBadge on research:* messages.
- "high" → green dot + "High confidence"
- "medium" → amber dot + "Medium confidence"  
- "low" → red dot + "Low confidence"
- Props: `{ confidence: "high"|"medium"|"low" }`

#### 4. `frontend/src/components/ResearchStats.jsx`
A compact expandable row below research responses (collapsed by default).
Shows: `N chunks · M episodes · K search hops · Word count`
Props: `{ stats: {chunks_found, episodes, search_hops, word_count} }`

### Files to MODIFY:

#### `frontend/src/api.js`
Add a new function `streamResearchChat(sessionId, message, callbacks)`:
```javascript
// Identical to streamChat() but calls /research/stream endpoint
// callbacks: { onToken, onStep, onDone, onError }
// onStep(step) is called for {"agent": "...", "step": "..."} events
// onDone(meta) receives the done event payload (includes confidence, agent_steps, research_stats)
export function streamResearchChat(sessionId, message, { onToken, onStep, onDone, onError }) {
  // ... same SSE parsing as streamChat, but:
  // 1. URL: /sessions/${sessionId}/chat/research/stream
  // 2. Parse {"agent", "step"} events → call onStep({agent, step})
  // 3. done event has extra fields: confidence, healing_attempts, agent_steps, research_stats
}
```

#### `frontend/src/App.jsx`
Add:
- `const [researchMode, setResearchMode] = useState(false)` state
- When `researchMode=true`, call `streamResearchChat()` instead of `streamChat()`
- Pass `agentSteps` state (array of {agent, step} objects) to ChatMessage during streaming
- Pass `confidence` from done event to message metadata
- Pass `researchStats` from done event to message metadata
- Place `<ResearchModeToggle>` component inside the ChatInput row

#### `frontend/src/components/ChatMessage.jsx`
Add:
- Show `<AgentTracker>` ABOVE the streaming message content when `isStreaming && agentSteps.length > 0`
- Show `<ConfidenceBadge confidence={msg.confidence}>` next to SkillBadge when skill starts with "research:"
- Show `<ResearchStats stats={msg.researchStats}>` below message when researchStats is present
- Self-healing notification: if `msg.healingAttempts > 0`, show a small amber banner:
  `"🔧 Self-healed {n} time(s) — artifact was automatically fixed"`

#### `frontend/src/components/ArtifactPane.jsx`
Add a self-healing banner at the top if artifact was healed:
- Prop: `healingAttempts: number`
- Show if `healingAttempts > 0`: amber info bar "⚡ Self-healed {n}× — ValidatorAgent fixed errors automatically"

---

## KEY PATTERNS TO FOLLOW

### SSE Streaming (see existing streamChat in api.js)
The existing `streamChat()` uses `EventSource`-like manual fetch with `ReadableStream`.
Copy that exact pattern for `streamResearchChat()` — only change the URL and add
parsing for `{"agent", "step"}` events.

### State management in App.jsx
```javascript
// Currently exists:
const [agentStep, setAgentStep] = useState('');  // single string

// You need to ADD:
const [agentSteps, setAgentSteps] = useState([]);  // array of {agent, step}

// In streamResearchChat onStep callback:
onStep: (step) => {
  setAgentStep(step.step);           // keep existing single-step for ChatMessage
  setAgentSteps(prev => [...prev, step]);  // add to full trace for AgentTracker
},
// Reset on new message:
setAgentSteps([]);
```

### SkillBadge (already handles research:* skills)
The `SkillBadge` component may not know about `research:qa`, `research:ship30for30`.
Add those variants to SkillBadge's skill map with a 🔬 prefix.

---

## IMPORTANT CONSTRAINTS

1. **DO NOT modify** `backend/router.py`, `backend/skills/`, or `backend/main.py`'s
   classic `/chat/stream` endpoint — they must remain working.
2. **DO NOT use Tailwind utility classes** — use the existing custom CSS variables.
3. The toggle goes **near the chat input** (NOT in the topbar).
4. Component IDs must be unique for browser testing (required by assignment rubric).
5. After Phase 2, update `docs/design.md` with the new components.

---

## HOW TO TEST AFTER PHASE 2

1. Open http://localhost:5173
2. Click "🔬 Research" button near the input
3. Type: "What did Brian Chesky say about company culture?"
4. Verify: AgentTracker appears above streaming response, showing 5 agents progressing
5. Type: "Write a Ship30for30 essay on product-market fit"  
6. Verify: Essay streams, word count shown in ResearchStats
7. Type: "Build me a dashboard for growth metrics"
8. Verify: ArtifactPane opens with HTML dashboard, ConfidenceBadge shows, self-heal runs if needed

---

## RUNNING CONTEXT

- Backend: `uvicorn main:app --reload --port 8000` (from `backend/` dir, with venv)
- Frontend: `npm run dev` (from `frontend/` dir)
- Ollama model: `qwen3:4b` (local)
- DB: Supabase (credentials in `backend/.env` → DATABASE_URL)
