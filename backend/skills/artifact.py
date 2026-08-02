"""
skills/artifact.py — Artifact generation (two-call split, Option B).

Why two calls instead of tag extraction:
  The old approach asked the model to wrap HTML in <artifact type="html">...</artifact>
  and then regex-extracted the content. qwen3's <think> block confused the regex,
  and truncation left unclosed tags that made the extractor fall through to the
  "treat everything as markdown" last resort — raw tags in chat, broken HTML.

Two-call split eliminates the parsing problem entirely:
  Call 1 → short intro sentence   (shown in chat message)
  Call 2 → raw HTML page only     (entire response = artifact, nothing to parse)
  Repair → one self-healing retry if output looks malformed

Scope: this file and its call in main.py only. Q&A / essay skills untouched.
"""
from __future__ import annotations
import re
from typing import Dict, Optional, List

from rag import retrieve, build_context, dedupe_sources
from llm import LLMProvider


# ── System prompts ────────────────────────────────────────────────────────────

INTRO_SYSTEM_PROMPT = (
    "You write one concise sentence (max 20 words) introducing a data visualization. "
    "No preamble, just the sentence."
)

HTML_SYSTEM_PROMPT = """\
You are Lenny's Growth Assistant. Generate a complete, self-contained HTML dashboard.

YOUR ENTIRE RESPONSE MUST BE A VALID HTML PAGE.
Start with <!DOCTYPE html> and end with </html>.
NO explanation. NO wrapper tags. NO text before or after the HTML.

=== VISUALIZATION LIBRARIES (CDN — works in preview iframe) ===
Charts:      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
Interactive: <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

=== DESIGN SYSTEM (always include this <style> block) ===
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', system-ui, sans-serif; background: #0d0d0d; color: #f2f2f2; padding: 24px; min-height: 100vh; }
  h1 { font-size: 1.3rem; font-weight: 700; margin-bottom: 4px; color: #fff; }
  h2 { font-size: 0.9rem; font-weight: 500; margin-bottom: 20px; color: #888; }
  .card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
  .metric { font-size: 2rem; font-weight: 800; color: #4f8ef7; }
  .label { font-size: 0.7rem; color: #888; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .tag { display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 0.7rem; font-weight: 600; background: #4f8ef720; color: #4f8ef7; border: 1px solid #4f8ef740; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  th { text-align: left; padding: 8px 12px; color: #666; border-bottom: 1px solid #2a2a2a; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e1e1e; color: #e0e0e0; }
  tr:hover td { background: #1e1e1e; }
</style>

=== STRICT RULES ===
1. Start DIRECTLY with <!DOCTYPE html> — nothing before it, not even a blank line.
2. End with </html> — nothing after it.
3. Use Chart.js for all charts (bar, line, radar, doughnut).
4. Ground ALL data in the transcript context — cite specific guest names.
5. Dark theme. Metric cards. Charts. Tables. Make it visually impressive.
6. Every <canvas> must have a unique id attribute.
7. CDN <script> tags must NOT be self-closing: <script src="..."></script>.
8. Responsive layout — works at 420px width (the artifact pane width).
9. NO placeholder data — use real names, numbers, frameworks from the transcript.
"""


# ── Public interface ──────────────────────────────────────────────────────────

