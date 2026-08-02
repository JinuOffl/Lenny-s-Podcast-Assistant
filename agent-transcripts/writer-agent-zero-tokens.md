# Failure Log: WriterAgent Streaming 0 Tokens

**Date:** 2026-08-02  
**Agent:** WriterAgent (`backend/agents/writer.py`)  
**Status:** Fixed ✅

---

## What Happened

On the first end-to-end test of the Research Mode pipeline, the backend returned a successful
response with the full agent pipeline firing correctly — but the `word_count` in the
done event was `0`, and no `{"token": "..."}` SSE events appeared in the output.

### Raw Backend Output (Broken)

```
data: {"agent": "OrchestratorAgent", "step": "🧠 Analyzing..."}
data: {"agent": "ResearchAgent", "step": "✅ Found 5 chunks from 4 episodes (1 search hop)"}
data: {"agent": "WriterAgent", "step": "✍️  Generating answer from 5 sources..."}
data: {"agent": "WriterAgent", "step": "✅ Response generated (0 words)"}   ← BUG HERE
data: {"agent": "ValidatorAgent", "step": "✅ Validating output quality..."}
data: {"done": true, "skill_used": "qa", "word_count": 0, ...}
```

Notice: **zero `{"token": "..."}` events between WriterAgent and ValidatorAgent.**

---

## Root Cause Analysis

### Bug 1: DB row dicts passed directly to LLM API

In the original `stream_writer_response()`:

```python
# ❌ WRONG: ctx.history contains raw DB row dicts
messages = list(ctx.history)
```

The `ctx.history` list contained dicts like:
```python
{"role": "user", "content": "...", "skill_used": "qa", "sources": [...], "artifact": None}
```

Ollama's `/api/chat` endpoint requires messages to be `{"role": "...", "content": "..."}` only.
Extra keys caused the message list to be **silently rejected** — the LLM received no messages
and returned an empty response.

### Bug 2: `.format()` KeyError on JSON-containing context

The original code:
```python
user_content = user_content.format(
    context=context_block,
    query=ctx.user_query,
)
```

If `context_block` contained any `{` or `}` characters (common in JSON-format transcript
excerpts), `str.format()` would raise a `KeyError` or `IndexError` — silently caught in
the generator, resulting in 0 tokens yielded.

---

## Fix Applied

Rebuilt `stream_writer_response()` to:

1. **Build a clean message list from scratch** — filter only `role` + `content` from history:
```python
messages: List[Dict] = []
if ctx.history:
    for m in ctx.history[-6:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"][:1000]})
```

2. **Construct user_content directly with f-strings** — no `.format()` calls:
```python
user_content = (
    f"TRANSCRIPT CONTEXT:\n{context_block}\n\n"
    f"---\n\n"
    f"QUESTION: {ctx.user_query}"
)
messages.append({"role": "user", "content": user_content})
```

3. **Added a streaming fallback** — if `provider.stream()` fails, falls back to `provider.chat()`:
```python
try:
    async for token in provider.stream(messages, ...):
        yield token
except Exception as e:
    fallback = await provider.chat(messages, ...)
    yield fallback
```

---

## Result After Fix

```
data: {"agent": "WriterAgent", "step": "✍️  Generating answer from 5 sources..."}
data: {"token": "Based"}
data: {"token": " on"}
data: {"token": " the"}
... (242 more tokens) ...
data: {"agent": "WriterAgent", "step": "✅ Response generated (242 words)"}
```

---

## Lesson Learned

**Never pass database row objects directly to the LLM API.** Always construct clean
`{"role": str, "content": str}` dicts explicitly. DB rows carry extra columns that
different LLM providers handle differently — some reject them, some silently ignore them.

Similarly, **never use str.format() for LLM prompt construction** if the injected content
can contain curly braces (JSON, code, etc.). Use f-strings instead.
