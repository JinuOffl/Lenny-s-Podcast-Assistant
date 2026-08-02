"""
router.py — LLM-based agentic skill classifier.

Two-stage routing:
  Stage 1 (instant): Follow-up detection — short messages referencing prior context
                     skip RAG, use history only. No LLM call needed.
  Stage 2 (LLM):    Intent classification via a small, fast LLM call.
                     Returns one of: 'qa' | 'ship30for30' | 'artifact' | 'multi' | 'followup'
                     Falls back to keyword matching if LLM fails or times out.

This makes the system truly agentic: the LLM reasons about WHICH skill(s) to invoke
rather than relying on hardcoded keyword lists.
"""
from __future__ import annotations
from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMProvider

# ── Keyword fallback lists (used when LLM classification fails) ───────────────

SHIP30_KEYWORDS = [
    "essay", "ship30", "write an article", "atomic essay",
    "write me an essay", "write a post", "linkedin post",
    "tweet thread", "newsletter", "write about", "write on",
    "short post", "long-form", "draft a post", "write me a",
]

ARTIFACT_KEYWORDS = [
    "html", "create html", "make a page", "landing page",
    "artifact", "code for", "web page",
    "dashboard", "chart", "visualization", "graph",
    "create a chart", "create a dashboard", "build a dashboard",
    "show me a chart", "show me a table", "create a table",
    "interactive", "ui for", "page for",
    "build me a", "create a page", "make a dashboard",
    "create an html", "build an html", "generate html",
    "generate a chart", "generate a dashboard", "line chart", "bar chart",
    "draw", "plot",
]

FOLLOWUP_SIGNALS = [
    "convert this", "convert it", "convert the",
    "turn this", "turn it into",
    "summarize this", "summarize it",
    "expand on", "expand this", "expand that",
    "based on this", "based on the above", "based on that",
    "from the above", "from the essay", "from the answer",
    "can you make", "can you convert",
    "make it a", "make this a", "make that a",
    "what about this", "this into", "that into",
]

# ── Router LLM prompt ─────────────────────────────────────────────────────────

_ROUTER_SYSTEM = """You are the routing agent for Lenny's Growth Assistant — an AI built on Lenny Rachitsky's podcast transcripts.

Your ONLY job: classify the user's message into exactly one skill name.

SKILLS:
  qa           → factual question about product management, growth, startups, or podcast content
  ship30for30  → request to write an essay, article, LinkedIn post, newsletter, or long-form content
  artifact     → request to build an HTML page, chart, dashboard, visualization, or interactive component
  multi        → complex request that EXPLICITLY needs two outputs (e.g. "write an essay AND create a chart",
                 "generate a report with a visualization", "write about X and build a dashboard")
  followup     → short message referencing prior conversation (pronouns: "this", "that", "it", "the above",
                 "previous", "can you expand", "what about")

RULES:
  1. Reply with ONLY the skill name. One word. No punctuation, no explanation.
  2. Choose ship30for30 only if user explicitly asks to "write" something or mentions "essay/post/article".
  3. Choose multi RARELY — only when user clearly wants two distinct output types in one request.
  4. When unsure between qa and ship30for30, pick qa.
"""

_ROUTER_USER = """Classify this message into one skill:

User message: "{message}"

Conversation context (last 2 turns):
{history_summary}

Reply with ONE word only: qa, ship30for30, artifact, multi, or followup"""


# ── Helper: keyword fallback ──────────────────────────────────────────────────

def _keyword_classify(msg: str) -> str:
    """Fallback classification — no LLM required."""
    m = msg.lower()

    has_ship30   = any(k in m for k in SHIP30_KEYWORDS)
    has_artifact = any(k in m for k in ARTIFACT_KEYWORDS)

    if has_ship30 and has_artifact:
        return "multi"
    if has_ship30:
        return "ship30for30"
    if has_artifact:
        return "artifact"
    if _is_followup(m):
        return "followup"
    return "qa"


def _is_followup(msg_lower: str) -> bool:
    """Synchronous follow-up check — no LLM needed."""
    # Short generic conversational remarks — never need RAG
    CHITCHAT = {
        "ok", "okay", "sure", "thanks", "thank you", "got it", "nice",
        "cool", "great", "yes", "no", "yep", "nope", "alright", "right",
        "hmm", "hm", "ah", "wow", "lol", "haha", "interesting",
        "tell me more", "go on", "continue", "more", "why",
    }
    if msg_lower.strip() in CHITCHAT:
        return True
    # Also catch multi-word combos of chitchat words ("ok interesting", "sure thanks", etc.)
    words = msg_lower.strip().split()
    if 1 <= len(words) <= 4 and all(w in CHITCHAT for w in words):
        return True
    if any(sig in msg_lower for sig in FOLLOWUP_SIGNALS):
        return True
    word_count = len(msg_lower.split())
    context_pronouns = ["this", "that", "it", "the above", "previous", "them", "these"]
    if word_count < 8 and any(p in msg_lower for p in context_pronouns):
        return True
    return False


# ── Public interface ──────────────────────────────────────────────────────────

def is_followup(user_message: str) -> bool:
    """Public export for backward-compat with main.py."""
    return _is_followup(user_message.lower().strip())


async def classify_skill(
    user_message: str,
    provider: "LLMProvider",
    history: Optional[List[Dict]] = None,
) -> str:
    """
    Classify the user's intent using LLM reasoning.

    Stage 1: Fast-path follow-up detection (no LLM).
    Stage 2: LLM call with tiny max_tokens=12 for classification.
    Fallback: keyword matching if LLM fails or returns unexpected value.

    Returns: 'qa' | 'ship30for30' | 'artifact' | 'multi' | 'followup'
    """
    msg_lower = user_message.lower().strip()

    # ── Stage 1: instant follow-up detection ──────────────────────────────────
    if _is_followup(msg_lower):
        print(f"[router] Stage1 followup: '{user_message[:60]}'")
        return "followup"

    # ── Stage 1b: unambiguous multi-intent (skip LLM — no ambiguity here) ────
    # If message has BOTH essay keywords AND artifact keywords, it's always multi
    _has_ship30   = any(k in msg_lower for k in SHIP30_KEYWORDS)
    _has_artifact = any(k in msg_lower for k in ARTIFACT_KEYWORDS)
    if _has_ship30 and _has_artifact:
        print(f"[router] Fast-path multi (both essay+artifact keywords): '{user_message[:60]}'")
        return "multi"

    # ── Stage 2: LLM classification ───────────────────────────────────────────
    history_summary = "No prior context."
    if history:
        last_two = history[-2:]
        lines = []
        for m in last_two:
            snippet = m["content"][:150].replace("\n", " ")
            lines.append(f"  {m['role'].upper()}: {snippet}...")
        history_summary = "\n".join(lines)

    prompt = _ROUTER_USER.format(
        message=user_message[:400],
        history_summary=history_summary,
    )

    try:
        raw = await provider.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_ROUTER_SYSTEM,
            max_tokens=12,   # One word — keep it fast
        )
        skill = raw.strip().lower().split()[0].rstrip(".,!?")
        valid = {"qa", "ship30for30", "artifact", "multi", "followup"}

        if skill in valid:
            print(f"[router] LLM → '{skill}' | msg: '{user_message[:60]}'")
            return skill

        print(f"[router] LLM returned unexpected '{skill}', using keyword fallback")
        return _keyword_classify(user_message)

    except Exception as exc:
        print(f"[router] LLM classification failed ({exc}), using keyword fallback")
        return _keyword_classify(user_message)
