"""
llm.py — LLM provider abstraction.

Usage:
    from llm import get_llm_provider
    provider = get_llm_provider()
    response = await provider.chat(messages, system_prompt)
    # or for streaming:
    async for token in provider.stream(messages, system_prompt):
        print(token, end="", flush=True)
"""
from __future__ import annotations
import asyncio
import json as _json
import re
import urllib.request
from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator
import anthropic
from config import settings


# ── Utility: strip qwen3 <think>...</think> blocks ───────────────────────────

def strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> blocks that qwen3 emits before its answer."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# ── Base interface ────────────────────────────────────────────────────────────

class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Send messages and return the assistant reply as a plain string."""
        ...

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens. Default: fall back to non-streaming (yields full response)."""
        response = await self.chat(messages, system_prompt, max_tokens)
        yield response

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        ...


# ── Ollama provider ───────────────────────────────────────────────────────────

def _ollama_chat_sync(base_url: str, payload: dict) -> str:
    """Sync urllib call to Ollama /api/chat — run in executor to stay async-friendly."""
    data = _json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = _json.loads(resp.read())
    return result["message"]["content"]


def _ollama_stream_sync(base_url: str, payload: dict):
    """Generator that yields token strings from Ollama streaming response."""
    data = _json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        for line in resp:
            line = line.decode("utf-8").strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
                token = obj.get("message", {}).get("content", "")
                if token:
                    yield token
                if obj.get("done"):
                    break
            except Exception:
                continue


def _ollama_health_sync(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_chat_model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if system_prompt:
            payload["system"] = system_prompt

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _ollama_chat_sync, self.base_url, payload)
        return strip_thinking_tags(raw)

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"num_predict": max_tokens},
        }
        if system_prompt:
            payload["system"] = system_prompt

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            in_think = False
            buf = ""
            for token in _ollama_stream_sync(self.base_url, payload):
                buf += token
                # Strip <think>...</think> from stream
                while True:
                    if not in_think:
                        start = buf.find("<think>")
                        if start == -1:
                            # No think tag — emit everything safe
                            safe = buf
                            buf = ""
                            if safe:
                                loop.call_soon_threadsafe(queue.put_nowait, safe)
                            break
                        else:
                            # Emit before think tag
                            safe = buf[:start]
                            buf = buf[start:]
                            if safe:
                                loop.call_soon_threadsafe(queue.put_nowait, safe)
                            in_think = True
                    else:
                        end = buf.find("</think>")
                        if end == -1:
                            buf = buf  # still inside think block
                            break
                        else:
                            buf = buf[end + len("</think>"):]
                            in_think = False
            # Emit remaining buffer
            if buf and not in_think:
                loop.call_soon_threadsafe(queue.put_nowait, buf.strip())
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        loop.run_in_executor(None, _run)

        while True:
            token = await queue.get()
            if token is None:
                break
            yield token

    async def health_check(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _ollama_health_sync, self.base_url)


# ── Anthropic provider ────────────────────────────────────────────────────────

class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        msg = await self.client.messages.create(**kwargs)
        return strip_thinking_tags(msg.content[0].text)

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with self.client.messages.stream(**kwargs) as s:
            async for token in s.text_stream:
                yield token

    async def health_check(self) -> bool:
        if not settings.anthropic_api_key:
            return False
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="GET",
            )
            loop = asyncio.get_event_loop()
            def _check():
                try:
                    with urllib.request.urlopen(req, timeout=5) as r:
                        return r.status == 200
                except Exception:
                    return False
            return await loop.run_in_executor(None, _check)
        except Exception:
            return False


# ── Factory ───────────────────────────────────────────────────────────────────

def get_llm_provider(provider: str | None = None) -> LLMProvider:
    name = (provider or settings.llm_provider).lower()
    if name == "anthropic":
        return AnthropicProvider()
    return OllamaProvider()
