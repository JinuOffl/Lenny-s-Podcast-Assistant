# Architecture: Lenny's Growth Assistant

**Version:** 0.1

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User's Browser                           │
│   React + Vite + Tailwind                                       │
│   ┌──────────┐  ┌──────────────────┐  ┌───────────────────┐   │
│   │ Sidebar  │  │    Chat Pane     │  │   Artifact Pane   │   │
│   │ sessions │  │ messages + input │  │ iframe / markdown │   │
│   └──────────┘  └──────────────────┘  └───────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP JSON (no streaming)
┌────────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend (port 8000)                   │
│                                                                  │
│   POST /sessions/{id}/chat                                       │
│        │                                                         │
│        ▼                                                         │
│   router.classify_skill()   ← deterministic keyword match       │
│        │                                                         │
│        ├── "qa"          → skills/qa.py                         │
│        ├── "ship30for30" → skills/ship30for30.py                │
│        └── "artifact"    → skills/artifact.py                   │
│              │                                                   │
│              ▼                                                   │
│         rag.retrieve()   ← pgvector cosine similarity           │
│              │                                                   │
│              ▼                                                   │
│         llm.chat()       ← OllamaProvider | AnthropicProvider   │
│              │                                                   │
│              ▼                                                   │
│        persist message → Supabase                                │
│        return ChatResponse JSON                                  │
└────────────┬─────────────────────────────────────────────────────┘
             │
    ┌────────┴──────────────────────────────────────┐
    │           Supabase Postgres (pgvector)         │
    │   sessions │ messages │ transcript_chunks      │
    └────────────┴──────────────────────────────────┘
             │
    ┌────────┴──────────────┐
    │       Ollama           │
    │  llama3.3:8b (chat)   │
    │  nomic-embed-text      │
    └───────────────────────┘
```

---

## Key Design Decisions

### 1. Rule-based Router (not an LLM classifier)

**Decision:** Classify user intent with keyword matching, not an LLM call.

**Reasoning:** With 3 skills and clearly differentiated trigger phrases, a keyword classifier achieves >95% accuracy with zero latency and zero token cost. An LLM classifier adds ~1-2 seconds of latency and 200-500 tokens per request for no accuracy gain at this scale. If we ever need 10+ skills with nuanced overlap (e.g., "compare retention strategies across companies" might be QA or ship30), we'd switch to an embedding-based nearest-neighbour classifier against skill descriptions. That's P2.

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
