"""
skills/artifact.py — Structured artifact generation skill.

The LLM wraps output in <artifact type="html"> or <artifact type="markdown"> tags.
Backend extracts these; frontend renders in the artifact pane.

Key rules for HTML:
- ALL charts/visualizations must use inline Canvas API or inline SVG only.
- NO external CDN (Chart.js, D3, etc.) — iframe sandbox blocks external scripts.
- All CSS must be inline or in a <style> block.
"""
from __future__ import annotations
import re
from typing import Dict, Optional, Tuple, List

from rag import retrieve, build_context, dedupe_sources
from llm import LLMProvider

SYSTEM_PROMPT = """You are Lenny's Growth Assistant. You generate self-contained HTML or Markdown artifacts.

CRITICAL: YOUR ENTIRE RESPONSE MUST BE WRAPPED IN AN ARTIFACT TAG. NO EXCEPTIONS.

For HTML artifacts:
<artifact type="html">
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  /* All CSS here — inline only, NO external CSS */
  body { font-family: system-ui, sans-serif; background: #0d0d0d; color: #f2f2f2; padding: 24px; margin: 0; }
</style>
</head>
<body>
  <!-- content here -->
  <script>
    /* Pure vanilla JS only — NO CDN libraries (Chart.js, D3, etc.) */
    /* For charts: use Canvas 2D API or inline SVG */
  </script>
</body>
</html>
</artifact>

For Markdown artifacts:
<artifact type="markdown">
# Title
content...
</artifact>

STRICT RULES:
1. Response MUST start with <artifact and end with </artifact>. Nothing before or after.
2. HTML must be FULLY self-contained — no external scripts, no CDN URLs, no external images.
3. For line charts, bar charts: use HTML5 Canvas with vanilla JS (no Chart.js).
4. Ground all content in the transcript context — cite specific guests by name.
5. Make it beautiful: dark theme (#0d0d0d bg, #f2f2f2 text), clear typography, well-spaced.
6. DO NOT say "Here is the HTML:" before the tag. Start directly with <artifact.

CHART EXAMPLE (use this pattern for any chart):
<script>
const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');
const data = [/* your data */];
// draw manually with ctx.fillRect, ctx.strokeRect, ctx.lineTo etc.
</script>
"""


def extract_artifact(text: str) -> Tuple[str, Optional[Dict]]:
    """
    Extract <artifact type="...">...</artifact> block from LLM response.
    Also handles case where LLM outputs raw HTML without artifact tags.
    """
    # Primary: look for <artifact type="..."> tags
    pattern = r'<artifact\s+type=["\'](\w+)["\']\s*>(.*?)</artifact>'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if match:
        artifact_type = match.group(1).lower()
        artifact_content = match.group(2).strip()
        outside = (text[: match.start()].strip() + text[match.end():].strip()).strip()
        response_text = outside or "Here's the artifact I generated:"
        return response_text, {"type": artifact_type, "content": artifact_content}

    # Fallback: if LLM output looks like raw HTML, wrap it
    stripped = text.strip()
    if stripped.lower().startswith("<!doctype html") or stripped.lower().startswith("<html"):
        return "Here's the artifact I generated:", {"type": "html", "content": stripped}

    # Last resort: treat as markdown artifact
    return "Here's the artifact I generated:", {"type": "markdown", "content": stripped}


async def run_artifact(
    user_message: str,
    provider: LLMProvider,
    conn,
    history: Optional[List[Dict]] = None,
) -> Dict:
    """
    Run the artifact generation skill.

    Returns:
        {"response": str, "skill_used": "artifact", "sources": list,
         "artifact": {"type": ..., "content": ...} | None}
    """
    # 1. Retrieve relevant chunks for grounding
    chunks = await retrieve(user_message, conn, top_k=4)
    context = build_context(chunks)

    # 2. Build messages — history gives context for what kind of artifact was requested
    messages = list(history or [])
    messages.append({
        "role": "user",
        "content": (
            f"TRANSCRIPT CONTEXT (use for grounding content):\n{context}\n\n"
            f"---\n\n"
            f"REQUEST: {user_message}\n\n"
            f"Respond ONLY with an <artifact> tag wrapping your complete output. "
            f"No text before or after the tag."
        ),
    })

    # 3. Call LLM (high token limit for full HTML pages)
    raw_response = await provider.chat(messages, system_prompt=SYSTEM_PROMPT, max_tokens=4096)

    # 4. Parse artifact tags
    response_text, artifact = extract_artifact(raw_response)
    sources = dedupe_sources(chunks)

    return {
        "response": response_text,
        "skill_used": "artifact",
        "sources": sources,
        "artifact": artifact,
    }
