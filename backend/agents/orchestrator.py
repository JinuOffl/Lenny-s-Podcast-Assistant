"""
agents/orchestrator.py — OrchestratorAgent

Analyzes the user query + conversation history and produces an
ExecutionPlan: which crew to assemble, what to search for, how complex
the query is.

Design:
  - Pure LLM call (no tool use) — works with Ollama and Anthropic
  - Returns a structured JSON plan parsed from the LLM response
  - Falls back to keyword-based plan if LLM fails or times out
"""
from __future__ import annotations
import json
import re
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMProvider

from agents.shared_context import SharedContext, ExecutionPlan

# ── Keywords (same as router.py — used for fallback plan) ────────────────────
_ESSAY_KWORDS = [
    "essay", "ship30", "write an article", "atomic essay",
    "write me an essay", "write a post", "linkedin post",
    "tweet thread", "newsletter", "write about", "write on",
    "short post", "long-form", "draft a post", "write me a",
]
_ARTIFACT_KWORDS = [
    "html", "dashboard", "chart", "visualization", "graph",
    "landing page", "create an html", "build a dashboard",
    "show me a chart", "generate a chart", "bar chart", "line chart",
    "interactive", "web page", "build me a", "create a page",
]

# ── Orchestrator system prompt ────────────────────────────────────────────────
_ORCHESTRATOR_SYSTEM = """\
You are the OrchestratorAgent for Lenny's Research Assistant — an AI that answers 
product management and growth questions using Lenny Rachitsky's podcast transcripts.

Your ONLY job: analyze the user's message and produce a JSON execution plan.

OUTPUT FORMAT (respond ONLY with valid JSON, no preamble):
{
  "needs_essay": false,
  "needs_artifact": false,  
  "needs_qa": true,
  "complexity": "simple",
  "primary_search_query": "<refined query for vector search>",
  "secondary_search_query": "<optional second query for multi-hop, else empty string>",
  "crew_type": "qa",
  "reasoning": "<1 sentence explaining your plan>"
}

FIELD RULES:
- complexity: "simple" (1 topic) | "deep" (multi-facet, needs >6 chunks) | "multi" (needs essay + artifact)
- crew_type: "qa" | "essay" | "full_research"
- primary_search_query: rewrite the user's message as the best vector search query (specific, topic-focused)
- secondary_search_query: ONLY if complexity=deep or multi AND there's a second distinct topic to search; else ""
- needs_essay: true ONLY if user explicitly asks to write/draft/create content
- needs_artifact: true ONLY if user asks for chart/dashboard/html/visualization
- needs_qa: true unless needs_essay is true and user didn't also ask a question

EXAMPLES:
User: "What did Brian Chesky say about culture?"
→ {"needs_essay":false,"needs_artifact":false,"needs_qa":true,"complexity":"simple","primary_search_query":"Brian Chesky company culture values","secondary_search_query":"","crew_type":"qa","reasoning":"Simple factual lookup about Brian Chesky's culture views."}

User: "Write a Ship30for30 essay on retention AND build a dashboard"
→ {"needs_essay":true,"needs_artifact":true,"needs_qa":false,"complexity":"multi","primary_search_query":"retention strategies user churn prevention","secondary_search_query":"growth metrics engagement activation","crew_type":"full_research","reasoning":"User wants both essay and dashboard on retention — full research crew needed."}
"""

_ORCHESTRATOR_USER = """\
Conversation context (last 2 turns):
{history_summary}

User message: "{message}"

Respond ONLY with the JSON plan. No other text.
"""


# ── Public interface ──────────────────────────────────────────────────────────

async def run_orchestrator(
    ctx: SharedContext,
    provider: "LLMProvider",
) -> SharedContext:
    """
    Run the OrchestratorAgent.
    Fills ctx.plan with an ExecutionPlan.
    """
    history_summary = "No prior context."
    if ctx.history:
        last_two = ctx.history[-2:]
        lines = []
        for m in last_two:
            snippet = m["content"][:120].replace("\n", " ")
            lines.append(f"  {m['role'].upper()}: {snippet}...")
        history_summary = "\n".join(lines)

    prompt = _ORCHESTRATOR_USER.format(
        history_summary=history_summary,
        message=ctx.user_query[:400],
    )

    try:
        raw = await provider.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_ORCHESTRATOR_SYSTEM,
            max_tokens=300,
        )
        plan = _parse_plan(raw, ctx.user_query)
    except Exception as exc:
        print(f"[OrchestratorAgent] LLM failed ({exc}), using keyword fallback")
        plan = _keyword_plan(ctx.user_query)

    ctx.plan = plan
    ctx.add_step("OrchestratorAgent", f"🧠 Plan: {plan.crew_type} crew — {plan.reasoning}")
    print(f"[OrchestratorAgent] crew={plan.crew_type} essay={plan.needs_essay} artifact={plan.needs_artifact} complexity={plan.complexity}")
    return ctx


def _parse_plan(raw: str, query: str) -> ExecutionPlan:
    """Extract JSON from LLM response and build ExecutionPlan.

    Handles qwen3:4b quirks:
    - <think>...</think> blocks before the JSON
    - Markdown code fences (```json ... ```)
    - Extra commentary after the closing brace
    - Trailing backticks or whitespace
    """
    # 1. Strip thinking tags
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # 2. Strip markdown code fences (```json ... ``` or ``` ... ```)
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = re.sub(r"```", "", raw).strip()

    # 3. Try progressive JSON extraction — scan from last `}` backwards
    #    This handles trailing commentary like "I hope this helps!"
    data = None
    last_brace = raw.rfind("}")
    if last_brace != -1:
        first_brace = raw.find("{")
        if first_brace != -1 and first_brace < last_brace:
            candidate = raw[first_brace:last_brace + 1]
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # 4. Fallback: original greedy regex
    if data is None:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

    if data is None:
        print(f"[OrchestratorAgent] Could not extract JSON from: {raw[:200]!r}")
        return _keyword_plan(query)

    try:
        return ExecutionPlan(
            needs_essay=bool(data.get("needs_essay", False)),
            needs_artifact=bool(data.get("needs_artifact", False)),
            needs_qa=bool(data.get("needs_qa", True)),
            complexity=str(data.get("complexity", "simple")),
            primary_search_query=str(data.get("primary_search_query", query)),
            secondary_search_query=str(data.get("secondary_search_query", "")),
            crew_type=str(data.get("crew_type", "qa")),
            reasoning=str(data.get("reasoning", ""))[:200],
        )
    except (KeyError, TypeError):
        return _keyword_plan(query)


def _keyword_plan(query: str) -> ExecutionPlan:
    """Keyword-based fallback plan — zero LLM calls."""
    m = query.lower()
    has_essay = any(k in m for k in _ESSAY_KWORDS)
    has_artifact = any(k in m for k in _ARTIFACT_KWORDS)

    if has_essay and has_artifact:
        crew_type = "full_research"
        complexity = "multi"
    elif has_essay:
        crew_type = "essay"
        complexity = "deep"
    else:
        crew_type = "qa"
        complexity = "simple"

    return ExecutionPlan(
        needs_essay=has_essay,
        needs_artifact=has_artifact,
        needs_qa=not has_essay,
        complexity=complexity,
        primary_search_query=query,
        secondary_search_query="",
        crew_type=crew_type,
        reasoning="Keyword fallback plan",
    )
