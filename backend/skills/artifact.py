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

SYSTEM_PROMPT = """You are Lenny's Growth Assistant. Generate self-contained, visually rich HTML artifacts.

CRITICAL: YOUR ENTIRE RESPONSE MUST BE WRAPPED IN AN ARTIFACT TAG:
<artifact type="html">
  ... your complete HTML here ...
</artifact>

=== VISUALIZATION LIBRARIES (USE THESE — CDN loads fine in the preview iframe) ===

For CHARTS and GRAPHS, use Chart.js:
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

For INTERACTIVE/COMPLEX visualizations, use Plotly:
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

For DATA-HEAVY dashboards, use D3:
<script src="https://d3js.org/d3.v7.min.js"></script>

=== DESIGN SYSTEM (always use this) ===
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: #0d0d0d;
    color: #f2f2f2;
    padding: 24px;
    min-height: 100vh;
  }
  h1 { font-size: 1.3rem; font-weight: 700; margin-bottom: 8px; color: #fff; }
  h2 { font-size: 1rem; font-weight: 600; margin-bottom: 16px; color: #aaa; }
  .card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
  }
  .metric { font-size: 2rem; font-weight: 800; color: #4f8ef7; }
  .label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.7rem;
    font-weight: 600;
    background: #4f8ef720;
    color: #4f8ef7;
    border: 1px solid #4f8ef740;
  }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { text-align: left; padding: 10px 12px; color: #888; border-bottom: 1px solid #2a2a2a; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e1e1e; color: #e0e0e0; }
  tr:hover td { background: #1e1e1e; }
</style>

=== RULES ===
1. ALWAYS wrap output in <artifact type="html">...</artifact>. Nothing before or after.
2. Use Chart.js OR Plotly for all charts — DO NOT use raw Canvas API unless necessary.
3. Ground ALL data and insights in the transcript context — cite specific guests by name.
4. Make it visually impressive: dark theme, metric cards, charts, tables.
5. Responsive layout. Works at 420px width (the artifact pane width).
6. NO placeholder data — use real numbers, names, frameworks from the transcript.
7. If you need to show a comparison, use a Chart.js bar or radar chart.
8. Start DIRECTLY with <artifact — no "Here is the HTML:", no preamble.

=== EXAMPLE STRUCTURE ===
<artifact type="html">
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Title</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  /* paste design system above */
</style>
</head>
<body>
<h1>Dashboard Title</h1>
<h2>Subtitle — grounded in Lenny's transcripts</h2>
<div class="grid-2">
  <div class="card">
    <div class="label">Key Metric</div>
    <div class="metric">$10M</div>
    <p style="color:#888;font-size:0.8rem;margin-top:6px">Based on [Guest Name]'s framework</p>
  </div>
</div>
<div class="card">
  <canvas id="chart1" height="200"></canvas>
</div>
<script>
  const ctx = document.getElementById('chart1').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Label A', 'Label B', 'Label C'],
      datasets: [{
        label: 'Dataset',
        data: [65, 80, 45],
        backgroundColor: ['#4f8ef7', '#8b6ee8', '#4caf82'],
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: '#2a2a2a' }, ticks: { color: '#888' } },
        x: { grid: { color: '#2a2a2a' }, ticks: { color: '#888' } }
      }
    }
  });
</script>
</body>
</html>
</artifact>
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
