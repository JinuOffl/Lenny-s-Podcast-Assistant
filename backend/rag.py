"""
rag.py — Retrieval-Augmented Generation helpers.

Provides:
  - get_embedding(text)  — calls Ollama nomic-embed-text
  - retrieve(query, conn, top_k) — pgvector cosine similarity search
"""
from __future__ import annotations
import asyncio
import json as _json
import urllib.request
from typing import List, Dict
from config import settings


# ── Embedding ─────────────────────────────────────────────────────────────────

def _embed_sync(text: str) -> List[float]:
    """Sync urllib call to Ollama — runs in a thread pool to stay non-blocking."""
    payload = _json.dumps({"model": settings.ollama_embed_model, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{settings.ollama_base_url}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = _json.loads(resp.read())
    return data["embedding"]


async def get_embedding(text: str) -> List[float]:
    """
    Get a 768-dim embedding from Ollama nomic-embed-text.
    Runs the sync urllib call in a thread pool so the event loop stays unblocked.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _embed_sync, text)



# ── Retrieval ─────────────────────────────────────────────────────────────────

async def retrieve(query: str, conn, top_k: int | None = None) -> List[Dict]:
    """
    Embed the query then retrieve the top-k most similar transcript chunks
    using pgvector cosine similarity.

    Returns a list of dicts with keys:
        content, guest, episode_title, youtube_url, episode_slug, chunk_index
    """
    k = top_k or settings.rag_top_k
    embedding = await get_embedding(query)

    # pgvector cosine distance operator: <=>
    # psycopg3: pass embedding as string repr of list for ::vector cast
    emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
    cur = await conn.execute(
        """
        SELECT
            content,
            guest,
            episode_title,
            youtube_url,
            episode_slug,
            chunk_index,
            1 - (embedding <=> %s::vector) AS similarity
        FROM transcript_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (emb_str, emb_str, k),
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]


def build_context(chunks: List[Dict]) -> str:
    """
    Format retrieved chunks into a context block for the LLM prompt.
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        guest = chunk.get("guest", "Unknown")
        title = chunk.get("episode_title", "Unknown Episode")
        parts.append(
            f"--- Source {i}: {guest} — \"{title}\" ---\n{chunk['content']}"
        )
    return "\n\n".join(parts)


def dedupe_sources(chunks: List[Dict]) -> List[Dict]:
    """
    Return unique episode sources (deduped by youtube_url) from retrieved chunks.
    """
    seen: set[str] = set()
    sources = []
    for chunk in chunks:
        url = chunk.get("youtube_url", "")
        if url not in seen:
            seen.add(url)
            sources.append({
                "guest": chunk.get("guest", ""),
                "episode_title": chunk.get("episode_title", ""),
                "youtube_url": url,
            })
    return sources