async def run_artifact(
    user_message: str,
    provider: LLMProvider,
    conn,
    history: Optional[List[Dict]] = None,
    step_callback=None,          # optional: async callable(step: str) called live
) -> Dict:
    """
    Generate an artifact using the two-call split approach.

    step_callback: if provided, called at each phase so the SSE stream can emit
    live status labels: Searching → Generating → Repairing (if needed).

    Returns:
        {
          "response":   str,
          "skill_used": "artifact",
          "sources":    list,
          "artifact":   {"type": "html", "content": str} | None
        }
    """
    async def _emit(step: str):
        if step_callback:
            await step_callback(step)

    # ── Retrieve RAG context ──────────────────────────────────────────────────
    await _emit("Searching")
    chunks = await retrieve(user_message, conn, top_k=4)
    context = build_context(chunks)
    sources = dedupe_sources(chunks)

    # ── Call 1: intro sentence ────────────────────────────────────────────────
    await _emit("Generating")
    intro = await _generate_intro(provider, user_message, context)

    # ── Call 2: raw HTML ──────────────────────────────────────────────────────
    html_content = await _generate_html(provider, user_message, context, history or [])

    # ── Self-repair if HTML looks broken ─────────────────────────────────────
    if html_content and not _is_valid_html(html_content):
        print("[artifact] HTML validation failed — attempting self-repair")
        await _emit("Repairing")
        html_content = await _repair_html(provider, html_content)

    artifact = {"type": "html", "content": html_content} if html_content else None

    return {
        "response": intro,
        "skill_used": "artifact",
        "sources": sources,
        "artifact": artifact,
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _generate_intro(provider: LLMProvider, user_message: str, context: str) -> str:
    """Call 1 — one sentence intro shown in the chat bubble."""
    try:
        raw = await provider.chat(
            messages=[{
                "role": "user",
                "content": (
                    f"TRANSCRIPT CONTEXT:\n{context[:600]}\n\n"
                    f"REQUEST: {user_message}\n\n"
                    f"Write one sentence introducing the visualization you are about to generate."
                ),
            }],
            system_prompt=INTRO_SYSTEM_PROMPT,
            max_tokens=60,
        )
        intro = raw.strip().rstrip('.') + '.'
        # Guard: reject if it looks like the model rambled
        if len(intro.split()) > 30:
            intro = "Here's an interactive dashboard grounded in Lenny's podcast transcripts."
        return intro
    except Exception:
        return "Here's an interactive dashboard grounded in Lenny's podcast transcripts."


async def _generate_html(
    provider: LLMProvider,
    user_message: str,
    context: str,
    history: List[Dict],
) -> Optional[str]:
    """Call 2 — full HTML page. Entire response = artifact content, nothing to parse."""
    messages = list(history)
    messages.append({
        "role": "user",
        "content": (
            f"TRANSCRIPT CONTEXT (ground all data here — cite specific guests):\n{context}\n\n"
            f"---\n\n"
            f"REQUEST: {user_message}\n\n"
            f"Generate a complete HTML dashboard with metric cards, a Chart.js chart, "
            f"and a data table. All data must come from the transcript context above."
        ),
    })

    try:
        raw = await provider.chat(
            messages=messages,
            system_prompt=HTML_SYSTEM_PROMPT,
            max_tokens=4096,
        )
        return _clean_html(raw)
    except Exception as e:
        print(f"[artifact] HTML generation failed: {e}")
        return None


async def _repair_html(provider: LLMProvider, broken_html: str) -> Optional[str]:
    """One self-healing retry — send broken HTML back and ask for a fix."""
    try:
        raw = await provider.chat(
            messages=[{
                "role": "user",
                "content": (
                    f"The following HTML is malformed or incomplete. "
                    f"Return ONLY the corrected, complete HTML page. "
                    f"Start with <!DOCTYPE html> and end with </html>. Nothing else.\n\n"
                    f"BROKEN HTML:\n{broken_html[:2000]}"
                ),
            }],
            system_prompt=HTML_SYSTEM_PROMPT,
            max_tokens=4096,
        )
        repaired = _clean_html(raw)
        if _is_valid_html(repaired):
            print("[artifact] Self-repair succeeded")
            return repaired
        print("[artifact] Self-repair did not produce valid HTML — returning best effort")
        return repaired if repaired else broken_html
    except Exception as e:
        print(f"[artifact] Self-repair failed: {e}")
        return broken_html


def _clean_html(raw: str) -> str:
    """
    Strip any accidental wrapper the model added despite instructions.
    Since we ask for raw HTML only, this is mostly defensive.
    """
    s = raw.strip()

    # Remove <artifact> wrapper tags if the model added them anyway
    s = re.sub(r'</?artifact[^>]*>', '', s, flags=re.IGNORECASE).strip()

    # Strip markdown code fences (```html ... ```)
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
    """Minimal sanity check — does this look like a real HTML page?"""
    if not html or len(html) < 100:
        return False
    lower = html.lower().lstrip()
    return (
        (lower.startswith('<!doctype html') or lower.startswith('<html'))
        and '</html>' in lower
    )
