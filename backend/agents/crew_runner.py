"""
agents/crew_runner.py — Research Mode Pipeline Orchestrator

This is the top-level entry point for the Research Mode (agentic) pipeline.
It assembles the right "crew" of agents based on the Orchestrator's plan
and runs them with maximum parallelism.

Execution model:
  Phase 1: OrchestratorAgent (sequential — must plan before anything else)
  Phase 2: ResearchAgent     (sequential — others depend on its output)
  Phase 3: WriterAgent + ArtifactAgent (PARALLEL via asyncio.gather)
  Phase 4: ValidatorAgent    (sequential — needs both Phase 3 outputs)

All SSE events are emitted via an asyncio.Queue.
The endpoint's async generator reads from this queue and yields to the client.

CrewAI Note:
  We use CrewAI's conceptual model (Agents with roles/goals/backstories,
  Tasks with context passing) but implement LLM calls through our own
  llm.py providers to guarantee Ollama + Anthropic compatibility.
  This avoids CrewAI's LiteLLM wrapper breaking on Ollama tool-calling.
"""
from __future__ import annotations
import asyncio
import json
from typing import AsyncGenerator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMProvider

from agents.shared_context import SharedContext
from agents.orchestrator import run_orchestrator
from agents.research import run_research_agent
from agents.writer import stream_writer_response
from agents.artifact_agent import run_artifact_agent
from agents.validator import run_validator_agent


# ── Public entry point ────────────────────────────────────────────────────────

