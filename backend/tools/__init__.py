"""
tools/ — Pure Python tool functions used by Research Mode agents.

These are NOT LLM tool-calls — they are regular async Python functions
whose results are injected into agent task descriptions as text.
This means they work with ANY LLM (Ollama, Anthropic) without
requiring function-calling/tool-use capability from the model.
"""
