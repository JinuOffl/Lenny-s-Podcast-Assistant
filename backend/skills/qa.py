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

SYSTEM_PROMPT = """You are Lenny's Growth Assistant — a knowledgeable guide built from Lenny Rachitsky's podcast transcripts.

Your rules:
1. Answer ONLY using the transcript context provided below. Do not use outside knowledge.
2. Always reference specific guests and episodes by name when the context supports it.
3. If the context does not contain a clear answer, say plainly:
   "I don't have grounded information on this specific topic from Lenny's Podcast."
4. Be concise, concrete, and actionable. Avoid vague platitudes.
5. Format your answer with clear structure — use **bold** for key points, bullet lists for multiple items, and short paragraphs.
6. Use the conversation history below to understand follow-up questions and references like "what about that?" or "expand on point 2".
"""


async def run_qa(
    user_message: str,
    provider: LLMProvider,
    conn,
    history: Optional[List[Dict]] = None,
) -> Dict:
    """
    Run the Q&A skill.

    Args:
        user_message: The latest user query.
        provider: LLM provider instance.
        conn: DB connection for RAG retrieval.
        history: Previous messages in this session [{role, content}, ...].

    Returns:
        {"response": str, "skill_used": "qa", "sources": list, "artifact": None}
    """
    # 1. Retrieve relevant chunks
    chunks = await retrieve(user_message, conn)

    # 2. Build context string
    context = build_context(chunks)

    # 3. Build messages: history + current message with context injected
    messages = list(history or [])

    messages.append({
        "role": "user",
        "content": (
            f"TRANSCRIPT CONTEXT:\n{context}\n\n"
            f"---\n\n"
            f"QUESTION: {user_message}"
        ),
    })

    # 4. Call LLM
    response_text = await provider.chat(messages, system_prompt=SYSTEM_PROMPT)

    # 5. Deduplicate sources
    sources = dedupe_sources(chunks)

    return {
        "response": response_text,
        "skill_used": "qa",
        "sources": sources,
        "artifact": None,
    }