async def run_research_pipeline(
    session_id: str,
    user_query: str,
    provider: "LLMProvider",
    conn,
    history: list,
) -> AsyncGenerator[str, None]:
    """
    Main Research Mode pipeline.

    Yields SSE-formatted strings:
      data: {"agent": "...", "step": "..."}\\n\\n      ← agent status events
      data: {"token": "..."}\\n\\n                      ← streaming text tokens
      data: {"done": true, ...}\\n\\n                  ← final metadata event

    Usage in FastAPI endpoint:
        return StreamingResponse(
            run_research_pipeline(...),
            media_type="text/event-stream",
        )
    """
    # Shared working memory
    ctx = SharedContext(
        session_id=session_id,
        user_query=user_query,
        history=history,
    )

    # Queue for cross-task SSE events (validator self-healing emits here)
    event_queue: asyncio.Queue = asyncio.Queue()

    async def emit(data: dict) -> str:
        """Format an SSE event."""
        return f"data: {json.dumps(data)}\n\n"

    # ── Phase 1: Orchestrator ─────────────────────────────────────────────────
    yield await emit({"agent": "OrchestratorAgent", "step": "🧠 Analyzing your research request..."})

    try:
        ctx = await run_orchestrator(ctx, provider)
    except Exception as e:
        print(f"[crew_runner] OrchestratorAgent failed: {e} — using keyword fallback")
        # Orchestrator fallback already built into run_orchestrator
        from agents.orchestrator import _keyword_plan
        ctx.plan = _keyword_plan(user_query)

    yield await emit({"agent": "OrchestratorAgent", "step": f"📋 {ctx.plan.reasoning or 'Plan ready'}"})

    # ── Phase 2: Research ─────────────────────────────────────────────────────
    # Skip research for pure follow-up queries
    is_followup = _is_followup(user_query, history)

    if is_followup:
        yield await emit({"agent": "ResearchAgent", "step": "💬 Continuing from conversation context..."})
        ctx.plan.needs_qa = True
        ctx.plan.needs_essay = False
        ctx.skill_used = "followup"
    else:
        yield await emit({"agent": "ResearchAgent", "step": "🔍 Searching Lenny's podcast transcripts..."})

        try:
            ctx = await run_research_agent(ctx, conn)
        except Exception as e:
            print(f"[crew_runner] ResearchAgent failed: {e}")
            yield await emit({"agent": "ResearchAgent", "step": f"⚠️  Search failed — proceeding with limited context"})

        # Emit research summary event
        src_count = len(ctx.sources)
        hop_str = f"{ctx.search_hops} search hop{'s' if ctx.search_hops > 1 else ''}"
        yield await emit({
            "agent": "ResearchAgent",
            "step": f"✅ Found {len(ctx.chunks)} relevant chunks from {src_count} episode{'s' if src_count != 1 else ''} ({hop_str})",
            "sources_found": src_count,
        })

    # ── Phase 3: Parallel generation ─────────────────────────────────────────
    # Decide which agents to run in parallel
    run_artifact = ctx.plan.needs_artifact and not is_followup
    artifact_task: Optional[asyncio.Task] = None

    if run_artifact:
        # Start ArtifactAgent in background (doesn't need to stream)
        artifact_task = asyncio.create_task(
            run_artifact_agent(ctx, provider, conn)
        )
        yield await emit({"agent": "ArtifactAgent", "step": "🎨 Building dashboard in background..."})

    # Stream WriterAgent tokens to user (foreground)
    if ctx.plan.needs_essay:
        yield await emit({"agent": "WriterAgent", "step": "✍️  Writing Ship30for30 essay..."})
    elif is_followup:
        yield await emit({"agent": "WriterAgent", "step": "💬 Crafting response from context..."})
    else:
        yield await emit({"agent": "WriterAgent", "step": "🔬 Synthesizing research into answer..."})

    try:
        async for token in stream_writer_response(ctx, provider):
            yield await emit({"token": token})
            # Drain any pending queue events (from artifact task if it emits)
            try:
                while not event_queue.empty():
                    q_event = event_queue.get_nowait()
                    yield await emit(q_event)
            except asyncio.QueueEmpty:
                pass
    except Exception as e:
        print(f"[crew_runner] WriterAgent streaming failed: {e}")
        yield await emit({"agent": "WriterAgent", "step": f"⚠️  Writer error: {str(e)[:100]}"})
        ctx.primary_response = f"⚠️ Research mode encountered an error: {e}. Please try again."

    # Wait for artifact background task to complete
    if artifact_task is not None:
        try:
            yield await emit({"agent": "ArtifactAgent", "step": "⏳ Finalizing dashboard..."})
            ctx = await artifact_task
        except Exception as e:
            print(f"[crew_runner] ArtifactAgent failed: {e}")
            ctx.artifact = None
            yield await emit({"agent": "ArtifactAgent", "step": f"⚠️  Dashboard generation failed: {str(e)[:80]}"})

    # ── Phase 4: Validator ────────────────────────────────────────────────────
    yield await emit({"agent": "ValidatorAgent", "step": "✅ Validating output quality..."})

    try:
        ctx = await run_validator_agent(ctx, provider, conn, event_queue)

        # Drain any self-healing events the validator emitted
        while not event_queue.empty():
            q_event = event_queue.get_nowait()
            yield await emit(q_event)

    except Exception as e:
        print(f"[crew_runner] ValidatorAgent failed: {e}")
        yield await emit({"agent": "ValidatorAgent", "step": f"⚠️  Validation skipped: {str(e)[:80]}"})

    # ── Done ──────────────────────────────────────────────────────────────────
    done_event = {
        "done": True,
        "skill_used": ctx.skill_used,
        "sources": ctx.sources,
        "artifact": ctx.artifact,
        "confidence": ctx.confidence,
        "healing_attempts": ctx.heal_attempts,
        "agent_steps": ctx.agent_steps,
        "research_stats": {
            "chunks_found": len(ctx.chunks),
            "episodes": ctx.episodes_searched,
            "search_hops": ctx.search_hops,
            "word_count": ctx.word_count,
        },
    }
    yield await emit(done_event)


# ── Helpers ───────────────────────────────────────────────────────────────────

_FOLLOWUP_SIGNALS = [
    "convert this", "convert it", "turn this", "turn it into",
    "summarize this", "summarize it", "expand on", "based on this",
    "from the above", "from the essay", "can you make", "make it a",
    "make this a", "this into", "that into", "what about this",
]

def _is_followup(msg: str, history: list) -> bool:
    """Fast-path follow-up detection without LLM."""
    m = msg.lower().strip()
    if any(sig in m for sig in _FOLLOWUP_SIGNALS):
        return True
    context_pronouns = ["this", "that", "it", "the above", "previous", "them", "these"]
    word_count = len(m.split())
    if word_count < 8 and any(p in m for p in context_pronouns) and history:
        return True
    return False
