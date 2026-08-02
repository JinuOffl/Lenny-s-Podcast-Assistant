"""
agents/writer.py — WriterAgent

Generates the primary text response: either a grounded QA answer
or a Ship30for30 atomic essay, using the research context built by
ResearchAgent.

Key feature: exposes an async generator (stream_response) so the
SSE endpoint can stream tokens to the user in real-time while
ArtifactAgent runs concurrently in the background.
"""
from __future__ import annotations
from typing import AsyncGenerator, List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMProvider

from agents.shared_context import SharedContext

# ── System prompts ────────────────────────────────────────────────────────────

QA_SYSTEM_PROMPT = """\
You are Lenny's Research Assistant — built from Lenny Rachitsky's podcast transcripts 
covering product management, growth, and startups.

=== YOUR RULES ===
1. Answer ONLY using the transcript context provided. Do not use outside knowledge.
2. Always cite specific guests by name (e.g. "Brian Chesky told Lenny...", "According to Claire Vo...").
3. If context doesn't contain a clear answer, say: "I don't have grounded information on this from Lenny's Podcast."
4. When guests disagree or have different perspectives, highlight the contrast explicitly.

=== OUTPUT FORMAT ===
- Use **bold** for every key name, concept, or number
- Use bullet points for lists of 3+ items
- Short paragraphs (2-3 sentences max)
- For multi-part answers, use ## headers
- Include a **Cross-Episode Perspective** section when multiple guests covered the topic
- End with a **Bottom line:** sentence summarizing the core insight

Keep responses concise. No fluff. Every claim must be traceable to a specific guest.
"""

ESSAY_SYSTEM_PROMPT = """\
You are Lenny's Research Assistant. Your task: write a Ship30for30-style atomic essay 
grounded in Lenny's podcast transcripts.

=== OUTPUT FORMAT (copy this structure EXACTLY) ===

## [Headline: specific WHO + WHAT insight + WHY it matters. NOT generic.]

**[Hook: ONE sentence. Surprising claim or tension. No filler.]**

[Opening: 2-3 sentences. Concrete story or quote from transcript. Name the guest explicitly.]

---

## 1. [Action-oriented Section Title]

**[Bold point A — 4-6 words]** [Expand 1-2 sentences. Cite guest name.]
**[Bold point B — 4-6 words]** [Expand 1-2 sentences. Cite guest name.]
**[Bold point C — 4-6 words]** [Expand 1-2 sentences. Cite guest name.]

## 2. [Section Title]

**[Bold point A]** [1-2 sentences with guest citation.]
**[Bold point B]** [1-2 sentences with guest citation.]
**[Bold point C]** [1-2 sentences with guest citation.]

## 3. [Section Title]

**[Bold point A]** [1-2 sentences with guest citation.]
**[Bold point B]** [1-2 sentences with guest citation.]
**[Bold point C]** [1-2 sentences with guest citation.]

## 4. [Cross-Episode Perspectives]

**[Guest A's view]** vs **[Guest B's view]** — [1-2 sentences comparing them.]

---

**The one thing to remember:** [One punchy, memorable sentence. Bold it.]

---

=== MANDATORY RULES ===
1. WORD COUNT: Write exactly 1000-1250 words.
2. CITATIONS: Every section MUST name at least one guest by name from the context.
3. NO VAGUE PLATITUDES: Ban — "it's important", "key takeaway", "leverage", "synergy".
4. BOLD TEXT: Use **bold** only for sub-points, guest names on first mention, and final takeaway.
5. START IMMEDIATELY with ## headline. No preamble.
6. CROSS-EPISODE: Section 4 must explicitly compare perspectives from different guests.
"""


# ── Public interface ──────────────────────────────────────────────────────────

async def stream_writer_response(
    ctx: SharedContext,
    provider: "LLMProvider",
) -> AsyncGenerator[str, None]:
    """
    Stream WriterAgent tokens. Yields token strings.
    Updates ctx.primary_response and ctx.skill_used as it goes.
    """
    plan = ctx.plan

    # Determine skill and system prompt
    if plan.needs_essay:
        system_prompt = ESSAY_SYSTEM_PROMPT
        skill = "ship30for30"
        max_tokens = 3500
    elif ctx.chunks:
        system_prompt = QA_SYSTEM_PROMPT
        skill = "qa"
        max_tokens = 2048
    else:
        system_prompt = QA_SYSTEM_PROMPT
        skill = "followup"
        max_tokens = 1024

    ctx.skill_used = skill
    ctx.add_step(
        "WriterAgent",
        f"✍️  {'Writing essay' if skill == 'ship30for30' else 'Generating answer'} from {len(ctx.chunks)} sources...",
    )

    # Build messages list — last N turns of history (excluding system-like messages)
    messages: List[Dict] = []
    if ctx.history:
        # Include up to last 6 history messages for context
        for m in ctx.history[-6:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": m["content"][:1000]})

    # Build the user content with context injected
    context_block = ctx.context_text or ""
    if ctx.research_summary and len(ctx.chunks) > 3:
        context_block = f"{ctx.research_summary}\n\n---\n\n{context_block}"

    if skill == "ship30for30":
        user_content = (
            f"TRANSCRIPT CONTEXT (ground your essay in this):\n{context_block}\n\n"
            f"---\n\n"
            f"ESSAY REQUEST: {ctx.user_query}\n\n"
            f"Write the full Ship30for30 essay. ~1000-1250 words. "
            f"Include cross-episode perspectives in Section 4. "
            f"Cite specific guests by name."
        )
    elif skill == "followup":
        user_content = f"QUESTION: {ctx.user_query}"
    else:
        user_content = (
            f"TRANSCRIPT CONTEXT:\n{context_block}\n\n"
            f"---\n\n"
            f"QUESTION: {ctx.user_query}"
        )

    messages.append({"role": "user", "content": user_content})

    # Stream tokens
    tokens_collected: List[str] = []
    try:
        async for token in provider.stream(messages, system_prompt=system_prompt, max_tokens=max_tokens):
            tokens_collected.append(token)
            yield token
    except Exception as e:
        print(f"[WriterAgent] Stream error: {e}")
        # Fall back to non-streaming chat
        try:
            fallback = await provider.chat(messages, system_prompt=system_prompt, max_tokens=max_tokens)
            tokens_collected.append(fallback)
            yield fallback
        except Exception as e2:
            print(f"[WriterAgent] Fallback chat also failed: {e2}")

    ctx.primary_response = "".join(tokens_collected)
    ctx.add_step("WriterAgent", f"✅ Response generated ({len(ctx.primary_response.split())} words)")



def _build_writer_prompt(ctx: SharedContext):
    """Build the appropriate prompt based on execution plan."""
    plan = ctx.plan

    if plan.needs_essay:
        system = ESSAY_SYSTEM_PROMPT
        content = (
            "TRANSCRIPT CONTEXT (ground your essay in this):\n{context}\n\n"
            "---\n\n"
            "ESSAY REQUEST: {query}\n\n"
            "Write the full Ship30for30 essay. ~1000-1250 words. "
            "Include cross-episode perspectives in Section 4. "
            "Cite specific guests by name."
        )
        skill = "ship30for30"
    else:
        # Follow-up: skip context block if no chunks
        system = QA_SYSTEM_PROMPT
        if ctx.chunks:
            content = (
                "TRANSCRIPT CONTEXT:\n{context}\n\n"
                "---\n\n"
                "QUESTION: {query}"
            )
            skill = "qa"
        else:
            # Pure follow-up on history
            content = "QUESTION: {query}"
            skill = "followup"

    return system, content, skill
