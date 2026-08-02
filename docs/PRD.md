# PRD: Lenny's Growth Assistant

**Version:** 2.0 — Research Mode shipped  
**Status:** In Progress (Phase 3 — Polish + Submission)  
**Author:** Jinu  
**Date:** 2026-08-02

---

## 1. Problem Statement

Product and growth practitioners spend hours rewatching Lenny's Podcast to surface specific advice. There's no way to query across 269 episodes in natural language, generate structured essays grounded in that knowledge, or create interactive artifacts from it — the content is locked inside long-form video.

---

## 2. Target User

A PM, growth lead, or early-stage founder who:
- Regularly listens to Lenny's Podcast and trusts its frameworks
- Wants to query across episodes ("What did the best growth leaders say about retention?")
- Needs to rapidly produce a structured essay or a shareable artifact grounded in that knowledge
- Is fine running this locally with their own API keys

---

## 3. MVP Scope

### In Scope (P0 — non-negotiable, maps directly to rubric)
- [x] FastAPI backend with session and message persistence in Supabase Postgres
- [x] LLM toggle: Ollama (local, default) ↔ Anthropic Claude (cloud)
- [x] Grounded Q&A over a curated subset of ~40-80 Lenny's Podcast episodes
- [x] Ship30for30 atomic essay generation skill
- [x] Artifact generation skill (HTML + Markdown) with in-app rendered viewer
- [x] Rule-based router (zero-latency, deterministic, explainable)
- [x] Split-pane UI: sidebar (session list) + chat pane + artifact pane
- [x] `/health` endpoint checking DB + LLM reachability
- [x] Public GitHub repo
- [x] `docs/` — PRD.md, design.md, architecture.md
- [x] README with local setup instructions
- [x] **Research Mode** — 5-agent pipeline (Orchestrator → Research → Writer + Artifact → Validator)
- [x] **Self-healing artifacts** — ValidatorAgent retries up to 2× with error context injected
- [x] **AgentTracker UI** — live pipeline viz in chat (pending/active/done/healing)
- [x] **ResearchModeToggle** — GPT-style pill near chat input
- [x] **ConfidenceBadge** — source-count-based confidence scoring
- [x] **Streaming** — SSE token-by-token with parallel artifact generation

### Still Needed (P1 — Phase 3)
- [ ] `agent-transcripts/` folder — raw failure/correction logs (rubric mandatory)
- [ ] Video demo recording (2-3 min, camera on, by Aug 2)
- [ ] Remove debug console.logs before final submission
- [ ] README update — add Research Mode setup + endpoint docs

### Explicitly Cut (P2 — cut without guilt)
- Authentication / multi-user
- Full 269-episode ingestion (config change, not architecture change)
- Any cloud deployment (evaluator runs locally with their own keys)

---

## 4. Success Criteria

| Criterion | Measurable target |
|---|---|
| Q&A grounded in transcripts | Answers cite specific guests by name; "I don't know" when context is absent |
| Essay quality | Ship30for30 structure followed: headline, golden intersection, wheels-and-spokes, bold takeaway |
| Artifact rendering | HTML renders in sandboxed iframe; Markdown renders with syntax highlighting |
| Both LLM providers work | Demo shows Ollama response AND Anthropic response for same query |
| Local setup time | Evaluator can run `README` steps and reach a working app in < 15 min |
| DB persistence | Refresh page → sessions and history still present |

---

## 5. Data Scope Decision (write this in your demo)

**Curated subset:** ~40-80 episodes from four index files:
- `index/product-management.md`
- `index/growth-strategy.md`
- `index/product-market-fit.md`
- `index/leadership.md`

**Rationale:** Embedding 269 full transcripts at ~700-token chunks is ~5,000+ embedding API calls. Curating to 60 high-signal episodes still covers the most-cited guests (Brian Chesky, Shreyas Doshi, Bangaly Kaba, etc.) and allows a demo-ready knowledge base within a 3-day build window.

**Scaling:** Changing `CURATED_INDEX_FILES` in `scripts/ingest.py` to include all index files scales to all 269 episodes without any architecture change.

---

## 6. Technical Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| Database | Supabase Postgres + pgvector | Satisfies mandatory requirement; vector search in same DB |
| Embeddings | `nomic-embed-text` via Ollama | 8k context window; zero new deps |
| Local LLM | `qwen3:4b` / any Ollama model (via `.env`) | Model-agnostic; evaluator substitutes their own |
| Cloud LLM | Anthropic `claude-sonnet-5` (optional) | Evaluator's own API key; falls back to Ollama if absent |
| Classic Router | Rule-based keyword classifier | Deterministic, zero latency, explainable |
| Research Router | OrchestratorAgent (LLM JSON plan + keyword fallback) | Adaptive; graceful fallback if LLM returns invalid JSON |
| Streaming | SSE token-by-token (WriterAgent) | Perceived latency ↓; user sees content at ~8s not ~60s |
| Agent framework | Pure Python async (CrewAI conceptual model) | Avoids Ollama/OpenAI tool-calling incompatibility |
| Parallelism | asyncio.gather() for Writer + Artifact | ~30% latency reduction on essay+dashboard queries |
| Self-healing | ValidatorAgent loop (max 2 retries) | Broken HTML fixed automatically; "⚡ Self-healed" UI banner |
| Tools | Pure Python functions, not LLM function-calling | Sidesteps Ollama tool-calling protocol issues entirely |
