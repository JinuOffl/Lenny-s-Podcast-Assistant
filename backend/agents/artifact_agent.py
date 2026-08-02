"""
agents/artifact_agent.py — ArtifactAgent (two-call split, Option B).

Receives SharedContext from ResearchAgent — uses pre-fetched transcript chunks,
the WriterAgent's essay (if generated), and the Orchestrator's plan.

Why two-call split:
  The old single-call approach asked the model to wrap HTML in <artifact> tags
  and then regex-extracted the content. qwen3's <think> block confused the regex.
  Now: Call 1 = one-sentence intro, Call 2 = raw HTML only (nothing to parse).
  The ValidatorAgent's self-healing loop handles repair at the pipeline level.
  We also add a local repair pass here for HTML-specific structural failures.
"""
from __future__ import annotations
import re
from typing import Optional, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMProvider

from agents.shared_context import SharedContext


# ── System prompts ────────────────────────────────────────────────────────────

INTRO_SYSTEM_PROMPT = (
    "You write one concise sentence (max 20 words) introducing a data visualization. "
    "No preamble, just the sentence."
)

ARTIFACT_HTML_PROMPT = """\
You are Lenny's Research Assistant. Generate a complete, self-contained HTML dashboard.

YOUR ENTIRE RESPONSE MUST BE A VALID HTML PAGE.
Start with <!DOCTYPE html> and end with </html>.
NO explanation. NO wrapper tags. NO text before or after the HTML.

=== ALLOWED VISUALIZATION LIBRARIES (CDN — works in preview iframe) ===
Charts:      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
Interactive: <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

=== DESIGN SYSTEM (always include this <style> block) ===
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
1. Start DIRECTLY with <!DOCTYPE html> — nothing before it.
2. End with </html> — nothing after it.
3. Use Chart.js for all charts.
4. Ground ALL data in the transcript context — cite specific guest names inline.
5. Dark theme. Metric cards. Charts. Tables. Sources footer.
6. Every <canvas> must have a unique id attribute.
7. CDN <script> tags: <script src="..."></script> — NOT self-closing.
8. Responsive — works at 420px width.
9. Include a "Sources" footer listing guests referenced.
"""


# ── Public interface ──────────────────────────────────────────────────────────

async def run_artifact_agent(
    ctx: SharedContext,
    provider: "LLMProvider",
    conn,
    heal_error: Optional[str] = None,
) -> SharedContext:
    """
    ArtifactAgent execution — two-call split.

    If heal_error is provided (called by ValidatorAgent), this is a repair pass:
    the broken content + error are sent back for correction.
    """
    ctx.add_step(
        "ArtifactAgent",
        "Fixing artifact..." if heal_error else "Building interactive dashboard...",
    )

    if heal_error:
        # Repair path: ValidatorAgent detected a problem — fix the existing artifact
        html_content = await _repair_html(
            provider=provider,
            broken_html=(ctx.artifact or {}).get("content", ""),
            error=heal_error,
        )
        if html_content:
            ctx.artifact = {"type": "html", "content": html_content}
        return ctx

    # ── Normal path: two-call split ───────────────────────────────────────────

    # Call 1 — short intro (updates ctx.primary_response only if no essay was written)
    intro = await _generate_intro(provider, ctx)

    # Call 2 — raw HTML page
    html_content = await _generate_html(provider, ctx)

    # Local self-repair if HTML looks structurally broken
    if html_content and not _is_valid_html(html_content):
        print("[ArtifactAgent] HTML validation failed — local repair attempt")
        html_content = await _repair_html(provider, html_content, error="HTML is incomplete or malformed")

    ctx.artifact = {"type": "html", "content": html_content} if html_content else None

    # If WriterAgent didn't already produce prose, use the intro as the response
    if not ctx.primary_response:
        ctx.primary_response = intro

    return ctx


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _generate_intro(provider: "LLMProvider", ctx: SharedContext) -> str:
    """Call 1 — one sentence intro for the chat bubble."""
    try:
        raw = await provider.chat(
            messages=[{
                "role": "user",
                "content": (
                    f"TRANSCRIPT CONTEXT:\n{ctx.context_text[:600]}\n\n"
                    f"REQUEST: {ctx.user_query}\n\n"
                    f"Write one sentence introducing the visualization you are about to generate."
                ),
            }],
            system_prompt=INTRO_SYSTEM_PROMPT,
            max_tokens=60,
        )
        intro = raw.strip().rstrip('.') + '.'
        if len(intro.split()) > 30:
            intro = "Here's an interactive dashboard grounded in Lenny's podcast transcripts."
        return intro
    except Exception:
        return "Here's an interactive dashboard grounded in Lenny's podcast transcripts."


