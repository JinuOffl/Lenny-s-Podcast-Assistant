"""
agents/artifact_agent.py — ArtifactAgent

Generates interactive HTML dashboards / data visualizations
grounded in the research context from ResearchAgent.

Receives full SharedContext — can access:
  - The raw transcript chunks (data source)
  - The WriterAgent's essay (if already generated)
  - The Orchestrator's plan
"""
from __future__ import annotations
import re
from typing import Optional, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMProvider

from agents.shared_context import SharedContext

# ── System prompt ─────────────────────────────────────────────────────────────

ARTIFACT_SYSTEM_PROMPT = """\
You are Lenny's Research Assistant. Generate self-contained, visually rich HTML dashboards.

CRITICAL: YOUR ENTIRE RESPONSE MUST BE:
<artifact type="html">
  ... your complete HTML here ...
</artifact>

=== ALLOWED VISUALIZATION LIBRARIES (CDN — works in preview iframe) ===
Charts: <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
Interactive: <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

=== DESIGN SYSTEM ===
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', system-ui, sans-serif; background: #0d0d0d; color: #f2f2f2; padding: 24px; min-height: 100vh; }
  h1 { font-size: 1.3rem; font-weight: 700; margin-bottom: 4px; color: #fff; }
  h2 { font-size: 0.9rem; font-weight: 500; margin-bottom: 20px; color: #888; }
  .card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
  .metric { font-size: 2rem; font-weight: 800; color: #f97316; }
  .label { font-size: 0.7rem; color: #888; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 0.7rem; font-weight: 600; background: #f9731620; color: #f97316; border: 1px solid #f9731640; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  th { text-align: left; padding: 8px 12px; color: #666; border-bottom: 1px solid #2a2a2a; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e1e1e; color: #e0e0e0; }
  tr:hover td { background: #1e1e1e; }
  .source-tag { font-size: 0.65rem; color: #666; font-style: italic; }
</style>

=== STRICT RULES ===
1. Wrap EVERYTHING in <artifact type="html">...</artifact>. Nothing before or after.
2. Use Chart.js for all charts — bar, line, radar, doughnut.
3. Ground ALL data in the transcript context — cite specific guests inline.
4. Dark theme. Metric cards. Charts. Tables. Make it impressive.
5. Every canvas must have a unique id attribute.
6. CDN scripts must be closed as: <script src="..."></script> (not self-closing).
7. Start DIRECTLY with <artifact — no preamble, no "Here is the HTML:".
8. Include a "Sources" footer listing the guests referenced.
"""


# ── Public interface ──────────────────────────────────────────────────────────

async def run_artifact_agent(
    ctx: SharedContext,
    provider: "LLMProvider",
    conn,
    heal_error: Optional[str] = None,
) -> SharedContext:
    """
    ArtifactAgent execution.

    If heal_error is provided, this is a self-healing retry:
    the error is injected into the prompt so the agent can fix it.
    """
    ctx.add_step(
        "ArtifactAgent",
        "🔧 Fixing artifact..." if heal_error else "🎨 Building interactive dashboard...",
    )

    messages = _build_artifact_messages(ctx, heal_error)

    try:
        raw = await provider.chat(
            messages=messages,
            system_prompt=ARTIFACT_SYSTEM_PROMPT,
            max_tokens=4096,
        )
        artifact = _extract_artifact(raw)
        ctx.artifact = artifact
    except Exception as e:
        print(f"[ArtifactAgent] Generation failed: {e}")
        ctx.artifact = None

    return ctx


def _build_artifact_messages(ctx: SharedContext, heal_error: Optional[str]) -> List[Dict]:
    """Build the message list for artifact generation."""
    messages = []

    # Include conversation history for context
    if ctx.history:
        messages.extend(ctx.history[-4:])  # Last 2 turns

    # If WriterAgent already produced an essay, include it as context
    essay_context = ""
    if ctx.primary_response and ctx.plan.needs_essay:
        essay_context = f"\n\nESSAY ALREADY GENERATED (use same data):\n{ctx.primary_response[:1500]}"

    user_content = (
        f"TRANSCRIPT CONTEXT (ground all data in this):\n{ctx.context_text}\n"
        f"{essay_context}\n\n"
        "---\n\n"
        f"REQUEST: {ctx.user_query}\n\n"
        "Generate a complete, interactive HTML dashboard. "
        "Include metric cards, a Chart.js chart, and a data table. "
        "All data must come from the transcript context — cite specific guests."
    )

    if heal_error:
        user_content = (
            f"SELF-HEALING REQUEST — Fix the following error in your previous HTML output:\n\n"
            f"ERROR: {heal_error}\n\n"
            f"PREVIOUS OUTPUT (first 800 chars):\n"
            f"{(ctx.artifact or {}).get('content', '')[:800]}...\n\n"
            f"Fix ONLY the error. Keep all other content identical. "
            f"Output the COMPLETE corrected HTML inside <artifact type=\"html\">...</artifact>."
        )

    messages.append({"role": "user", "content": user_content})
    return messages


def _extract_artifact(raw: str) -> Optional[Dict]:
    """Parse <artifact type="...">...</artifact> from LLM output."""
    # Primary: look for artifact tags
    pattern = r'<artifact\s+type=["\'](\w+)["\']\s*>(.*?)</artifact>'
    match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)

    if match:
        return {
            "type": match.group(1).lower(),
            "content": match.group(2).strip(),
        }

    # Fallback: raw HTML
    stripped = raw.strip()
    if stripped.lower().startswith("<!doctype html") or stripped.lower().startswith("<html"):
        return {"type": "html", "content": stripped}

    # Last resort: treat as markdown
    if len(stripped) > 100:
        return {"type": "markdown", "content": stripped}

    return None
