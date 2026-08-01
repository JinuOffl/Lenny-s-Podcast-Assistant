"""
skills/artifact.py — Structured artifact generation skill.

The LLM wraps its output in <artifact type="html">...</artifact> or
<artifact type="markdown">...</artifact> tags. The backend regex-extracts
these so the frontend can render them in the artifact pane.

Why regex on full response (not streaming)?
  The artifact tags may wrap the entire output, so we need the complete
  response before we can extract them. Streaming + regex is fragile here.
"""
from __future__ import annotations
import re
from typing import Dict, Optional, Tuple

from rag import retrieve, build_context, dedupe_sources
from llm import LLMProvider

SYSTEM_PROMPT = """You are Lenny's Growth Assistant. You generate self-contained HTML or Markdown artifacts.

CRITICAL RULE — YOUR ENTIRE RESPONSE MUST BE WRAPPED IN AN ARTIFACT TAG. NO EXCEPTIONS.

For HTML: wrap your ENTIRE response like this:
<artifact type="html">
<!DOCTYPE html>
<html>
<head><style>/* inline styles only — no external CSS or CDN */</style></head>
<body><!-- content here --></body>
</html>
</artifact>

For Markdown: wrap your ENTIRE response like this:
<artifact type="markdown">
# Title
content...
</artifact>

RULES:
1. Your response must START with <artifact and END with </artifact>. Nothing before or after.
2. HTML must be completely self-contained — all CSS inline, no external links.
3. Ground content in the transcript context provided — cite specific guests by name.
4. Make the artifact beautiful and useful, not a minimal stub.

DO NOT output any text outside the artifact tags. Do not say "Here is the HTML:" before the tag.
DO NOT output plain HTML without wrapping it in <artifact type="html">...</artifact>.
"""


def extract_artifact(text: str) -> Tuple[str, Optional[Dict]]:
    """
    Extract an <artifact type="...">...</artifact> block from the LLM response.

    Returns:
        (response_text, artifact_dict | None)

    Where response_text is the text outside the artifact tags (or a default message)
    and artifact_dict is {"type": "html"|"markdown", "content": "..."}.
    """
    pattern = r'<artifact\s+type=["\'](\w+)["\']>(.*?)</artifact>'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if not match:
        # LLM forgot the tags — return the raw text as a markdown artifact
        return "Here's the artifact I generated:", {
            "type": "markdown",
            "content": text.strip(),
        }

    artifact_type = match.group(1).lower()
    artifact_content = match.group(2).strip()

    # Everything outside the artifact tags becomes the response text
    outside = text[: match.start()].strip() + text[match.end() :].strip()
    response_text = outside.strip() or "Here's the artifact I generated:"

    return response_text, {"type": artifact_type, "content": artifact_content}


async def run_artifact(
    user_message: str,
    provider: LLMProvider,
    conn,
) -> Dict:
    """
    Run the artifact generation skill.

    Returns:
        {
            "response": str,              # text outside artifact tags
            "skill_used": "artifact",
            "sources": List[Dict],
            "artifact": {"type": ..., "content": ...} | None,
        }
    """
    # 1. Retrieve relevant chunks for grounding
    chunks = await retrieve(user_message, conn, top_k=4)
    context = build_context(chunks)

    # 2. Build prompt
    messages = [
        {
            "role": "user",
            "content": (
                f"TRANSCRIPT CONTEXT (use for grounding the content):\n{context}\n\n"
                f"---\n\n"
                f"REQUEST: {user_message}\n\n"
                f"Respond ONLY with an <artifact> tag wrapping your output."
            ),
        }
    ]

    # 3. Call LLM
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
