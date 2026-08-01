"""
skills/ship30for30.py — Ship30for30 atomic essay generation skill.

Uses a rigid output template that qwen3/claude must follow exactly.
Grounded in retrieved transcript context. Accepts conversation history.
"""
from __future__ import annotations
from typing import Dict, List, Optional

from rag import retrieve, build_context, dedupe_sources
from llm import LLMProvider

SYSTEM_PROMPT = """You are Lenny's Growth Assistant writing a Ship30for30-style atomic essay.

SHIP30FOR30 FRAMEWORK — follow this output template EXACTLY:

## [Write a specific, intriguing headline here — not generic]

**[One-sentence opening hook that creates tension or curiosity]**

[2-3 sentence concrete story or example from the transcript — cite the guest by name. e.g. "Brian Chesky told Lenny..."]

---

## 1. [Section Title]

**[Bold subpoint]** [1-2 sentences expanding the point. Concrete, not abstract.]

**[Bold subpoint]** [1-2 sentences expanding the point.]

**[Bold subpoint]** [1-2 sentences expanding the point.]

## 2. [Section Title]

**[Bold subpoint]** [1-2 sentences]

**[Bold subpoint]** [1-2 sentences]

**[Bold subpoint]** [1-2 sentences]

## 3. [Section Title]

**[Bold subpoint]** [1-2 sentences]

**[Bold subpoint]** [1-2 sentences]

**[Bold subpoint]** [1-2 sentences]

## 4. [Section Title]

**[Bold subpoint]** [1-2 sentences]

**[Bold subpoint]** [1-2 sentences]

---

**The one thing to remember:** [Write one memorable, screenshot-worthy insight that captures the whole essay. Make it bold and punchy.]

---

RULES:
- Target: 1000-1250 words total. DO NOT write more.
- Every section must cite a specific guest by name from the transcript context.
- Short punchy sentences mixed with 2-3 sentence elaborations.
- NO vague platitudes. Every claim must be grounded in the transcript.
- The headline must say WHO it's for, WHAT the idea is, and PROMISE a specific insight.
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
