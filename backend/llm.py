"""
llm.py — LLM provider abstraction.

Usage:
    from llm import get_llm_provider
    provider = get_llm_provider()          # uses settings.llm_provider
    response = await provider.chat(messages, system_prompt)
"""
from __future__ import annotations
import asyncio
import json as _json
import urllib.request
from abc import ABC, abstractmethod
from typing import List, Dict
import anthropic
from config import settings


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
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = _json.loads(resp.read())
    return result["message"]["content"]


def _ollama_health_sync(base_url: str) -> bool:
    """Check Ollama is reachable."""
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
        return await loop.run_in_executor(None, _ollama_chat_sync, self.base_url, payload)

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
        return msg.content[0].text

    async def health_check(self) -> bool:
        if not settings.anthropic_api_key:
            return False
        # Lightweight check via urllib (avoids httpx/trio dep)
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
    """
    Return a provider instance.
    Falls back to settings.llm_provider if no argument given.
    """
    name = (provider or settings.llm_provider).lower()
    if name == "anthropic":
        return AnthropicProvider()
    return OllamaProvider()
