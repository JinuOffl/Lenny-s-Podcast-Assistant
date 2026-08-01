"""
config.py — centralised settings loaded from .env
All modules import `settings` from here; never call os.environ directly.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Resolve .env — works whether uvicorn runs from backend/ or project root
_here = Path(__file__).resolve().parent          # backend/
_env_files = (
    _here.parent / ".env",   # project root  ← user created it here
    _here / ".env",          # backend/       ← fallback
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,   # allow both field name and alias
    )

    # ── Supabase / Postgres ──────────────────────────────────────────────────
    database_url: str = Field(..., alias="DATABASE_URL")

    # ── Anthropic ────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-5", alias="ANTHROPIC_MODEL")

    # ── Ollama ───────────────────────────────────────────────────────────────
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_chat_model: str = Field(default="llama3.3:8b", alias="OLLAMA_CHAT_MODEL")
    ollama_embed_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBED_MODEL")

    # ── App ──────────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")

    # ── RAG ──────────────────────────────────────────────────────────────────
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    chunk_size: int = Field(default=700, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP")


settings = Settings()
