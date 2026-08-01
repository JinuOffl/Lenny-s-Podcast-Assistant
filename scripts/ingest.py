"""
scripts/ingest.py — Clone transcripts repo, chunk episodes, embed, upsert to Supabase.

Usage:
    cd scripts
    pip install -r ../backend/requirements.txt PyYAML tiktoken httpx psycopg[binary]
    python ingest.py

What it does:
  1. Clones https://github.com/ChatPRD/lennys-podcast-transcripts (shallow)
  2. Reads index files to build a curated list of ~40-80 episodes
  3. Parses each episode's YAML frontmatter + transcript body
  4. Chunks each transcript at ~700 tokens / 100 overlap
  5. Embeds each chunk via Ollama nomic-embed-text
  6. Upserts into Supabase transcript_chunks table

Prerequisites:
  - Ollama running with nomic-embed-text pulled:
      ollama pull nomic-embed-text
  - .env file at project root with DATABASE_URL set
  - pgvector extension enabled in Supabase (run backend/db.py first)
"""

import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

# Force UTF-8 output on Windows (default console is cp1252 which can't print emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from typing import List, Dict, Optional

import psycopg
import yaml

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
REPO_DIR = SCRIPT_DIR / "transcripts_repo"

# Load .env — try project root first, then backend/ (user may have created it there)
from dotenv import load_dotenv
_env_root    = PROJECT_ROOT / ".env"
_env_backend = PROJECT_ROOT / "backend" / ".env"
if _env_root.exists():
    load_dotenv(_env_root)
elif _env_backend.exists():
    load_dotenv(_env_backend)
else:
    print("⚠️  No .env file found — falling back to system environment variables")

