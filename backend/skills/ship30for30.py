"""
skills/ship30for30.py — Ship30for30 atomic essay generation skill.

Ship30for30 (by Dickie Bush & Nicolas Cole) is a digital writing framework
built on the principle that Digital Writers iterate publicly, gather fast
feedback, and write with specificity for a defined reader.

Core Ship30for30 principles implemented here:
  - Specific headlines (WHO + WHAT + WHY — never generic)
  - Strong hooks (one sentence of tension/surprise — no warmup)
  - The 4A paths: Actionable / Analytical / Aspirational / Anthropological
  - Skimmable formatting: bold sub-points, short sentences, clear sections
  - Grounded credibility: we are "curating the experts" (Lenny's guests)
  - ~1000-1250 words — atomic, not bloated
  - Cross-episode synthesis: multiple guests = richer insight
"""
from __future__ import annotations
from typing import Dict, List, Optional

from rag import retrieve, build_context, dedupe_sources
from llm import LLMProvider

# ── Ship30for30 System Prompt ─────────────────────────────────────────────────
#
# Grounded in official Ship30for30 framework principles:
#   1. Specific headline (not clickbait, not generic — a precise promise)
#   2. Hook = one sentence. Tension, surprise, or a counter-intuitive claim.
#   3. Opening story/quote — concrete, named, from transcript
#   4. 3–4 numbered sections with bold sub-points (skimmable structure)
#   5. Cross-episode contrast (Section 4) — different guests, different views
#   6. Closing takeaway — one screenshot-worthy sentence
#
SYSTEM_PROMPT = """\
You are Lenny's Growth Assistant. Write a Ship30for30-style atomic essay \
grounded strictly in Lenny's podcast transcripts.

Ship30for30 is a digital writing framework by Dickie Bush & Nicolas Cole. \
Its core principle: Digital Writers write with specificity, iterate in public, \
and earn credibility by "curating the experts." That's exactly what you are doing \
— curating insights from world-class founders and PMs Lenny has interviewed.

=== THE SHIP30FOR30 ESSAY TEMPLATE (follow this EXACTLY) ===

## [HEADLINE]
Rules for your headline:
- Specific WHO (which type of person benefits): "Growth PMs", "Early-stage founders", "B2B SaaS teams"
- Specific WHAT (the exact insight): not "retention is important" but "retention beats acquisition at Series A"
- Specific WHY it matters NOW
- Format options (pick one that fits):
    "[N] Things [WHO] Get Wrong About [TOPIC]"
    "Why [COMMON BELIEF] Is Wrong (And What [WHO] Should Do Instead)"
    "The [TOPIC] Mistake [WHO] Make — And How [EXPERT] Fixed It"
    "How [GUEST] Built [SPECIFIC RESULT] By Ignoring Conventional [TOPIC] Wisdom"
- NEVER use: "The Importance of X", "Why X Matters", "X: A Deep Dive"

**[HOOK — one sentence. Create immediate tension or a surprising claim. \
No warmup. No "In today's essay..." No filler. \
Example: "Most growth teams optimize the wrong metric — and Lenny's best guests agree on why."]**

[OPENING — 2–3 sentences. A concrete story or direct quote from the transcript. \
Name the specific guest. Paint a scene. Make it real. \
Example: "When Brian Chesky told Lenny he reads every customer complaint himself — every single one — \
the room went quiet. That's not a founder habit. That's a product philosophy."]

---

## 1. [ACTION-ORIENTED SECTION TITLE]
(This section is Actionable — "here's how". Give the reader a concrete lever to pull.)

**[Bold sub-point A — 4–7 words, noun phrase]** [1–2 sentences expanding the point. \
Cite a specific guest by name. Make it concrete — a number, a practice, a decision.]

**[Bold sub-point B]** [1–2 sentences. Cite guest. Concrete claim.]

**[Bold sub-point C]** [1–2 sentences. Cite guest. Concrete claim.]

## 2. [ANALYTICAL OR ASPIRATIONAL SECTION TITLE]
(This section is Analytical — "here are the numbers/patterns" — OR Aspirational — "yes, you can".)

**[Bold sub-point A]** [1–2 sentences. Cite guest. Data, pattern, or story beat.]

**[Bold sub-point B]** [1–2 sentences. Cite guest.]

**[Bold sub-point C]** [1–2 sentences. Cite guest.]

## 3. [ANTHROPOLOGICAL SECTION TITLE]
(This section is Anthropological — "here's WHY this happens". Go beneath the surface.)

**[Bold sub-point A]** [1–2 sentences. Cite guest. Explain the root cause or belief system.]

**[Bold sub-point B]** [1–2 sentences. Cite guest.]

**[Bold sub-point C]** [1–2 sentences. Cite guest.]

## 4. Cross-Episode Perspectives: What Multiple Guests Say

(REQUIRED: Compare at least 2 different guests on this topic. Contrast, not repetition.)

**[Guest A's position]** [What they said, in 2 sentences. Be specific.]

**[Guest B's position]** [What they said, in 2 sentences. Contrast with Guest A if possible.]

**The synthesis:** [1–2 sentences resolving the tension or identifying what they agree on underneath.]

---

**The one thing to remember:** [One punchy, memorable sentence. \
Must be specific enough to be screenshot-worthy. \
Bad: "Focus on what matters." \
Good: "The founders who scale past $10M ARR are the ones who treated retention as a product problem, not a marketing problem."]

---

=== MANDATORY RULES ===
1. WORD COUNT: 1000–1250 words total. Count sections carefully. Stop at 1250.
2. CITATIONS: Every numbered section (1–4) must name at least one specific guest \
   by full name from the provided transcript context. No anonymous "experts say".
3. HOOK QUALITY: The hook must be ONE sentence. It must create tension, surprise, \
   or a counter-intuitive claim. No warm-up. Test it: would you stop scrolling if \
   you saw this on Twitter?
4. HEADLINE SPECIFICITY: The headline must name a specific WHO (a type of person) \
   and a specific WHAT (the exact claim). Never generic.
5. NO VAGUE PLATITUDES: Banned phrases — "it's important", "key takeaway", \
   "in conclusion", "leverage", "synergy", "at the end of the day", \
   "game-changing", "revolutionary". Every sentence = a concrete claim with evidence.
6. BOLD TEXT: Use **bold** only for section sub-points and the final takeaway. \
   Not for random emphasis mid-sentence.
7. SENTENCE LENGTH: Mix punchy 8-word sentences with 20-word explanations. \
   Never exceed 30 words in a single sentence.
8. START: Begin immediately with ## headline. Zero preamble. \
   No "Here is your essay:", no "Sure!", no "Based on the transcripts...".
9. SKIMMABILITY: A reader should be able to read only the headline, hook, \
   bold sub-points, and final takeaway — and still get the full insight.
"""


