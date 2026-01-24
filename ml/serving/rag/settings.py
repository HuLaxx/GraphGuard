"""
RAG settings for GraphGuard.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _split_csv(value: str | None, default: List[str]) -> List[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class RagSettings:
    enabled: bool
    index_dir: Path
    default_index: str

    vector_store: str
    embeddings_provider: str
    embeddings_model: str

    chunk_size: int
    chunk_overlap: int

    top_k: int
    score_threshold: float

    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int

    groq_api_key: str | None
    openai_base_url: str | None
    openai_api_key: str | None
    ollama_base_url: str
    pg_dsn: str | None
    pg_table: str

    repo_include_exts: List[str]
    repo_exclude_dirs: List[str]
    repo_max_file_kb: int
    auto_index_enabled: bool
    auto_index_root: Path
    auto_index_background: bool
    auto_index_index: str


_SETTINGS: RagSettings | None = None


def get_rag_settings() -> RagSettings:
    global _SETTINGS
    if _SETTINGS is not None:
        return _SETTINGS

    root_dir = Path(os.getenv("RAG_INDEX_DIR", "data/rag/indexes")).resolve()

    _SETTINGS = RagSettings(
        enabled=_as_bool(os.getenv("RAG_ENABLED"), True),
        index_dir=root_dir,
        default_index=os.getenv("RAG_DEFAULT_INDEX", "graphguard"),
        vector_store=os.getenv("RAG_VECTOR_STORE", "simple"),
        embeddings_provider=os.getenv("RAG_EMBEDDINGS_PROVIDER", "sentence_transformers"),
        embeddings_model=os.getenv("RAG_EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        chunk_size=_as_int(os.getenv("RAG_CHUNK_SIZE"), 800),
        chunk_overlap=_as_int(os.getenv("RAG_CHUNK_OVERLAP"), 120),
        top_k=_as_int(os.getenv("RAG_TOP_K"), 6),
        score_threshold=_as_float(os.getenv("RAG_SCORE_THRESHOLD"), 0.2),
        llm_provider=os.getenv("RAG_LLM_PROVIDER", "groq"),
        llm_model=os.getenv("RAG_LLM_MODEL", "llama-3.3-70b-versatile"),
        llm_temperature=_as_float(os.getenv("RAG_LLM_TEMPERATURE"), 0.2),
        llm_max_tokens=_as_int(os.getenv("RAG_LLM_MAX_TOKENS"), 512),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        openai_base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
        openai_api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        pg_dsn=os.getenv("RAG_PG_DSN") or os.getenv("SUPABASE_DB_URL"),
        pg_table=os.getenv("RAG_PG_TABLE", "rag_chunks"),
        repo_include_exts=_split_csv(
            os.getenv("RAG_REPO_INCLUDE_EXTS"),
            [
                ".md", ".txt", ".py", ".ts", ".tsx", ".js", ".json",
                ".yml", ".yaml", ".toml", ".graphql", ".sql", ".sh", ".ps1"
            ],
        ),
        repo_exclude_dirs=_split_csv(
            os.getenv("RAG_REPO_EXCLUDE_DIRS"),
            [
                ".git", "node_modules", "__pycache__", "mlruns", "data",
                "models", "dist", "build", ".next", ".venv", "venv"
            ],
        ),
        repo_max_file_kb=_as_int(os.getenv("RAG_REPO_MAX_FILE_KB"), 512),
        auto_index_enabled=_as_bool(os.getenv("RAG_AUTO_INDEX_ON_STARTUP"), False),
        auto_index_root=Path(os.getenv("RAG_AUTO_INDEX_ROOT", ".")),
        auto_index_background=_as_bool(os.getenv("RAG_AUTO_INDEX_BACKGROUND"), True),
        auto_index_index=os.getenv("RAG_AUTO_INDEX_INDEX", os.getenv("RAG_DEFAULT_INDEX", "graphguard")),
    )

    return _SETTINGS
