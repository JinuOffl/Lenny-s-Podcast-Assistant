# PRD: Lensight (Lenny's Growth Assistant)

**Version:** 2.1 — Production Complete  
**Status:** Shipped (All Phases Done)  
**Author:** Jinu  
**Date:** 2026-08-02

---

## 1. Problem Statement

Product and growth practitioners spend hours rewatching Lenny's Podcast to surface specific advice. Content is locked inside long-form videos across 260+ episodes without a natural language query interface, structured essay generator, or interactive dashboard builder.

---

## 2. Target User

A PM, growth lead, or early-stage founder who:
- Regularly listens to Lenny's Podcast and trusts its growth frameworks
- Wants to query across episodes ("What did growth leaders say about retention?")
- Rapidly generates structured Ship30for30 essays or shareable HTML dashboards
- Runs the application locally with Ollama or switches to Anthropic API keys

---

## 3. Feature Checklist & Implementation Status

### Core Features (All Complete)

- [x] **FastAPI backend** with Supabase Postgres + `pgvector` storage
- [x] **Session management** — create, rename, delete, persistent history
- [x] **LLM Provider Toggle:** Local Ollama (`qwen3:4b`) ↔ Cloud Anthropic (`claude-sonnet-5`)
- [x] **Grounded Q&A:** Vector retrieval over ~180 transcript episodes (`nomic-embed-text`, 768-dim)
- [x] **Ship30for30 Essay Skill:** Structured atomic essays (~1000-1250 words) grounded in podcast frameworks

### Artifact System (Complete)

- [x] **Two-Call Split Artifact Architecture:**
  - Call 1: Concise 1-sentence intro shown in chat bubble
  - Call 2: Pure raw HTML dashboard page (zero regex tag parsing)
  - Self-repair loop in ValidatorAgent for malformed HTML
- [x] **In-App Artifact Viewer:** Sandboxed `<iframe>` Preview tab + Source tab with copy button

### Agentic Routing (Complete)

- [x] **2-Stage Skill Router:**
  - Stage 1: instant followup detection (chitchat set, pronoun + short message, followup signals) — zero LLM
  - Stage 2: LLM call at `max_tokens=12` → one-word classification
  - Fallback: keyword matching if LLM fails or returns unexpected value
  - 5 skills: `qa`, `ship30for30`, `artifact`, `multi`, `followup`

### Research Mode — 5-Agent Pipeline (Complete)

- [x] **OrchestratorAgent:** LLM-powered JSON execution plan (crew_type, complexity, search queries)
- [x] **ResearchAgent:** Multi-hop RAG (1-2 search passes, cross-episode synthesis, no LLM)
- [x] **WriterAgent:** Streams QA answers or Ship30for30 essays token-by-token
- [x] **ArtifactAgent:** Generates interactive HTML dashboards (runs parallel with WriterAgent)
- [x] **ValidatorAgent:** Quality checks + self-healing loop (max 2 attempts, HTML repair)
- [x] **SharedContext:** Mutable working memory dataclass passed through all 4 phases

### UI & Design (Complete)

- [x] **Lensight dark monochrome design system** — near-pure black, white-only accents
- [x] **Live AgentTracker** pipeline visualization (Research Mode)
- [x] **ResearchStats** — chunks found, episodes, search hops, word count
- [x] **SourcesAccordion** — collapsible episode citations with YouTube links
- [x] **ConfidenceBadge** — high / medium / low based on source count
- [x] **SkillBadge** — Q&A / Essay / Artifact / Multi
- [x] **Empty-state suggestion chips** — categorized by skill type
- [x] **Smart session title generation** — LLM-generated on first message

---

## 4. Architecture Summary

| Layer | Component | Implementation |
|---|---|---|
| Frontend | React 18 + Vite + Tailwind | Split-pane chat & artifact viewer, 12 components |
| API Layer | FastAPI | SSE streaming endpoints (`/chat/stream`, `/chat/research/stream`) |
| Skill Router | `router.py` | 2-stage: instant followup detection + LLM classification |
| Vector Storage | Supabase Postgres (`pgvector`) | 768-dim embeddings (`nomic-embed-text`) |
| Classic Skills | `skills/` | qa, ship30for30, artifact — direct RAG → LLM pipeline |
| Agent Engine | `agents/` | 5-agent async pipeline with `asyncio.gather` parallelism |
| Artifact Engine | Two-Call Split | Call 1 intro + Call 2 raw HTML + ValidatorAgent self-healing |
| LLM Providers | `llm.py` | `LLMProvider` ABC — OllamaProvider + AnthropicProvider |

---

## 5. Constraints & Non-Goals

- **No user authentication** — single-user local demo
- **No real-time collaboration** — single session per browser
- **Ollama must be running locally** for embeddings regardless of which chat LLM is selected
- **Transcript corpus is read-only** — no user-uploaded documents in this version
