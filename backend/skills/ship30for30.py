"""
skills/ship30for30.py — Ship30for30 atomic essay generation skill.

The Ship30for30 framework (verified from the source guide) encoded as a
system prompt. Every essay is grounded in retrieved transcript context.
"""
from __future__ import annotations
from typing import Dict

from rag import retrieve, build_context, dedupe_sources
from llm import LLMProvider

SYSTEM_PROMPT = """You are Lenny's Growth Assistant writing a Ship30for30-style atomic essay.

SHIP30FOR30 FRAMEWORK — follow this exactly:

HEADLINE:
- Answers WHO is this for, WHAT is the core idea, the FEEL of the essay, and the PROMISE (what the reader gains).
- Make it specific and intriguing — not generic clickbait.

OPENING (Golden Intersection):
- Open with a personal story, a concrete moment, or a striking example pulled directly from the transcript context.
- Immediately pair it with the answer to a real question readers have.
- Do NOT open with a lecture or a definition.

STRUCTURE (Wheels & Spokes):
- Organize with 3-4 clear section headings (Wheels).
- Under each heading, use bold subheadings (Spokes) — no more than 2-3 sentences each.
- Keep paragraphs short: never more than 3-5 sentences.

RHYTHM:
- Vary sentence length deliberately: short punchy line → 3-5 sentence expansion → short punchy line.
- Every sentence must move the idea forward. Do NOT restate the previous sentence.

CLOSING:
- End with one clear, bold takeaway line that the reader could screenshot and share.
- NOT a vague summary — a memorable, actionable insight.

LENGTH: ~1000-1250 words.

GROUNDING RULES:
- Ground every major point in the provided transcript context.
- Cite specific guests by name (e.g., "Brian Chesky told Lenny...").
- If the context is thin, say so and write from what IS there.
"""


async def run_ship30(
    user_message: str,
    provider: LLMProvider,
    conn,
) -> Dict:
    """
    Run the Ship30for30 essay skill.

    Returns:
        {
            "response": str,           # the full essay text
            "skill_used": "ship30for30",
            "sources": List[Dict],
            "artifact": None,          # essay goes in response, not artifact pane
        }
    """
    # 1. Retrieve relevant chunks
    chunks = await retrieve(user_message, conn, top_k=6)

    # 2. Build context
    context = build_context(chunks)

    # 3. Build prompt
    messages = [
        {
            "role": "user",
            "content": (
                f"TRANSCRIPT CONTEXT (use this to ground your essay):\n{context}\n\n"
                f"---\n\n"
                f"ESSAY REQUEST: {user_message}\n\n"
                f"Write a full Ship30for30 atomic essay following the framework above. "
                f"~1000-1250 words. Cite specific guests from the context."
            ),
        }
    ]

    # 4. Call LLM (longer output — bump max_tokens)
    response_text = await provider.chat(messages, system_prompt=SYSTEM_PROMPT, max_tokens=3000)

    sources = dedupe_sources(chunks)

    return {
        "response": response_text,
        "skill_used": "ship30for30",
        "sources": sources,
        "artifact": None,
    }
