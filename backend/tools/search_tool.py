"""
tools/search_tool.py — RAG retrieval tool for Research Mode agents.

These are PURE PYTHON FUNCTIONS — not LLM tool calls.
Results are injected as text into agent task descriptions,
making them compatible with Ollama and any other LLM.
"""
from __future__ import annotations
from typing import List, Dict, Tuple
import sys
import os

# Ensure backend root is on path when imported from agents/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import retrieve, build_context, dedupe_sources


async def execute_search(
    query: str,
    conn,
    top_k: int = 5,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Single-hop RAG search.

    Returns:
        (context_text, sources, raw_chunks)
    """
    chunks = await retrieve(query, conn, top_k=top_k)
    context = build_context(chunks)
    sources = dedupe_sources(chunks)
    return context, sources, chunks


async def execute_multi_hop_search(
    queries: List[str],
    conn,
    top_k_per_query: int = 5,
    max_total_chunks: int = 10,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Multi-hop RAG: runs multiple search queries and merges results.
    Deduplicates by (episode_slug, chunk_index) to avoid repetition.

    Returns:
        (context_text, sources, merged_chunks)
    """
    all_chunks: List[Dict] = []
    seen: set = set()

    for query in queries:
        chunks = await retrieve(query, conn, top_k=top_k_per_query)
        for chunk in chunks:
            key = f"{chunk.get('episode_slug', '')}_{chunk.get('chunk_index', 0)}"
            if key not in seen:
                seen.add(key)
                all_chunks.append(chunk)

    # Cap and sort by similarity (already returned ordered by similarity)
    merged = all_chunks[:max_total_chunks]
    context = build_context(merged)
    sources = dedupe_sources(merged)
    return context, sources, merged


def assess_research_quality(chunks: List[Dict], min_chunks: int = 4) -> Tuple[bool, str]:
    """
    Determine if the research result is rich enough.

    Returns:
        (is_sufficient, reason)
    """
    if not chunks:
        return False, "No transcript chunks found — topic may not be covered in the knowledge base"

    unique_episodes = len({c.get("episode_slug", "") for c in chunks})

    if len(chunks) < min_chunks:
        return False, f"Only {len(chunks)} chunks found across {unique_episodes} episode(s) — expanding search"

    if unique_episodes < 2:
        return False, f"All chunks from a single episode — expanding to cross-reference more guests"

    return True, f"Found {len(chunks)} chunks from {unique_episodes} episodes — sufficient for analysis"


def build_cross_episode_summary(chunks: List[Dict]) -> str:
    """
    Group chunks by guest and return a structured summary string
    used by the WriterAgent to write comparative sections.

    Example output:
        PERSPECTIVES FOUND:
        • Brian Chesky (Airbnb): [key point from chunks]
        • Casey Winters (Eventbrite): [key point from chunks]
    """
    guest_map: Dict[str, List[str]] = {}
    for chunk in chunks:
        guest = chunk.get("guest", "Unknown Guest")
        if guest not in guest_map:
            guest_map[guest] = []
        # Take first 200 chars of each chunk as a representative snippet
        snippet = chunk.get("content", "")[:200].replace("\n", " ").strip()
        guest_map[guest].append(snippet)

    if not guest_map:
        return ""

    lines = ["CROSS-EPISODE PERSPECTIVES:"]
    for guest, snippets in guest_map.items():
        # Take the first (highest-similarity) snippet per guest
        lines.append(f"  • {guest}: {snippets[0]}...")

    return "\n".join(lines)