DATABASE_URL = os.getenv("DATABASE_URL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# ── Curated episode slugs ─────────────────────────────────────────────────────
# Sourced from index/product-management.md, index/growth-strategy.md,
# index/product-market-fit.md, index/leadership.md
# ~60 high-signal episodes covering the core PM/growth topics.
# Scaling to all 269 = change CURATED_INDEX_FILES to include all index files.

CURATED_INDEX_FILES = [
    "product-management.md",
    "growth-strategy.md",
    "product-market-fit.md",
    "leadership.md",
]

TRANSCRIPTS_REPO_URL = "https://github.com/ChatPRD/lennys-podcast-transcripts"


# ── Step 1: Clone repo ────────────────────────────────────────────────────────

def clone_or_update_repo() -> None:
    if REPO_DIR.exists():
        print("📁 Repo already cloned — pulling latest...")
        subprocess.run(["git", "-C", str(REPO_DIR), "pull", "--ff-only"], check=True)
    else:
        print(f"⬇️  Cloning {TRANSCRIPTS_REPO_URL} ...")
        subprocess.run(
            ["git", "clone", "--depth=1", TRANSCRIPTS_REPO_URL, str(REPO_DIR)],
            check=True,
        )
    print("✅ Repo ready.")


# ── Step 2: Build episode list from index files ───────────────────────────────

def parse_slug_from_md_link(line: str) -> Optional[str]:
    """
    Extract slug from a markdown link like:
      - [Brian Chesky](../episodes/brian-chesky/transcript.md)
    Returns 'brian-chesky' or None.
    """
    match = re.search(r"\.\./episodes/([^/]+)/transcript\.md", line)
    return match.group(1) if match else None


def get_curated_slugs() -> List[str]:
    """
    Read the curated index files and return a deduplicated list of episode slugs.
    """
    slugs: list[str] = []
    seen: set[str] = set()
    index_dir = REPO_DIR / "index"

    for index_file in CURATED_INDEX_FILES:
        path = index_dir / index_file
        if not path.exists():
            print(f"⚠️  Index file not found: {path} — skipping")
            continue

        with open(path, encoding="utf-8") as f:
            for line in f:
                slug = parse_slug_from_md_link(line)
                if slug and slug not in seen:
                    seen.add(slug)
                    slugs.append(slug)

    print(f"📋 Curated episode count: {len(slugs)}")
    return slugs


# ── Step 3: Parse transcript ──────────────────────────────────────────────────

def parse_transcript(slug: str) -> Optional[Dict]:
    """
    Parse YAML frontmatter + transcript body from an episode file.

    Returns a dict with metadata + body text, or None if parse fails.
    """
    transcript_path = REPO_DIR / "episodes" / slug / "transcript.md"
    if not transcript_path.exists():
        print(f"  ⚠️  Transcript not found: {transcript_path}")
        return None

    raw = transcript_path.read_text(encoding="utf-8", errors="replace")

    # Split YAML frontmatter from body
    # Format: starts with ---, ends with ---
    parts = raw.split("---", 2)
    if len(parts) < 3:
        # No frontmatter — treat entire file as body
        return {
            "slug": slug,
            "guest": slug.replace("-", " ").title(),
            "episode_title": slug.replace("-", " ").title(),
            "youtube_url": "",
            "body": raw.strip(),
        }

    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        print(f"  ⚠️  YAML parse error in {slug}: {e}")
        meta = {}

    body = parts[2].strip()

    return {
        "slug": slug,
        "guest": meta.get("guest", slug.replace("-", " ").title()),
        "episode_title": meta.get("title", slug.replace("-", " ").title()),
        "youtube_url": meta.get("youtube_url", ""),
        "body": body,
    }


# ── Step 4: Chunk text ────────────────────────────────────────────────────────
# We use a simple word-count based chunker (fast, no extra deps).
# ~700 words ≈ ~700 tokens for English prose (1:1 rough ratio).
# nomic-embed-text's 8k context means even double this is safe.

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Split text into overlapping chunks by word count.

    chunk_size: target words per chunk
    overlap: words to repeat at the start of the next chunk
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks


# ── Step 5: Embed via Ollama (sync, uses only stdlib urllib) ──────────────────

def get_embedding(text: str) -> List[float]:
    """
    Call Ollama /api/embeddings via urllib (stdlib only — no httpx needed).
    Falls back to zero vector on connection error.
    """
    import urllib.request
    import json as _json

    payload = _json.dumps({"model": OLLAMA_EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = _json.loads(resp.read())
    return data["embedding"]


# ── Step 6: Upsert to Supabase (sync psycopg) ────────────────────────────────

def upsert_chunks(
    episode: Dict,
    chunks: List[str],
    embeddings: List[List[float]],
    conn,
) -> None:
    """
    Delete existing chunks for this episode slug, then insert fresh ones.
    (Simple upsert strategy — avoids duplicate chunks on re-runs.)
    """
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM transcript_chunks WHERE episode_slug = %s",
            (episode["slug"],),
        )
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            cur.execute(
                """
                INSERT INTO transcript_chunks
                    (episode_slug, guest, episode_title, youtube_url, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                """,
                (
                    episode["slug"],
                    episode["guest"],
                    episode["episode_title"],
                    episode["youtube_url"],
                    idx,
                    chunk,
                    str(embedding),
                ),
            )
    conn.commit()


# ── Main pipeline (fully synchronous) ────────────────────────────────────────

def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set. Check your .env file.")
        sys.exit(1)

    # 1. Clone/update repo
    clone_or_update_repo()

    # 2. Get curated episode list
    slugs = get_curated_slugs()

    # 3. Connect to DB (sync psycopg — no event loop issues on Windows)
    print("\nConnecting to database...")
    import psycopg as _psycopg
    conn = _psycopg.connect(DATABASE_URL, autocommit=False)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()

    print(f"Ollama embed model: {OLLAMA_EMBED_MODEL}")
    print("Starting ingest — this will take several minutes...\n")

    total_chunks = 0
    skipped = 0

    for i, slug in enumerate(slugs, 1):
        print(f"[{i}/{len(slugs)}] {slug}")

        # Parse transcript
        episode = parse_transcript(slug)
        if not episode or not episode["body"].strip():
            print(f"  SKIP: empty or missing transcript")
            skipped += 1
            continue

        # Chunk
        chunks = chunk_text(episode["body"])
        print(f"  {len(chunks)} chunks ({len(episode['body'].split())} words)")

        # Embed chunks in parallel — Ollama queues them on GPU
        # max_workers=6: sweet spot for RTX 3050 / single-GPU Ollama
        # (16 workers causes request timeouts; GPU throughput saturates at ~4-8)
        def _embed_single(arg):
            idx, chunk = arg
            try:
                return idx, get_embedding(chunk)
            except Exception as e:
                print(f"  WARNING: embedding failed for chunk {idx}: {e}")
                return idx, [0.0] * 768

        indexed_chunks = list(enumerate(chunks))
        embeddings_map = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            for idx, emb in executor.map(_embed_single, indexed_chunks):
                embeddings_map[idx] = emb

        embeddings = [embeddings_map[i] for i in range(len(chunks))]

        # Upsert to DB
        upsert_chunks(episode, chunks, embeddings, conn)
        total_chunks += len(chunks)
        print(f"  OK — {len(chunks)} chunks stored")

    conn.close()

    print(f"\n{'='*50}")
    print(f"Ingest complete!")
    print(f"  Episodes processed : {len(slugs) - skipped}")
    print(f"  Episodes skipped   : {skipped}")
    print(f"  Total chunks stored: {total_chunks}")


if __name__ == "__main__":
    # No asyncio needed — everything is synchronous now
    main()

