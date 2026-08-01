"""
router.py — Rule-based skill classifier.

Why rule-based instead of an LLM classifier:
  - Deterministic: same input always produces same routing decision.
  - Zero latency: no extra LLM call, no tokens spent.
  - Trivially explainable during demo / code review.
  - At MVP scale (3 skills), keyword matching covers >95% of real queries.

If we later need fuzzy routing (e.g. 10+ skills), swap this for a
lightweight embedding-based nearest-neighbour classifier — but that's P2.
"""

SHIP30_KEYWORDS = [
    "essay", "ship30", "write an article", "atomic essay",
    "write me an essay", "write a post", "linkedin post",
    "tweet thread", "newsletter", "write about", "write on",
    "short post", "long-form", "draft a post",
]

# NOTE: Keep these specific — overly-broad keywords like "generate", "table",
# "build a", "render" catch too many Q&A queries (e.g. "generate a list of",
# "make a table comparing", "build a case for"). Artifact routing should require
# clear HTML/visual/code intent.
ARTIFACT_KEYWORDS = [
    # Explicit HTML / code
    "html", "create html", "make a page", "landing page",
    "artifact", "code for", "web page",
    # Interactive / visual
    "dashboard", "chart", "visualization", "graph",
    "create a chart", "create a dashboard", "build a dashboard",
    "show me a chart", "show me a table", "create a table",
    "interactive", "ui for", "page for",
    # Explicit build-something requests (must be specific)
    "build me a", "create a page", "make a dashboard",
    "create an html", "build an html", "generate html",
    "generate a chart", "generate a dashboard",
]


def classify_skill(user_message: str) -> str:
    """
    Returns one of: 'qa' | 'ship30for30' | 'artifact'

    Evaluation order matters:
    1. ship30for30 — checked first because "write" is a strong signal
    2. artifact — second because "generate" / "create" can overlap with qa
    3. qa — default fallback
    """
    msg = user_message.lower()

    if any(k in msg for k in SHIP30_KEYWORDS):
        return "ship30for30"

    if any(k in msg for k in ARTIFACT_KEYWORDS):
        return "artifact"

    return "qa"
