# Failure Log: OrchestratorAgent JSON Parsing Failure

**Date:** 2026-08-02  
**Agent:** OrchestratorAgent (`backend/agents/orchestrator.py`)  
**Status:** Partially fixed — keyword fallback working, LLM path degraded ⚠️

---

## What Happened

Every Research Mode query falls back to `"Keyword fallback plan"` instead of using
the OrchestratorAgent's LLM-generated plan. The agent step trace shows:

```
{"agent": "OrchestratorAgent", "step": "🧠 Plan: qa crew — Keyword fallback plan"}
```

Expected (when LLM works):
```
{"agent": "OrchestratorAgent", "step": "🧠 Plan: ship30for30 crew — Essay on product-market fit"}
```

---

## Root Cause: qwen3:4b Chain-of-Thought Interference

`qwen3:4b` is a "thinking" model — it emits `<think>...</think>` blocks **before** its
actual JSON output. The `llm.py` `OllamaProvider.chat()` method strips these via:

```python
return strip_thinking_tags(raw)
```

However, `OrchestratorAgent._parse_plan()` does its own JSON extraction **after** calling
`provider.chat()`, so it receives the cleaned text. The real issue is subtler:

### The Actual Failure Sequence

1. `provider.chat()` called with JSON-schema prompt
2. qwen3 returns:
   ```
   <think>
   Let me analyze the query. It's asking about product-market fit...
   The user wants an essay format...
   </think>
   {
     "crew_type": "ship30for30",
     "refined_query": "product-market fit strategies",
     "needs_artifact": false,
     ...
   }
   ```
3. `strip_thinking_tags()` strips the think block → returns clean JSON ✓
4. But qwen3 **sometimes** wraps its response in markdown:
   ````
   Here is my plan:
   ```json
   {"crew_type": "ship30for30", ...}
   ```
   ````
5. The JSON extraction regex `r'\{.*?\}'` with `re.DOTALL` finds the first `{` — but
   if the think block wasn't fully stripped (partial match edge case), the regex fails.
6. `_parse_plan()` catches the `json.JSONDecodeError` and silently returns the keyword fallback.

### Observed Error (from uvicorn logs)
```
[OrchestratorAgent] JSON parse failed: Expecting ',' delimiter: line 1 col 47 (char 46)
[OrchestratorAgent] Using keyword fallback plan
```

---

## Attempted Fix

Added markdown code block stripping before JSON extraction in `_parse_plan()`:

```python
def _parse_plan(raw: str) -> Optional[ExecutionPlan]:
    # Strip markdown code fences
    raw = re.sub(r'```(?:json)?\s*', '', raw).strip()
    raw = re.sub(r'```\s*$', '', raw).strip()
    
    # Extract JSON object
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    ...
```

**Result:** Improvement in ~60% of cases. The other 40% fail when qwen3 generates
additional commentary after the JSON closing brace, corrupting the match group.

---

## Current State

The keyword fallback works correctly and the pipeline functions end-to-end:
- `needs_essay` detection: works via keyword matching (ship30, essay, write)
- `needs_artifact` detection: works via keyword matching (dashboard, chart, visualize)
- `needs_qa` detection: default for all other queries

**Impact:** The Orchestrator's LLM-powered query refinement and complexity assessment
are not being used. The pipeline still produces correct results via the fallback.

---

## Recommended Fix (Not Yet Applied)

Use a more structured prompting approach — ask for JSON only, no preamble:

```python
ORCHESTRATOR_SYSTEM = """
You are a JSON-only planning agent. Output ONLY valid JSON. No markdown. No explanation.
No preamble. Just the JSON object.
"""
```

Or switch to Anthropic for the Orchestrator — Claude reliably returns JSON when asked.

---

## Lesson Learned

**Local models with chain-of-thought (qwen3, deepseek-r1) require explicit output
format enforcement at every JSON extraction point.** "Return JSON" in the system prompt
is insufficient — add "No markdown fences. No explanation. Just the JSON." to the user
message, and validate with a stricter extraction pattern.

Consider using `json.loads()` on progressive substrings (from the end) to find the last
valid JSON object in the response, rather than relying on the first regex match.
