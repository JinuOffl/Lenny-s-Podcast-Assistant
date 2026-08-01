"""
models.py — Pydantic request/response schemas shared by all endpoints.
"""
from __future__ import annotations
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


# ── Session ──────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = "New chat"
    llm_provider: str = "ollama"


class SessionOut(BaseModel):
    id: UUID
    title: str
    llm_provider: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionUpdate(BaseModel):
    title: str


# ── Message ──────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    skill_used: Optional[str] = None
    artifact_json: Optional[dict] = None
    sources: Optional[List[dict]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ArtifactPayload(BaseModel):
    type: str   # "html" | "markdown"
    content: str


class SourceItem(BaseModel):
    guest: str
    episode_title: str
    youtube_url: str


class ChatResponse(BaseModel):
    response: str
    skill_used: str
    sources: List[SourceItem] = []
    artifact: Optional[ArtifactPayload] = None


# ── Config ───────────────────────────────────────────────────────────────────

class LLMConfigOut(BaseModel):
    llm_provider: str
    ollama_chat_model: str
    anthropic_model: str


class LLMConfigSet(BaseModel):
    llm_provider: str  # "ollama" | "anthropic"
