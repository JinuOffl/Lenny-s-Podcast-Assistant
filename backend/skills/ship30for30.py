"""
skills/ship30for30.py — Ship30for30 atomic essay generation skill.

Uses a rigid output template that qwen3/claude must follow exactly.
Grounded in retrieved transcript context. Accepts conversation history.
"""
from __future__ import annotations
from typing import Dict, List, Optional

from rag import retrieve, build_context, dedupe_sources
from llm import LLMProvider

SYSTEM_PROMPT = """You are Lenny's Growth Assistant. Your task: write a Ship30for30-style atomic essay grounded in Lenny's podcast transcripts.

=== OUTPUT FORMAT (copy this structure EXACTLY) ===

## [Headline: specific, WHO it helps + WHAT insight + WHY it matters. NOT generic.]

**[Hook: ONE sentence. Create tension or a surprising claim. No filler.]**

[Opening paragraph: 2-3 sentences. Concrete story or quote from the transcript. Name the guest explicitly. Example: "When Brian Chesky told Lenny he reads every customer complaint personally..."]

---

## 1. [Section Title — make it action-oriented]

**[Bold point A — 4-6 words]** [Expand in 1-2 sentences. Cite guest name from transcripts.]

**[Bold point B — 4-6 words]** [Expand in 1-2 sentences. Cite guest name from transcripts.]

**[Bold point C — 4-6 words]** [Expand in 1-2 sentences. Cite guest name from transcripts.]

## 2. [Section Title]

**[Bold point A]** [1-2 sentences with guest citation.]

**[Bold point B]** [1-2 sentences with guest citation.]

**[Bold point C]** [1-2 sentences with guest citation.]

## 3. [Section Title]

**[Bold point A]** [1-2 sentences with guest citation.]

**[Bold point B]** [1-2 sentences with guest citation.]

**[Bold point C]** [1-2 sentences with guest citation.]

## 4. [Section Title]

**[Bold point A]** [1-2 sentences with guest citation.]

**[Bold point B]** [1-2 sentences with guest citation.]

---

**The one thing to remember:** [One punchy, memorable sentence. Make it screenshot-worthy. Bold it.]

---

=== MANDATORY RULES ===
1. WORD COUNT: Write exactly 1000-1250 words. Count carefully. Stop at 1250.
2. CITATIONS: Every section (1-4) MUST name at least one specific podcast guest by name from the context.
3. NO VAGUE PLATITUDES: Ban these phrases — "it's important", "key takeaway", "in conclusion", "leverage", "synergy". Every sentence must be a concrete claim with evidence.
4. BOLD TEXT: Use **bold** only for the sub-points at the start of each bullet. Not for random emphasis.
5. SHORT SENTENCES: Mix 8-word punchy sentences with 20-word explanations. Never write a sentence longer than 30 words.
6. START IMMEDIATELY with the ## headline. No preamble, no "Here is your essay:", no meta-commentary.
"""


async def run_ship30(
    user_message: str,
    provider: LLMProvider,
    conn,
    history: Optional[List[Dict]] = None,
) -> Dict:
    """
    Run the Ship30for30 essay skill.

    Returns:
        {"response": str, "skill_used": "ship30for30", "sources": list, "artifact": None}
    """
    # 1. Retrieve relevant chunks (more than Q&A for richer essay material)
    chunks = await retrieve(user_message, conn, top_k=6)
    context = build_context(chunks)

    # 2. Build messages with history
    messages = list(history or [])
    messages.append({
        "role": "user",
        "content": (
            f"TRANSCRIPT CONTEXT (ground your essay in this):\n{context}\n\n"
            f"---\n\n"
            f"ESSAY REQUEST: {user_message}\n\n"
            f"Write the full Ship30for30 essay following the template above. "
            f"~1000-1250 words. Cite specific guests from the context by name."
        ),
    })

    # 3. Call LLM (bump tokens for full essay)
    response_text = await provider.chat(messages, system_prompt=SYSTEM_PROMPT, max_tokens=3500)

    sources = dedupe_sources(chunks)

    return {
        "response": response_text,
        "skill_used": "ship30for30",
        "sources": sources,
        "artifact": None,
    }