async def _generate_html(provider: "LLMProvider", ctx: SharedContext) -> Optional[str]:
    """Call 2 — full raw HTML. Entire response = artifact content."""
    # Build messages: include last few turns of history + essay context if available
    messages = list(ctx.history[-4:]) if ctx.history else []

    essay_context = ""
    if ctx.primary_response and ctx.plan.needs_essay:
        essay_context = (
            f"\n\nESSAY ALREADY GENERATED (use the same data and guests):\n"
            f"{ctx.primary_response[:1500]}"
        )

    messages.append({
        "role": "user",
        "content": (
            f"TRANSCRIPT CONTEXT (ground all data here — cite specific guests):\n"
            f"{ctx.context_text}"
            f"{essay_context}\n\n"
            f"---\n\n"
            f"REQUEST: {ctx.user_query}\n\n"
            f"Generate a complete HTML dashboard with metric cards, a Chart.js chart, "
            f"and a data table. All data must come from the transcript context above. "
            f"Include a Sources footer listing the guests referenced."
        ),
    })

    try:
        raw = await provider.chat(
            messages=messages,
            system_prompt=ARTIFACT_HTML_PROMPT,
            max_tokens=4096,
        )
        return _clean_html(raw)
    except Exception as e:
        print(f"[ArtifactAgent] HTML generation failed: {e}")
        return None


async def _repair_html(
    provider: "LLMProvider",
    broken_html: str,
    error: str = "HTML is malformed",
) -> Optional[str]:
    """Self-healing repair — send broken output back for correction."""
    try:
        raw = await provider.chat(
            messages=[{
                "role": "user",
                "content": (
                    f"Fix the following error in this HTML dashboard:\n"
                    f"ERROR: {error}\n\n"
                    f"BROKEN HTML (first 2000 chars):\n{broken_html[:2000]}\n\n"
                    f"Return ONLY the corrected, complete HTML page. "
                    f"Start with <!DOCTYPE html> and end with </html>. Nothing else."
                ),
            }],
            system_prompt=ARTIFACT_HTML_PROMPT,
            max_tokens=4096,
        )
        repaired = _clean_html(raw)
        if _is_valid_html(repaired):
            print("[ArtifactAgent] Self-repair succeeded")
            return repaired
        return repaired if repaired else broken_html
    except Exception as e:
        print(f"[ArtifactAgent] Self-repair failed: {e}")
        return broken_html


def _clean_html(raw: str) -> str:
    """Strip any accidental wrapper the model added despite instructions."""
    s = raw.strip()

    # Remove <artifact> wrapper if model added it anyway
    s = re.sub(r'</?artifact[^>]*>', '', s, flags=re.IGNORECASE).strip()

    # Strip markdown code fences
    s = re.sub(r'^```[a-z]*\n?', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(r'\n?```$', '', s).strip()

    # Fast-forward to <!DOCTYPE or <html if there's a preamble
    lower = s.lower()
    for marker in ('<!doctype html', '<html'):
        pos = lower.find(marker)
        if pos > 0:
            s = s[pos:]
            lower = s.lower()
            break

    # Truncate anything after </html>
    end = lower.rfind('</html>')
    if end != -1:
        s = s[:end + 7]

    return s.strip()


def _is_valid_html(html: str) -> bool:
    """Minimal sanity check — does this look like a complete HTML page?"""
    if not html or len(html) < 100:
        return False
    lower = html.lower().lstrip()
    return (
        (lower.startswith('<!doctype html') or lower.startswith('<html'))
        and '</html>' in lower
    )
