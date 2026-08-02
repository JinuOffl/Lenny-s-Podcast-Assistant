# Agent Transcripts

Raw logs of real agent failures, corrections, and self-healing attempts captured during
the development of Lenny's Growth Assistant Research Mode.

These are **unedited** interactions that shaped the final architecture.

## Files

| File | What Happened |
|---|---|
| `writer-agent-zero-tokens.md` | WriterAgent streamed 0 tokens on first run — root cause + fix |
| `orchestrator-json-failure.md` | OrchestratorAgent couldn't parse its own LLM output — qwen3 think-block interference |
| `artifact-self-healing-demo.md` | ValidatorAgent caught a broken HTML artifact and self-healed it |
