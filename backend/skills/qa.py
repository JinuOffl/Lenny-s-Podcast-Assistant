"""
skills/qa.py — Grounded Q&A skill.

Retrieves relevant transcript chunks via pgvector, then asks the LLM to
answer ONLY from that context. Conversation history is included so the LLM
can answer follow-up questions correctly.
"""
from __future__ import annotations
from typing import List, Dict, Optional

from rag import retrieve, build_context, dedupe_sources
from llm import LLMProvider

SYSTEM_PROMPT = """You are Lenny's Growth Assistant — built from Lenny Rachitsky's podcast transcripts covering product management, growth, and startups.

=== YOUR RULES ===
1. Answer ONLY using the transcript context provided. Do not use outside knowledge.
2. Always cite specific guests by name (e.g. "Brian Chesky told Lenny...", "According to Claire Vo...").
3. If context doesn't contain a clear answer, say: "I don't have grounded information on this from Lenny's Podcast."

=== OUTPUT FORMAT ===
Structure every response for maximum scannability:

- Use **bold** for every key name, concept, or number
- Use bullet points for lists of 3+ items
- Use short paragraphs (2-3 sentences max)
- For multi-part answers, use ## headers to separate sections
- End with a **Bottom line:** sentence summarizing the core insight

Keep responses concise. No fluff. No vague platitudes. Every claim must be traceable to a specific guest or episode in the context.
"""


async def run_qa(
    user_message: str,
    provider: LLMProvider,
    conn,
    history: Optional[List[Dict]] = None,
    rag_context: bool = True,
) -> Dict:
    """
    Run the Q&A skill.

    Args:
        rag_context: If False, skip RAG retrieval (for follow-up messages that
                     reference prior conversation content).
    """
    chunks = []
    context = ""
    if rag_context:
        chunks = await retrieve(user_message, conn)
        context = build_context(chunks)

    messages = list(history or [])

    if rag_context and context:
        messages.append({
            "role": "user",
            "content": (
                f"TRANSCRIPT CONTEXT:\n{context}\n\n"
                f"---\n\n"
                f"QUESTION: {user_message}"
            ),
        })
    else:
        # Follow-up: just pass the message, LLM uses history
        messages.append({"role": "user", "content": user_message})

    response_text = await provider.chat(messages, system_prompt=SYSTEM_PROMPT)
    sources = dedupe_sources(chunks) if chunks else []

    return {
        "response": response_text,
        "skill_used": "followup" if not rag_context else "qa",
        "sources": sources,
        "artifact": None,
    }
