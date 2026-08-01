# PRD: Lenny's Growth Assistant

**Version:** 1.0 — MVP complete  
**Status:** Submitted  
**Author:** Jinu  
**Date:** 2026-08-03

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
- [x] `agent-transcripts/` folder with real failures and lessons
- [x] `docs/` — PRD.md, design.md, architecture.md
- [x] README with local setup instructions (evaluator runs with their own keys)
- [x] Demo video

### Out of Scope (P1 — if time allows)
- [ ] Citation cards with YouTube deep-links
- [ ] Dropdown to switch between multiple local models
- [ ] Per-session loading / empty states
- [ ] Basic automated tests

### Explicitly Cut (P2 — cut without guilt)
- Streaming responses (conflicts with artifact tag parsing; not in rubric)
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
| Embeddings | `nomic-embed-text` via Ollama | 8k context window (vs MiniLM's 256 tokens); zero new deps |
| Local LLM | `llama3.2` / any Ollama model (configurable via `.env`) | Evaluator substitutes their own model; app is model-agnostic |
| Cloud LLM | Anthropic `claude-sonnet-5` (optional) | Requires evaluator's own API key; app falls back to Ollama if key absent |
| Router | Rule-based keyword classifier | Deterministic, zero latency, trivially explainable |
| Streaming | Disabled for MVP | Conflicts with `<artifact>` tag extraction from full response |
| Agent framework | None — 50-line router | Easier to explain; no dependency risk under time pressure |
