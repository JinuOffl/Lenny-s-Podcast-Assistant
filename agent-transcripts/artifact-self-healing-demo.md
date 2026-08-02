# Failure Log: Artifact Self-Healing Demo

**Date:** 2026-08-02  
**Agent:** ValidatorAgent + ArtifactAgent (`backend/agents/validator.py`, `artifact_agent.py`)  
**Status:** Working as designed ✅ (self-healing triggered intentionally to test the loop)

---

## What Happened

During testing of the self-healing loop, a test query was sent that asked ArtifactAgent
to generate a chart with intentionally incomplete HTML. The ValidatorAgent caught the error,
triggered a self-heal, and the UI displayed the amber "Self-healed" banner.

**Test query:** `"Create an HTML line chart showing growth metrics across episodes"`

---

## First ArtifactAgent Attempt (Broken)

ArtifactAgent generated HTML that included an unclosed `<script>` tag:

```html
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js" />   <!-- ← SELF-CLOSING, INVALID -->
</head>
<body>
  <canvas id="myChart"></canvas>
  <script>
    new Chart(document.getElementById('myChart'), { ... });
  </script>
</body>
</html>
```

The `validate_html()` tool caught this:
```
Error: Script tag appears to be self-closing. Use <script src="..."></script> syntax.
```

---

## ValidatorAgent SSE Events (Visible in Browser)

```json
{"agent": "ValidatorAgent", "step": "✅ Validating output quality..."}
{"agent": "ValidatorAgent", "step": "🔧 Self-healing artifact (attempt 1/2) — Script tag appears to be self-closing"}
{"agent": "ArtifactAgent", "step": "🔧 Fixing artifact..."}
{"agent": "ValidatorAgent", "step": "✅ Artifact self-healed successfully after 1 attempt(s)!"}
```

---

## Self-Heal Prompt Injected

The healing prompt passed to ArtifactAgent on retry:

```
SELF-HEALING REQUEST — Fix the following error in your previous HTML output:

ERROR: Script tag appears to be self-closing. Use <script src="..."></script> syntax.

PREVIOUS OUTPUT (first 800 chars):
<html><head><script src="https://cdn.jsdelivr.net/npm/chart.js" />...

Fix ONLY the error. Keep all other content identical.
Output the COMPLETE corrected HTML inside <artifact type="html">...</artifact>.
```

---

## Second ArtifactAgent Attempt (Healed)

```html
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>  <!-- ← Fixed -->
</head>
<body>
  <canvas id="myChart"></canvas>
  <script>
    new Chart(document.getElementById('myChart'), { ... });
  </script>
</body>
</html>
```

`validate_html()` passed. Confidence stayed `medium`. Done event:
```json
{
  "done": true,
  "healing_attempts": 1,
  "confidence": "medium",
  ...
}
```

---

## UI Result

The ArtifactPane showed the working chart. Below the response in the chat:

```
⚡ Self-healed 1× — ValidatorAgent fixed errors automatically
```

(amber banner in ResearchStats component)

---

## validate_html() Checks Implemented

The `validate_tool.py` `validate_html()` function checks:

1. Minimum length (< 50 chars = too short)
2. Self-closing script tags (`<script ... />` is invalid HTML)
3. Unclosed `<html>` or `<body>` tags
4. Missing `<canvas>` when Chart.js is imported
5. Missing `<script>` closing tag
6. Balanced brace count in inline `<script>` blocks (heuristic)

---

## Lesson Learned

**The self-healing loop works best when the error message is precise and actionable.**
Generic errors like "HTML is invalid" don't give the LLM enough signal to fix the right thing.
Specific errors like "Script tag is self-closing — use `<script src='...'></script>`" allow
the model to make a targeted fix without regenerating the entire artifact.

The 800-character prefix of the broken output included in the heal prompt helps the model
understand the structure it's fixing, reducing the chance of it generating something
completely different.
