"""
tools/validate_tool.py — HTML and Markdown validation for the ValidatorAgent.

Pure Python — no LLM calls. Fast structural checks that catch the most
common generation failures before they reach the user.
"""
from __future__ import annotations
import re
from typing import Optional, List


# ── HTML Validation ───────────────────────────────────────────────────────────

def validate_html(html: str) -> Optional[str]:
    """
    Structural validation of generated HTML.

    Returns:
        None  → HTML is valid, ready to render
        str   → error description (fed into self-healing prompt)
    """
    if not html or len(html.strip()) < 100:
        return "HTML content is empty or too short (< 100 chars)"

    h = html.strip()
    h_lower = h.lower()

    # 1. Must have some HTML structure
    if "<html" not in h_lower and "<!doctype" not in h_lower:
        if "<body" not in h_lower:
            return "Missing HTML document structure — no <html>, <!DOCTYPE>, or <body> tag found"

    # 2. Artifact wrapper tags must be stripped
    if "<artifact" in h_lower or "</artifact>" in h_lower:
        return "Response still contains <artifact> wrapper tags — backend must extract content only"

    # 3. Script tag balance
    script_opens = len(re.findall(r"<script(?:\s[^>]*)?>", h, re.IGNORECASE))
    script_closes = len(re.findall(r"</script>", h, re.IGNORECASE))
    if script_opens != script_closes:
        return (
            f"Mismatched <script> tags: {script_opens} opening, {script_closes} closing. "
            f"Every <script> must have a matching </script>."
        )

    # 4. CDN scripts must be properly closed
    cdn_tags = re.findall(r'<script\s+src=["\'][^"\']+["\'][^>]*>', h, re.IGNORECASE)
    for tag in cdn_tags:
        if tag.rstrip().endswith("/>"):
            continue  # self-closed OK
        # Check if there's a corresponding </script> right after
        idx = h.lower().find(tag.lower())
        after = h[idx + len(tag): idx + len(tag) + 20]
        if "</script>" not in after.lower():
            return f"CDN script tag not closed with </script>: {tag[:60]}..."

    # 5. Body tag pairing
    has_body_open = "<body" in h_lower
    has_body_close = "</body>" in h_lower
    if has_body_open and not has_body_close:
        return "Unclosed <body> tag — add </body> before </html>"

    # 6. Canvas elements must have an id
    canvas_tags = re.findall(r"<canvas[^>]*>", h, re.IGNORECASE)
    for tag in canvas_tags:
        if "id=" not in tag.lower():
            return f"<canvas> element missing required id attribute: {tag[:60]}"

    # 7. Chart.js canvas references must match existing ids
    chart_ids = re.findall(r"""getElementById\(['"]([\w-]+)['"]\)""", h)
    canvas_ids = re.findall(r"""<canvas[^>]+id=['"]([\w-]+)['"]""", h, re.IGNORECASE)
    for cid in chart_ids:
        if canvas_ids and cid not in canvas_ids:
            return (
                f"getElementById('{cid}') references an element that doesn't exist. "
                f"Available canvas ids: {canvas_ids}"
            )

    return None  # ✅ Valid


def validate_markdown(md: str) -> Optional[str]:
    """
    Basic markdown validation.

    Returns:
        None  → valid
        str   → error description
    """
    if not md or len(md.strip()) < 50:
        return "Markdown content too short (< 50 chars)"

    # Should have at least one heading
    if not re.search(r"^#{1,3}\s", md, re.MULTILINE):
        return "Markdown missing headers — add at least one # heading"

    return None


# ── Essay Validation ──────────────────────────────────────────────────────────

def validate_essay(text: str, min_words: int = 1000, max_words: int = 1350) -> Optional[str]:
    """
    Validate Ship30for30 essay structure and length.

    Returns:
        None  → valid
        str   → error description
    """
    word_count = len(text.split())

    if word_count < min_words:
        return (
            f"Essay too short: {word_count} words. "
            f"Minimum is {min_words} words. Add more concrete examples from the transcripts."
        )

    if word_count > max_words:
        return (
            f"Essay too long: {word_count} words. "
            f"Maximum is {max_words} words. Remove the least concrete section."
        )

    # Should have a headline (## at start)
    if not re.search(r"^##\s", text.strip(), re.MULTILINE):
        return "Essay missing Ship30for30 headline (## heading at the start)"

    # Should have bold text (key formatting requirement)
    bold_count = len(re.findall(r"\*\*[^*]+\*\*", text))
    if bold_count < 5:
        return f"Essay has only {bold_count} bold phrases — Ship30for30 requires heavy bold formatting for scannability"

    return None


# ── Error Context Builder ─────────────────────────────────────────────────────

def build_heal_prompt(error: str, original_content: str, attempt: int) -> str:
    """
    Build the self-healing prompt given the validation error.
    Injected into ArtifactAgent's retry task.
    """
    return (
        f"SELF-HEALING ATTEMPT {attempt}:\n"
        f"The previous output had a validation error:\n\n"
        f"  ERROR: {error}\n\n"
        f"ORIGINAL OUTPUT (first 500 chars):\n"
        f"  {original_content[:500]}...\n\n"
        f"Fix ONLY the error above. Keep all other content identical. "
        f"Output the complete corrected HTML wrapped in <artifact type=\"html\">...</artifact>."
    )
