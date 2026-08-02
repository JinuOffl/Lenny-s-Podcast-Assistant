"""
agents/validator.py — ValidatorAgent + Self-Healing Loop

The last agent to run. Checks:
  - HTML artifact structural validity
  - Essay word count and formatting quality
  - Citation presence (guests named in response)

If HTML is broken, triggers ArtifactAgent retry with the error as context.
If essay is too short, logs it (we stream so we can't re-generate after the fact).
Max 2 self-healing attempts before graceful degradation.
"""
from __future__ import annotations
import asyncio
from typing import AsyncGenerator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMProvider

from agents.shared_context import SharedContext
from agents.artifact_agent import run_artifact_agent
from tools.validate_tool import validate_html, validate_markdown, validate_essay
from tools.count_tool import essay_stats


MAX_HEAL_ATTEMPTS = 2


async def run_validator_agent(
    ctx: SharedContext,
    provider: "LLMProvider",
    conn,
    event_queue: asyncio.Queue,
) -> SharedContext:
    """
    ValidatorAgent execution.

    Validates all generated outputs and self-heals if needed.
    Emits SSE events via event_queue for real-time UI updates.
    """
    ctx.add_step("ValidatorAgent", "✅ Checking output quality...")

    # ── 1. Validate HTML artifact ─────────────────────────────────────────────
    if ctx.artifact and ctx.artifact.get("type") == "html":
        await _validate_and_heal_artifact(ctx, provider, conn, event_queue)

    # ── 2. Validate Markdown artifact ─────────────────────────────────────────
    if ctx.artifact and ctx.artifact.get("type") == "markdown":
        error = validate_markdown(ctx.artifact.get("content", ""))
        if error:
            print(f"[ValidatorAgent] Markdown error: {error}")
            # Markdown is simpler — just log, don't self-heal
            ctx.add_step("ValidatorAgent", f"⚠️  Markdown issue: {error}")

    # ── 3. Validate essay (can't re-stream, so just report stats) ────────────
    if ctx.primary_response and ctx.plan.needs_essay:
        error = validate_essay(ctx.primary_response)
        stats = essay_stats(ctx.primary_response, ctx.sources)
        ctx.word_count = stats["word_count"]

        if error:
            print(f"[ValidatorAgent] Essay issue: {error}")
            ctx.add_step("ValidatorAgent", f"⚠️  Essay: {error}")
        else:
            ctx.add_step(
                "ValidatorAgent",
                f"✅ Essay valid — {stats['word_count']} words, "
                f"{stats['bold_phrases']} bold phrases, "
                f"{stats['guest_citations']}/{len(ctx.sources)} guests cited",
            )

    # ── 4. Validate QA response ───────────────────────────────────────────────
    if ctx.primary_response and not ctx.plan.needs_essay:
        stats = essay_stats(ctx.primary_response, ctx.sources)
        ctx.word_count = stats["word_count"]
        citations = stats["guest_citations"]

        if citations == 0 and ctx.sources:
            ctx.add_step("ValidatorAgent", "⚠️  No guest names found in response — citations may be weak")
        else:
            ctx.add_step(
                "ValidatorAgent",
                f"✅ QA valid — {stats['word_count']} words, {citations} guests cited",
            )

    # ── 5. Final confidence ───────────────────────────────────────────────────
    ctx.confidence = ctx.compute_confidence()
    ctx.validation_passed = ctx.heal_attempts < MAX_HEAL_ATTEMPTS or ctx.artifact is not None
    ctx.add_step("ValidatorAgent", f"🏁 Validation complete — confidence: {ctx.confidence}")

    print(
        f"[ValidatorAgent] Done. heal_attempts={ctx.heal_attempts} "
        f"confidence={ctx.confidence} validation_passed={ctx.validation_passed}"
    )
    return ctx


async def _validate_and_heal_artifact(
    ctx: SharedContext,
    provider: "LLMProvider",
    conn,
    event_queue: asyncio.Queue,
) -> None:
    """
    Self-healing loop for HTML artifacts.
    Retries up to MAX_HEAL_ATTEMPTS times with the error injected into prompt.
    """
    for attempt in range(1, MAX_HEAL_ATTEMPTS + 1):
        content = ctx.artifact.get("content", "")
        error = validate_html(content)

        if error is None:
            ctx.add_step("ValidatorAgent", "✅ HTML artifact validated successfully")
            print(f"[ValidatorAgent] HTML valid on attempt {attempt}")
            return

        # Emit self-healing SSE event
        heal_msg = f"🔧 Self-healing artifact (attempt {attempt}/{MAX_HEAL_ATTEMPTS}) — {error[:80]}"
        ctx.add_step("ValidatorAgent", heal_msg)
        await event_queue.put({"agent": "ValidatorAgent", "step": heal_msg})
        ctx.heal_attempts += 1
        ctx.heal_errors.append(error)

        print(f"[ValidatorAgent] HTML error (attempt {attempt}): {error}")

        # Re-run ArtifactAgent with error context
        ctx = await run_artifact_agent(ctx, provider, conn, heal_error=error)

        if ctx.artifact is None:
            await event_queue.put({
                "agent": "ValidatorAgent",
                "step": f"⚠️  Artifact generation failed after {attempt} attempt(s) — skipping artifact",
            })
            print(f"[ValidatorAgent] ArtifactAgent returned None on attempt {attempt}")
            return

    # Final check after all attempts
    final_error = validate_html(ctx.artifact.get("content", ""))
    if final_error:
        await event_queue.put({
            "agent": "ValidatorAgent",
            "step": f"⚠️  Could not fix artifact after {MAX_HEAL_ATTEMPTS} attempts — rendering best available",
        })
        ctx.add_step("ValidatorAgent", f"⚠️  Rendering artifact with known issues: {final_error[:100]}")
    else:
        ctx.add_step("ValidatorAgent", f"✅ Artifact self-healed successfully after {ctx.heal_attempts} attempt(s)!")
        await event_queue.put({
            "agent": "ValidatorAgent",
            "step": f"✅ Artifact self-healed successfully after {ctx.heal_attempts} attempt(s)!",
        })
