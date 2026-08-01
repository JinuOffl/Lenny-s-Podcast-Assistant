"""
db.py — Postgres connection (psycopg3 + pgvector) and schema bootstrap.

Usage:
    from db import get_conn

    async with get_conn() as conn:
        row = await conn.fetchrow("SELECT 1")
"""
import sys
import asyncio
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from config import settings

# ── Connection pool (created once at startup) ─────────────────────────────────
_pool: AsyncConnectionPool | None = None


async def init_pool() -> None:
    """Call this once during FastAPI lifespan startup."""
    global _pool
    _pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
        open=False,
    )
    await _pool.open()


async def close_pool() -> None:
    """Call this during FastAPI lifespan shutdown."""
    global _pool
    if _pool:
        await _pool.close()


@asynccontextmanager
async def get_conn():
    """Async context manager that yields a psycopg3 connection from the pool."""
    if _pool is None:
        raise RuntimeError("DB pool not initialised — call init_pool() first.")
    async with _pool.connection() as conn:
        conn.row_factory = dict_row
        yield conn


# ── Schema DDL (run once via `python db.py`) ─────────────────────────────────
SCHEMA_SQL = """
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL DEFAULT 'New chat',
    llm_provider TEXT NOT NULL DEFAULT 'ollama',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    skill_used  TEXT,                   -- 'qa' | 'ship30for30' | 'artifact'
    artifact_json JSONB,               -- {"type": "html"|"markdown", "content": "..."}
    sources     JSONB,                 -- [{"guest":..., "episode_title":..., "youtube_url":...}]
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Transcript chunks table (with pgvector embedding column)
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_slug    TEXT NOT NULL,
    guest           TEXT,
    episode_title   TEXT,
    youtube_url     TEXT,
    chunk_index     INT NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(768)        -- nomic-embed-text outputs 768 dims
);

-- IVFFlat index for fast cosine similarity search
-- NOTE: IVFFlat requires data to exist before building; re-run after ingest.
-- If you have < 1000 rows, skip this and use exact search (still fast at this scale).
-- CREATE INDEX IF NOT EXISTS idx_chunks_embedding
--     ON transcript_chunks USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);
"""


if __name__ == "__main__":
    """Run `python db.py` to create all tables in Supabase."""
    import asyncio
    import sys

    # Windows fix: psycopg async requires SelectorEventLoop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def _bootstrap():
        await init_pool()
        async with get_conn() as conn:
            await conn.execute(SCHEMA_SQL)
            print("✅ Schema applied successfully.")
        await close_pool()

    asyncio.run(_bootstrap())
