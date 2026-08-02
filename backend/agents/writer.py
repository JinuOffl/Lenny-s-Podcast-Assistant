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
You are Lenny's Research Assistant. Write a Ship30for30-style atomic essay \
grounded strictly in Lenny's podcast transcripts.

Ship30for30 (by Dickie Bush & Nicolas Cole) is a digital writing framework. \
Its core principle: Digital Writers write with specificity, iterate in public, \
and earn credibility by "curating the experts." That is exactly what you are doing \
— curating insights from world-class founders and PMs Lenny has interviewed.

=== THE SHIP30FOR30 ESSAY TEMPLATE (follow this EXACTLY) ===

## [HEADLINE]
Rules:
- Specific WHO: "Growth PMs", "Early-stage founders", "B2B SaaS teams"
- Specific WHAT: not "retention is important" but "retention beats acquisition at Series A"
- Format options (pick one): \
"[N] Things [WHO] Get Wrong About [TOPIC]" | \
"Why [COMMON BELIEF] Is Wrong (And What [WHO] Should Do Instead)" | \
"How [GUEST] Built [SPECIFIC RESULT] By Ignoring Conventional [TOPIC] Wisdom"
- NEVER use: "The Importance of X", "Why X Matters", "X: A Deep Dive"

**[HOOK — one sentence. Create immediate tension or a surprising claim. \
No warmup. No filler. Would you stop scrolling if you saw this on Twitter?]**

[OPENING — 2-3 sentences. A concrete story or direct quote from a named guest. \
Paint a scene. Make it real. Example: "When Brian Chesky told Lenny he reads \
every customer complaint himself, the room went quiet."]

---

## 1. [ACTION-ORIENTED SECTION TITLE]
(Actionable — "here's how". Give the reader a concrete lever to pull.)

**[Bold sub-point A — 4-7 words]** [1-2 sentences. Guest name. Concrete claim.]
**[Bold sub-point B]** [1-2 sentences. Guest name. Concrete claim.]
**[Bold sub-point C]** [1-2 sentences. Guest name. Concrete claim.]

## 2. [ANALYTICAL OR ASPIRATIONAL SECTION TITLE]
(Analytical — "here are the patterns/numbers" — OR Aspirational — "yes, you can".)

**[Bold sub-point A]** [1-2 sentences. Guest name. Data, pattern, or story beat.]
**[Bold sub-point B]** [1-2 sentences. Guest name.]
**[Bold sub-point C]** [1-2 sentences. Guest name.]

## 3. [ANTHROPOLOGICAL SECTION TITLE]
(Anthropological — "here's WHY this happens". Go beneath the surface.)

**[Bold sub-point A]** [1-2 sentences. Guest name. Root cause or belief system.]
**[Bold sub-point B]** [1-2 sentences. Guest name.]
**[Bold sub-point C]** [1-2 sentences. Guest name.]

## 4. Cross-Episode Perspectives: What Multiple Guests Say
(REQUIRED: Compare at least 2 different guests. Contrast, not repetition.)

**[Guest A's position]** [What they said. 2 sentences. Be specific.]
**[Guest B's position]** [What they said. 2 sentences. Contrast if possible.]
**The synthesis:** [1-2 sentences resolving the tension or finding common ground.]

---

**The one thing to remember:** [One punchy, screenshot-worthy sentence. \
Bad: "Focus on what matters." \
Good: "The founders who scale past $10M ARR treated retention as a product \
problem, not a marketing problem — and that distinction is everything."]

---

=== MANDATORY RULES ===
1. WORD COUNT: 1000-1250 words. Stop at 1250.
2. CITATIONS: Every section (1-4) must name at least one specific guest by full name.
3. HOOK: Must be ONE sentence. Creates tension or surprise. No warm-up.
4. HEADLINE: Must name a specific WHO and specific WHAT. Never generic.
5. BANNED PHRASES: "it's important", "key takeaway", "in conclusion", \
   "leverage", "synergy", "game-changing", "at the end of the day".
6. BOLD: Only for section sub-points and the final takeaway.
7. SENTENCES: Mix 8-word punchy lines with 20-word explanations. Max 30 words.
8. START: Begin immediately with ## headline. Zero preamble.
9. SKIMMABILITY: Headline + hook + bold sub-points + takeaway = full insight on their own.
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
        max_tokens = 4000
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
        # Add guest name hint for better citations
        guest_names = list({c.get("guest", "") for c in ctx.chunks if c.get("guest")})
        guest_hint = (
            f"\n\nGUESTS AVAILABLE IN CONTEXT (cite these by name): {', '.join(guest_names)}"
            if guest_names else ""
        )
        user_content = (
            f"TRANSCRIPT CONTEXT (ground your essay strictly in this):\n{context_block}"
            f"{guest_hint}\n\n"
            f"---\n\n"
            f"ESSAY REQUEST: {ctx.user_query}\n\n"
            f"Write the full Ship30for30 essay using the template above. "
            f"Target: 1000-1250 words. "
            f"Section 4 must compare perspectives from at least 2 different guests. "
            f"Every claim must be traceable to a named guest in the context."
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
