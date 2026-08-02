"""
agents/research.py — ResearchAgent

Performs multi-hop RAG retrieval from Lenny's Podcast transcript chunks.
Uses the Orchestrator's plan (search queries, complexity) to determine
how many hops to run and how many chunks to retrieve.

No LLM calls in this agent — pure vector search + Python analysis.
The agent's "intelligence" is in the multi-hop logic and quality assessment.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMProvider

from agents.shared_context import SharedContext
from tools.search_tool import (
    execute_search,
    execute_multi_hop_search,
    assess_research_quality,
    build_cross_episode_summary,
)


async def run_research_agent(
    ctx: SharedContext,
    conn,
) -> SharedContext:
    """
    ResearchAgent execution.

    Strategy:
      1. Run primary search (from Orchestrator's refined query)
      2. Assess quality — if thin (<4 chunks or single episode), do second hop
      3. If complexity=deep/multi, always do multi-hop for richer context
      4. Build cross-episode summary for WriterAgent's comparative analysis
    """
    plan = ctx.plan
    query = plan.primary_search_query or ctx.user_query

    # ── Hop 1: Primary search ─────────────────────────────────────────────────
    top_k = 6 if plan.complexity in ("deep", "multi") else 5
    context, sources, chunks = await execute_search(query, conn, top_k=top_k)

    ctx.search_hops = 1
    ctx.chunks = chunks
    ctx.sources = sources
    ctx.context_text = context

    sufficient, quality_msg = assess_research_quality(chunks)
    ctx.add_step("ResearchAgent", f"🔍 Found {len(chunks)} chunks from {len(sources)} episode(s)")
    print(f"[ResearchAgent] Hop 1: {len(chunks)} chunks, {len(sources)} episodes — {quality_msg}")

    # ── Hop 2: Expand if needed ───────────────────────────────────────────────
    needs_second_hop = (
        not sufficient  # thin results
        or plan.complexity in ("deep", "multi")  # always go deep for research
        or bool(plan.secondary_search_query)  # Orchestrator asked for it
    )

    if needs_second_hop:
        ctx.add_step("ResearchAgent", f"🔄 Expanding search — {quality_msg}")
        print(f"[ResearchAgent] Triggering Hop 2 — {quality_msg}")

        queries = [query]
        if plan.secondary_search_query:
            queries.append(plan.secondary_search_query)
        else:
            # Auto-generate a complementary query by reformulating
            queries.append(_reformulate_query(ctx.user_query))

        context2, sources2, chunks2 = await execute_multi_hop_search(
            queries=queries,
            conn=conn,
            top_k_per_query=5,
            max_total_chunks=10,
        )

        ctx.search_hops = 2
        ctx.chunks = chunks2
        ctx.sources = sources2
        ctx.context_text = context2
        ctx.add_step(
            "ResearchAgent",
            f"✅ Research complete — {len(chunks2)} chunks from {len(sources2)} episodes (2 hops)",
        )
        print(f"[ResearchAgent] Hop 2 complete: {len(chunks2)} total chunks, {len(sources2)} episodes")

    # ── Compute confidence and cross-episode summary ──────────────────────────
    ctx.confidence = ctx.compute_confidence()
    ctx.research_summary = build_cross_episode_summary(ctx.chunks)
    ctx.episodes_searched = len({c.get("episode_slug", "") for c in ctx.chunks})

    print(f"[ResearchAgent] Done. confidence={ctx.confidence}, episodes={ctx.episodes_searched}")
    return ctx


def _reformulate_query(original_query: str) -> str:
    """
    Simple query reformulation for second hop.
    Adds PM/growth context to broaden or deepen the search.
    """
    # Strip common question words and rephrase as topic search
    import re
    cleaned = re.sub(
        r"^(what|how|why|when|who|did|does|can|should|tell me|explain)\s+",
        "",
        original_query.lower().strip(),
    )
    # Add complementary growth context
    growth_terms = ["strategy", "framework", "lessons", "advice", "examples"]
    return f"{cleaned} {growth_terms[hash(original_query) % len(growth_terms)]}"