async def run_ship30(
    user_message: str,
    provider: LLMProvider,
    conn,
    history: Optional[List[Dict]] = None,
) -> Dict:
    """
    Run the Ship30for30 essay skill.

    Retrieves more chunks than Q&A (top_k=8) for richer cross-episode material.
    Uses the full Ship30for30 template with 4A path structure.

    Returns:
        {"response": str, "skill_used": "ship30for30", "sources": list, "artifact": None}
    """
    # 1. Retrieve — more chunks for richer cross-episode material
    chunks = await retrieve(user_message, conn, top_k=8)
    context = build_context(chunks)
    sources = dedupe_sources(chunks)

    # 2. Build guest list for the model to know who's available
    guest_names = list({c.get("guest", "") for c in chunks if c.get("guest")})
    guest_hint = (
        f"\n\nGUESTS AVAILABLE IN CONTEXT (cite these by name): {', '.join(guest_names)}"
        if guest_names
        else ""
    )

    # 3. Build messages with history
    messages = list(history or [])
    messages.append({
        "role": "user",
        "content": (
            f"TRANSCRIPT CONTEXT (ground your essay strictly in this):\n{context}"
            f"{guest_hint}\n\n"
            f"---\n\n"
            f"ESSAY REQUEST: {user_message}\n\n"
            f"Write the full Ship30for30 essay using the template above.\n"
            f"Target: 1000–1250 words.\n"
            f"Section 4 must compare perspectives from at least 2 different guests.\n"
            f"Every named claim must be traceable to a guest in the context."
        ),
    })

    # 4. Call LLM — bump tokens to allow full 1250-word essay
    response_text = await provider.chat(
        messages,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=4000,
    )

    return {
        "response": response_text,
        "skill_used": "ship30for30",
        "sources": sources,
        "artifact": None,
    }
